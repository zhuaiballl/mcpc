#!/usr/bin/env python3
"""
测试MCP服务器数量统计爬虫功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from engine.stats_crawler import StatsCrawler


async def test_stats_crawler():
    """测试统计爬虫"""
    print("🧪 开始测试MCP服务器数量统计爬虫...")
    
    # 创建爬虫实例
    crawler = StatsCrawler("config/stats_config.yaml")
    
    try:
        # 运行爬虫
        stats = await crawler.run()
        
        print(f"✅ 测试完成！成功爬取了 {len(stats)} 个网站")
        
        # 显示结果
        print("\n📊 测试结果:")
        for stat in stats:
            status_icon = "✅" if stat.status == 'success' else "❌"
            print(f"  {status_icon} {stat.site_name}: {stat.server_count} 个服务器 ({stat.status})")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_stats_crawler())
    sys.exit(0 if success else 1) 