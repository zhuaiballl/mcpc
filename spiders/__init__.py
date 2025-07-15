from .base_parser import MCPParser, MCPv1Parser, MCPv2Parser
from .github_api_parser import GitHubAPIParser
from .github_parser import GitHubParser
from .smithery_parser import SmitheryParser
from .glama_client_parser import GlamaClientParser

# 解析器注册表
parser_registry = {
    'github_api_parser': GitHubAPIParser,
    'github_parser': GitHubParser,
    'smithery_parser': SmitheryParser,
    'glama_client_parser': GlamaClientParser,
}

__all__ = [
    'MCPParser',
    'MCPv1Parser', 
    'MCPv2Parser',
    'GitHubAPIParser',
    'GitHubParser',
    'SmitheryParser',
    'GlamaClientParser',
    'parser_registry'
]