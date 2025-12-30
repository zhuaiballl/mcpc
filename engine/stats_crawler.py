"""
MCP Server Count Statistics Crawler
Used to periodically get the number of MCP servers recorded on various websites
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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


@dataclass
class SiteStats:
    """Website statistics information"""
    site_name: str
    url: str
    server_count: int
    crawled_at: str
    status: str  # success, error, timeout
    error_message: Optional[str] = None
    response_time: Optional[float] = None


class StatsCrawler:
    """MCP server count statistics crawler"""   
    
    def __init__(self, config_path: str = "config/stats_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.session = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration file"""
        if not self.config_path.exists():
            # Create default configuration file
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
        """Save configuration file"""
        self.config_path.parent.mkdir(exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _extract_count_from_html(self, html: str, selectors: List[str]) -> Optional[int]:
        """Extract server count from HTML using specified selectors"""
        soup = BeautifulSoup(html, 'html.parser')
        
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    # Process text-containing selectors
                    text_pattern = re.search(r':contains\(["\']?([^"\']+)["\']?\)', selector)
                    if text_pattern:
                        search_text = text_pattern.group(1)
                        elements = soup.find_all(text=re.compile(search_text, re.IGNORECASE))
                        for element in elements:
                            parent = element.parent
                            if parent:
                                # Find numbers in parent element's text
                                text = parent.get_text()
                                numbers = re.findall(r'\d+', text)
                                if numbers:
                                    return int(numbers[0])
                else:
                    # Process CSS selectors with escaped characters
                    processed_selector = selector.replace('\\:', ':')
                    
                    # Process normal CSS selectors
                    elements = soup.select(processed_selector)
                    for element in elements:
                        # Try to extract number from element text
                        text = element.get_text()
                        
                        # Handle numbers with commas (e.g. "11,000")
                        # First remove commas, then extract number
                        text_clean = text.replace(',', '')
                        
                        # Extract all numbers
                        numbers = re.findall(r'\d+', text_clean)
                        if numbers:
                            # For "Showing 1-30 of 1158 servers" cases, take the last number
                            # For "11,000" cases, take the first number
                            if 'of' in text.lower() and len(numbers) > 1:
                                # If text contains "of", usually the last number is the total count
                                return int(numbers[-1])
                            else:
                                # Otherwise, take the first number
                                return int(numbers[0])
                        
                        # Try to extract number from data attributes
                        for attr in ['data-count', 'data-total', 'data-servers']:
                            if element.has_attr(attr):
                                try:
                                    return int(element[attr])
                                except (ValueError, TypeError):
                                    continue
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        return None
    
    def _selenium_count(self, site_config):
        start_time = time.time()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(site_config.get('timeout', 60))
        driver.get(site_config['url'])
        last_count = 0
        scroll_pause = 2
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            elements = driver.find_elements('css selector', site_config['selector'])
            if len(elements) == last_count:
                break
            last_count = len(elements)
        server_count = last_count
        driver.quit()
        return SiteStats(
            site_name=site_config['name'],
            url=site_config['url'],
            server_count=server_count,
            crawled_at=datetime.now().isoformat(),
            status="success",
            response_time=time.time() - start_time
        )

    def _selenium_text(self, site_config):
        import re
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        import time
        start_time = time.time()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(site_config.get('timeout', 60))
        driver.get(site_config['url'])
        selectors = [site_config['count_selector']] + site_config.get('fallback_selectors', [])
        server_count = None
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector.replace('\\:', ':'))
                for element in elements:
                    text = element.text.replace(',', '')
                    numbers = re.findall(r'\d+', text)
                    if numbers:
                        server_count = int(numbers[0])
                        break
                if server_count is not None:
                    break
            except Exception:
                continue
        driver.quit()
        if server_count is not None:
            return SiteStats(
                site_name=site_config['name'],
                url=site_config['url'],
                server_count=server_count,
                crawled_at=datetime.now().isoformat(),
                status="success",
                response_time=time.time() - start_time
            )
        else:
            return SiteStats(
                site_name=site_config['name'],
                url=site_config['url'],
                server_count=0,
                crawled_at=datetime.now().isoformat(),
                status="error",
                error_message="Selenium failed to extract server count",
                response_time=time.time() - start_time
            )

    def _selenium_pagination_count(self, site_config):
        """Count total servers using pagination"""
        start_time = time.time()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(site_config.get('timeout', 60))
        
        total_count = 0
        current_page = 1
        max_pages = site_config.get('max_pages', 100)  # Set the maximum number of pages to prevent infinite loops
        item_selector = site_config.get('item_selector', 'div.server-item')
        next_page_selector = site_config.get('next_page_selector', 'a.next-page')
        page_delay = site_config.get('page_delay', 2)  # Page load delay
        
        # Variables for speed statistics
        page_times = []  # Record processing time for each page
        
        try:
            # Visit the first page
            driver.get(site_config['url'])
            
            while current_page <= max_pages:
                # Record the start time for the current page
                page_start_time = time.time()
                
                # Wait for the page to load
                time.sleep(page_delay)
                
                # Count the number of servers on the current page
                items = driver.find_elements(By.CSS_SELECTOR, item_selector)
                current_page_count = len(items)
                total_count += current_page_count
                
                # Calculate the processing time for the current page
                page_process_time = time.time() - page_start_time
                # Record the processing time for the current page
                page_times.append(page_process_time)
                
                # Calculate the average processing speed
                avg_page_time = sum(page_times) / len(page_times) if page_times else 0
                pages_per_minute = 60 / avg_page_time if avg_page_time > 0 else 0
                items_per_minute = total_count / (time.time() - start_time) * 60 if (time.time() - start_time) > 0 else 0
                
                # Calculate the elapsed time
                elapsed_time = time.time() - start_time
                elapsed_minutes = elapsed_time / 60
                
                # Estimate the remaining time (based on average processing time and processed pages)
                estimated_remaining_pages = max_pages - current_page
                estimated_remaining_time = estimated_remaining_pages * avg_page_time
                estimated_remaining_minutes = estimated_remaining_time / 60
                
                # Record the current page processing speed information
                logger.info(f"mcp.so page {current_page}/{max_pages}: {current_page_count} servers, total: {total_count}")
                logger.info(f"  - processing speed: {pages_per_minute:.1f} pages/min, {items_per_minute:.1f} items/min")
                logger.info(f"  - elapsed time: {elapsed_minutes:.1f} minutes")
                logger.info(f"  - estimated remaining time: {estimated_remaining_minutes:.1f} minutes")
                
                # Try to find the next page button
                try:
                    next_page_button = driver.find_element(By.CSS_SELECTOR, next_page_selector)
                    # Check if the next page button is clickable
                    if next_page_button.is_enabled() and next_page_button.is_displayed():
                        # Scroll to the next page button
                        driver.execute_script("arguments[0].scrollIntoView();", next_page_button)
                        time.sleep(0.5)  # Wait for scroll to complete
                        next_page_button.click()
                        current_page += 1
                    else:
                        logger.info("Reached last page")
                        break
                except Exception as e:
                    logger.info(f"Failed to find or click next page button: {e}")
                    break
        except Exception as e:
            logger.error(f"Error occurred during pagination crawl: {e}")
        finally:
            # Calculate the total crawl time and final speed
            total_time = time.time() - start_time
            total_minutes = total_time / 60
            final_items_per_minute = total_count / total_time * 60 if total_time > 0 else 0
            
            logger.info(f"mcp.so pagination crawl completed - total server count: {total_count}")
            logger.info(f"  - total crawl time: {total_minutes:.1f} minutes")
            logger.info(f"  - average crawl speed: {final_items_per_minute:.1f} items/min")
            
            driver.quit()
        
        return SiteStats(
            site_name=site_config['name'],
            url=site_config['url'],
            server_count=total_count,
            crawled_at=datetime.now().isoformat(),
            status="success" if total_count > 0 else "error",
            error_message="Failed to extract server count through pagination" if total_count == 0 else None,
            response_time=time.time() - start_time
        )
    
    def _selenium_smithery_pagination_count(self, site_config):
        """Count total servers for smithery.ai using pagination info"""
        start_time = time.time()
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(site_config.get('timeout', 60))
        
        total_count = 0
        items_per_page = site_config.get('items_per_page', 21)
        
        try:
            # Visit the first page
            logger.info(f"Visiting smithery first page: {site_config['url']}")
            driver.get(site_config['url'])
            time.sleep(2)  # Wait for page to load
            
            # Find the last page link
            last_page_selector = site_config.get('last_page_selector')
            if not last_page_selector:
                raise ValueError("last_page_selector is required for smithery pagination")
            
            try:
                last_page_link = driver.find_element(By.CSS_SELECTOR, last_page_selector)
                last_page_text = last_page_link.text.strip()
                logger.info(f"Found last page link text: {last_page_text}")
                
                # Extract page number from the link text
                import re
                page_numbers = re.findall(r'\d+', last_page_text)
                if not page_numbers:
                    raise ValueError(f"Could not extract page number from: {last_page_text}")
                
                total_pages = int(page_numbers[0])
                logger.info(f"Total pages: {total_pages}")
                
                # Get the last page URL
                last_page_url = last_page_link.get_attribute('href')
                logger.info(f"Last page URL: {last_page_url}")
                
                # Visit the last page
                logger.info("Visiting last page to count servers...")
                driver.get(last_page_url)
                time.sleep(2)  # Wait for page to load
                
                # Count servers on the last page
                server_list_selector = site_config.get('server_list_selector')
                if not server_list_selector:
                    raise ValueError("server_list_selector is required for smithery pagination")
                
                server_elements = driver.find_elements(By.CSS_SELECTOR, server_list_selector)
                last_page_count = len(server_elements)
                logger.info(f"Last page server count: {last_page_count}")
                
                # Calculate total count: (total_pages - 1) * items_per_page + last_page_count
                total_count = (total_pages - 1) * items_per_page + last_page_count
                logger.info(f"Total server count calculated: ({total_pages} - 1) * {items_per_page} + {last_page_count} = {total_count}")
                
            except Exception as e:
                logger.error(f"Failed to extract pagination info: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error occurred during smithery pagination crawl: {e}")
            total_count = 0
        finally:
            driver.quit()
        
        return SiteStats(
            site_name=site_config['name'],
            url=site_config['url'],
            server_count=total_count,
            crawled_at=datetime.now().isoformat(),
            status="success" if total_count > 0 else "error",
            error_message="Failed to extract server count through pagination" if total_count == 0 else None,
            response_time=time.time() - start_time
        )
    
    async def crawl_site_stats(self, site_config: Dict[str, Any]) -> SiteStats:
        """Crawl statistics for a single website"""
        start_time = time.time()
        session = await self._get_session()
        
        # Get the retry configuration from the site configuration
        max_retries = site_config.get('max_retries', 1)
        retry_delay = site_config.get('retry_delay', 5)
        
        for attempt in range(max_retries + 1):
            try:
                # cursor.directory special case
                if site_config.get('type') == 'selenium_scroll_count':
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self._selenium_count, site_config)
                # mcp_market selenium_text
                if site_config.get('type') == 'selenium_text':
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self._selenium_text, site_config)
                # mcp_so selenium_pagination_count
                if site_config.get('type') == 'selenium_pagination_count':
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self._selenium_pagination_count, site_config)
                # smithery smithery_pagination_count
                if site_config.get('type') == 'smithery_pagination_count':
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, self._selenium_smithery_pagination_count, site_config)
                
                # Handle Cloudflare protected websites
                if site_config.get('cloudflare_protected', False):
                    # Use a more realistic User-Agent
                    user_agent = site_config.get('user_agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                    headers = {
                        'User-Agent': user_agent,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0',
                    }
                    
                    # Add request delay to avoid Cloudflare detection
                    request_delay = site_config.get('request_delay', 5)
                    if request_delay > 0:
                        await asyncio.sleep(request_delay)
                else:
                    headers = site_config.get('headers', {})
                
                timeout = aiohttp.ClientTimeout(total=site_config.get('timeout', 30))
                
                async with session.get(site_config['url'], headers=headers, timeout=timeout) as response:
                    response_time = time.time() - start_time
                    
                    # Handle 429 error (Too many requests)
                    if response.status == 429:
                        if attempt < max_retries:
                            logger.warning(f"Website {site_config['name']} returned 429 error, retry {attempt + 1} times, wait {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            return SiteStats(
                                site_name=site_config['name'],
                                url=site_config['url'],
                                server_count=0,
                                crawled_at=datetime.now().isoformat(),
                                status="error",
                                error_message=f"HTTP 429 - Too many requests, retried {max_retries} times",
                                response_time=response_time
                            )
                    
                    if response.status == 200:
                        html = await response.text()
                        
                        # Check if Cloudflare interception is detected
                        if 'cloudflare' in html.lower() and ('checking your browser' in html.lower() or 'ray id' in html.lower()):
                            if attempt < max_retries:
                                logger.warning(f"Website {site_config['name']} intercepted by Cloudflare, retry {attempt + 1} times, wait {retry_delay} seconds...")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                return SiteStats(
                                    site_name=site_config['name'],
                                    url=site_config['url'],
                                    server_count=0,
                                    crawled_at=datetime.now().isoformat(),
                                    status="error",
                                    error_message="Cloudflare interception detected",
                                    response_time=response_time
                                )
                        
                        # Extract server count using the primary selector
                        count_selectors = [site_config['count_selector']] + site_config.get('fallback_selectors', [])
                        server_count = await self._extract_count_from_html(html, count_selectors)
                        
                        # Successfully extracted server count
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
                                error_message="Failed to extract server count",
                                response_time=response_time
                            )
                    else:
                        if attempt < max_retries and response.status in [429, 500, 502, 503, 504]:
                            logger.warning(f"Website {site_config['name']} returned HTTP {response.status}, retry {attempt + 1} times, wait {retry_delay} seconds...")
                            await asyncio.sleep(retry_delay)
                            continue
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
                if attempt < max_retries:
                    logger.warning(f"Website {site_config['name']} request timeout, retry {attempt + 1} times, wait {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return SiteStats(
                        site_name=site_config['name'],
                        url=site_config['url'],
                        server_count=0,
                        crawled_at=datetime.now().isoformat(),
                        status="timeout",
                        error_message="Request timeout",
                        response_time=time.time() - start_time
                    )
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Website {site_config['name']} request failed: {e}, retry {attempt + 1} times, wait {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
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
        """Crawl statistics for all sites"""
        tasks = []
        for site_config in self.config['sites']:
            task = self.crawl_site_stats(site_config)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process exception results
        stats = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                site_config = self.config['sites'][i]
                logger.error(f"Website {site_config['name']} crawl failed: {result}")
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
        """Save statistics results"""
        output_dir = Path(self.config['output_dir'])
        output_dir.mkdir(exist_ok=True)
        
        # Save current statistics results
        current_file = output_dir / f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(current_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(stat) for stat in stats], f, ensure_ascii=False, indent=2)
        
        # Save latest statistics results
        latest_file = output_dir / "latest_stats.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump([asdict(stat) for stat in stats], f, ensure_ascii=False, indent=2)
        
        # Update history records
        history_file = output_dir / "stats_history.json"
        history = []
        if history_file.exists():
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # Add new statistics record
        history.append({
            "timestamp": datetime.now().isoformat(),
            "stats": [asdict(stat) for stat in stats]
        })
        
        # Keep only the latest 100 records
        if len(history) > 100:
            history = history[-100:]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Statistics results saved to {current_file}")
        
    def generate_report(self, stats: List[SiteStats]) -> str:
        """Generate statistics report"""
        report = []
        report.append("# MCP Server Count Statistics Report")
        report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        total_servers = 0
        successful_sites = 0
        
        for stat in stats:
            report.append(f"## {stat.site_name}")
            report.append(f"- URL: {stat.url}")
            report.append(f"- Server Count: {stat.server_count}")
            report.append(f"- Status: {stat.status}")
            
            if stat.response_time:
                report.append(f"- Response Time: {stat.response_time:.2f} seconds")
            
            if stat.error_message:
                report.append(f"- Error Message: {stat.error_message}")
            
            report.append("")
            
            if stat.status == "success":
                total_servers += stat.server_count
                successful_sites += 1
        
        report.append("## Summary")
        report.append(f"- Successfully crawled websites: {successful_sites}/{len(stats)}")
        report.append(f"- Total server count: {total_servers}")
        report.append("")
        
        return "\n".join(report)
    
    async def run(self):
        """Run statistics crawler"""
        logger.info("Start crawling MCP server count statistics...")
        
        try:
            stats = await self.crawl_all_sites()
            self.save_stats(stats)
            
            # Generate statistics report
            report = self.generate_report(stats)
            output_dir = Path(self.config['output_dir'])
            report_file = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            logger.info(f"Statistics report generated: {report_file}")
            logger.info("MCP server count statistics crawl completed")
            
            return stats
            
        except Exception as e:
            logger.error(f"Statistics crawler run failed: {e}")
            raise
        finally:
            if self.session and not self.session.closed:
                await self.session.close()


async def main():
    """Main function"""
    crawler = StatsCrawler()
    await crawler.run()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())