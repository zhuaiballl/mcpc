from .distributed_crawler import DistributedCrawler
import json
import os
from pathlib import Path
from typing import Dict, Any, AsyncIterator

class PulseCrawler(DistributedCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.output_dir = self.base_dir / "pulse"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.pulsemcp.com/v0beta"
        self.session.headers.update({
            'User-Agent': 'MCPCrawler/1.0 (https://github.com/yourusername/mcpc)'
        })

    def _normalize_path(self, path):
        """规范化路径，移除特殊字符"""
        # 替换特殊字符为下划线
        normalized = path.replace('@', '_').replace('/', '_').replace('\\', '_')
        return normalized

    async def _fetch_page(self, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取Pulse API的页面数据
        Args:
            site_config: 站点配置
        Returns:
            API响应数据
        """
        url = site_config.get('next_url', f"{self.base_url}/servers")
        params = {
            'count_per_page': 100,  # 每页获取100条数据
        }
        
        if 'query' in site_config:
            params['query'] = site_config['query']
            
        print(f"请求URL: {url}")
        print(f"请求参数: {params}")
        response = self.session.get(url, params=params)
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Pulse API: {response.status_code}")
            
        data = response.json()
        print(f"Pulse API响应状态码: {response.status_code}")
        print(f"Pulse API响应内容: {json.dumps(data, indent=2)[:1000]}...")
        
        return data

    async def crawl_site(self, site_config) -> AsyncIterator[Dict[str, Any]]:
        """异步迭代器实现，用于分页获取数据
        Args:
            site_config: 站点配置
        Returns:
            AsyncIterator[Dict[str, Any]]: 异步迭代器，每次迭代返回一页数据
        """
        try:
            total_servers = 0
            
            while True:
                print(f"正在抓取数据...")
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("没有获取到数据，可能已达到最后一页")
                    break
                
                # 处理服务器数据
                servers = data.get('servers', [])
                if not servers:  # 如果返回的服务器列表为空，说明已经到达最后一页
                    print("获取到空列表，已到达最后一页")
                    break
                    
                total_servers += len(servers)
                print(f"本页获取到 {len(servers)} 条服务器数据，总计 {total_servers} 条")
                
                # 处理每个服务器的数据
                for server in servers:
                    try:
                        # 规范化路径
                        normalized_path = self._normalize_path(server.get('name', 'unknown'))
                        server_dir = self.output_dir / normalized_path
                        server_dir.mkdir(parents=True, exist_ok=True)
                        
                        # 保存服务器元数据
                        metadata = {
                            'name': server.get('name', ''),
                            'url': server.get('url', ''),
                            'external_url': server.get('external_url', ''),
                            'short_description': server.get('short_description', ''),
                            'source_code_url': server.get('source_code_url', ''),
                            'github_stars': server.get('github_stars', 0),
                            'package_registry': server.get('package_registry', ''),
                            'package_name': server.get('package_name', ''),
                            'package_download_count': server.get('package_download_count', 0),
                            'ai_generated_description': server.get('EXPERIMENTAL_ai_generated_description', ''),
                            'source': 'pulse'
                        }
                        
                        metadata_path = server_dir / f"{normalized_path}.pulse.json"
                        with open(metadata_path, 'w') as f:
                            json.dump(metadata, f, indent=2)
                        print(f"已保存服务器元数据: {metadata_path}")
                        
                    except Exception as e:
                        print(f"处理服务器 {server.get('name', 'unknown')} 时发生错误: {str(e)}")
                        continue
                
                yield data
                
                # 检查是否有下一页
                next_url = data.get('next')
                if not next_url:
                    print("没有下一页数据，停止抓取")
                    break
                    
                # 更新下一页URL
                site_config['next_url'] = next_url
                
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
            raise

    async def run(self):
        """运行爬虫的主方法"""
        try:
            # 确保配置存在
            if not self.configs:
                raise ValueError("No configuration found")
            
            # 获取第一个配置（pulse的配置）
            site_config = self.configs[0]
            
            # 创建结果列表
            results = []
            
            # 使用异步迭代器处理数据
            async for result in self.crawl_site(site_config):
                print(f"已抓取到 {len(result.get('servers', []))} 条pulse服务器数据")
                results.extend(result.get('servers', []))
            
            # 保存所有服务器的元数据
            metadata_path = self.base_dir / "pulse" / "all_servers.pulse.json"
            with open(metadata_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"pulse数据已保存至 {os.path.abspath(metadata_path)}")
            
        except Exception as e:
            print(f"运行爬虫时发生错误: {str(e)}")
            raise 