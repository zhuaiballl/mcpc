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
        """Normalize path by removing special characters"""
        # Replace special characters with underscore
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
        """Download GitHub repo contents to local directory"""
        if not self.github_token:
            print("GITHUB_TOKEN not set, cannot download GitHub repo")
            return
        owner, repo = self.extract_github_repo_info(repo_url)
        if not owner or not repo:
            print(f"Invalid GitHub repo URL, skipped: {repo_url}")
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
            print(f"Downloaded GitHub repo: {repo_url} to {dest_dir}")
        except Exception as e:
            print(f"Failed to download GitHub repo {repo_url}: {e}")

    async def _fetch_page(self, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch page data from Pulse API
        Args:
            site_config: Site configuration
        Returns:
            API response data
        """
        params = {
            'count_per_page': 100,
            'offset': site_config.get('offset', 0)
        }
        if 'query' in site_config:
            params['query'] = site_config['query']
        print(f"Request params: {params}")
        response = self.session.get(
            f"{self.base_url}/servers",
            params=params
        )
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Pulse API: {response.status_code}")
        data = response.json()
        print(f"Pulse API response status code: {response.status_code}")
        print(f"Pulse API response content: {json.dumps(data, indent=2)[:1000]}...")
        return data

    async def crawl_site(self, site_config) -> AsyncIterator[Dict[str, Any]]:
        """Asynchronous iterator implementation for pagination
        Args:
            site_config: Site configuration
        Returns:
            AsyncIterator[Dict[str, Any]]: Asynchronous iterator, each iteration returns a page of data
        """
        try:
            offset = 0
            total_servers = 0
            all_servers = []  # Collect all server data
            
            while True:
                print(f"Crawling with offset {offset}...")
                site_config['offset'] = offset
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("No data received, may be the last page")
                    break
                
                # Process server data
                servers = data.get('servers', [])
                if not servers:  # If the returned server list is empty, it means we have reached the last page
                    print("Empty server list received, may be the last page")
                    break
                    
                total_servers += len(servers)
                print(f"Received {len(servers)} servers, total {total_servers} so far")
                
                # Process each server's data
                for server in servers:
                    try:
                        # Save server metadata
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
                            'categories': server.get('categories', []),
                            'tags': server.get('tags', []),
                            'source': 'pulse',
                            'crawled_at': datetime.now().isoformat()
                        }
                        
                        all_servers.append(metadata)
                        print(f"Collected metadata for server: {server.get('name', 'unknown')}")
                        
                    except Exception as e:
                        print(f"Error processing server {server.get('name', 'unknown')}: {str(e)}")
                        continue
                
                yield data
                
                # Check if there is next page
                next_url = data.get('next')
                if not next_url:
                    print("No next page data, stop crawling")
                    break
                    
                # Update next page URL
                site_config['next_url'] = next_url
                
                offset += len(servers)
                
            # Save all servers' summary information
            summary_path = self.output_dir / "pulse.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'source': 'pulse',
                    'total_count': len(all_servers),
                    'crawled_at': datetime.now().isoformat(),
                    'servers': all_servers
                }, f, indent=2)
            print(f"All servers summary saved to: {summary_path}")
                
        except Exception as e:
            print(f"Error during pulse crawling: {str(e)}")
            raise

    async def run(self):
        """Run the pulse crawler's main method"""
        try:
            # Ensure configuration exists
            if not self.configs:
                raise ValueError("No configuration found")
            
            # Get the first configuration (pulse's configuration)
            site_config = self.configs[0]
            
            # Use asynchronous iterator to process data
            async for result in self.crawl_site(site_config):
                print(f"Collected {len(result.get('servers', []))} pulse server records")
            
            print("Pulse data crawling completed")
            
        except Exception as e:
            print(f"Error running pulse crawler: {str(e)}")
            raise 