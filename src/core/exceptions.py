"""
自定义异常层级 (v3.1)
"""


class FrameworkError(Exception):
    """框架基础异常"""
    pass


class DataFetchError(FrameworkError):
    """数据获取异常"""
    pass


class ConfigValidationError(FrameworkError):
    """配置校验异常"""
    pass


class DividendModeError(ConfigValidationError):
    """分红模式配置异常（仅支持 reinvest / cash）"""
    pass


class StrategyError(FrameworkError):
    """策略执行异常"""
    pass


class ValidationError(FrameworkError):
    """数据验证异常"""
    pass


class VisualizationError(FrameworkError):
    """可视化异常"""
    pass


class ConfigError(FrameworkError):
    """配置异常"""
    pass
