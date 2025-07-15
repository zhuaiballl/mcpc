# MCP Client 抓取功能

本项目现在支持抓取MCP Client信息，与现有的Server抓取功能并行。

## 功能特点

- 支持抓取多个数据源的MCP Client信息
- 使用Selenium处理动态加载的网页内容
- 自动获取GitHub仓库链接
- 保存完整的client元数据
- 支持分类标签提取

## 数据结构

每个Client的数据结构如下：

```json
{
  "name": "Client Name",  // 可以包含空格
  "description": "网站上关于该client的描述信息",
  "detail_url": "https://example.com/client-page",  // 详情页面链接
  "github_url": "https://github.com/example/client-repo",  // GitHub仓库链接
  "categories": ["chat", "development", "productivity"],  // 分类标签数组
  "source": "glama",  // 数据来源
  "crawled_at": "2024-01-01T12:00:00Z"  // 抓取时间戳
}
```

## 使用方法

### 1. 抓取所有Client数据

```bash
python -m engine.crawler_engine --config config/sites_config.yaml --type clients
```

### 2. 抓取特定数据源的Client

```bash
python -m engine.crawler_engine --config config/sites_config.yaml --type clients --sources glama_clients
```

### 3. 抓取所有数据（Server + Client）

```bash
python -m engine.crawler_engine --config config/sites_config.yaml --type all
```

### 4. 测试特定Client爬虫

```bash
python test_glama_client.py
```

## 输出目录结构

```
mcp_clients/
├── glama/
│   └── glama.json  # 所有glama clients的汇总信息
├── pulse/
│   └── pulse.json  # 所有pulse clients的汇总信息
└── config.json
```

### 汇总文件格式

```json
{
  "source": "glama",
  "total_count": 37,
  "crawled_at": "2024-01-01T12:00:00Z",
  "clients": [
    {
      "name": "5ire",
      "description": "5ire is a cross-platform desktop AI assistant, MCP client...",
      "detail_url": "https://glama.ai/mcp/clients/5ire",
      "github_url": "https://github.com/nanbingxyz/5ire",
      "categories": ["Desktop"],
      "source": "glama",
      "crawled_at": "2024-01-01T12:00:00Z"
    }
    // ... 更多client数据
  ]
}
```

## 支持的数据源

### 1. Glama.ai

- **URL**: https://glama.ai/mcp/clients
- **特点**: 使用Selenium处理动态内容
- **数据**: name, description, detail_url, github_url, categories
- **爬虫类**: `GlamaClientCrawler`

## 配置说明

在 `config/sites_config.yaml` 中添加client数据源配置：

```yaml
- name: "glama_clients"
  url: "https://glama.ai/mcp/clients"
  parser: "glama_client_parser"
  headers:
    Accept: "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    User-Agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
  error_handling:
    max_retries: 3
    retry_delay: 5
    rate_limit_wait: 60
```

## 环境要求

1. **Python 3.8+**
2. **Chrome浏览器**: 用于Selenium
3. **ChromeDriver**: 与Chrome版本匹配
4. **依赖包**: 见 `requirements.txt`

### 安装ChromeDriver

```bash
# 检查Chrome版本
google-chrome --version

# 下载对应版本的ChromeDriver
# 从 https://googlechromelabs.github.io/chrome-for-testing/ 下载

# 安装ChromeDriver
sudo mkdir -p /usr/local/bin
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

## 扩展新的Client数据源

要添加新的client数据源，需要：

1. **创建爬虫类**: 继承 `ClientCrawler`
2. **创建解析器**: 继承 `MCPClientParser`
3. **更新配置**: 在 `sites_config.yaml` 中添加配置
4. **注册爬虫**: 在 `crawler_engine.py` 中注册

### 示例：添加新的Client爬虫

```python
# engine/new_client_crawler.py
from .client_crawler import ClientCrawler

class NewClientCrawler(ClientCrawler):
    def __init__(self, config_path):
        super().__init__(config_path)
        self.output_dir = self.base_dir / "new_source"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def crawl_site(self, site_config):
        # 实现具体的抓取逻辑
        # 最后保存汇总文件到 new_source.json
        pass
```

## 注意事项

1. **Selenium依赖**: Client爬虫使用Selenium处理动态内容，需要Chrome浏览器和ChromeDriver
2. **请求频率**: 添加了延迟避免请求过快
3. **错误处理**: 包含重试机制和错误日志
4. **数据去重**: 支持按名称去重
5. **编码处理**: 使用UTF-8编码保存中文内容
6. **输出简化**: 只输出汇总文件，不创建单独的client目录

## 故障排除

### 1. ChromeDriver错误

```
WebDriverException: Message: unknown error: cannot find Chrome binary
```

**解决方案**: 确保Chrome浏览器已正确安装

### 2. 页面加载超时

```
TimeoutException: Message: timeout
```

**解决方案**: 增加等待时间或检查网络连接

### 3. 元素定位失败

```
NoSuchElementException: Message: no such element
```

**解决方案**: 检查网页结构是否发生变化，更新XPath选择器

## 开发计划

- [ ] 添加更多client数据源
- [ ] 实现数据去重和合并
- [ ] 添加数据验证和清洗
- [ ] 支持增量更新
- [ ] 添加统计和报告功能 