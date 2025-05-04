import requests
from pathlib import Path
import json
import os
from typing import Dict, Any, AsyncIterator, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

class CursorCrawler:
    def __init__(self, config_path):
        self.base_dir = Path("mcp_servers")
        self.output_dir = self.base_dir / "cursor"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path
        self.github_token = os.getenv('GITHUB_TOKEN')

    def _get_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=chrome_options)

    def _scroll_to_bottom(self, driver, pause_time=2):
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def _parse_items(self, html) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('a.flex.h-full.items-center.p-4.transition-colors.border')
        results = []
        for a in items:
            name = a.select_one('h3').get_text(strip=True) if a.select_one('h3') else ''
            description = a.select_one('p').get_text(strip=True) if a.select_one('p') else ''
            detail_url = 'https://cursor.directory' + a['href']
            img = a.select_one('img')
            icon_url = img['src'] if img else ''
            alt_name = img['alt'] if img else ''
            results.append({
                'name': name,
                'description': description,
                'detail_url': detail_url,
                'icon_url': icon_url,
                'alt_name': alt_name
            })
        return results

    def _get_github_repo_url(self, detail_url: str) -> str:
        try:
            resp = requests.get(detail_url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            a = soup.select_one('body > div.min-h-screen.mt-24.px-4 > div:nth-child(1) > a')
            if a and a['href'].startswith('https://github.com/'):
                return a['href']
        except Exception as e:
            print(f"获取 {detail_url} 的 GitHub repo 链接失败: {e}")
        return None

    def _download_github_repo(self, repo_url: str, dest_dir: Path):
        if not self.github_token:
            print("未设置 GITHUB_TOKEN，无法抓取 GitHub repo")
            return
        parts = repo_url.rstrip('/').split('/')
        if len(parts) < 2:
            print(f"repo_url 格式不正确: {repo_url}")
            return
        owner, repo = parts[-2], parts[-1]
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
        headers = {'Authorization': f'token {self.github_token}'}
        def download_dir(api_url, local_dir):
            resp = requests.get(api_url, headers=headers, timeout=30)
            if resp.status_code == 404:
                print(f"repo 404: {api_url}")
                return
            resp.raise_for_status()
            for item in resp.json():
                if item['type'] == 'file':
                    file_resp = requests.get(item['download_url'], headers=headers, timeout=30)
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

    async def crawl_site(self, site_config=None) -> AsyncIterator[List[Dict[str, Any]]]:
        # 兼容接口，实际只抓取一次
        yield self._crawl_all()

    def _crawl_all(self) -> List[Dict[str, Any]]:
        driver = self._get_driver()
        try:
            driver.get('https://cursor.directory/mcp')
            self._scroll_to_bottom(driver)
            html = driver.page_source
            results = self._parse_items(html)
            print(f"共抓取到 {len(results)} 条cursor MCP数据")
            # 保存每个MCP为单独文件，并抓取GitHub repo
            for item in results:
                normalized_name = item['name'].replace('/', '_').replace('@', '_').replace(' ', '_')
                server_dir = self.output_dir / normalized_name
                server_dir.mkdir(parents=True, exist_ok=True)
                metadata_path = server_dir / f"{normalized_name}.cursor.json"
                with open(metadata_path, 'w') as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)
                # 获取并抓取GitHub repo
                repo_url = self._get_github_repo_url(item['detail_url'])
                if repo_url:
                    self._download_github_repo(repo_url, server_dir)
                else:
                    print(f"未找到 {item['name']} 的 GitHub repo 链接")
            # 保存总表
            all_path = self.output_dir / "all_servers.cursor.json"
            with open(all_path, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"cursor数据已保存至 {all_path.resolve()}")
            return results
        finally:
            driver.quit()

    async def run(self):
        # 兼容统一接口
        async for _ in self.crawl_site():
            pass