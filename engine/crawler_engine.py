import json
import os
import asyncio
from pathlib import Path
from .distributed_crawler import DistributedCrawler
from .smithery_crawler import SmitheryCrawler
import argparse
import yaml

def main():
    parser = argparse.ArgumentParser(description='Crawler Engine')
    parser.add_argument('--config', type=str, required=True, help='Path to the configuration file')
    parser.add_argument('--sources', type=str, nargs='+', help='List of data sources to crawl (e.g., smithery modelcontextprotocol)')
    args = parser.parse_args()

    # 加载配置
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # 获取所有可用的爬虫类
    crawler_classes = {
        'smithery': SmitheryCrawler,
        'modelcontextprotocol': DistributedCrawler
    }

    # 如果没有指定数据源，则抓取所有数据源
    sources_to_crawl = args.sources if args.sources else list(crawler_classes.keys())

    # 验证指定的数据源是否有效
    invalid_sources = [source for source in sources_to_crawl if source not in crawler_classes]
    if invalid_sources:
        print(f"Error: Invalid data sources specified: {', '.join(invalid_sources)}")
        print(f"Available data sources: {', '.join(crawler_classes.keys())}")
        return

    # 创建输出目录
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

if __name__ == "__main__":
    main()