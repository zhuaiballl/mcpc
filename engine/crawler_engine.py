import json
import os
import time
from pathlib import Path
from requests_cache import CachedSession  # 新增导入语句
from spiders import parser_registry  # 新增导入
from .exceptions import CrawlExhausted  # 修正异常导入

class DistributedCrawler:
    def __init__(self, config_path):
        self.load_config(config_path)
        self.session = CachedSession()  # 现在可以正确调用
        self.output_dir = Path("mcp_servers_modelcontextprotocol_io")  # 修改输出目录名称
        self.output_dir.mkdir(exist_ok=True)
        # 添加一个集合来跟踪已处理的目录
        self.processed_dirs = set()
        # 添加一个字典来跟踪目录的父子关系
        self.dir_parents = {}
        # 添加一个集合来跟踪规范化的路径
        self.normalized_paths = set()
        # 添加日志文件
        self.log_file = self.output_dir / "crawler.log"
        self._setup_logging()
    
    async def crawl_site(self, site_config):
        try:
            page_num = 1
            while True:
                print(f"正在抓取第 {page_num} 页...")  # 添加进度输出
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("没有获取到数据，可能已达到最后一页")
                    break
                yield data
                # 添加分页终止条件判断
                if page_num >= site_config.get('pagination', {}).get('max_pages', 1):
                    break
                page_num +=1
        except CrawlExhausted as e:
            print(f"抓取结束: {str(e)}")
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
    
    
    def _create_parser(self, parser_type):
        # 工厂模式创建解析器实例
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
                
            # 直接处理API返回的数据，不再使用解析器
            items = []
            for item in data:
                if isinstance(item, dict):
                    items.append({
                        'type': 'file' if item.get('type') == 'file' else 'dir',
                        'name': item.get('name'),
                        'path': item.get('path'),
                        'download_url': item.get('download_url'),
                        'url': item.get('url'),
                        'size': item.get('size', 0)
                    })
            
            print(f"解析到的项目数量: {len(items)}")
            for item in items:
                print(f"项目类型: {item.get('type')}, 名称: {item.get('name')}, 路径: {item.get('path')}")
            
            # 处理目录和文件
            servers = []
            current_dir_files = []
            
            # 获取当前目录路径
            current_path = site_config.get('current_path', '')
            if not current_path:
                current_path = site_config['url'].split('/contents/')[-1].split('?')[0]
            
            # 处理所有项目
            for item in items:
                # 使用原始路径并规范化
                item_path = item['path']
                normalized_path = self._normalize_path(item_path)
                
                # 获取父目录路径
                parent_path = str(Path(normalized_path).parent)
                if parent_path == '.':
                    parent_path = ''
                
                # 检查路径是否已处理
                if normalized_path in self.processed_dirs:
                    print(f"路径 {normalized_path} 已经处理过，跳过")
                    continue
                self.processed_dirs.add(normalized_path)
                
                if item.get('type') == 'file':
                    # 处理文件
                    file_path = self.output_dir / normalized_path
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        print(f"正在获取文件 {item['name']} 的内容...")
                        content_response = self.session.get(
                            item['download_url'],
                            headers=headers
                        )
                        content_response.raise_for_status()
                        content = content_response.text
                        print(f"文件 {item['name']} 的内容长度: {len(content)}")
                        with open(file_path, 'w') as f:
                            f.write(content)
                        current_dir_files.append({
                            'name': item['name'],
                            'path': normalized_path,
                            'size': item.get('size', 0)
                        })
                        print(f"已保存文件: {file_path}")
                    except Exception as e:
                        print(f"获取文件 {item['name']} 内容失败: {str(e)}")
                elif item.get('type') == 'dir':
                    # 处理目录
                    print(f"正在获取目录 {normalized_path} 的内容...")
                    dir_config = site_config.copy()
                    dir_config['url'] = item['url']
                    dir_config['current_path'] = item_path
                    
                    # 记录目录的父子关系
                    self.dir_parents[normalized_path] = parent_path
                    
                    dir_items = await self._fetch_page(dir_config)
                    
                    # 创建服务器目录
                    server_dir = self.output_dir / normalized_path
                    server_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 保存文件内容并收集文件信息
                    files = []
                    if dir_items:
                        for file_item in dir_items:
                            if file_item.get('type') == 'file':
                                files.append({
                                    'name': file_item['name'],
                                    'path': self._normalize_path(file_item['path']),
                                    'size': file_item.get('size', 0)
                                })
                    
                    # 创建目录的元数据
                    metadata = {
                        'name': item['name'],
                        'path': normalized_path,
                        'url': f"https://github.com/modelcontextprotocol/servers/tree/main/src/{item_path}",
                        'files': files,
                        'parent_directory': parent_path if parent_path else None,
                        'subdirectories': [
                            child for child, parent in self.dir_parents.items()
                            if parent == normalized_path
                        ],
                        'type': 'directory',
                        'total_files': len(files),
                        'total_size': sum(f.get('size', 0) for f in files),
                        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 保存目录的元数据
                    metadata_path = server_dir / f"{item['name']}.modelcontextprotocol.io.json"
                    metadata_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(metadata_path, 'w') as f:
                        json.dump(metadata, f, indent=2)
                    print(f"已保存元数据: {metadata_path}")
                    
                    servers.append(metadata)
            
            # 创建当前目录的元数据
            if current_dir_files:
                current_dir_name = current_path.split('/')[-1]
                normalized_current_path = self._normalize_path(current_path)
                metadata = {
                    'name': current_dir_name,
                    'path': normalized_current_path,
                    'url': f"https://github.com/modelcontextprotocol/servers/tree/main/src/{current_path}",
                    'files': current_dir_files,
                    'parent_directory': str(Path(normalized_current_path).parent) if normalized_current_path else None,
                    'subdirectories': [
                        child for child, parent in self.dir_parents.items()
                        if parent == normalized_current_path
                    ],
                    'type': 'directory',
                    'total_files': len(current_dir_files),
                    'total_size': sum(f.get('size', 0) for f in current_dir_files),
                    'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                metadata_path = self.output_dir / normalized_current_path / f"{current_dir_name}.modelcontextprotocol.io.json"
                metadata_path.parent.mkdir(parents=True, exist_ok=True)
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                print(f"已保存当前目录元数据: {metadata_path}")
            
            return items  # 返回所有项目，包括文件和目录
            
        except Exception as e:
            raise CrawlExhausted(f"抓取失败: {str(e)}")
    
    
    def _create_auth(self, site_config):
        if site_config.get('auth', {}).get('type') == 'bearer_token':
            from requests.auth import HTTPBearerAuth
            return HTTPBearerAuth(os.getenv(site_config['auth']['token']))
        return None

    def _normalize_path(self, path):
        """规范化路径，移除嵌套的src目录"""
        parts = path.split('/')
        # 如果路径以src开头，移除src前缀
        if parts[0] == 'src':
            return '/'.join(parts[1:])
        # 否则，保持原始路径
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

# 将以下代码移到类定义外部（文件最末尾）
if __name__ == "__main__":
    import asyncio
    
    crawler = DistributedCrawler("config/sites_config.yaml")
    loop = asyncio.get_event_loop()
    
    async def run():
        all_results = []
        async for result in crawler.crawl_site(crawler.configs[0]):
            print(f"已抓取到 {len(result)} 条服务器数据")
            all_results.extend(result)
        
        # 保存所有服务器的元数据
        metadata_path = crawler.output_dir / "all_servers.modelcontextprotocol.io.json"
        with open(metadata_path, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"数据已保存至 {os.path.abspath(metadata_path)}")
    
    loop.run_until_complete(run())