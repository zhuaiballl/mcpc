import json
import os
import asyncio
from pathlib import Path
from .distributed_crawler import DistributedCrawler
from .smithery_crawler import SmitheryCrawler

if __name__ == "__main__":
    async def run():
        # 处理modelcontextprotocol数据
        modelcontext_crawler = DistributedCrawler("config/sites_config.yaml")
        modelcontext_results = []
        async for result in modelcontext_crawler.crawl_site(modelcontext_crawler.configs[0]):
            print(f"已抓取到 {len(result)} 条modelcontextprotocol服务器数据")
            modelcontext_results.extend(result)
        
        # 保存modelcontextprotocol服务器的元数据
        metadata_path = modelcontext_crawler.base_dir / "modelcontextprotocol" / "all_servers.modelcontextprotocol.io.json"
        with open(metadata_path, 'w') as f:
            json.dump(modelcontext_results, f, indent=2)
        print(f"modelcontextprotocol数据已保存至 {os.path.abspath(metadata_path)}")
        
        # 处理smithery数据
        smithery_crawler = SmitheryCrawler("config/sites_config.yaml")
        smithery_results = []
        async for result in smithery_crawler.crawl_site(smithery_crawler.configs[1]):
            print(f"已抓取到 {len(result.get('servers', []))} 条smithery服务器数据")
            smithery_results.extend(result.get('servers', []))
        
        # 保存smithery服务器的元数据
        metadata_path = smithery_crawler.base_dir / "smithery" / "all_servers.smithery.json"
        with open(metadata_path, 'w') as f:
            json.dump(smithery_results, f, indent=2)
        print(f"smithery数据已保存至 {os.path.abspath(metadata_path)}")
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())