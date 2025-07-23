"""
MCP服务器数量统计定时任务调度器
每小时自动运行统计爬虫
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
import yaml
from typing import Optional
import argparse

from .stats_crawler import StatsCrawler

logger = logging.getLogger(__name__)


class StatsScheduler:
    """统计任务调度器"""
    
    def __init__(self, config_path: str = "config/stats_config.yaml"):
        self.config_path = Path(config_path)
        self.crawler = StatsCrawler(config_path)
        self.running = False
        self.next_run = None
        self.interval_hours = 1  # 默认每小时运行一次
        
    def _load_scheduler_config(self) -> dict:
        """加载调度器配置"""
        if not self.config_path.exists():
            return {"interval_hours": 1}
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get("scheduler", {"interval_hours": 1})
    
    def _setup_logging(self):
        """设置日志"""
        log_config = self.crawler.config.get("logging", {})
        log_level = getattr(logging, log_config.get("level", "INFO").upper())
        log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        
        # 创建日志目录
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 文件处理器
        log_file = log_dir / "stats_scheduler.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"收到信号 {signum}，正在停止调度器...")
        self.running = False
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    async def _run_single_crawl(self):
        """运行单次爬取"""
        try:
            logger.info("开始执行统计爬取任务...")
            start_time = datetime.now()
            
            stats = await self.crawler.run()
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"统计爬取任务完成，耗时 {duration:.2f} 秒")
            
            # 记录成功统计的网站数量
            successful_count = sum(1 for stat in stats if stat.status == "success")
            total_count = len(stats)
            logger.info(f"成功爬取 {successful_count}/{total_count} 个网站")
            
            return stats
            
        except Exception as e:
            logger.error(f"统计爬取任务失败: {e}")
            return None
    
    async def _schedule_next_run(self):
        """安排下次运行时间"""
        if self.next_run is None:
            # 第一次运行，立即执行
            self.next_run = datetime.now()
        else:
            # 计算下次运行时间
            self.next_run = self.next_run + timedelta(hours=self.interval_hours)
        
        logger.info(f"下次运行时间: {self.next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    async def _wait_until_next_run(self):
        """等待到下次运行时间"""
        if self.next_run is None:
            return
        
        now = datetime.now()
        if self.next_run > now:
            wait_seconds = (self.next_run - now).total_seconds()
            logger.info(f"等待 {wait_seconds:.0f} 秒到下次运行...")
            await asyncio.sleep(wait_seconds)
    
    async def run_forever(self):
        """永久运行调度器"""
        self._setup_logging()
        self._setup_signal_handlers()
        
        # 加载调度器配置
        scheduler_config = self._load_scheduler_config()
        self.interval_hours = scheduler_config.get("interval_hours", 1)
        
        logger.info(f"启动MCP服务器数量统计调度器")
        logger.info(f"运行间隔: {self.interval_hours} 小时")
        
        self.running = True
        
        try:
            while self.running:
                await self._schedule_next_run()
                await self._wait_until_next_run()
                
                if not self.running:
                    break
                
                # 执行爬取任务
                await self._run_single_crawl()
                
        except KeyboardInterrupt:
            logger.info("收到键盘中断，正在停止...")
        except Exception as e:
            logger.error(f"调度器运行出错: {e}")
        finally:
            self.running = False
            logger.info("调度器已停止")
    
    async def run_once(self):
        """运行一次爬取任务"""
        self._setup_logging()
        logger.info("执行单次统计爬取任务")
        return await self._run_single_crawl()
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            "running": self.running,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "interval_hours": self.interval_hours
        }


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP服务器数量统计调度器")
    parser.add_argument("--once", action="store_true", help="只运行一次爬取任务")
    parser.add_argument("--config", default="config/stats_config.yaml", help="配置文件路径")
    parser.add_argument("--interval", type=int, help="运行间隔（小时）")
    
    args = parser.parse_args()
    
    scheduler = StatsScheduler(args.config)
    
    if args.interval:
        scheduler.interval_hours = args.interval
    
    if args.once:
        await scheduler.run_once()
    else:
        await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(main()) 