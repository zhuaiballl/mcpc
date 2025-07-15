import json
import os
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, AsyncIterator, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from .client_crawler import ClientCrawler
import re

class GlamaClientCrawler(ClientCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.output_dir = self.base_dir / "glama"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self._setup_selenium()

    def _setup_selenium(self):
        """设置Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # 设置用户代理
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("Selenium WebDriver 初始化成功")
        except Exception as e:
            print(f"Selenium WebDriver 初始化失败: {str(e)}")
            raise

    def __del__(self):
        """析构函数，确保关闭WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    async def _parse_client_list(self) -> List[Dict[str, Any]]:
        """解析client列表页面
        Returns:
            List[Dict[str, Any]]: client列表
        """
        clients = []
        
        try:
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "ul"))
            )
            
            # 获取所有client列表项
            client_items = self.driver.find_elements(By.XPATH, "//ul/li")
            print(f"找到 {len(client_items)} 个client列表项")
            
            for item in client_items:
                try:
                    client_data = self._parse_client_item(item)
                    if client_data:
                        clients.append(client_data)
                except Exception as e:
                    print(f"解析client项时发生错误: {str(e)}")
                    continue
                    
        except TimeoutException:
            print("页面加载超时")
        except Exception as e:
            print(f"解析client列表时发生错误: {str(e)}")
            
        return clients

    def _parse_client_item(self, item_element) -> Dict[str, Any]:
        """解析单个client项
        Args:
            item_element: Selenium WebElement
        Returns:
            Dict[str, Any]: client数据
        """
        try:
            # 获取client名称
            name_element = item_element.find_element(By.XPATH, ".//h2/a")
            name = name_element.text.strip()
            detail_url = name_element.get_attribute("href")
            
            # 获取描述
            description_element = item_element.find_element(By.XPATH, ".//p")
            description = description_element.text.strip()
            
            # 获取分类标签
            categories = []
            try:
                category_elements = item_element.find_elements(By.XPATH, ".//ul/div[contains(@class, 'czikZZ')]")
                for cat_element in category_elements:
                    category = cat_element.text.strip()
                    if category:
                        categories.append(category)
            except NoSuchElementException:
                # 如果没有找到分类标签，尝试其他选择器
                try:
                    category_elements = item_element.find_elements(By.XPATH, ".//div[contains(@class, 'czikZZ')]")
                    for cat_element in category_elements:
                        category = cat_element.text.strip()
                        if category and category not in categories:
                            categories.append(category)
                except:
                    pass
            
            # 构建client数据
            client_data = {
                'name': name,
                'description': description,
                'detail_url': detail_url,
                'github_url': '',  # 暂时为空，需要访问详情页面获取
                'categories': categories,
                'source': 'glama',
                'crawled_at': datetime.now().isoformat()
            }
            
            print(f"解析到client: {name}")
            return client_data
            
        except Exception as e:
            print(f"解析client项时发生错误: {str(e)}")
            return None

    async def _get_github_url_from_detail_page(self, detail_url: str) -> str:
        """从详情页面获取GitHub URL
        Args:
            detail_url: 详情页面URL
        Returns:
            GitHub URL，如果没有找到则返回空字符串
        """
        try:
            print(f"访问详情页面: {detail_url}")
            self.driver.get(detail_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 查找GitHub链接
            github_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'github.com')]")
            
            for link in github_links:
                href = link.get_attribute("href")
                if href and "github.com" in href:
                    # 过滤掉issue创建链接
                    if "issues/new" not in href:
                        print(f"找到GitHub链接: {href}")
                        return href
            
            # 如果没有找到GitHub链接，尝试其他方式
            # 查找包含"GitHub"、"Repository"等关键词的链接
            repo_keywords = ["github", "repository", "repo", "source"]
            for keyword in repo_keywords:
                try:
                    elements = self.driver.find_elements(By.XPATH, f"//a[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{keyword}')]")
                    for element in elements:
                        href = element.get_attribute("href")
                        if href and "github.com" in href and "issues/new" not in href:
                            print(f"通过关键词'{keyword}'找到GitHub链接: {href}")
                            return href
                except:
                    continue
            
            print(f"在详情页面 {detail_url} 中没有找到GitHub链接")
            return ""
            
        except Exception as e:
            print(f"获取详情页面时发生错误: {str(e)}")
            return ""

    async def crawl_site(self, site_config) -> AsyncIterator[Dict[str, Any]]:
        """抓取glama.ai client数据
        Args:
            site_config: 站点配置
        Returns:
            AsyncIterator[Dict[str, Any]]: 异步迭代器
        """
        try:
            url = site_config.get('url', 'https://glama.ai/mcp/clients')
            print(f"开始抓取glama.ai client数据: {url}")
            
            # 访问页面
            self.driver.get(url)
            
            # 等待页面加载
            time.sleep(3)
            
            # 解析client列表
            clients = await self._parse_client_list()
            print(f"总共解析到 {len(clients)} 个client")
            
            # 处理每个client
            for i, client in enumerate(clients, 1):
                print(f"处理第 {i}/{len(clients)} 个client: {client['name']}")
                
                # 获取GitHub URL
                if client['detail_url']:
                    github_url = await self._get_github_url_from_detail_page(client['detail_url'])
                    client['github_url'] = github_url
                
                # 添加延迟避免请求过快
                time.sleep(1)
            
            # 保存所有client的汇总信息
            all_clients_path = self.output_dir / "glama.json"
            with open(all_clients_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'source': 'glama',
                    'total_count': len(clients),
                    'crawled_at': datetime.now().isoformat(),
                    'clients': clients
                }, f, indent=2, ensure_ascii=False)
            
            print(f"已保存所有client汇总信息: {all_clients_path}")
            
            yield {'clients': clients, 'total_count': len(clients)}
            
        except Exception as e:
            print(f"抓取过程中发生错误: {str(e)}")
            raise

    async def run(self):
        """运行爬虫"""
        try:
            # 查找glama配置
            glama_config = None
            for config in self.configs:
                if 'glama' in config.get('name', ''):
                    glama_config = config
                    break
            
            if not glama_config:
                # 如果没有找到配置，使用默认配置
                glama_config = {
                    'name': 'glama_clients',
                    'url': 'https://glama.ai/mcp/clients',
                    'parser': 'glama_client_parser'
                }
            
            async for data in self.crawl_site(glama_config):
                print(f"抓取完成，共获取 {data.get('total_count', 0)} 个client")
                
        except Exception as e:
            print(f"运行爬虫时发生错误: {str(e)}")
            raise
        finally:
            if self.driver:
                self.driver.quit() 