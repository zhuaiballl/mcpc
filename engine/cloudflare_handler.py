"""
Cloudflare保护处理模块
用于处理被Cloudflare保护的网站
"""

import asyncio
import aiohttp
import random
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CloudflareHandler:
    """Cloudflare保护处理器"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
    
    def get_realistic_headers(self) -> Dict[str, str]:
        """获取真实的浏览器请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def is_cloudflare_blocked(self, html: str) -> bool:
        """检查是否被Cloudflare拦截"""
        cloudflare_indicators = [
            'checking your browser',
            'ray id',
            'cloudflare',
            'please wait',
            'ddos protection',
            'security check'
        ]
        
        html_lower = html.lower()
        return any(indicator in html_lower for indicator in cloudflare_indicators)
    
    async def handle_cloudflare_request(self, session: aiohttp.ClientSession, url: str, 
                                      site_config: Dict[str, Any]) -> Optional[str]:
        """处理Cloudflare保护的请求"""
        
        # 获取配置参数
        max_retries = site_config.get('max_retries', 3)
        base_delay = site_config.get('request_delay', 5)
        timeout = site_config.get('timeout', 30)
        
        for attempt in range(max_retries):
            try:
                # 随机延迟，避免规律性
                delay = base_delay + random.uniform(0, 2)
                await asyncio.sleep(delay)
                
                # 使用真实的请求头
                headers = self.get_realistic_headers()
                
                # 添加Referer（如果配置了）
                if 'referer' in site_config:
                    headers['Referer'] = site_config['referer']
                
                timeout_obj = aiohttp.ClientTimeout(total=timeout)
                
                async with session.get(url, headers=headers, timeout=timeout_obj) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # 检查是否被Cloudflare拦截
                        if self.is_cloudflare_blocked(html):
                            logger.warning(f"第{attempt + 1}次尝试被Cloudflare拦截: {site_config['name']}")
                            if attempt < max_retries - 1:
                                # 增加延迟重试
                                await asyncio.sleep(base_delay * (attempt + 1))
                                continue
                            else:
                                return None
                        
                        return html
                    else:
                        logger.warning(f"HTTP {response.status} for {site_config['name']}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(base_delay)
                            continue
                        else:
                            return None
                            
            except Exception as e:
                logger.error(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(base_delay)
                    continue
                else:
                    return None
        
        return None
    
    def get_site_specific_config(self, site_name: str) -> Dict[str, Any]:
        """获取特定网站的配置"""
        configs = {
            'mcp_so': {
                'request_delay': 10,  # 更长的延迟
                'max_retries': 2,     # 减少重试次数
                'timeout': 45,        # 更长的超时
                'referer': 'https://www.google.com/',  # 添加Referer
            }
        }
        return configs.get(site_name, {}) 