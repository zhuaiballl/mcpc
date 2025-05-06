# MCPC (Model Context Protocol Crawler)

MCPC is a web crawler tool designed to collect and organize information about Model Context Protocol (MCP) servers. It retrieves MCP server source code and related information through the GitHub API.

## Features

- Retrieve MCP server code via GitHub API
- Automatic directory structure and file relationship handling
- Server metadata generation
- Pagination and error retry support
- Caching for improved efficiency
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

Run the crawler:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml
```

To crawl specific data sources:
```bash
python -m engine.crawler_engine --config config/sites_config.yaml --sources glama smithery
```

## Output

The crawler generates the following in the `mcp_servers` directory:

- Server source code files
- Server metadata files (.json)
- Crawler logs (crawler.log)

## Notes

- Ensure the GitHub Token has sufficient permissions
- Be aware of GitHub API rate limits
- Use caching to reduce API calls
- Some data sources may require additional configuration or authentication

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
