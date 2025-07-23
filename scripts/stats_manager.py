#!/usr/bin/env python3
"""
MCP服务器数量统计管理工具
提供命令行接口来管理统计功能
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import yaml

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.stats_crawler import StatsCrawler
from engine.stats_scheduler import StatsScheduler


def print_stats_table(stats_data):
    """打印统计表格"""
    print("\n" + "="*80)
    print(f"{'网站名称':<15} {'服务器数量':<12} {'状态':<10} {'响应时间':<12} {'错误信息':<20}")
    print("="*80)
    
    total_servers = 0
    successful_sites = 0
    
    for stat in stats_data:
        status_icon = "✅" if stat['status'] == 'success' else "❌"
        response_time = f"{stat.get('response_time', 0):.2f}s" if stat.get('response_time') else "N/A"
        
        # 安全处理错误信息
        error_message = stat.get('error_message', '')
        if error_message is None:
            error_message = ''
        error_msg = error_message[:18] + "..." if len(error_message) > 18 else error_message
        
        print(f"{stat['site_name']:<15} {stat['server_count']:<12} {status_icon} {stat['status']:<8} {response_time:<12} {error_msg:<20}")
        
        if stat['status'] == 'success':
            total_servers += stat['server_count']
            successful_sites += 1
    
    print("="*80)
    print(f"成功爬取: {successful_sites}/{len(stats_data)} 个网站")
    print(f"总服务器数量: {total_servers}")
    print("="*80)


async def cmd_run_once(args):
    """运行一次统计爬取"""
    print("开始执行单次统计爬取...")
    
    try:
        crawler = StatsCrawler(args.config)
        stats = await crawler.run()
        
        if stats is None:
            print("❌ 爬取失败：返回结果为空")
            return None
        
        print_stats_table([stat.__dict__ for stat in stats])
        
        return stats
    except Exception as e:
        print(f"❌ 爬取过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


async def cmd_start_scheduler(args):
    """启动定时调度器"""
    print("启动MCP服务器数量统计调度器...")
    print(f"配置文件: {args.config}")
    print(f"运行间隔: {args.interval} 小时")
    print("按 Ctrl+C 停止调度器")
    
    scheduler = StatsScheduler(args.config)
    scheduler.interval_hours = args.interval
    
    await scheduler.run_forever()


def cmd_show_latest(args):
    """显示最新统计结果"""
    stats_dir = Path("stats")
    latest_file = stats_dir / "latest_stats.json"
    
    if not latest_file.exists():
        print("❌ 没有找到最新的统计结果")
        return
    
    with open(latest_file, 'r', encoding='utf-8') as f:
        stats_data = json.load(f)
    
    print(f"📊 最新统计结果 (生成时间: {stats_data[0].get('crawled_at', 'N/A')})")
    print_stats_table(stats_data)


def cmd_show_history(args):
    """显示历史统计记录"""
    stats_dir = Path("stats")
    history_file = stats_dir / "stats_history.json"
    
    if not history_file.exists():
        print("❌ 没有找到历史统计记录")
        return
    
    with open(history_file, 'r', encoding='utf-8') as f:
        history = json.load(f)
    
    print(f"📈 历史统计记录 (共 {len(history)} 条)")
    print("\n" + "="*100)
    print(f"{'时间':<20} {'网站':<15} {'服务器数量':<12} {'状态':<10}")
    print("="*100)
    
    # 显示最近的记录
    recent_records = history[-args.limit:] if args.limit else history[-10:]
    
    for record in recent_records:
        timestamp = record['timestamp']
        stats = record['stats']
        
        for stat in stats:
            status_icon = "✅" if stat['status'] == 'success' else "❌"
            print(f"{timestamp[:19]:<20} {stat['site_name']:<15} {stat['server_count']:<12} {status_icon} {stat['status']:<8}")
    
    print("="*100)


def cmd_show_config(args):
    """显示配置文件内容"""
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print(f"📋 配置文件: {config_path}")
    print("\n" + "="*50)
    print("调度器配置:")
    scheduler_config = config.get('scheduler', {})
    print(f"  运行间隔: {scheduler_config.get('interval_hours', 1)} 小时")
    
    print("\n网站配置:")
    sites = config.get('sites', [])
    for i, site in enumerate(sites, 1):
        print(f"  {i}. {site['name']}")
        print(f"     URL: {site['url']}")
        print(f"     选择器: {site['count_selector']}")
        print()


def cmd_add_site(args):
    """添加新网站配置"""
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # 检查网站是否已存在
    sites = config.get('sites', [])
    existing_names = [site['name'] for site in sites]
    
    if args.name in existing_names:
        print(f"❌ 网站 '{args.name}' 已存在")
        return
    
    # 添加新网站配置
    new_site = {
        'name': args.name,
        'url': args.url,
        'count_selector': args.selector,
        'fallback_selectors': [],
        'timeout': 30,
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    }
    
    sites.append(new_site)
    config['sites'] = sites
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ 成功添加网站配置: {args.name}")


def cmd_remove_site(args):
    """删除网站配置"""
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    sites = config.get('sites', [])
    original_count = len(sites)
    
    # 删除指定网站
    sites = [site for site in sites if site['name'] != args.name]
    
    if len(sites) == original_count:
        print(f"❌ 网站 '{args.name}' 不存在")
        return
    
    config['sites'] = sites
    
    # 保存配置
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✅ 成功删除网站配置: {args.name}")


def cmd_list_sites(args):
    """列出所有配置的网站"""
    config_path = Path(args.config)
    
    if not config_path.exists():
        print(f"❌ 配置文件不存在: {config_path}")
        return
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    sites = config.get('sites', [])
    
    if not sites:
        print("📝 没有配置任何网站")
        return
    
    print(f"📝 配置的网站列表 (共 {len(sites)} 个):")
    print("\n" + "="*80)
    print(f"{'序号':<4} {'网站名称':<15} {'URL':<50}")
    print("="*80)
    
    for i, site in enumerate(sites, 1):
        url = site['url'][:47] + "..." if len(site['url']) > 50 else site['url']
        print(f"{i:<4} {site['name']:<15} {url:<50}")
    
    print("="*80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="MCP服务器数量统计管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python scripts/stats_manager.py run-once                    # 运行一次统计爬取
  python scripts/stats_manager.py start-scheduler             # 启动定时调度器
  python scripts/stats_manager.py show-latest                 # 显示最新统计结果
  python scripts/stats_manager.py show-history                # 显示历史记录
  python scripts/stats_manager.py add-site --name test --url https://example.com --selector ".count"  # 添加网站
  python scripts/stats_manager.py remove-site --name test     # 删除网站
  python scripts/stats_manager.py list-sites                  # 列出所有网站
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # run-once 命令
    run_once_parser = subparsers.add_parser('run-once', help='运行一次统计爬取')
    run_once_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    
    # start-scheduler 命令
    scheduler_parser = subparsers.add_parser('start-scheduler', help='启动定时调度器')
    scheduler_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    scheduler_parser.add_argument('--interval', type=int, default=1, help='运行间隔（小时）')
    
    # show-latest 命令
    show_latest_parser = subparsers.add_parser('show-latest', help='显示最新统计结果')
    
    # show-history 命令
    show_history_parser = subparsers.add_parser('show-history', help='显示历史统计记录')
    show_history_parser.add_argument('--limit', type=int, help='显示记录数量限制')
    
    # show-config 命令
    show_config_parser = subparsers.add_parser('show-config', help='显示配置文件内容')
    show_config_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    
    # add-site 命令
    add_site_parser = subparsers.add_parser('add-site', help='添加新网站配置')
    add_site_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    add_site_parser.add_argument('--name', required=True, help='网站名称')
    add_site_parser.add_argument('--url', required=True, help='网站URL')
    add_site_parser.add_argument('--selector', required=True, help='数量选择器')
    
    # remove-site 命令
    remove_site_parser = subparsers.add_parser('remove-site', help='删除网站配置')
    remove_site_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    remove_site_parser.add_argument('--name', required=True, help='网站名称')
    
    # list-sites 命令
    list_sites_parser = subparsers.add_parser('list-sites', help='列出所有配置的网站')
    list_sites_parser.add_argument('--config', default='config/stats_config.yaml', help='配置文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'run-once':
            asyncio.run(cmd_run_once(args))
        elif args.command == 'start-scheduler':
            asyncio.run(cmd_start_scheduler(args))
        elif args.command == 'show-latest':
            cmd_show_latest(args)
        elif args.command == 'show-history':
            cmd_show_history(args)
        elif args.command == 'show-config':
            cmd_show_config(args)
        elif args.command == 'add-site':
            cmd_add_site(args)
        elif args.command == 'remove-site':
            cmd_remove_site(args)
        elif args.command == 'list-sites':
            cmd_list_sites(args)
    except KeyboardInterrupt:
        print("\n👋 操作已取消")
    except Exception as e:
        print(f"❌ 操作失败: {e}")


if __name__ == "__main__":
    main() 