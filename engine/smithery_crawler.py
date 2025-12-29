import re
from .distributed_crawler import DistributedCrawler
from spiders.smithery_parser import SmitheryParser
from .categories_manager import CategoriesManager
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
        self.categories_manager = CategoriesManager(self.base_dir)

    def _normalize_path(self, path):
        """Normalize path by removing special characters"""
        # Replace special characters with underscores
        normalized = path.replace('@', '_').replace('/', '_').replace('\\', '_')
        return normalized

    def _extract_github_url(self, server_data: Dict[str, Any]) -> str:
        """Extract GitHub URL from server data
        Args:
            server_data: Server data dictionary
        Returns:
            str: GitHub URL or empty string
        """
        # Extract GitHub URL from detail_url webpage
        detail_url = server_data.get('detail_url', '')
        if detail_url:
            try:
                # Add a delay to avoid too many requests
                time.sleep(0.5)
                
                response = requests.get(detail_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find GitHub links
                    github_links = soup.find_all('a', href=re.compile(r'github\.com'))
                    for link in github_links:
                        href = link.get('href', '')
                        if 'github.com' in href:
                            # Extract GitHub URL from href
                            github_match = re.search(r'https://github\.com/([^/\s\'\"\)]+/[^/\s\'\"\)]+)', href)
                            if github_match:
                                return f"https://github.com/{github_match.group(1)}"
                                    
            except Exception as e:
                print(f"Error extracting GitHub URL from {detail_url}: {e}")
        
        return ""

    async def _fetch_page(self, site_config):
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
            raise CrawlExhausted(f"Error fetching page {page}: {str(e)}")

    async def crawl_site(self, site_config):
        try:
            page_num = 1
            all_servers = []
            
            while True:
                print(f"Crawling page {page_num}...")
                site_config['current_page'] = page_num
                data = await self._fetch_page_with_retry(site_config)
                if not data:
                    print("No data received, possibly reached the last page")
                    break
                
                servers = data.get('servers', [])
                if not servers:
                    print("Received empty server list, possibly reached the last page")
                    break
                
                print(f"Collected {len(servers)} server records on page {page_num}")
                
                for server in servers:
                    try:
                        # Get detailed information for the server
                        server_details = await self._fetch_server_details(server['qualifiedName'])
                        
                        # Construct normalized server metadata
                        normalized_data = {
                            'name': server.get('displayName', ''),
                            'description': server.get('description', ''),
                            'detail_url': server.get('homepage', ''), 
                            'github_url': '', 
                            'categories': [], 
                            'source': 'smithery',
                            'raw_data': server_details
                        }
                        
                        # Extract GitHub URL from server details
                        github_url = self._extract_github_url(normalized_data)
                        normalized_data['github_url'] = github_url
                        
                        # Extract categories information from tags
                        normalized_data = self.categories_manager.update_categories_from_tags('smithery', normalized_data)
                        
                        all_servers.append(normalized_data)
                        print(f"Collected server metadata: {server['qualifiedName']} (GitHub: {github_url if github_url else 'N/A'})")
                        
                    except Exception as e:
                        print(f"Error fetching details for server {server['qualifiedName']}: {str(e)}")
                        continue
                
                yield data
                
                # If fewer servers than page_size, it's the last page
                if len(servers) < site_config.get('page_size', 100):
                    break
                    
                page_num += 1
            
            # Save all servers' summary information
            output_file = self.output_dir / "smithery.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(all_servers, f, ensure_ascii=False, indent=2)
            
            print(f"All servers summary saved to: {output_file}")
            
            # Statistics on GitHub URL extraction
            github_count = sum(1 for server in all_servers if server['github_url'])
            print(f"Successfully extracted GitHub URLs for {github_count}/{len(all_servers)} servers")
                
        except Exception as e:
            print(f"Error during smithery crawling: {str(e)}")
            raise

    async def _fetch_server_details(self, qualified_name: str) -> Dict[str, Any]:
        """Fetch detailed information for a server from smithery registry
        Args:
            qualified_name: The unique identifier for the server
        Returns:
            Dict[str, Any]: Detailed server information
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
            print(f"Error fetching server details for {qualified_name}: {str(e)}")
            return {}

    async def run(self):
        """Run the smithery crawler"""
        try:
            # Make sure the configuration exists
            if not self.configs:
                raise ValueError("No configuration found")
            
            # Get the first configuration (smithery's configuration)
            site_config = self.configs[0]
            
            # Run the crawler
            async for _ in self.crawl_site(site_config):
                pass
                
        except Exception as e:
            print(f"Error running smithery crawler: {str(e)}")
            raise 