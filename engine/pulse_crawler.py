from .distributed_crawler import DistributedCrawler
import json
import os
from pathlib import Path
from typing import Dict, Any, AsyncIterator
import requests
import re
from urllib.parse import urlparse
from datetime import datetime

proxies = {
    "http": "socks5h://127.0.0.1:1060",
    "https": "socks5h://127.0.0.1:1060"
}

class PulseCrawler(DistributedCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.output_dir = self.base_dir / "pulse"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://api.pulsemcp.com/v0beta"
        self.session.headers.update({
            'User-Agent': 'MCPCrawler/1.0 (https://github.com/yourusername/mcpc)'
        })
        self.github_token = os.getenv('GITHUB_TOKEN')

    def _normalize_path(self, path):
        """规范化路径，移除特殊字符"""
        # 替换特殊字符为下划线
        normalized = path.replace('@', '_').replace('/', '_').replace('\\', '_')
        return normalized

    def extract_github_repo_info(self, url):
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None, None
        m = re.match(r'^/([^/]+)/([^/]+)', parsed.path)
        if m:
            owner, repo = m.group(1), m.group(2)
            repo = repo[:-4] if repo.endswith('.git') else repo
            return owner, repo
        return None, None

    def _download_github_repo(self, repo_url: str, dest_dir: Path):
        if not self.github_token:
            print("未设置 GITHUB_TOKEN，无法抓取 GitHub repo")
            return
        owner, repo = self.extract_github_repo_info(repo_url)
        if not owner or not repo:
            print(f"链接不是有效的GitHub仓库链接，已跳过: {repo_url}")
            return
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
        headers = {'Authorization': f'token {self.github_token}'}
        def download_dir(api_url, local_dir):
            resp = requests.get(api_url, headers=headers, timeout=30, proxies=proxies)
            if resp.status_code == 404:
                print(f"repo 404: {api_url}")
                return
            resp.raise_for_status()
            for item in resp.json():
                if item['type'] == 'file':
                    file_resp = requests.get(item['download_url'], headers=headers, timeout=30, proxies=proxies)
                    file_resp.raise_for_status()
                    file_path = os.path.join(local_dir, item['name'])
                    with open(file_path, 'wb') as f:
                        f.write(file_resp.content)
                elif item['type'] == 'dir':
                    sub_dir = os.path.join(local_dir, item['name'])
                    os.makedirs(sub_dir, exist_ok=True)
                    download_dir(item['url'], sub_dir)
        os.makedirs(dest_dir, exist_ok=True)
        try:
            download_dir(api_url, str(dest_dir))
            print(f"已抓取 GitHub repo: {repo_url} 到 {dest_dir}")
        except Exception as e:
            print(f"抓取 GitHub repo {repo_url} 失败: {e}")

    async def _fetch_page(self, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """获取Pulse API的页面数据
        Args:
            site_config: 站点配置
        Returns:
            API响应数据
        """
        params = {
            'count_per_page': 100,
            'offset': site_config.get('offset', 0)
        }
        if 'query' in site_config:
            params['query'] = site_config['query']
        print(f"请求参数: {params}")
        response = self.session.get(
            f"{self.base_url}/servers",
            params=params
        )
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
            offset = 0
            total_servers = 0
            all_servers = []  # 收集所有服务器数据
            
            while True:
                print(f"正在抓取偏移量 {offset}...")
                site_config['offset'] = offset
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
                            'source': 'pulse',
                            'crawled_at': datetime.now().isoformat()
                        }
                        
                        all_servers.append(metadata)
                        print(f"已收集服务器元数据: {server.get('name', 'unknown')}")
                        
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
                
                offset += len(servers)
            
            # 保存所有服务器的汇总信息
            summary_path = self.output_dir / "pulse.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'source': 'pulse',
                    'total_count': len(all_servers),
                    'crawled_at': datetime.now().isoformat(),
                    'servers': all_servers
                }, f, indent=2)
            print(f"已保存所有服务器汇总信息: {summary_path}")
                
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
            
            # 使用异步迭代器处理数据
            async for result in self.crawl_site(site_config):
                print(f"已抓取到 {len(result.get('servers', []))} 条pulse服务器数据")
            
            print("pulse数据抓取完成")
            
        except Exception as e:
            print(f"运行爬虫时发生错误: {str(e)}")
            raise 