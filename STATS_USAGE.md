# MCP服务器数量统计功能使用指南

## 概述

MCPC项目新增了MCP服务器数量统计功能，可以定期（默认每小时）从多个网站爬取MCP服务器的数量信息，并生成统计报告。

## 功能特性

- 🔄 **定时爬取**: 支持每小时自动爬取（可自定义间隔）
- 📊 **多网站支持**: 同时爬取多个MCP服务器网站
- 📈 **历史记录**: 保存历史统计数据，支持趋势分析
- 📋 **自动报告**: 生成Markdown格式的统计报告
- ⚙️ **灵活配置**: 支持自定义网站配置和爬取规则
- 🛠️ **管理工具**: 提供完整的命令行管理工具

## 快速开始

### 1. 安装依赖

确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

### 2. 运行单次统计

测试统计功能是否正常工作：
```bash
python scripts/stats_manager.py run-once
```

### 3. 启动定时调度器

启动每小时自动爬取：
```bash
python scripts/stats_manager.py start-scheduler
```

## 详细使用说明

### 配置文件

统计功能使用 `config/stats_config.yaml` 配置文件：

```yaml
# 调度器配置
scheduler:
  interval_hours: 1  # 运行间隔（小时）

# 日志配置
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# 输出目录
output_dir: "stats"

# 网站配置列表
sites:
  - name: "smithery"
    url: "https://registry.smithery.ai/servers"
    count_selector: ".server-count, .total-count, [data-count]"
    fallback_selectors:
      - "h1:contains('servers')"
      - ".stats .number"
    timeout: 30
    headers:
      User-Agent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### 命令行工具

#### 基本命令

```bash
# 运行一次统计爬取
python scripts/stats_manager.py run-once

# 启动定时调度器
python scripts/stats_manager.py start-scheduler

# 显示最新统计结果
python scripts/stats_manager.py show-latest

# 显示历史记录
python scripts/stats_manager.py show-history
```

#### 高级选项

```bash
# 自定义配置文件
python scripts/stats_manager.py run-once --config my_config.yaml

# 自定义运行间隔（小时）
python scripts/stats_manager.py start-scheduler --interval 2

# 显示指定数量的历史记录
python scripts/stats_manager.py show-history --limit 50
```

### 网站管理

#### 查看配置的网站

```bash
python scripts/stats_manager.py list-sites
```

输出示例：
```
📝 配置的网站列表 (共 5 个):
================================================================================
序号 网站名称         URL
================================================================================
1    smithery        https://registry.smithery.ai/servers
2    pulse           https://pulse.mcp.dev
3    cursor          https://cursor.sh/extensions
4    awesome_mcp     https://github.com/modelcontextprotocol/awesome-mcp
5    glama           https://glama.ai/mcp
================================================================================
```

#### 添加新网站

```bash
python scripts/stats_manager.py add-site \
  --name example \
  --url https://example.com/servers \
  --selector ".server-count"
```

#### 删除网站

```bash
python scripts/stats_manager.py remove-site --name example
```

#### 查看配置详情

```bash
python scripts/stats_manager.py show-config
```

### 查看统计结果

#### 最新统计结果

```bash
python scripts/stats_manager.py show-latest
```

输出示例：
```
📊 最新统计结果 (生成时间: 2024-12-01T12:00:00)
================================================================================
网站名称         服务器数量     状态       响应时间      错误信息
================================================================================
smithery        150           ✅ success   1.23s
pulse           89            ✅ success   0.87s
cursor          45            ✅ success   1.45s
awesome_mcp     234           ✅ success   2.12s
glama           67            ✅ success   0.98s
================================================================================
成功爬取: 5/5 个网站
总服务器数量: 585
================================================================================
```

#### 历史记录

```bash
python scripts/stats_manager.py show-history --limit 10
```

输出示例：
```
📈 历史统计记录 (共 25 条)
====================================================================================================
时间                 网站           服务器数量     状态
====================================================================================================
2024-12-01 11:00:00  smithery      150           ✅ success
2024-12-01 11:00:00  pulse         89            ✅ success
2024-12-01 11:00:00  cursor        45            ✅ success
2024-12-01 11:00:00  awesome_mcp   234           ✅ success
2024-12-01 11:00:00  glama         67            ✅ success
2024-12-01 10:00:00  smithery      148           ✅ success
2024-12-01 10:00:00  pulse         87            ✅ success
...
====================================================================================================
```

## 输出文件说明

### 统计结果文件

- `stats/latest_stats.json`: 最新统计结果
- `stats/stats_YYYYMMDD_HHMMSS.json`: 带时间戳的统计文件
- `stats/stats_history.json`: 历史统计数据

### 报告文件

- `stats/report_YYYYMMDD_HHMMSS.md`: 生成的统计报告

### 日志文件

- `logs/stats_crawler.log`: 统计爬虫日志
- `logs/stats_scheduler.log`: 调度器日志

## 配置网站选择器

### 选择器类型

1. **CSS选择器**: 直接选择包含数量的元素
   ```yaml
   count_selector: ".server-count"
   ```

2. **属性选择器**: 从data属性获取数量
   ```yaml
   count_selector: "[data-count]"
   ```

3. **文本包含选择器**: 查找包含特定文本的元素
   ```yaml
   count_selector: "h1:contains('servers')"
   ```

### 备用选择器

如果主要选择器失败，系统会尝试备用选择器：

```yaml
fallback_selectors:
  - ".stats .number"
  - ".total-servers"
  - "h2:contains('total')"
```

## 故障排除

### 常见问题

1. **无法提取数量**
   - 检查选择器是否正确
   - 确认网站结构是否发生变化
   - 尝试添加更多备用选择器

2. **请求超时**
   - 增加timeout配置
   - 检查网络连接
   - 确认网站是否可访问

3. **权限错误**
   - 检查User-Agent设置
   - 确认是否需要认证

### 调试模式

启用详细日志：
```bash
# 修改配置文件中的日志级别
logging:
  level: DEBUG
```

### 测试单个网站

```bash
# 创建测试配置
echo "sites:
  - name: test
    url: https://example.com
    count_selector: .count
    timeout: 30" > test_config.yaml

# 运行测试
python scripts/stats_manager.py run-once --config test_config.yaml
```

## 高级用法

### 自定义爬取间隔

```bash
# 每30分钟爬取一次
python scripts/stats_manager.py start-scheduler --interval 0.5

# 每6小时爬取一次
python scripts/stats_manager.py start-scheduler --interval 6
```

### 集成到现有系统

```python
from engine.stats_crawler import StatsCrawler
import asyncio

async def custom_stats():
    crawler = StatsCrawler("config/stats_config.yaml")
    stats = await crawler.run()
    
    # 处理统计结果
    for stat in stats:
        if stat.status == "success":
            print(f"{stat.site_name}: {stat.server_count}")
        else:
            print(f"{stat.site_name}: 错误 - {stat.error_message}")

# 运行
asyncio.run(custom_stats())
```

### 数据导出

统计结果以JSON格式保存，可以轻松导入到其他系统：

```python
import json

with open("stats/latest_stats.json", "r") as f:
    stats = json.load(f)

# 转换为CSV
import csv
with open("stats_export.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["网站", "服务器数量", "状态", "时间"])
    for stat in stats:
        writer.writerow([
            stat["site_name"],
            stat["server_count"],
            stat["status"],
            stat["crawled_at"]
        ])
```

## 注意事项

1. **频率限制**: 避免过于频繁的请求，以免被网站封禁
2. **Cloudflare保护**: 某些网站（如mcp.so）启用了Cloudflare保护，建议：
   - 使用每日爬取配置（`config/stats_config_daily.yaml`）
   - 增加请求间隔和延迟
   - 使用真实的浏览器请求头
3. **选择器维护**: 网站结构变化时需要更新选择器
4. **数据备份**: 定期备份历史统计数据
5. **监控**: 关注日志文件，及时发现异常情况

## Cloudflare保护处理

对于启用了Cloudflare保护的网站（如mcp.so），系统提供了以下处理机制：

### 配置选项
```yaml
cloudflare_protected: true      # 启用Cloudflare保护处理
request_delay: 10              # 请求延迟（秒）
max_retries: 2                 # 最大重试次数
referer: "https://www.google.com/"  # 添加Referer头
```

### 使用建议
1. **降低爬取频率**: 使用每日爬取而不是每小时爬取
2. **增加延迟**: 设置较长的请求延迟（10-15秒）
3. **监控日志**: 关注是否被Cloudflare拦截的日志信息

### 启动每日爬取
```bash
python scripts/stats_manager.py start-scheduler --config config/stats_config_daily.yaml
```

## 支持

如果遇到问题，请：

1. 查看日志文件获取详细错误信息
2. 检查配置文件是否正确
3. 测试单个网站配置
4. 提交Issue到项目仓库 