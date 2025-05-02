from .base_parser import MCPParser  # 新增基类导入
from . import parser_registry  # 新增导入注册表实例

class GitHubParser(MCPParser):  # 现在可以正确继承
    def parse_server_list(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        servers = []
        
        for item in soup.select('.Box-row'):
            # 优化关键字段提取逻辑
            name_elem = item.select_one('.h3 a')
            stars_elem = item.select_one('[aria-label="Stargazers"]')
            
            server = {
                'name': name_elem.text.strip(),
                'url': f"https://github.com{name_elem['href']}",
                'description': (item.select_one('p', class_='col-9').text.strip() 
                               if item.select_one('p') else ""),
                'last_updated': item.select_one('relative-time')['datetime'],
                'language': (item.select_one('[itemprop="programmingLanguage"]').text 
                            if item.select_one('[itemprop="programmingLanguage"]') else ""),
                'stars': int(stars_elem.text.strip().replace(',', '')) if stars_elem else 0
            }
            servers.append(server)
        return servers

    def extract_pagination(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        current_page = soup.select_one('.current')
        return {
            'current_page': int(current_page.text) if current_page else 1,
            'total_pages': len(soup.select('.BtnGroup a')) or 1
        }

# 将注册代码移到类定义之后
parser_registry.register("github_parser", GitHubParser)