# MCPC (Model Context Protocol Crawler)

MCPC is a web crawler tool designed to collect and organize information about Model Context Protocol (MCP) servers. It retrieves MCP server source code and related information through the GitHub API.

## Features

- Retrieve MCP server code via GitHub API
- Automatic directory structure and file relationship handling
- Server metadata generation
- Pagination and error retry support
- Caching for improved efficiency

## Requirements

- Python 3.8+
- requests
- requests-cache
- PyYAML

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
python -m engine.crawler_engine
```

## Output

The crawler generates the following in the `mcp_servers_modelcontextprotocol_io` directory:

- Server source code files
- Server metadata files (.modelcontextprotocol.io.json)
- Crawler logs (crawler.log)

## Notes

- Ensure the GitHub Token has sufficient permissions
- Be aware of GitHub API rate limits
- Use caching to reduce API calls

## License

[To be determined]

## Contributing

Issues and Pull Requests are welcome. 