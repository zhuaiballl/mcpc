import json
import os
import asyncio
from pathlib import Path
from .distributed_crawler import DistributedCrawler
from .smithery_crawler import SmitheryCrawler
from .pulse_crawler import PulseCrawler
from .awesome_mcp_crawler import AwesomeMcpCrawler
from .cursor_crawler import CursorCrawler
from .glama_crawler import GlamaCrawler
from .glama_client_crawler import GlamaClientCrawler
from .source_downloader import SourceDownloader

import argparse
import yaml

def main():
    parser = argparse.ArgumentParser(description='Crawler Engine')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('--sources', type=str, nargs='+', help='List of data sources to crawl (e.g., smithery modelcontextprotocol pulse)')
    parser.add_argument('--type', choices=['servers', 'clients', 'all'], default='all', help='Type of data to crawl')
    parser.add_argument('--download-sources', action='store_true', help='Download server source code after crawling metadata')
    parser.add_argument('--download-only', action='store_true', help='Only download source code from existing metadata files')
    parser.add_argument('--download-source', type=str, help='Download source code for specific data source')
    args = parser.parse_args()

    # 如果只是下载源码
    if args.download_only or args.download_source:
        downloader = SourceDownloader()
        if args.download_source:
            downloader.download_sources_for_data_source(args.download_source)
        else:
            downloader.download_all_sources()
        return

    # 加载配置
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # 获取所有可用的爬虫类
    crawler_classes = {
        # Server爬虫
        'smithery': SmitheryCrawler,
        'modelcontextprotocol': DistributedCrawler,
        'pulse': PulseCrawler,
        'cursor': CursorCrawler,
        'awesome': AwesomeMcpCrawler,
        'glama': GlamaCrawler,
        
        # Client爬虫
        'glama_clients': GlamaClientCrawler,
    }

    # 根据类型过滤数据源
    if args.type == 'servers':
        # 只运行server爬虫
        sources_to_crawl = [source for source in (args.sources or list(crawler_classes.keys())) 
                           if source not in ['glama_clients']]
    elif args.type == 'clients':
        # 只运行client爬虫
        sources_to_crawl = [source for source in (args.sources or list(crawler_classes.keys())) 
                           if source in ['glama_clients']]
    else:
        # 运行所有爬虫
        sources_to_crawl = args.sources if args.sources else list(crawler_classes.keys())

    # 验证指定的数据源是否有效
    invalid_sources = [source for source in sources_to_crawl if source not in crawler_classes]
    if invalid_sources:
        print(f"Error: Invalid data sources specified: {', '.join(invalid_sources)}")
        print(f"Available data sources: {', '.join(crawler_classes.keys())}")
        return

    # 创建输出目录
    if args.type == 'clients':
        output_dir = Path("mcp_clients")
    else:
        output_dir = Path("mcp_servers")
    output_dir.mkdir(exist_ok=True)

    # 保存配置信息
    with open(output_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # 创建爬虫实例并运行
    for source in sources_to_crawl:
        print(f"\n开始抓取 {source} 数据源...")
        crawler_class = crawler_classes[source]
        crawler = crawler_class(args.config)
        asyncio.run(crawler.run())
        print(f"完成抓取 {source} 数据源")

    # 如果需要下载源码
    if args.download_sources and args.type != 'clients':
        print(f"\n开始下载server源码...")
        downloader = SourceDownloader()
        for source in sources_to_crawl:
            if source in ['smithery', 'pulse', 'cursor', 'awesome', 'glama', 'modelcontextprotocol']:
                print(f"\n下载 {source} 数据源的源码...")
                downloader.download_sources_for_data_source(source)

if __name__ == "__main__":
    main()