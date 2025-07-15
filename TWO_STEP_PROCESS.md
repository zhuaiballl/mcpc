# MCP Server 两步执行流程

本项目现在采用两步执行的方式来抓取MCP Server数据：

1. **第一步：抓取元数据** - 快速获取所有server的基本信息
2. **第二步：下载源码** - 根据元数据中的GitHub URL下载源码（可选）

## 为什么采用两步执行？

### 优势
- **速度更快**：第一步只抓取元数据，速度很快
- **灵活性更高**：可以选择是否下载源码，以及下载哪些数据源的源码
- **断点续传**：如果源码下载中断，可以单独重新下载
- **资源节省**：不需要源码时只执行第一步即可

### 适用场景
- **快速调研**：只需要了解有哪些server，不需要源码
- **批量下载**：需要所有server的源码进行离线分析
- **增量更新**：只更新特定数据源的源码

## 使用方法

### 第一步：抓取元数据

```bash
# 抓取所有数据源
python -m engine.crawler_engine --config config/sites_config.yaml

# 抓取特定数据源
python -m engine.crawler_engine --config config/sites_config.yaml --sources smithery pulse

# 只抓取servers（不包括clients）
python -m engine.crawler_engine --config config/sites_config.yaml --type servers

# 只抓取clients
python -m engine.crawler_engine --config config/sites_config.yaml --type clients
```

### 第二步：下载源码

#### 方式1：抓取元数据后立即下载源码
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --download-sources
```

#### 方式2：单独下载源码（推荐）
```bash
# 下载所有数据源的源码
python -m engine.crawler_engine --config config/sites_config.yaml --download-only

# 下载特定数据源的源码
python -m engine.crawler_engine --config config/sites_config.yaml --download-source smithery
```

#### 方式3：使用源码下载器
```bash
# 下载所有数据源的源码
python -m engine.source_downloader --all

# 下载特定数据源的源码
python -m engine.source_downloader --source smithery

# 指定基础目录
python -m engine.source_downloader --source smithery --base-dir /path/to/mcp_servers
```

## 输出结构

### 第一步输出（元数据）
```
mcp_servers/
├── smithery/
│   └── smithery.json  # 包含所有server的元数据
├── pulse/
│   └── pulse.json
├── cursor/
│   └── cursor.json
├── awesome/
│   └── awesome.json
├── glama/
│   └── glama.json
├── modelcontextprotocol/
│   └── modelcontextprotocol.json
└── crawler.log
```

### 第二步输出（源码）
```
mcp_servers/
├── smithery/
│   ├── smithery.json  # 元数据文件
│   ├── server_name_1/  # 源码目录
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   └── ...
│   ├── server_name_2/
│   │   ├── setup.py
│   │   └── ...
│   └── ...
├── pulse/
│   ├── pulse.json
│   ├── server_name_3/
│   └── ...
└── ...
```

## 元数据文件格式

每个数据源的元数据文件包含以下信息：

```json
{
  "source": "smithery",
  "total_count": 150,
  "crawled_at": "2024-01-01T12:00:00Z",
  "servers": [
    {
      "name": "Server Name",
      "description": "Server description",
      "url": "https://example.com",
      "github_url": "https://github.com/example/server",
      "source": "smithery",
      "crawled_at": "2024-01-01T12:00:00Z",
      // 其他字段根据数据源不同而不同
      "use_count": 100,
      "is_deployed": true,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

## 源码下载特性

### 智能跳过
- 如果源码目录已存在且不为空，会自动跳过
- 避免重复下载，节省时间和带宽

### 错误处理
- 单个server下载失败不会影响其他server
- 详细的错误日志和统计信息

### 速率限制
- 自动添加延迟避免GitHub API限制
- 使用代理支持（如果配置了）

### 断点续传
- 支持中断后重新运行，只下载缺失的源码
- 可以单独下载特定数据源的源码

## 环境要求

### 第一步（元数据抓取）
- Python 3.8+
- 相关依赖包（见requirements.txt）
- 对于某些数据源需要API Token

### 第二步（源码下载）
- GitHub Token（必需）
- 网络连接
- 足够的磁盘空间

## 配置GitHub Token

```bash
# 设置环境变量
export GITHUB_TOKEN=your_github_token

# 或者在运行时设置
GITHUB_TOKEN=your_github_token python -m engine.source_downloader --all
```

## 故障排除

### 常见问题

1. **GitHub API限制**
   - 确保设置了有效的GitHub Token
   - 检查Token权限是否足够

2. **网络连接问题**
   - 检查代理设置
   - 确保可以访问GitHub

3. **磁盘空间不足**
   - 检查可用磁盘空间
   - 源码可能占用大量空间

4. **权限问题**
   - 确保有写入目标目录的权限

### 调试技巧

```bash
# 查看详细日志
python -m engine.source_downloader --source smithery 2>&1 | tee download.log

# 测试单个server下载
python -c "
from engine.source_downloader import SourceDownloader
downloader = SourceDownloader()
downloader.download_github_repo('https://github.com/example/repo', Path('test_dir'))
"
```

## 性能优化

### 并行下载
- 当前版本是串行下载，避免API限制
- 未来版本可能支持并行下载

### 缓存机制
- 使用requests-cache减少重复请求
- 源码下载支持断点续传

### 增量更新
- 只下载新增或更新的server源码
- 支持按时间戳过滤 