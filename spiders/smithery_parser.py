from .base_parser import MCPParser
from typing import Dict, List, Any

class SmitheryParser(MCPParser):
    def parse_server_list(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析Smithery API返回的服务器列表
        Args:
            response_data: Smithery API返回的服务器列表JSON数据
        Returns:
            解析后的服务器列表
        """
        servers = []
        for server in response_data.get('servers', []):
            servers.append({
                'qualified_name': server['qualifiedName'],
                'display_name': server['displayName'],
                'description': server['description'],
                'homepage': server['homepage'],
                'use_count': server['useCount'],
                'is_deployed': server['isDeployed'],
                'created_at': server['createdAt'],
                'source': 'smithery'
            })
        return servers

    def extract_pagination(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """解析Smithery API的分页信息
        Args:
            response_data: Smithery API响应数据
        Returns:
            分页信息字典
        """
        pagination = response_data.get('pagination', {})
        return {
            'current_page': pagination.get('currentPage', 1),
            'total_pages': pagination.get('totalPages', 1),
            'page_size': pagination.get('pageSize', 10),
            'total_count': pagination.get('totalCount', 0)
        } 