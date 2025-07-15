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

    def _get_driver(self):
        """获取 Chrome WebDriver 实例"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
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
        """随机等待一段时间，模拟人类行为"""
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
            self._random_sleep(3, 6)  # 随机等待更长时间
            
            # 尝试多种方式查找 GitHub 链接
            github_url = None
            
            # 方法1: 使用 XPath 查找包含 "github.com" 的链接
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
            
            # 方法2: 使用 CSS 选择器
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
            
            # 方法3: 使用页面源码
            if not github_url:
                try:
                    page_source = driver.page_source
                    # 使用更严格的正则表达式匹配仓库URL
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
            print("未设置 GITHUB_TOKEN，无法抓取 GitHub repo")
            return
            
        owner, repo = self.extract_github_repo_info(repo_url)
        if not owner or not repo:
            print(f"链接不是有效的GitHub仓库链接，已跳过: {repo_url}")
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
            print(f"已抓取 GitHub repo: {repo_url} 到 {server_dir}")
        except Exception as e:
            print(f"抓取 GitHub repo {repo_url} 失败: {e}")

    def _load_all_items(self, driver):
        """点击 Load More 按钮直到加载所有项目"""
        while True:
            try:
                # 等待 Load More 按钮出现
                load_more = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Load More')]"))
                )
                
                # 检查按钮是否可见和可点击
                if not load_more.is_displayed() or not load_more.is_enabled():
                    print("Load More 按钮不可见或不可点击，可能已加载所有项目")
                    break
                
                # 滚动到按钮位置
                driver.execute_script("arguments[0].scrollIntoView(true);", load_more)
                self._random_sleep(1, 2)  # 短暂等待以确保按钮完全可见
                
                # 点击按钮
                load_more.click()
                print("点击了 Load More 按钮")
                
                # 等待新内容加载
                self._random_sleep(2, 3)
                
                # 检查是否还有更多内容可以加载
                try:
                    # 如果按钮不再可见或可点击，说明已加载所有内容
                    if not load_more.is_displayed() or not load_more.is_enabled():
                        print("已加载所有项目")
                        break
                except:
                    # 如果按钮不再存在，说明已加载所有内容
                    print("Load More 按钮不再存在，已加载所有项目")
                    break
                    
            except Exception as e:
                print(f"加载更多项目时发生错误: {str(e)}")
                break

    def crawl(self):
        url = 'https://glama.ai/mcp/servers'
        driver = self._get_driver()
        try:
            driver.get(url)
            self._random_sleep(3, 6)  # 随机等待更长时间
            
            # 加载所有项目
            self._load_all_items(driver)
            
            # 滚动到底部以确保所有内容都已加载
            self._scroll_to_bottom(driver)
            
            html = driver.page_source
            results = self._parse_list(html)
            print(f"共抓取到 {len(results)} 条 Glama MCP 数据")

            # 处理每个server，获取GitHub repo信息
            for item in results:
                # 获取并添加GitHub repo信息
                repo_url = self._get_github_repo_url(item['detail_url'])
                if repo_url:
                    item['github_url'] = repo_url
                    print(f"找到 {item['name']} 的 GitHub repo: {repo_url}")
                else:
                    item['github_url'] = ''
                    print(f"未找到 {item['name']} 的 GitHub repo 链接")
                
                # 添加source和crawled_at字段
                item['source'] = 'glama'
                item['crawled_at'] = datetime.now().isoformat()
                
                self._random_sleep(2, 4)  # 在请求之间添加随机延迟

            # 保存汇总文件
            summary_path = self.output_dir / "glama.json"
            with open(summary_path, 'w') as f:
                json.dump({
                    'source': 'glama',
                    'total_count': len(results),
                    'crawled_at': datetime.now().isoformat(),
                    'servers': results
                }, f, indent=2, ensure_ascii=False)
            print(f"Glama MCP 数据已保存至 {summary_path.resolve()}")
        finally:
            driver.quit()

    async def run(self):
        self.crawl() 