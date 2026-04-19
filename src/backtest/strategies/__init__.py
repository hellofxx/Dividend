"""
策略模块
"""

from .base import BaseStrategy, StrategyState
from .annual_line import AnnualLineStrategy


def create_default_strategy():
    """
    创建默认策略
    """
    return AnnualLineStrategy()


__all__ = [
    'BaseStrategy',
    'StrategyState',
    'AnnualLineStrategy',
    'create_default_strategy',
]
