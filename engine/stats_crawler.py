"""
MCP服务器数量统计爬虫
用于定期获取各个网站收录的MCP服务器数量
"""

import asyncio
import aiohttp
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import yaml
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)


@dataclass
class SiteStats:
    """网站统计信息"""
    site_name: str
    url: str
    server_count: int
    crawled_at: str
    status: str  # success, error, timeout
    error_message: Optional[str] = None
    response_time: Optional[float] = None


class StatsCrawler:
    """MCP服务器数量统计爬虫"""
    
    def __init__(self, config_path: str = "config/stats_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.session = None
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if not self.config_path.exists():
            # 创建默认配置
            default_config = {
                "sites": [
                    {
                        "name": "smithery",
                        "url": "https://registry.smithery.ai/servers",
                        "count_selector": ".server-count, .total-count, [data-count]",
                        "fallback_selectors": [
                            "h1:contains('servers')",
                            ".stats .number",
                            ".total-servers"
                        ],
                        "timeout": 30,
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                        }
                    }
                ],
                "output_dir": "stats",
                "log_file": "stats_crawler.log"
            }
            self._save_config(default_config)
            return default_config
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _save_config(self, config: Dict[str, Any]):
        """保存配置文件"""
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _extract_count_from_html(self, html: str, selectors: List[str]) -> Optional[int]:
        """从HTML中提取数量"""
        soup = BeautifulSoup(html, 'html.parser')
        
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    # 处理包含文本的选择器
                    text_pattern = re.search(r':contains\(["\']?([^"\']+)["\']?\)', selector)
                    if text_pattern:
                        search_text = text_pattern.group(1)
                        elements = soup.find_all(text=re.compile(search_text, re.IGNORECASE))
                        for element in elements:
                            parent = element.parent
                            if parent:
                                # 查找父元素中的数字
                                text = parent.get_text()
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    return int(numbers[0])
                else:
                    # 处理CSS选择器中的转义字符
                    # 将 \: 转换为 : 用于CSS选择器
                    processed_selector = selector.replace('\\:', ':')
                    
                    # 普通CSS选择器
                    elements = soup.select(processed_selector)
                    for element in elements:
                        # 尝试从元素文本中提取数字
                        text = element.get_text()
                        
                        # 处理包含千位分隔符的数字 (如 "11,000")
                        # 先移除逗号，然后提取数字
                        text_clean = text.replace(',', '')
                        
                        # 提取所有数字
                        numbers = re.findall(r'\d+', text_clean)
                        if numbers:
                            # 对于 "Showing 1-30 of 1158 servers" 这种情况，取最后一个数字
                            # 对于 "11,000" 这种情况，取第一个数字
                            if 'of' in text.lower() and len(numbers) > 1:
                                # 如果文本包含 "of"，通常最后一个数字是总数
                                return int(numbers[-1])
                            else:
                                # 否则取第一个数字
                                return int(numbers[0])
                        
                        # 尝试从data属性中获取
                        for attr in ['data-count', 'data-total', 'data-servers']:
                            if element.has_attr(attr):
                                try:
                                    return int(element[attr])
                                except (ValueError, TypeError):
                                    continue
            except Exception as e:
                logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        return None
    
    async def crawl_site_stats(self, site_config: Dict[str, Any]) -> SiteStats:
        """爬取单个网站的统计信息"""
        start_time = time.time()
        session = await self._get_session()
        
        try:
            # 处理Cloudflare保护的网站
            if site_config.get('cloudflare_protected', False):
                # 使用更真实的User-Agent
                user_agent = site_config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                headers = {
                    'User-Agent': user_agent,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
                
                # 添加请求延迟
                request_delay = site_config.get('request_delay', 5)
                if request_delay > 0:
                    await asyncio.sleep(request_delay)
            else:
                headers = site_config.get('headers', {})
            
            timeout = aiohttp.ClientTimeout(total=site_config.get('timeout', 30))
            
            async with session.get(site_config['url'], headers=headers, timeout=timeout) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    html = await response.text()
                    
                    # 检查是否被Cloudflare拦截
                    if 'cloudflare' in html.lower() and ('checking your browser' in html.lower() or 'ray id' in html.lower()):
                        return SiteStats(
                            site_name=site_config['name'],
                            url=site_config['url'],
                            server_count=0,
                            crawled_at=datetime.now().isoformat(),
                            status="error",
                            error_message="被Cloudflare拦截",
                            response_time=response_time
                        )
                    
                    # 提取数量
                    count_selectors = [site_config['count_selector']] + site_config.get('fallback_selectors', [])
                    server_count = await self._extract_count_from_html(html, count_selectors)
                    
                    if server_count is not None:
                        return SiteStats(
                            site_name=site_config['name'],
                            url=site_config['url'],
                            server_count=server_count,
                            crawled_at=datetime.now().isoformat(),
                            status="success",
                            response_time=response_time
                        )
                    else:
                        return SiteStats(
                            site_name=site_config['name'],
                            url=site_config['url'],
                            server_count=0,
                            crawled_at=datetime.now().isoformat(),
                            status="error",
                            error_message="无法提取服务器数量",
                            response_time=response_time
                        )
                else:
                    return SiteStats(
                        site_name=site_config['name'],
                        url=site_config['url'],
                        server_count=0,
                        crawled_at=datetime.now().isoformat(),
                        status="error",
                        error_message=f"HTTP {response.status}",
                        response_time=time.time() - start_time
                    )
                    
        except asyncio.TimeoutError:
            return SiteStats(
                site_name=site_config['name'],
                url=site_config['url'],
                server_count=0,
                crawled_at=datetime.now().isoformat(),
                status="timeout",
                error_message="请求超时",
                response_time=time.time() - start_time
            )
        except Exception as e:
            return SiteStats(
                site_name=site_config['name'],
                url=site_config['url'],
                server_count=0,
                crawled_at=datetime.now().isoformat(),
                status="error",
                error_message=str(e),
                response_time=time.time() - start_time
            )
    
    async def crawl_all_sites(self) -> List[SiteStats]:
        """爬取所有网站的统计信息"""
        tasks = []
        for site_config in self.config['sites']:
            task = self.crawl_site_stats(site_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        stats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                site_config = self.config['sites'][i]
                logger.error(f"网站 {site_config['name']} 爬取失败: {result}")
                stats.append(SiteStats(
                    site_name=site_config['name'],
                    url=site_config['url'],
                    server_count=0,
                    crawled_at=datetime.now().isoformat(),
                    status="error",
                    error_message=str(result)
                ))
            else:
                stats.append(result)
        
        return stats
    
    def save_stats(self, stats: List[SiteStats]):
        """保存统计结果"""
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(exist_ok=True)
        
        # 保存当前统计结果
        current_file = output_dir / f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(current_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(stat) for stat in stats], f, ensure_ascii=False, indent=2)
        
        # 保存最新统计结果
        latest_file = output_dir / "latest_stats.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(stat) for stat in stats], f, ensure_ascii=False, indent=2)
        
        # 更新历史记录
        history_file = output_dir / "stats_history.json"
        history = []
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # 添加新的统计记录
        history.append({
            "timestamp": datetime.now().isoformat(),
            "stats": [asdict(stat) for stat in stats]
        })
        
        # 只保留最近100条记录
        if len(history) > 100:
            history = history[-100:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"统计结果已保存到 {current_file}")
    
    def generate_report(self, stats: List[SiteStats]) -> str:
        """生成统计报告"""
        report = []
        report.append("# MCP服务器数量统计报告")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_servers = 0
        successful_sites = 0
        
        for stat in stats:
            report.append(f"## {stat.site_name}")
            report.append(f"- URL: {stat.url}")
            report.append(f"- 服务器数量: {stat.server_count}")
            report.append(f"- 状态: {stat.status}")
            
            if stat.response_time:
                report.append(f"- 响应时间: {stat.response_time:.2f}秒")
            
            if stat.error_message:
                report.append(f"- 错误信息: {stat.error_message}")
            
            report.append("")
            
            if stat.status == "success":
                total_servers += stat.server_count
                successful_sites += 1
        
        report.append("## 汇总")
        report.append(f"- 成功爬取的网站: {successful_sites}/{len(stats)}")
        report.append(f"- 总服务器数量: {total_servers}")
        report.append("")
        
        return "\n".join(report)
    
    async def run(self):
        """运行统计爬虫"""
        logger.info("开始爬取MCP服务器数量统计...")
        
        try:
            stats = await self.crawl_all_sites()
            self.save_stats(stats)
            
            # 生成报告
            report = self.generate_report(stats)
            output_dir = Path(self.config['output_dir'])
            report_file = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"统计报告已生成: {report_file}")
            logger.info("MCP服务器数量统计完成")
            
            return stats
            
        except Exception as e:
            logger.error(f"统计爬虫运行失败: {e}")
            raise
        finally:
            if self.session and not self.session.closed:
                await self.session.close()


async def main():
    """主函数"""
    crawler = StatsCrawler()
    await crawler.run()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 