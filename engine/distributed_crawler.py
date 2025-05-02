import json
import os
import time
from pathlib import Path
from requests_cache import CachedSession
from spiders import parser_registry
from .exceptions import CrawlExhausted

class DistributedCrawler:
    def __init__(self, config_path):
        self.load_config(config_path)
        self.session = CachedSession()
        # 创建基础输出目录
        self.base_dir = Path("mcp_servers")
        self.base_dir.mkdir(exist_ok=True)
        # 添加一个集合来跟踪已处理的目录
        self.processed_dirs = set()
        # 添加一个字典来跟踪目录的父子关系
        self.dir_parents = {}
        # 添加一个集合来跟踪规范化的路径
        self.normalized_paths = set()
        # 添加日志文件
        self.log_file = self.base_dir / "crawler.log"
        self._setup_logging()
    
    def _get_output_dir(self, site_config):
        """根据站点配置获取对应的输出目录"""
        # 从站点名称中提取数据源名称
        source_name = site_config['name'].split('_')[0]
        output_dir = self.base_dir / source_name
        output_dir.mkdir(exist_ok=True)
        return output_dir
    
    async def crawl_site(self, site_config):
        """抓取单个站点
        Args:
            site_config: 站点配置
        Returns:
            AsyncIterator[Dict[str, Any]]: 异步迭代器，每次迭代返回一页数据
        """
        try:
            # 获取输出目录
            output_dir = self._get_output_dir(site_config)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 获取认证信息
            auth = self._create_auth(site_config)
            if auth:
                self.session.headers.update(auth)
            
            page_num = 1
            while True:
                print(f"正在抓取第 {page_num} 页...")
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("没有获取到数据，可能已达到最后一页")
                    break
                    
                # 处理数据
                for item in data:
                    # 获取服务器路径
                    path = item.get('path', '')
                    if not path:
                        continue
                        
                    # 规范化路径
                    normalized_path = self._normalize_path(path)
                        
                    # 创建服务器目录
                    server_dir = output_dir / normalized_path
                    server_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 保存服务器元数据
                    metadata = {
                        'name': item.get('name', ''),
                        'path': normalized_path,
                        'sha': item.get('sha', ''),
                        'url': item.get('url', ''),
                        'source': 'modelcontextprotocol'
                    }
                    
                    metadata_path = server_dir / f"{item['name']}.json"
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    print(f"已保存元数据: {metadata_path}")
                    
                    # 获取服务器目录内容
                    if 'url' in item:
                        try:
                            # 使用 _fetch_page_with_retry 获取目录内容
                            dir_config = site_config.copy()
                            dir_config['url'] = item['url']
                            dir_data = await self._fetch_page_with_retry(dir_config)
                            
                            if dir_data:
                                for file in dir_data:
                                    if file['type'] == 'file':
                                        # 直接获取文件内容
                                        file_response = self.session.get(file['download_url'])
                                        if file_response.status_code == 200:
                                            file_path = server_dir / file['name']
                                            with open(file_path, 'w') as f:
                                                f.write(file_response.text)
                                            print(f"已保存文件: {file_path}")
                        except Exception as e:
                            print(f"获取目录内容时发生错误: {str(e)}")
                            continue
                
                yield data
                
                # 检查是否达到最大页数
                if page_num >= site_config.get('pagination', {}).get('max_pages', 1):
                    break
                    
                page_num += 1
                
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
            raise
    
    def _create_parser(self, parser_type):
        """工厂模式创建解析器实例"""
        return parser_registry.get(parser_type)
    
    def load_config(self, path):
        """动态加载YAML配置文件"""
        import yaml
        from pathlib import Path
        
        try:
            config_path = Path(__file__).parent.parent / path
            with open(config_path, 'r') as f:
                self.configs = yaml.safe_load(f)
        except FileNotFoundError:
            raise RuntimeError(f"配置文件 {path} 未找到")
        except yaml.YAMLError as e:
            raise RuntimeError(f"配置文件格式错误: {str(e)}")
    
    async def _fetch_page_with_retry(self, site_config):
        max_retries = site_config.get('error_handling', {}).get('max_retries', 3)
        retry_delay = site_config.get('error_handling', {}).get('retry_delay', 5)
        
        for attempt in range(max_retries):
            try:
                return await self._fetch_page(site_config)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"第 {attempt + 1} 次尝试失败，{retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    raise
    
    async def _fetch_page(self, site_config):
        try:
            headers = site_config.get('headers', {}).copy()
            auth_token = os.getenv(site_config['auth']['token'])
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            response = self.session.get(
                site_config['url'],
                headers=headers
            )
            
            print(f"API响应状态码: {response.status_code}")
            print(f"API响应内容: {response.text[:200]}...")
            
            if response.status_code == 403:
                print("可能遇到GitHub API速率限制，请检查GitHub Token是否正确设置")
                raise CrawlExhausted("GitHub API速率限制")
            
            response.raise_for_status()
            
            data = response.json()
            if not data:
                print("API返回空数据")
                return None
            
            return data
            
        except Exception as e:
            raise CrawlExhausted(f"抓取失败: {str(e)}")
    
    def _create_auth(self, site_config):
        if site_config.get('auth', {}).get('type') == 'bearer_token':
            from requests.auth import HTTPBearerAuth
            return HTTPBearerAuth(os.getenv(site_config['auth']['token']))
        return None
    
    def _normalize_path(self, path):
        """规范化路径，移除src前缀
        Args:
            path: 原始路径
        Returns:
            str: 规范化后的路径
        """
        # 移除src前缀
        if path.startswith('src/'):
            return path[4:]
        return path
    
    def _setup_logging(self):
        """设置日志记录"""
        import logging
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def _log_duplicate_directory(self, path, normalized_path):
        """记录重复目录的信息"""
        self.logger.warning(f"发现重复目录: 原始路径={path}, 规范化路径={normalized_path}")
        self.logger.info(f"已处理的目录: {sorted(self.processed_dirs)}")
        self.logger.info(f"目录关系: {json.dumps(self.dir_parents, indent=2)}") 