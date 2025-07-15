import json
import os
import requests
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse
import re
import time

proxies = {
    "http": "socks5h://127.0.0.1:1060",
    "https": "socks5h://127.0.0.1:1060"
}

class SourceDownloader:
    def __init__(self, base_dir: str = "mcp_servers"):
        self.base_dir = Path(base_dir)
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            print("警告: 未设置 GITHUB_TOKEN，可能会遇到API限制")

    def extract_github_repo_info(self, url: str) -> tuple:
        """从GitHub URL中提取owner和repo信息
        Args:
            url: GitHub仓库URL
        Returns:
            tuple: (owner, repo) 或 (None, None)
        """
        parsed = urlparse(url)
        if parsed.netloc != "github.com":
            return None, None
        m = re.match(r'^/([^/]+)/([^/]+)', parsed.path)
        if m:
            owner, repo = m.group(1), m.group(2)
            repo = repo[:-4] if repo.endswith('.git') else repo
            return owner, repo
        return None, None

    def download_github_repo(self, repo_url: str, dest_dir: Path) -> bool:
        """下载GitHub仓库源码
        Args:
            repo_url: GitHub仓库URL
            dest_dir: 目标目录
        Returns:
            bool: 是否下载成功
        """
        if not self.github_token:
            print(f"未设置 GITHUB_TOKEN，跳过下载: {repo_url}")
            return False
            
        owner, repo = self.extract_github_repo_info(repo_url)
        if not owner or not repo:
            print(f"链接不是有效的GitHub仓库链接，已跳过: {repo_url}")
            return False
            
        api_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
        headers = {'Authorization': f'token {self.github_token}'}
        
        def download_dir(api_url: str, local_dir: Path) -> bool:
            try:
                resp = requests.get(api_url, headers=headers, timeout=30, proxies=proxies)
                if resp.status_code == 404:
                    print(f"仓库不存在: {api_url}")
                    return False
                resp.raise_for_status()
                
                for item in resp.json():
                    if item['type'] == 'file':
                        try:
                            file_resp = requests.get(item['download_url'], headers=headers, timeout=30, proxies=proxies)
                            file_resp.raise_for_status()
                            file_path = local_dir / item['name']
                            with open(file_path, 'wb') as f:
                                f.write(file_resp.content)
                            print(f"已下载文件: {file_path}")
                        except Exception as e:
                            print(f"下载文件失败 {item['name']}: {str(e)}")
                    elif item['type'] == 'dir':
                        sub_dir = local_dir / item['name']
                        sub_dir.mkdir(exist_ok=True)
                        download_dir(item['url'], sub_dir)
                return True
            except Exception as e:
                print(f"下载目录失败 {api_url}: {str(e)}")
                return False
        
        dest_dir.mkdir(parents=True, exist_ok=True)
        try:
            success = download_dir(api_url, dest_dir)
            if success:
                print(f"已成功下载GitHub仓库: {repo_url} 到 {dest_dir}")
            return success
        except Exception as e:
            print(f"下载GitHub仓库 {repo_url} 失败: {e}")
            return False

    def load_metadata_file(self, file_path: Path) -> Dict[str, Any]:
        """加载元数据文件
        Args:
            file_path: 元数据文件路径
        Returns:
            Dict[str, Any]: 元数据内容
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载元数据文件失败 {file_path}: {str(e)}")
            return {}

    def download_sources_for_data_source(self, source_name: str) -> None:
        """为指定数据源下载所有server源码
        Args:
            source_name: 数据源名称 (如 'smithery', 'pulse', 'cursor', 'awesome', 'glama', 'modelcontextprotocol')
        """
        metadata_file = self.base_dir / source_name / f"{source_name}.json"
        
        if not metadata_file.exists():
            print(f"元数据文件不存在: {metadata_file}")
            return
        
        print(f"开始为 {source_name} 数据源下载源码...")
        
        # 加载元数据
        metadata = self.load_metadata_file(metadata_file)
        servers = metadata.get('servers', [])
        
        if not servers:
            print(f"没有找到server数据: {source_name}")
            return
        
        print(f"找到 {len(servers)} 个server，开始下载源码...")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for i, server in enumerate(servers, 1):
            server_name = server.get('name', f'unknown_{i}')
            github_url = server.get('github_url', '')
            
            print(f"[{i}/{len(servers)}] 处理: {server_name}")
            
            if not github_url:
                print(f"  跳过: 没有GitHub URL")
                skip_count += 1
                continue
            
            # 规范化server名称作为目录名
            normalized_name = self._normalize_server_name(server_name)
            server_dir = self.base_dir / source_name / normalized_name
            
            # 检查是否已经下载过
            if server_dir.exists() and any(server_dir.iterdir()):
                print(f"  跳过: 源码已存在")
                skip_count += 1
                continue
            
            # 下载源码
            try:
                success = self.download_github_repo(github_url, server_dir)
                if success:
                    success_count += 1
                else:
                    error_count += 1
                
                # 添加延迟避免请求过快
                time.sleep(1)
                
            except Exception as e:
                print(f"  下载失败: {str(e)}")
                error_count += 1
        
        print(f"\n下载完成统计:")
        print(f"  成功: {success_count}")
        print(f"  跳过: {skip_count}")
        print(f"  失败: {error_count}")
        print(f"  总计: {len(servers)}")

    def download_all_sources(self) -> None:
        """下载所有数据源的源码"""
        data_sources = ['smithery', 'pulse', 'cursor', 'awesome', 'glama', 'modelcontextprotocol']
        
        for source in data_sources:
            print(f"\n{'='*50}")
            print(f"处理数据源: {source}")
            print(f"{'='*50}")
            self.download_sources_for_data_source(source)

    def _normalize_server_name(self, name: str) -> str:
        """规范化server名称，用于创建目录名
        Args:
            name: 原始server名称
        Returns:
            str: 规范化后的名称
        """
        # 替换特殊字符为下划线
        normalized = re.sub(r'[^\w\s-]', '', name)
        # 将多个空格替换为单个空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        # 将空格替换为下划线
        normalized = normalized.replace(' ', '_')
        return normalized

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='下载MCP Server源码')
    parser.add_argument('--source', type=str, help='指定数据源名称 (如: smithery, pulse, cursor, awesome, glama, modelcontextprotocol)')
    parser.add_argument('--all', action='store_true', help='下载所有数据源的源码')
    parser.add_argument('--base-dir', type=str, default='mcp_servers', help='基础目录路径')
    
    args = parser.parse_args()
    
    downloader = SourceDownloader(args.base_dir)
    
    if args.all:
        downloader.download_all_sources()
    elif args.source:
        downloader.download_sources_for_data_source(args.source)
    else:
        print("请指定 --source 或 --all 参数")
        print("示例:")
        print("  python -m engine.source_downloader --source smithery")
        print("  python -m engine.source_downloader --all")

if __name__ == "__main__":
    main() 