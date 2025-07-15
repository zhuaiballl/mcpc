import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, AsyncIterator
from .distributed_crawler import DistributedCrawler

class ClientCrawler(DistributedCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.base_dir = Path("mcp_clients")  # 改为clients目录
        self.base_dir.mkdir(exist_ok=True)

    def _normalize_client_name(self, name: str) -> str:
        """规范化client名称，保留空格但移除其他特殊字符
        Args:
            name: 原始client名称
        Returns:
            规范化后的名称
        """
        # 保留空格，移除其他特殊字符
        import re
        normalized = re.sub(r'[^\w\s-]', '', name)
        # 将多个空格替换为单个空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    async def _get_github_url_from_detail_page(self, detail_url: str) -> str:
        """从详情页面获取GitHub URL
        Args:
            detail_url: 详情页面URL
        Returns:
            GitHub URL，如果没有找到则返回空字符串
        """
        try:
            response = self.session.get(detail_url)
            if response.status_code == 200:
                # 这里需要根据具体网站的HTML结构来解析GitHub链接
                # 暂时返回空字符串，具体实现由子类重写
                return ""
            else:
                print(f"获取详情页面失败: {response.status_code}")
                return ""
        except Exception as e:
            print(f"获取详情页面时发生错误: {str(e)}")
            return "" 