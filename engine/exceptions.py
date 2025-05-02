class CrawlExhausted(Exception):
    """爬取任务耗尽异常"""
    def __init__(self, message="无更多可抓取内容"):
        super().__init__(message)