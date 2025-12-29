import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re
from urllib.parse import urlparse, urljoin
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import requests_cache
import random
from datetime import datetime
import logging

# GitHub API proxy settings
github_proxies = {
    "http": "socks5h://127.0.0.1:1060",
    "https": "socks5h://127.0.0.1:1060"
}

class GlamaCrawler:
    def __init__(self, config_path):
        self.base_dir = Path("mcp_servers")
        self.output_dir = self.base_dir / "glama"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.base_url = "https://glama.ai"
        self.chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/local/bin/chromedriver')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def _get_driver(self):
        """Get Chrome WebDriver Instance"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--start-maximized')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-notifications')
        chrome_options.add_argument('--lang=en-US')
        
        # Add user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36')
        
        try:
            service = Service(executable_path=self.chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            # Set page load timeout
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e:
            print(f"Error initializing Chrome driver: {str(e)}")
            raise

    def _random_sleep(self, min_seconds=2, max_seconds=5):
        """Randomly wait for a period of time to simulate human behavior"""
        time.sleep(random.uniform(min_seconds, max_seconds))

    def _scroll_to_bottom(self, driver, pause_time=2):
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _parse_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('ul.cYdhWw > li')
        results = []
        for item in items:
            article = item.select_one('article')
            if not article:
                continue

            name_elem = article.select_one('h2 a')
            name = name_elem.get_text(strip=True) if name_elem else ''
            
            desc_elem = article.select_one('div.jrPWok')
            desc = desc_elem.get_text(strip=True) if desc_elem else ''

            detail_url = urljoin(self.base_url, name_elem['href']) if name_elem and 'href' in name_elem.attrs else ''

            # Get categories
            categories = []
            category_elems = article.select('ul.fPSBzf.hnMRLK.jrIcfy li a')
            for cat_elem in category_elems:
                if cat_elem.get('title'):
                    categories.append(cat_elem['title'])

            # Get stats
            stats = {}
            stats_elems = article.select('div.bYPztT.czikZZ.fPSBzf.hnMRLK.jsOvvq.jrIcfy')
            for stat_elem in stats_elems:
                if 'title' in stat_elem.attrs:
                    title = stat_elem['title']
                    value = stat_elem.get_text(strip=True)
                    if title == 'Tools':
                        stats['tools_count'] = int(value) if value.isdigit() else 0
                    elif title == 'Weekly Downloads':
                        stats['weekly_downloads'] = int(value) if value.isdigit() else 0
                    elif title == 'GitHub Stars':
                        stats['github_stars'] = int(value) if value.isdigit() else 0

            results.append({
                'name': name,
                'description': desc,
                'detail_url': detail_url,
                'categories': categories,
                'stats': stats
            })
        return results

    def _get_github_repo_url(self, detail_url):
        if not detail_url:
            return None
        
        driver = self._get_driver()
        try:
            driver.get(detail_url)
            self._random_sleep(3, 6)  # Random wait longer time
            
            # Try multiple methods to find GitHub link
            github_url = None
            
            # Method 1: XPath search for links containing "github.com"
            try:
                github_links = driver.find_elements(By.XPATH, "//a[contains(@href, 'github.com')]")
                if github_links:
                    for link in github_links:
                        url = link.get_attribute('href')
                        # 确保是仓库链接而不是组织链接
                        if re.match(r'https?://github\.com/[^/]+/[^/]+/?$', url):
                            github_url = url
                            break
            except Exception as e:
                print(f"XPath search failed: {str(e)}")
            
            # Method 2: CSS selector search
            if not github_url:
                try:
                    github_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="github.com"]')
                    for link in github_links:
                        url = link.get_attribute('href')
                        if re.match(r'https?://github\.com/[^/]+/[^/]+/?$', url):
                            github_url = url
                            break
                except Exception as e:
                    print(f"CSS selector search failed: {str(e)}")
            
            # Method 3: Search in page source
            if not github_url:
                try:
                    page_source = driver.page_source
                    # Use stricter regex to match repo URLs
                    github_pattern = r'https?://github\.com/[^/]+/[^/"\']+/?'
                    matches = re.findall(github_pattern, page_source)
                    for url in matches:
                        if re.match(r'https?://github\.com/[^/]+/[^/]+/?$', url):
                            github_url = url
                            break
                except Exception as e:
                    print(f"Page source search failed: {str(e)}")
            
            if github_url:
                print(f"Found GitHub repository URL: {github_url}")
            else:
                print(f"No valid GitHub repository URL found for {detail_url}")
            
            return github_url
            
        except Exception as e:
            print(f"Error getting GitHub repo URL: {str(e)}")
        finally:
            driver.quit()
        return None

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

    def _download_github_repo(self, repo_url, server_dir):
        if not self.github_token:
            print("GITHUB_TOKEN not set, cannot fetch GitHub repo")
            return
            
        owner, repo = self.extract_github_repo_info(repo_url)
        if not owner or not repo:
            print(f"Link is not a valid GitHub repo link, skipped: {repo_url}")
            return
            
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
        headers = {'Authorization': f'token {self.github_token}'}
        
        def download_dir(api_url, local_dir):
            # Use proxies only for GitHub API requests
            resp = requests.get(api_url, headers=headers, timeout=30, proxies=github_proxies)
            if resp.status_code == 404:
                print(f"repo 404: {api_url}")
                return
            resp.raise_for_status()
            
            for item in resp.json():
                if item['type'] == 'file':
                    file_resp = requests.get(item['download_url'], headers=headers, timeout=30, proxies=github_proxies)
                    file_resp.raise_for_status()
                    file_path = os.path.join(local_dir, item['name'])
                    with open(file_path, 'wb') as f:
                        f.write(file_resp.content)
                elif item['type'] == 'dir':
                    sub_dir = os.path.join(local_dir, item['name'])
                    os.makedirs(sub_dir, exist_ok=True)
                    download_dir(item['url'], sub_dir)
        
        os.makedirs(server_dir, exist_ok=True)
        try:
            download_dir(api_url, str(server_dir))
            print(f"Successfully fetched GitHub repo: {repo_url} to {server_dir}")
        except Exception as e:
            print(f"Failed to fetch GitHub repo {repo_url}: {e}")

    def _load_all_items(self, driver):
        """Click Load More button until all items are loaded"""
        while True:
            try:
                # Wait for Load More button to appear
                load_more = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Load More')]"))
                )
                
                # Check if button is visible and clickable
                if not load_more.is_displayed() or not load_more.is_enabled():
                    print("Load More button is not visible or clickable, may have loaded all items")
                    break
                
                # Scroll to button position
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                self._random_sleep(1, 2)  # Short wait to ensure button is fully visible
                
                # Click the button
                load_more.click()
                print("Clicked Load More button")
                
                # Wait for new content to load  
                self._random_sleep(2, 3)
                
                # Check if there are more items to load
                try:
                    # If button is not visible or clickable, all items are loaded
                    if not load_more.is_displayed() or not load_more.is_enabled():
                        print("All items have been loaded")
                        break
                except:
                    # If button is not found, all items are loaded
                    print("Load More button is not found, all items have been loaded")
                    break
                    
            except Exception as e:
                print(f"Error loading more items: {str(e)}")
                break

    def _api_request(self, endpoint, params=None):
        """Basic API request method"""
        url = f"https://glama.ai/api/mcp/v1/{endpoint}"
        headers = {"Accept": "application/json"}
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
    
    def fetch_all_servers(self):
        all_servers = []
        params = {"first": 100}
        after = None
        max_retries = 3
        while True:
            retry_count = 0
            while retry_count < max_retries:
                try:
                    if after:
                        params["after"] = after
                    else:
                        params.pop("after", None)
                    data = self._api_request("servers", params)
                    print(f"API response: pageInfo={data.get('pageInfo') if data else None}, servers_count={len(data['servers']) if data and 'servers' in data else 0}")
                    if not data or "servers" not in data or "pageInfo" not in data:
                        self.logger.error("API response data is incomplete")
                        raise Exception("API response data is incomplete")

                    # Handle field renaming
                    for server in data["servers"]:
                        if "repository" in server and server["repository"] and "url" in server["repository"]:
                            server["github_url"] = server["repository"]["url"]
                            del server["repository"]

                    all_servers.extend(data["servers"])

                    self.logger.info(f"Current page records: {len(data['servers'])}, total records: {len(all_servers)}, has next page: {data['pageInfo']['hasNextPage']}")

                    if not data["pageInfo"]["hasNextPage"]:
                        return all_servers

                    after = data["pageInfo"]["endCursor"]
                    time.sleep(random.uniform(1.5, 3.0))
                    break  # Current page successfully processed, break retry loop
                except Exception as e:
                    retry_count += 1
                    self.logger.error(f"API request failed (retry {retry_count}/{max_retries}): {str(e)}")
                    time.sleep(retry_count * 3)
            if retry_count == max_retries:
                self.logger.error("Continuous multiple API request failures, stopping crawl.")
                break
        return all_servers

    def crawl(self):
        url = 'https://glama.ai/mcp/servers'
        driver = self._get_driver()
        try:
            driver.get(url)
            self._random_sleep(3, 6)  # Random wait longer time
            
            # Load all items    
            self._load_all_items(driver)
            
            # Scroll to bottom to ensure all content is loaded  
            self._scroll_to_bottom(driver)
            
            html = driver.page_source
            results = self._parse_list(html)
            print(f"Total Glama MCP servers found: {len(results)}")

            # Process each server, get GitHub repo information
            for item in results:
                # Get and add GitHub repo information
                repo_url = self._get_github_repo_url(item['detail_url'])
                if repo_url:
                    item['github_url'] = repo_url
                    print(f"Found GitHub repo for {item['name']}: {repo_url}")
                else:
                    item['github_url'] = ''
                    print(f"Did not find GitHub repo for {item['name']}")
                
                # Add source and crawled_at fields
                item['source'] = 'glama'
                item['crawled_at'] = datetime.now().isoformat()
                
                self._random_sleep(2, 4)  # Random delay between requests

            # Save summary file
            summary_path = self.output_dir / "glama.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'source': 'glama',
                    'total_count': len(results),
                    'crawled_at': datetime.now().isoformat(),
                    'servers': results
                }, f, indent=2, ensure_ascii=False)
            print(f"Glama MCP servers data saved to {summary_path.resolve()}")
        finally:
            driver.quit()

    async def run(self):
        self.crawl()