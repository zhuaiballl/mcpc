from .base_parser import MCPParser
from typing import Dict, List, Any

class GitHubAPIParser(MCPParser):
    def parse_server_list(self, response_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析GitHub API返回的目录内容
        Args:
            response_data: GitHub API返回的目录内容JSON数据
        Returns:
            解析后的服务器列表
        """
        servers = []
        for item in response_data:
            if item['type'] == 'dir':
                # 如果是目录，返回目录信息以便后续递归获取
                servers.append({
                    'name': item['name'],
                    'path': item['path'],
                    'url': item['url'],  # 这是API URL，用于获取目录内容
                    'type': 'dir'
                })
            elif item['type'] == 'file' and item['name'].endswith('.py'):
                # 如果是Python文件，返回文件信息
                servers.append({
                    'name': item['name'],
                    'path': item['path'],
                    'url': item['html_url'],
                    'download_url': item['download_url'],
                    'type': 'file',
                    'size': item['size']
                })
        return servers

    def extract_pagination(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析GitHub API的分页信息
        Args:
            response_data: GitHub API响应头
        Returns:
            分页信息字典
        """
        # GitHub API使用Link头进行分页
        link_header = response_data.get('Link', '')
        if not link_header:
            return {'current_page': 1, 'total_pages': 1}
            
        # 解析Link头中的分页信息
        links = {}
        for link in link_header.split(','):
            url, rel = link.split(';')
            url = url.strip('<>')
            rel = rel.strip().replace('rel="', '').replace('"', '')
            links[rel] = url
            
        # 从URL中提取页码
        current_page = 1
        if 'next' in links:
            current_page = int(links['next'].split('page=')[1].split('&')[0]) - 1
        elif 'prev' in links:
            current_page = int(links['prev'].split('page=')[1].split('&')[0]) + 1
            
        # 从last链接中获取总页数
        total_pages = current_page
        if 'last' in links:
            total_pages = int(links['last'].split('page=')[1].split('&')[0])
            
        return {
            'current_page': current_page,
            'total_pages': total_pages
        }