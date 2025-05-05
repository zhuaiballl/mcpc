import requests
from bs4 import BeautifulSoup
from pathlib import Path
import json
import re
from urllib.parse import urlparse
import os

proxies = {
    "http": "socks5h://127.0.0.1:1060",
    "https": "socks5h://127.0.0.1:1060"
}

class AwesomeMcpCrawler:
    def __init__(self, config_path):
        self.base_dir = Path("mcp_servers")
        self.output_dir = self.base_dir / "awesome"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path
        self.github_token = os.getenv('GITHUB_TOKEN')

    def _parse_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('div.grid > div.rounded-xl')
        results = []
        for div in items:
            name = div.select_one('div.tracking-tight.text-xl.font-semibold')
            name = name.get_text(strip=True) if name else ''
            desc = div.select_one('div.text-sm.text-gray-600.leading-relaxed')
            desc = desc.get_text(strip=True) if desc else ''
            a = div.select_one('a[href]')
            detail_url = 'https://mcpservers.org' + a['href'] if a else ''
            results.append({
                'name': name,
                'description': desc,
                'detail_url': detail_url
            })
        return results

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

    def _get_github_repo_url(self, detail_url: str) -> str:
        try:
            resp = requests.get(detail_url, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            a = soup.select_one('body > div > div > div > div.mb-8 > a')
            if a and a['href'].startswith('https://github.com/'):
                return a['href']
            elif a:
                print(f"Detail页的GitHub链接不是GitHub仓库链接，已跳过: {a['href']}")
        except Exception as e:
            print(f"获取 {detail_url} 的 GitHub repo 链接失败: {e}")
        return None

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

    def crawl(self):
        url = 'https://mcpservers.org/'
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        results = self._parse_list(resp.text)
        print(f"共抓取到 {len(results)} 条 awesome MCP 数据")
        # 保存每个 server，并抓取GitHub repo
        for item in results:
            normalized_name = item['name'].replace('/', '_').replace('@', '_').replace(' ', '_')
            server_dir = self.output_dir / normalized_name
            server_dir.mkdir(parents=True, exist_ok=True)
            metadata_path = server_dir / f"{normalized_name}.awesome.json"
            with open(metadata_path, 'w') as f:
                json.dump(item, f, indent=2, ensure_ascii=False)
            # 获取并抓取GitHub repo
            repo_url = self._get_github_repo_url(item['detail_url'])
            if repo_url:
                self._download_github_repo(repo_url, server_dir)
            else:
                print(f"未找到 {item['name']} 的 GitHub repo 链接")
        # 保存总表
        all_path = self.output_dir / "all_servers.awesome.json"
        with open(all_path, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"awesome MCP 数据已保存至 {all_path.resolve()}")

    async def run(self):
        self.crawl() 