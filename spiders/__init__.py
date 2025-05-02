class ParserRegistry:
    """解析器注册表工厂类"""
    def __init__(self):
        self._parsers = {}

    def register(self, name, parser_class):
        """注册解析器类
        Args:
            name: 解析器名称
            parser_class: 解析器类
        """
        self._parsers[name] = parser_class

    def get(self, name):
        """获取解析器类
        Args:
            name: 解析器名称
        Returns:
            解析器类
        """
        parser_class = self._parsers.get(name)
        if parser_class is None:
            raise ValueError(f"未找到解析器: {name}")
        return parser_class

# 初始化注册表实例
parser_registry = ParserRegistry()
from .github_parser import GitHubParser  # 添加GitHub解析器导入

# 注册默认解析器
parser_registry.register("github_parser", GitHubParser)

# 注册解析器
from .github_api_parser import GitHubAPIParser
parser_registry.register("github_api_parser", GitHubAPIParser)