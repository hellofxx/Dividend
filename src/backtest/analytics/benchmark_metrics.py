"""
基准对比专用指标 (v4.0)

职责：多策略对比所需的指标计算
- 策略对比表构建
- 超额收益计算
- 相对风险指标

设计原则：
- 复用基础指标（MetricsCalculator、ReturnsCalculator）
- 专注对比逻辑，不重复实现基础计算
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.models import BacktestResult
from .metrics import MetricsCalculator
from .returns import ReturnsCalculator

logger = logging.getLogger(__name__)


@dataclass
class StrategySummary:
    """策略汇总数据"""
    name: str
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    calmar_ratio: float
    volatility: float
    sortino_ratio: float
    excess_return: float = 0.0  # 相对于基准的超额收益


class BenchmarkMetrics:
    """
    基准对比指标计算器
    
    统一计算多策略对比所需的所有指标
    """

    @staticmethod
    def calculate_all_metrics(equity_curve: pd.DataFrame) -> Dict[str, float]:
        """
        计算策略的所有指标（用于对比）
        
        2026-04-14 修正：
        - DCA 策略的风险指标使用 calc_dca_risk（基于净值变化）
        - 普通策略的风险指标使用 calc_risk（基于市值变化）
        
        Args:
            equity_curve: 资金曲线 DataFrame
            
        Returns:
            完整指标字典
        """
        from src.core.models import TradeRecord
        
        # 检测 DCA
        is_dca = 'invested_so_far' in equity_curve.columns and 'shares' in equity_curve.columns
        
        # 风险指标（DCA 使用专用方法）
        if is_dca:
            risk_metrics = MetricsCalculator.calc_dca_risk(equity_curve)
        else:
            risk_metrics = MetricsCalculator.calc_risk(equity_curve)
        
        # 收益率指标
        if is_dca:
            # DCA：使用专用方法（平均成本法）
            ret_metrics = MetricsCalculator.calc_dca_returns(equity_curve)
        else:
            # 普通策略：使用标准方法
            init_cash = float(equity_curve['total_value'].iloc[0]) if len(equity_curve) > 0 else 1.0
            ret_metrics = MetricsCalculator.calc_returns(equity_curve, init_cash)
        
        # 合并
        metrics = {**ret_metrics, **risk_metrics}
        
        return metrics

    @staticmethod
    def build_compare_table(
        strategies: List[Tuple[str, pd.DataFrame]],
        benchmark_curve: Optional[pd.DataFrame] = None,
        benchmark_name: str = "基准"
    ) -> pd.DataFrame:
        """
        构建策略对比表
        
        Args:
            strategies: [(策略名称, 资金曲线), ...]
            benchmark_curve: 基准资金曲线（用于计算超额收益）
            benchmark_name: 基准名称
            
        Returns:
            对比表 DataFrame
        """
        rows = []
        
        # 计算基准收益
        benchmark_return = 0.0
        if benchmark_curve is not None and len(benchmark_curve) > 0:
            benchmark_return = ReturnsCalculator.index_total_return(benchmark_curve)
        
        for name, equity_curve in strategies:
            if len(equity_curve) == 0:
                continue
                
            metrics = BenchmarkMetrics.calculate_all_metrics(equity_curve)
            
            # 计算超额收益
            excess = metrics.get('total_return', 0.0) - benchmark_return
            
            rows.append({
                'strategy': name,
                'total_return': metrics.get('total_return', 0.0),
                'annual_return': metrics.get('annual_return', 0.0),
                'max_drawdown': metrics.get('max_drawdown', 0.0),
                'volatility': metrics.get('volatility', 0.0),
                'sharpe_ratio': metrics.get('sharpe_ratio', 0.0),
                'sortino_ratio': metrics.get('sortino_ratio', 0.0),
                'calmar_ratio': metrics.get('calmar_ratio', 0.0),
                'excess_return': excess,
            })
        
        # 添加基准行
        if benchmark_curve is not None and len(benchmark_curve) > 0:
            benchmark_metrics = BenchmarkMetrics.calculate_all_metrics(benchmark_curve)
            rows.append({
                'strategy': benchmark_name,
                'total_return': benchmark_metrics.get('total_return', 0.0),
                'annual_return': benchmark_metrics.get('annual_return', 0.0),
                'max_drawdown': benchmark_metrics.get('max_drawdown', 0.0),
                'volatility': benchmark_metrics.get('volatility', 0.0),
                'sharpe_ratio': benchmark_metrics.get('sharpe_ratio', 0.0),
                'sortino_ratio': benchmark_metrics.get('sortino_ratio', 0.0),
                'calmar_ratio': benchmark_metrics.get('calmar_ratio', 0.0),
                'excess_return': 0.0,
            })
        
        return pd.DataFrame(rows)

    @staticmethod
    def calc_excess_return(
        strategy_return: float,
        benchmark_return: float
    ) -> float:
        """计算超额收益"""
        return strategy_return - benchmark_return

    @staticmethod
    def calc_tracking_error(
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series
    ) -> float:
        """
        计算跟踪误差
        
        跟踪误差 = 收益率差异的标准差 × √252
        """
        if len(strategy_returns) != len(benchmark_returns):
            min_len = min(len(strategy_returns), len(benchmark_returns))
            strategy_returns = strategy_returns.iloc[:min_len]
            benchmark_returns = benchmark_returns.iloc[:min_len]
        
        diff = strategy_returns - benchmark_returns
        return diff.std() * np.sqrt(252) * 100

    @staticmethod
    def calc_information_ratio(
        excess_return: float,
        tracking_error: float
    ) -> float:
        """计算信息比率"""
        return excess_return / tracking_error if tracking_error > 0 else 0.0

    @staticmethod
    def get_annual_returns_for_chart(equity_curve: pd.DataFrame) -> Dict[int, float]:
        """
        获取年度收益率（供图表使用）
        
        自动检测 DCA 并使用合适的方法
        """
        is_dca = 'shares' in equity_curve.columns and 'invested_so_far' in equity_curve.columns
        
        if is_dca:
            return ReturnsCalculator.dca_year_returns(equity_curve)
        else:
            return ReturnsCalculator.calendar_year_returns(equity_curve)

    @staticmethod
    def get_twr_series(equity_curve: pd.DataFrame) -> pd.Series:
        """
        获取时间加权收益率序列（供图表使用）
        """
        return ReturnsCalculator.time_weighted_return(equity_curve)
