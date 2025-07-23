# MCPC (Model Context Protocol Crawler)

MCPC is a web crawler tool designed to collect and organize information about Model Context Protocol (MCP) servers. It retrieves MCP server source code and related information through the GitHub API.

## Features

- Retrieve MCP server code via GitHub API
- Automatic directory structure and file relationship handling
- Server metadata generation
- Pagination and error retry support
- Caching for improved efficiency
- Categories management for better organization
- **Periodic MCP server count statistics** - Automatically collect server counts from multiple websites every hour
- Support for multiple data sources:
  - Model Context Protocol GitHub repository
  - Smithery Registry
  - Pulse MCP
  - Cursor Directory
  - Awesome MCP
  - Glama AI

## Requirements

- Python 3.8+
- requests
- requests-cache
- PyYAML
- selenium
- beautifulsoup4
- aiohttp

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/mcpc.git
cd mcpc
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

### GitHub API Token

The project uses GitHub API for data retrieval and requires a GitHub Token:

1. Create a Personal Access Token on GitHub:
   - Visit https://github.com/settings/tokens
   - Click "Generate new token"
   - Select appropriate permissions (at least `repo` access)
   - Copy the generated token

2. Set the environment variable:
```bash
export GITHUB_TOKEN=your_github_token
```

### Configuration File

The project uses `config/sites_config.yaml` for configuration, including:

- API URL
- Request headers
- Pagination settings
- Error handling strategies

## Usage

### Step 1: Collect Metadata

Run the crawler to collect metadata:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml
```

To crawl specific data sources:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --sources glama smithery
```

To crawl only servers or clients:
```bash
# Servers only
python -m engine.crawler_engine --config config/sites_config.yaml --type servers

# Clients only
python -m engine.crawler_engine --config config/sites_config.yaml --type clients
```

### Step 2: Download Source Code (Optional)

#### Method 1: Download source code immediately after metadata collection
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --download-sources
```

#### Method 2: Download source code separately
```bash
# All data sources
python -m engine.crawler_engine --config config/sites_config.yaml --download-only

# Specific data source
python -m engine.crawler_engine --config config/sites_config.yaml --download-source smithery
```

### Step 3: Categories Management (Optional)

#### Method 1: Extract categories from detail pages during metadata collection
Categories are automatically extracted from detail URLs during the metadata collection process.

#### Method 2: Crawl categories separately from directory pages
```bash
# All data sources
python -m engine.crawler_engine --config config/sites_config.yaml --categories-only

# Specific data source
python -m engine.crawler_engine --config config/sites_config.yaml --categories-source smithery
```

#### Method 3: Use category crawler directly
```bash
python test_categories.py
```

#### Method 3: Use source downloader directly
```bash
# All data sources
python -m engine.source_downloader --all

# Specific data source
python -m engine.source_downloader --source smithery
```

### Step 4: MCP Server Count Statistics (New Feature)

The project now includes a periodic statistics crawler that automatically collects MCP server counts from multiple websites.

#### Run Statistics Crawler Once
```bash
# Run statistics crawler once
python scripts/stats_manager.py run-once

# Or use the crawler directly
python -m engine.stats_crawler
```

#### Start Periodic Statistics Scheduler
```bash
# Start scheduler with default 1-hour interval
python scripts/stats_manager.py start-scheduler

# Start scheduler with custom interval (e.g., 2 hours)
python scripts/stats_manager.py start-scheduler --interval 2

# Or use the scheduler directly
python -m engine.stats_scheduler
```

#### View Statistics Results
```bash
# View latest statistics
python scripts/stats_manager.py show-latest

# View history records
python scripts/stats_manager.py show-history

# View history with limit
python scripts/stats_manager.py show-history --limit 20
```

#### Manage Website Configurations
```bash
# List all configured websites
python scripts/stats_manager.py list-sites

# Add new website
python scripts/stats_manager.py add-site --name example --url https://example.com --selector ".count"

# Remove website
python scripts/stats_manager.py remove-site --name example

# Show configuration
python scripts/stats_manager.py show-config
```

#### Test Statistics Functionality
```bash
# Test the statistics crawler
python test_stats_crawler.py
```

## Output

The crawler generates the following in the `mcp_servers` directory:

- Server metadata files (.json) - one file per data source
- Server source code files (optional, downloaded in step 2)
- Crawler logs (crawler.log)

### Output Directory Structure

```
mcp_servers/
├── smithery/
│   ├── smithery.json  # All smithery servers metadata
│   ├── server_name_1/  # Server source code (step 2)
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   └── ...
│   └── server_name_2/  # Server source code (step 2)
│       ├── main.py
│       └── ...
├── modelcontextprotocol/
│   ├── modelcontextprotocol.json  # All GitHub API servers metadata
│   └── server_name_3/  # Server source code (step 2)
├── pulse/
│   ├── pulse.json  # All pulse servers metadata
│   └── server_name_4/  # Server source code (step 2)
├── cursor/
│   ├── cursor.json  # All cursor servers metadata
│   └── server_name_5/  # Server source code (step 2)
├── awesome/
│   ├── awesome.json  # All awesome MCP servers metadata
│   └── server_name_6/  # Server source code (step 2)
├── glama/
│   ├── glama.json  # All glama servers metadata
│   └── server_name_7/  # Server source code (step 2)
└── crawler.log

stats/  # Statistics output directory (new feature)
├── latest_stats.json      # Latest statistics results
├── stats_history.json     # Historical statistics data
├── stats_20241201_120000.json  # Timestamped statistics files
├── report_20241201_120000.md   # Generated reports
└── ...

logs/  # Log files (new feature)
├── stats_crawler.log      # Statistics crawler logs
└── stats_scheduler.log    # Scheduler logs
```

### Summary File Format

Each data source generates a summary JSON file containing:

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
      "categories": ["AI & ML", "Database", "Development"],
      "source": "smithery",
      "crawled_at": "2024-01-01T12:00:00Z"
    }
    // ... more servers
  ]
}
```

## Categories Management

The crawler supports two methods for managing server categories:

### Method 1: Automatic Tag Extraction
During metadata collection, the crawler automatically extracts categories/tags from server detail pages. This works for data sources that provide tags on their detail pages.

### Method 2: Directory-based Categories
For data sources that organize servers by categories in separate directory pages, the crawler can crawl these pages separately and assign categories to existing servers.

### Categories Statistics
You can view categories statistics for any data source:
```bash
python -c "
from engine.categories_manager import CategoriesManager
from pathlib import Path
manager = CategoriesManager(Path('.'))
stats = manager.get_categories_statistics('smithery')
print(f'Total servers: {stats.get(\"total_servers\", 0)}')
print(f'Servers with categories: {stats.get(\"servers_with_categories\", 0)}')
print(f'Category coverage: {stats.get(\"category_coverage\", \"0%\")}')
"
```

## Notes

- Ensure the GitHub Token has sufficient permissions
- Be aware of GitHub API rate limits
- Use caching to reduce API calls
- Some data sources may require additional configuration or authentication
- Categories extraction may require additional requests to detail pages

## License

[To be determined]

## Contributing

Issues and Pull Requests are welcome.

## Environment Setup

### Prerequisites

1. Python 3.8 or higher
2. Google Chrome browser
3. ChromeDriver matching your Chrome version
4. SOCKS5 proxy (optional, for GitHub API access)

### Installation

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
.\venv\Scripts\activate  # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install Google Chrome:
   - Linux (Ubuntu/Debian):
     ```bash
     wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
     sudo dpkg -i google-chrome-stable_current_amd64.deb
     ```
   - Or download from [Chrome's official website](https://www.google.com/chrome/)

4. Install ChromeDriver:
   - Check your Chrome version:
     ```bash
     google-chrome --version
     ```
   - Download matching ChromeDriver version from [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)
   - Install ChromeDriver:
     ```bash
     # Create directory if it doesn't exist
     sudo mkdir -p /usr/local/bin
     
     # Extract and move ChromeDriver
     unzip chromedriver-linux64.zip
     sudo mv chromedriver-linux64/chromedriver /usr/local/bin/
     sudo chmod +x /usr/local/bin/chromedriver
     ```

5. Set up GitHub token (required for repository data collection):
   ```bash
   export GITHUB_TOKEN='your_github_token'
   ```

6. (Optional) Set up SOCKS5 proxy for GitHub API access:
   - The crawler uses a SOCKS5 proxy at `127.0.0.1:1060` by default
   - You can modify the proxy settings in the crawler code if needed

## Usage

1. Configure the data sources in `config/sites_config.yaml`

2. Run the crawler:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --sources [source_name]
```

Available source names:
- awesome
- cursor
- glama
- pulse
- smithery

Example:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --sources glama
```

## Output

The crawler will create a `mcp_servers` directory with subdirectories for each data source. Each server's data will be stored in its own directory with the following structure:

```
mcp_servers/
├── [source_name]/
│   ├── [server_name]/
│   │   ├── [server_name].[source_name].json  # Server metadata
│   │   └── [repository files]  # If GitHub repository is available
│   └── all_servers.[source_name].json  # List of all servers
```
