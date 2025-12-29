#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Category Crawler for MCP Servers
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup
import time
import re
from .categories_manager import CategoriesManager

class CategoryCrawler:
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.categories_manager = CategoriesManager(base_dir)
        
    def crawl_smithery_categories(self):
        """Crawl the category directory of Smithery"""
        print("Start crawling Smithery category directory...")
        
        category_prompts = {
            'Web Search': 'web search',
            'Browser Automation': 'browser automation',
            'Memory Management': 'memory systems and memory extensions for agents',
            'Structured Problem Solving': 'Find systems focused on enhancing structured problem-solving, systematic reasoning, and the use of mental models or reflective thinking strategies. Surfaces tools for breaking down complex challenges, guiding decision-making, and facilitating stepwise or collaborative cognitive processes.',
            'LLM Tool Integration': 'Integrate large language models with external tools, data sources, and APIs to enable dynamic access to information, resources, analytics, and automated actions within AI workflows. Facilitate seamless interaction between LLMs and diverse platforms for enhanced context-aware capabilities.',
            'Media Discovery & Recommendations': 'Discover and recommend entertainment content including movies, TV shows, music, and live events. Retrieve detailed media information, browse and manage personal media libraries, and receive personalized suggestions for viewing or attendance based on user preferences and current trends.'
        }
        
        category_mapping = {}
        
        for category_name, prompt in category_prompts.items():
            try:
                print(f"Crawling category: {category_name}")
                server_names = self._extract_smithery_category_servers_by_keyword(prompt)
                if server_names:
                    category_mapping[category_name] = server_names
                    print(f"Category {category_name} contains {len(server_names)} servers")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to crawl category {category_name}: {e}")
                continue
        
        # Update existing data
        if category_mapping:
            self.categories_manager.update_categories_from_directory('smithery', category_mapping)
            print("Smithery category information updated successfully")
        else:
            print("No valid category information retrieved")
    
    def crawl_smithery_categories_from_file(self, categories_file: str = "collected_categories/all_categories.json"):
        """Crawl Smithery categories from a JSON file containing category prompts"""
        print(f"Start automatically batch crawling Smithery category directory, source file: {categories_file}")
        import json
        from pathlib import Path
        
        real_categories = [
            "Find systems focused on enhancing structured problem-solving capabilities, including step-by-step reasoning, logical analysis, and systematic approaches to complex challenges.",
            "Image generation tools and APIs for creating, editing, and enhancing images, including text-to-image generation, image manipulation, and visual content creation.",
            "browser automation",
            "web search",
            "Discover and recommend entertainment content including movies, TV shows, music, and live events. Provide personalized recommendations based on user preferences and viewing history.",
            "memory systems and memory extensions for agents",
            "Find tools for real-time web and documentation search, enabling quick access to current information and up-to-date documentation across various sources.",
            "Find solutions that enable remote or secure execution of code, including sandboxed environments, containerized execution, and secure code evaluation platforms."
        ]
                
        print(f"Using {len(real_categories)} real category prompts for batch crawling...")
        
        # Init CategoriesManager if not exists
        if not hasattr(self, 'categories_manager'):
            self.categories_manager = CategoriesManager(self.base_dir)
        
        total_servers = 0
        
        for i, prompt in enumerate(real_categories, 1):
            print(f"\n[{i}/{len(real_categories)}] Crawling category: {prompt[:50]}...")
            
            try:
                # Use website crawling method to support long prompts
                servers = self._search_smithery_servers_from_web(prompt)
                
                if servers:
                    print(f"  Found {len(servers)} servers")
                    # Add servers to the category
                    self.categories_manager.add_servers_to_category(prompt, servers)
                    total_servers += len(servers)
                else:
                    print(f"  No servers found")
                    
                # Add delay to avoid too many requests
                time.sleep(2)
                
            except Exception as e:
                print(f"  Failed to crawl category: {e}")
                continue
        
        print(f"\nBatch crawling completed! Total {total_servers} servers processed")
        
        # Save category data
        self.categories_manager.save_categories()
        print(f"Category data saved to: {self.base_dir}/categories.json")
    
    def _search_smithery_servers_from_web(self, prompt: str) -> List[dict]:
        """Directly crawl servers from Smithery website URL for a given prompt"""
        import requests
        import re
        from bs4 import BeautifulSoup
        import urllib.parse
        
        # Construct search URL
        encoded_prompt = urllib.parse.quote(prompt)
        search_url = f"https://smithery.ai/search?q={encoded_prompt}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        all_servers = []
        page = 1
        total_pages = 1
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        while page <= total_pages:
            url = f"https://smithery.ai/search?q={prompt.replace(' ', '+')}&page={page}"
            resp = requests.get(url, headers=headers)
            soup = BeautifulSoup(resp.text, 'html.parser')
            scripts = soup.find_all('script')
            print(f"    Page {page} has {len(scripts)} script tags")
            script_found = False
            for idx, script in enumerate(scripts):
                if script.string and 'servers' in script.string:
                    script_found = True
                    print(f"    script[{idx}] contains 'servers', length: {len(script.string)}")
                    if idx == 41:
                        # Write script[41] content to debug file
                        with open('debug_script41.txt', 'w', encoding='utf-8') as f:
                            f.write(script.string)
                        print(f"    Script[41] content written to debug_script41.txt")
                    break
            if not script_found:
                print(f"    No script found with 'servers' in content on page {page}, skip")
            page += 1
        return all_servers

    def _search_smithery_servers(self, prompt: str) -> List[dict]:
        """Call Smithery API to search for servers based on the given prompt"""
        import requests
        import json
        import os
        
        # Get API key
        api_key = os.getenv('SMITHERY_API_KEY')
        if not api_key:
            print("    SMITHERY_API_KEY environment variable not set, skip search")
            return []
        
        # Smithery API endpoint
        api_url = "https://registry.smithery.ai/servers"
        
        # Request parameters
        params = {
            'q': prompt,
            'page': 1,
            'pageSize': 100
        }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        all_servers = []
        page = 1
        
        while True:
            params['page'] = page
            try:
                response = requests.get(api_url, params=params, headers=headers, timeout=15)
                response.raise_for_status()
                
                data = response.json()
                servers = data.get('servers', [])
                
                if not servers:
                    break
                
                for server in servers:
                    server_info = {
                        'name': server.get('displayName', ''),
                        'description': server.get('description', ''),
                        'github_url': '',
                        'detail_url': server.get('homepage', ''),
                        'category': prompt,
                        'qualified_name': server.get('qualifiedName', '')
                    }
                    all_servers.append(server_info)
                
                print(f"    Page {page} found {len(servers)} servers")
                
                if len(servers) < params['pageSize']:
                    break
                    
                page += 1
                
            except Exception as e:
                print(f"    API request failed on page {page}: {e}")
                break
        
        return all_servers

    def _extract_smithery_category_servers_by_keyword(self, keyword: str) -> List[str]:
        """Extract server names from Smithery API search results based on the given keyword"""
        server_names = []
        
        try:
            # Call Smithery API to search for servers based on the given keyword
            api_key = os.getenv('SMITHERY_API_KEY')
            if not api_key:
                print("    SMITHERY_API_KEY environment variable is not set")
                return server_names
            
            page = 1
            page_size = 100
            
            while True:
                # Construct search URL
                import urllib.parse
                encoded_keyword = urllib.parse.quote(keyword)
                search_url = f"https://registry.smithery.ai/servers?q={encoded_keyword}&page={page}&pageSize={page_size}"
                
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(search_url, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    servers = data.get('servers', [])
                    
                    if not servers:
                        break
                    
                    for server in servers:
                        name = server.get('displayName', '')
                        if name and name not in server_names:  # Avoid duplicates
                            server_names.append(name)
                    
                    print(f"Keyword '{keyword}' page {page} found {len(servers)} servers")
                    
                    if len(servers) < page_size:
                        break
                    
                    page += 1
                    time.sleep(0.5)
                
                else:
                    print(f"    API request failed with status code: {response.status_code}")
                    break
                
        except Exception as e:
            print(f"    Failed to extract servers by keyword '{keyword}': {e}")
        
        return server_names
    
    def crawl_pulse_categories(self):
        """Crawl categories from Pulse website"""
        print("Start crawling Pulse category directories...")
        
        category_urls = {
            'AI & ML': 'https://pulse.mcp.dev/categories/ai-ml',
            'Database': 'https://pulse.mcp.dev/categories/database',
            'File System': 'https://pulse.mcp.dev/categories/file-system',
            'Network': 'https://pulse.mcp.dev/categories/network',
            'Productivity': 'https://pulse.mcp.dev/categories/productivity',
            'Development': 'https://pulse.mcp.dev/categories/development',
        }
        
        category_mapping = {}
        
        for category_name, url in category_urls.items():
            try:
                print(f"Start crawling category: {category_name}")
                server_names = self._extract_pulse_category_servers(url)
                if server_names:
                    category_mapping[category_name] = server_names
                    print(f"Category {category_name} contains {len(server_names)} servers")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to crawl category {category_name}: {e}")
                continue
        
        # Update existing data
        if category_mapping:
            self.categories_manager.update_categories_from_directory('pulse', category_mapping)
            print("Pulse category directories updated successfully")
        else:
            print("No valid category directories were retrieved")
    
    def _extract_pulse_category_servers(self, category_url: str) -> List[str]:
        """Extract server names from Pulse category page"""
        server_names = []
        
        try:
            response = requests.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                server_elements = soup.find_all(['div', 'a'], class_=re.compile(r'server|item|card'))
                
                for element in server_elements:
                    name_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'], 
                                              class_=re.compile(r'title|name|display'))
                    if name_element:
                        name = name_element.get_text(strip=True)
                        if name and len(name) > 1:
                            server_names.append(name)
                
        except Exception as e:
            print(f"Failed to extract servers from category page: {e}")
        
        return server_names
    
    def crawl_cursor_categories(self):
        """Crawl Cursor category directories"""
        print("Start crawling Cursor category directories...")
        
        category_urls = {
            'AI & ML': 'https://cursor.sh/extensions/categories/ai-ml',
            'Database': 'https://cursor.sh/extensions/categories/database',
            'File System': 'https://cursor.sh/extensions/categories/file-system',
            'Network': 'https://cursor.sh/extensions/categories/network',
            'Productivity': 'https://cursor.sh/extensions/categories/productivity',
            'Development': 'https://cursor.sh/extensions/categories/development',
        }
        
        category_mapping = {}
        
        for category_name, url in category_urls.items():
            try:
                print(f"Start crawling category: {category_name}")
                server_names = self._extract_cursor_category_servers(url)
                if server_names:
                    category_mapping[category_name] = server_names
                    print(f"Category {category_name} contains {len(server_names)} servers")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to crawl category {category_name}: {e}")
                continue
        
        # Update existing data
        if category_mapping:
            self.categories_manager.update_categories_from_directory('cursor', category_mapping)
            print("Cursor category directories updated successfully")
        else:
            print("No valid category directories were retrieved")
    
    def _extract_cursor_category_servers(self, category_url: str) -> List[str]:
        """Extract server names from Cursor category page"""
        server_names = []
        
        try:
            response = requests.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                

                server_elements = soup.find_all(['div', 'a'], class_=re.compile(r'server|item|card'))
                
                for element in server_elements:
                    name_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'], 
                                              class_=re.compile(r'title|name|display'))
                    if name_element:
                        name = name_element.get_text(strip=True)
                        if name and len(name) > 1:
                            server_names.append(name)
                
        except Exception as e:
            print(f"Failed to extract servers from category page: {e}")
        
        return server_names
    
    def crawl_awesome_categories(self):
        """Crawl Awesome MCP category directories"""
        print("Start crawling Awesome MCP category directories...")
        
        category_urls = {
            'AI & ML': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/ai-ml',
            'Database': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/database',
            'File System': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/file-system',
            'Network': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/network',
            'Productivity': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/productivity',
            'Development': 'https://github.com/modelcontextprotocol/awesome-mcp/categories/development',
        }
        
        category_mapping = {}
        
        for category_name, url in category_urls.items():
            try:
                print(f"Start crawling category: {category_name}")
                server_names = self._extract_awesome_category_servers(url)
                if server_names:
                    category_mapping[category_name] = server_names
                    print(f"Category {category_name} contains {len(server_names)} servers")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to crawl category {category_name}: {e}")
                continue
        
        # Update existing data
        if category_mapping:
            self.categories_manager.update_categories_from_directory('awesome', category_mapping)
            print("Awesome MCP category directories updated successfully")
        else:
            print("No valid category directories were retrieved")
    
    def _extract_awesome_category_servers(self, category_url: str) -> List[str]:
        """Extract server names from Awesome MCP category page"""
        server_names = []
        
        try:
            response = requests.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                server_elements = soup.find_all(['div', 'a'], class_=re.compile(r'server|item|card'))
                
                for element in server_elements:
                    name_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'], 
                                              class_=re.compile(r'title|name|display'))
                    if name_element:
                        name = name_element.get_text(strip=True)
                        if name and len(name) > 1:
                            server_names.append(name)
                
        except Exception as e:
            print(f"Failed to extract servers from category page: {e}")
        
        return server_names
    
    def crawl_glama_categories(self):
        """Crawl Glama category directories"""
        print("Start crawling Glama category directories...")
        
        category_urls = {
            'AI & ML': 'https://glama.ai/categories/ai-ml',
            'Database': 'https://glama.ai/categories/database',
            'File System': 'https://glama.ai/categories/file-system',
            'Network': 'https://glama.ai/categories/network',
            'Productivity': 'https://glama.ai/categories/productivity',
            'Development': 'https://glama.ai/categories/development',
        }
        
        category_mapping = {}
        
        for category_name, url in category_urls.items():
            try:
                print(f"Start crawling category: {category_name}")
                server_names = self._extract_glama_category_servers(url)
                if server_names:
                    category_mapping[category_name] = server_names
                    print(f"Category {category_name} contains {len(server_names)} servers")
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Failed to crawl category {category_name}: {e}")
                continue
        
        # Update existing data
        if category_mapping:
            self.categories_manager.update_categories_from_directory('glama', category_mapping)
            print("Glama category directories updated successfully")
        else:
            print("No valid category directories were retrieved")
    
    def _extract_glama_category_servers(self, category_url: str) -> List[str]:
        """Extract server names from Glama category page"""
        server_names = []
        
        try:
            response = requests.get(category_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                

                server_elements = soup.find_all(['div', 'a'], class_=re.compile(r'server|item|card'))
                
                for element in server_elements:
                    name_element = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div'], 
                                              class_=re.compile(r'title|name|display'))
                    if name_element:
                        name = name_element.get_text(strip=True)
                        if name and len(name) > 1:
                            server_names.append(name)
                
        except Exception as e:
            print(f"Failed to extract servers from category page: {e}")
        
        return server_names
    
    def get_categories_statistics(self, source_name: str):
        """Get category statistics"""
        return self.categories_manager.get_categories_statistics(source_name) 