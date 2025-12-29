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
from .category_crawler import CategoryCrawler

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
    parser.add_argument('--categories-only', action='store_true', help='Only crawl categories for existing data sources')
    parser.add_argument('--categories-source', type=str, help='Crawl categories for specific data source')
    args = parser.parse_args()

    if args.download_only or args.download_source:
        downloader = SourceDownloader()
        if args.download_source:
            downloader.download_sources_for_data_source(args.download_source)
        else:
            downloader.download_all_sources()
        return
    
    if args.categories_only or args.categories_source:
        category_crawler = CategoryCrawler(Path("."))
        if args.categories_source:
            # crawl categories for specific data source
            if args.categories_source == 'smithery':
                category_crawler.crawl_smithery_categories()
            elif args.categories_source == 'pulse':
                category_crawler.crawl_pulse_categories()
            elif args.categories_source == 'cursor':
                category_crawler.crawl_cursor_categories()
            elif args.categories_source == 'awesome':
                category_crawler.crawl_awesome_categories()
            elif args.categories_source == 'glama':
                category_crawler.crawl_glama_categories()
            else:
                print(f"Error: Unknown data source for categories: {args.categories_source}")
                return
        else:
            # crawl categories for all data sources
            category_crawler.crawl_smithery_categories()
            category_crawler.crawl_pulse_categories()
            category_crawler.crawl_cursor_categories()
            category_crawler.crawl_awesome_categories()
            category_crawler.crawl_glama_categories()
        return

    # load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Get available crawler classes
    crawler_classes = {
        # Server crawler
        'smithery': SmitheryCrawler,
        'modelcontextprotocol': DistributedCrawler,
        'pulse': PulseCrawler,
        'cursor': CursorCrawler,
        'awesome': AwesomeMcpCrawler,
        'glama': GlamaCrawler,
        
        # Client crawler
        'glama_clients': GlamaClientCrawler,
    }

    # filter data sources based on type
    if args.type == 'servers':
        # run server crawlers
        sources_to_crawl = [source for source in (args.sources or list(crawler_classes.keys())) 
                           if source not in ['glama_clients']]
    elif args.type == 'clients':
        # run client crawlers
        sources_to_crawl = [source for source in (args.sources or list(crawler_classes.keys())) 
                           if source in ['glama_clients']]
    else:
        # run all crawlers
        sources_to_crawl = args.sources if args.sources else list(crawler_classes.keys())

    # verify specified data sources
    invalid_sources = [source for source in sources_to_crawl if source not in crawler_classes]
    if invalid_sources:
        print(f"Error: Invalid data sources specified: {', '.join(invalid_sources)}")
        print(f"Available data sources: {', '.join(crawler_classes.keys())}")
        return

    # create output directory
    if args.type == 'clients':
        output_dir = Path("mcp_clients")
    else:
        output_dir = Path("mcp_servers")
    output_dir.mkdir(exist_ok=True)

    # save config info
    with open(output_dir / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    # create crawler instances and run
    for source in sources_to_crawl:
        print(f"\nStart crawling {source} data source...")
        crawler_class = crawler_classes[source]
        crawler = crawler_class(args.config)
        asyncio.run(crawler.run())
        print(f"Finish crawling {source} data source")

    # if download sources is specified and type is not clients
    if args.download_sources and args.type != 'clients':
        print(f"\nStart downloading server source code...")
        downloader = SourceDownloader()
        for source in sources_to_crawl:
            if source in ['smithery', 'pulse', 'cursor', 'awesome', 'glama', 'modelcontextprotocol']:
                print(f"\nDownload source code for {source} data source...")
                downloader.download_sources_for_data_source(source)

if __name__ == "__main__":
    main()