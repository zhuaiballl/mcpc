import re
from .distributed_crawler import DistributedCrawler
from spiders.smithery_parser import SmitheryParser
import os
import json
from typing import Dict, Any, AsyncIterator
from pathlib import Path
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import time

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

    def _extract_github_url(self, server_data: Dict[str, Any]) -> str:
        """从server数据中提取GitHub URL
        Args:
            server_data: 服务器数据
        Returns:
            str: GitHub URL或空字符串
        """
        # 从detail_url网页中提取GitHub URL
        detail_url = server_data.get('detail_url', '')
        if detail_url:
            try:
                # 添加延迟避免请求过快
                time.sleep(0.5)
                
                response = requests.get(detail_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 查找GitHub链接
                    github_links = soup.find_all('a', href=re.compile(r'github\.com'))
                    for link in github_links:
                        href = link.get('href', '')
                        if 'github.com' in href:
                            # 提取GitHub URL
                            github_match = re.search(r'https://github\.com/([^/\s\'\"\)]+/[^/\s\'\"\)]+)', href)
                            if github_match:
                                return f"https://github.com/{github_match.group(1)}"
                                    
            except Exception as e:
                print(f"从网页提取GitHub URL失败: {e}")
        
        return ""

    async def _fetch_page(self, site_config):
        """重写_fetch_page方法以适配smithery API"""
        try:
            page = site_config.get('current_page', 1)
            page_size = site_config.get('page_size', 100)
            
            url = f"https://registry.smithery.ai/servers?page={page}&pageSize={page_size}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data
        except Exception as e:
            from .exceptions import CrawlExhausted
            raise CrawlExhausted(f"抓取失败: {str(e)}")

    async def crawl_site(self, site_config):
        """重写crawl_site方法以适配smithery数据结构"""
        try:
            page_num = 1
            all_servers = []
            
            while True:
                print(f"正在抓取第 {page_num} 页...")
                site_config['current_page'] = page_num
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("没有获取到数据，可能已达到最后一页")
                    break
                
                servers = data.get('servers', [])
                if not servers:
                    print("获取到空列表，已到达最后一页")
                    break
                
                print(f"本页获取到 {len(servers)} 条服务器数据")
                
                for server in servers:
                    try:
                        # 获取服务器详细信息
                        server_details = await self._fetch_server_details(server['qualifiedName'])
                        
                        # 构建标准化的数据
                        normalized_data = {
                            'name': server.get('displayName', ''),
                            'description': server.get('description', ''),
                            'detail_url': server.get('homepage', ''),  # 使用API返回的homepage字段
                            'github_url': '',  # 先设为空，稍后填充
                            'categories': [],  # smithery没有明确的分类
                            'source': 'smithery',
                            'raw_data': server_details
                        }
                        
                        # 提取GitHub URL
                        github_url = self._extract_github_url(normalized_data)
                        normalized_data['github_url'] = github_url
                        
                        all_servers.append(normalized_data)
                        print(f"已收集服务器元数据: {server['qualifiedName']} (GitHub: {github_url if github_url else 'N/A'})")
                        
                    except Exception as e:
                        print(f"获取服务器 {server['qualifiedName']} 详细信息时发生错误: {str(e)}")
                        continue
                
                yield data
                
                # 如果返回的servers数量少于page_size，说明已经到最后一页
                if len(servers) < site_config.get('page_size', 100):
                    break
                    
                page_num += 1
            
            # 保存所有服务器的汇总信息
            output_file = self.output_dir / "smithery.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_servers, f, ensure_ascii=False, indent=2)
            
            print(f"数据已保存到: {output_file}")
            
            # 统计GitHub URL提取情况
            github_count = sum(1 for server in all_servers if server['github_url'])
            print(f"成功提取GitHub URL的servers: {github_count}/{len(all_servers)}")
                
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
            raise

    async def _fetch_server_details(self, qualified_name: str) -> Dict[str, Any]:
        """获取服务器的详细信息
        Args:
            qualified_name: 服务器的唯一标识符
        Returns:
            Dict[str, Any]: 服务器的详细信息
        """
        try:
            url = f"https://registry.smithery.ai/servers/{qualified_name}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            print(f"获取服务器详细信息失败: {e}")
            return {}

    async def run(self):
        """运行爬虫的主方法"""
        try:
            # 确保配置存在
            if not self.configs:
                raise ValueError("No configuration found")
            
            # 获取第一个配置（smithery的配置）
            site_config = self.configs[0]
            
            # 运行爬虫
            async for _ in self.crawl_site(site_config):
                pass
                
        except Exception as e:
            print(f"运行过程中发生错误: {str(e)}")
            raise 