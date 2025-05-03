from .distributed_crawler import DistributedCrawler
from spiders.smithery_parser import SmitheryParser
import os
import json
from typing import Dict, Any, AsyncIterator
from pathlib import Path

class SmitheryCrawler(DistributedCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.parser = SmitheryParser()
        self.output_dir = self.base_dir / "smithery"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = os.getenv('SMITHERY_API_KEY')
        if not self.api_key:
            raise ValueError("SMITHERY_API_KEY environment variable is not set")

    def _normalize_path(self, path):
        """规范化路径，移除特殊字符"""
        # 替换特殊字符为下划线
        normalized = path.replace('@', '_').replace('/', '_').replace('\\', '_')
        return normalized

    async def _fetch_page(self, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取Smithery API的页面数据
        Args:
            site_config: 站点配置
        Returns:
            API响应数据
        """
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json'
        }
        
        params = {
            'page': site_config.get('current_page', 1),
            'pageSize': site_config.get('page_size', 100)  # 使用配置中的pageSize
        }
        
        if 'q' in site_config:
            params['q'] = site_config['q']
            
        print(f"请求参数: {params}")
        response = self.session.get(
            'https://registry.smithery.ai/servers',
            headers=headers,
            params=params
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Smithery API: {response.status_code}")
            
        data = response.json()
        print(f"Smithery API响应状态码: {response.status_code}")
        print(f"Smithery API响应头: {dict(response.headers)}")
        print(f"Smithery API响应内容: {json.dumps(data, indent=2)[:1000]}...")  # 打印更多响应内容
        
        # 保存服务器数据
        for server in data.get('servers', []):
            # 规范化路径
            normalized_path = self._normalize_path(server.get('qualifiedName', server.get('name', 'unknown')))
            server_dir = self.output_dir / normalized_path
            server_dir.mkdir(parents=True, exist_ok=True)
            
            # 安全地获取字段值
            metadata = {
                'qualified_name': server.get('qualifiedName', ''),
                'display_name': server.get('displayName', ''),
                'description': server.get('description', ''),
                'homepage': server.get('homepage', ''),
                'use_count': server.get('useCount', 0),
                'is_deployed': server.get('isDeployed', False),
                'created_at': server.get('createdAt', ''),
                'source': 'smithery'
            }
            
            metadata_path = server_dir / f"{normalized_path}.smithery.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"已保存服务器元数据: {metadata_path}")
        
        return data

    def _create_auth(self, site_config: Dict[str, Any]) -> Dict[str, str]:
        """创建Smithery API认证信息
        Args:
            site_config: 站点配置
        Returns:
            认证信息字典
        """
        return {
            'Authorization': f'Bearer {self.api_key}'
        }

    async def crawl_site(self, site_config) -> AsyncIterator[Dict[str, Any]]:
        """异步迭代器实现，用于分页获取数据
        Args:
            site_config: 站点配置
        Returns:
            AsyncIterator[Dict[str, Any]]: 异步迭代器，每次迭代返回一页数据
        """
        try:
            page_num = 1
            total_servers = 0
            total_pages = None
            
            while True:
                print(f"正在抓取第 {page_num} 页...")
                site_config['current_page'] = page_num
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("没有获取到数据，可能已达到最后一页")
                    break
                
                # 获取分页信息
                if total_pages is None:
                    total_pages = data.get('pagination', {}).get('totalPages', 1)
                    print(f"总页数: {total_pages}")
                
                # 处理服务器数据
                servers = data.get('servers', [])
                if not servers:  # 如果返回的服务器列表为空，说明已经到达最后一页
                    print("获取到空列表，已到达最后一页")
                    break
                    
                total_servers += len(servers)
                print(f"本页获取到 {len(servers)} 条服务器数据，总计 {total_servers} 条")
                
                yield data
                
                # 检查是否达到最大页数或总页数
                if page_num >= total_pages or page_num >= site_config.get('pagination', {}).get('max_pages', 100):
                    print(f"已达到最大页数 {page_num}，停止抓取")
                    break
                    
                page_num += 1
                
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
            raise 