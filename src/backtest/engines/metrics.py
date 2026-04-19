"""
基础指标计算器 (v4.0 - 兼容层)

此模块现在作为 analytics 模块的兼容层存在。
所有实际计算逻辑已迁移至 quant_core.analytics.metrics。

保持向后兼容：现有代码调用 MetricsCalculator 不受影响。
"""

import logging
from typing import List, Dict

import pandas as pd

from src.core.models import TradeRecord
from src.backtest.analytics.metrics import MetricsCalculator as _MetricsCalculator
from src.backtest.analytics.metrics import RiskMetrics, ReturnMetrics

logger = logging.getLogger(__name__)


class MetricsCalculator(_MetricsCalculator):
    """
    基础指标计算器（兼容层）
    
    继承自 analytics.MetricsCalculator，保持完全向后兼容。
    新代码建议直接使用：from quant_core.analytics import MetricsCalculator
    """
    
    # 完全继承父类实现，无需额外代码
    pass
