#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Categories Manager for MCP Servers
Process and manage categories information for MCP servers
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from bs4 import BeautifulSoup
import time
import re

class CategoriesManager:
    """Manage categories information for MCP servers"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.servers_dir = base_dir / "mcp_servers"
        
    def update_categories_from_tags(self, source_name: str, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract categories from detail_url webpage based on tags
        Args:
            source_name: Source name    
            server_data: Server data dictionary
        Returns:
            Dict[str, Any]: Updated server data dictionary
        """
        detail_url = server_data.get('detail_url', '')
        if not detail_url:
            return server_data
            
        try:
            # Add delay to avoid too many requests
            time.sleep(0.5)
            
            response = requests.get(detail_url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                if source_name == 'smithery':
                    categories = self._extract_smithery_tags(soup)
                elif source_name == 'pulse':
                    categories = self._extract_pulse_tags(soup)
                elif source_name == 'cursor':
                    categories = self._extract_cursor_tags(soup)
                elif source_name == 'awesome':
                    categories = self._extract_awesome_tags(soup)
                elif source_name == 'glama':
                    categories = self._extract_glama_tags(soup)
                else:
                    categories = self._extract_generic_tags(soup)
                
                if categories:
                    server_data['categories'] = categories
                    print(f"Extracted categories for {server_data.get('name', 'Unknown')}: {categories}")
                    
        except Exception as e:
            print(f"Failed to extract tags from {detail_url}: {e}")
            
        return server_data
    
    def _extract_smithery_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from Smithery website"""
        categories = []
        
        # Find tag elements
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:  # Avoid extracting long texts
                categories.append(text)
        
        # Remove duplicates and filter out empty/whitespace strings
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]  # Limit to 10 categories
    
    def _extract_pulse_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from Pulse website"""
        categories = []
        
        # Find tag elements
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label|badge'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]
    
    def _extract_cursor_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from Cursor website"""
        categories = []
        
        # Find tag elements
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label|badge'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]
    
    def _extract_awesome_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from Awesome MCP website"""
        categories = []
        
        # Find tag elements     
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label|badge'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]
    
    def _extract_glama_tags(self, soup: BeautifulSoup) -> List[str]:
        """Extract tags from Glama website"""
        categories = []
        
        # Find tag elements
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label|badge'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]
    
    def _extract_generic_tags(self, soup: BeautifulSoup) -> List[str]:
        """Generic tag extraction method"""
        categories = []
        
        # Find possible tag elements
        tag_elements = soup.find_all(['span', 'div', 'a'], class_=re.compile(r'tag|category|label|badge'))
        for element in tag_elements:
            text = element.get_text(strip=True)
            if text and len(text) < 50:
                categories.append(text)
        
        categories = list(set(categories))
        categories = [cat for cat in categories if cat and not cat.isspace()]
        
        return categories[:10]
    
    def update_categories_from_directory(self, source_name: str, category_mapping: Dict[str, List[str]]):
        """Update categories for existing servers in a directory based on category mapping
        Args:
            source_name: Name of the data source
            category_mapping: Category mapping {category_name: [server_names]}
        """
        json_file = self.servers_dir / source_name / f"{source_name}.json"
        
        if not json_file.exists():
            print(f"File does not exist: {json_file}")
            return
            
        try:
            # Read existing data
            with open(json_file, 'r', encoding='utf-8') as f:
                servers = json.load(f)
            
            # Create server name to categories mapping
            server_to_categories = {}
            for category, server_names in category_mapping.items():
                for server_name in server_names:
                    if server_name not in server_to_categories:
                        server_to_categories[server_name] = []
                    server_to_categories[server_name].append(category)
            
            # Update categories for each server
            updated_count = 0
            for server in servers:
                server_name = server.get('name', '')
                if server_name in server_to_categories:
                    # Merge existing categories with new categories
                    existing_categories = server.get('categories', [])
                    new_categories = server_to_categories[server_name]
                    all_categories = list(set(existing_categories + new_categories))
                    server['categories'] = all_categories
                    updated_count += 1
                    print(f"Update {server_name}'s categories: {all_categories}")
            
            # Save updated data
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(servers, f, ensure_ascii=False, indent=2)
            
            print(f"Successfully updated categories for {updated_count} servers")
            
        except Exception as e:
            print(f"Failed to update categories: {e}")
    
    def get_categories_statistics(self, source_name: str) -> Dict[str, Any]:
        """Get statistics about categories for a source
        Args:
            source_name: Name of the data source
        Returns:
            Dict[str, Any]: Statistics about categories
        """
        json_file = self.servers_dir / source_name / f"{source_name}.json"
        
        if not json_file.exists():
            return {}
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                servers = json.load(f)
            
            category_stats = {}
            for server in servers:
                categories = server.get('categories', [])
                for category in categories:
                    if category not in category_stats:
                        category_stats[category] = 0
                    category_stats[category] += 1
            
            return category_stats
            
        except Exception as e:
            print(f"Failed to get categories statistics: {e}")
            return {}
    
    def add_servers_to_category(self, category: str, servers: List[dict]):
        """Add servers to a specified category
        Args:
            category: Category name
            servers: List of server dictionaries
        """
        categories_dir = self.base_dir / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)
        
        categories_file = categories_dir / "categories.json"
        
        categories_data = {}
        if categories_file.exists():
            try:
                with open(categories_file, 'r', encoding='utf-8') as f:
                    categories_data = json.load(f)
            except Exception as e:
                print(f"Failed to read categories data: {e}")
                categories_data = {}
        
        if category not in categories_data:
            categories_data[category] = []
        
        for server in servers:
            server_name = server.get('name', '')
            if server_name and server_name not in [s.get('name', '') for s in categories_data[category]]:
                categories_data[category].append(server)
        
        self.save_categories(categories_data)
    
    def save_categories(self, categories_data: Dict[str, List[dict]] = None):
        """Save category data to categories.json file
        Args:
            categories_data: Category data, if None then use internal data
        """
        categories_dir = self.base_dir / "categories"
        categories_dir.mkdir(parents=True, exist_ok=True)
        
        categories_file = categories_dir / "categories.json"
        
        if categories_data is None:
            if categories_file.exists():
                try:
                    with open(categories_file, 'r', encoding='utf-8') as f:
                        categories_data = json.load(f)
                except Exception as e:
                    print(f"Failed to read categories data: {e}")
                    categories_data = {}
            else:
                categories_data = {}
        
        # Save category data
        try:
            with open(categories_file, 'w', encoding='utf-8') as f:
                json.dump(categories_data, f, ensure_ascii=False, indent=2)
            print(f"Categories data saved to: {categories_file}")
        except Exception as e:
            print(f"Failed to save categories: {e}") 
