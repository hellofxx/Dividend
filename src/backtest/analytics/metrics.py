"""
基础指标计算器 (v4.0)

职责：所有基础金融指标的统一计算入口
- 收益率指标：累计、年化
- 风险指标：最大回撤、夏普比率、卡玛比率、索提诺比率、波动率
- 交易统计：胜率、盈亏比

设计原则：
- 所有方法均为 @classmethod，可直接调用
- 输入统一为 DataFrame (date, total_value) + trades 列表
- 返回标准化字典，字段名保持一致
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.models import TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """风险指标数据类"""
    volatility: float       # 年化波动率 (%)
    downside_dev: float     # 下行偏差 (%)
    max_drawdown: float     # 最大回撤 (%)
    sharpe_ratio: float     # 夏普比率
    sortino_ratio: float    # 索提诺比率
    calmar_ratio: float     # 卡玛比率


@dataclass
class ReturnMetrics:
    """收益指标数据类"""
    total_return: float     # 累计收益率 (%)
    annual_return: float    # 年化收益率 (%)
    

class MetricsCalculator:
    """
    基础指标计算器
    
    所有方法均为 @classmethod，可直接调用：
        MetricsCalculator.calc(equity_df, trades, init_cash)
        MetricsCalculator.calc_risk(equity_df, risk_free_rate)
    """

    # ==================== 公共入口 ====================

    @classmethod
    def calc(
        cls,
        equity_curve: pd.DataFrame,
        trades: List[TradeRecord],
        init_cash: float,
        **kwargs
    ) -> Dict[str, float]:
        """
        计算所有基础指标（收益 + 风险 + 交易统计）
        
        Args:
            equity_curve: 资金曲线 DataFrame（列: date, total_value）
            trades: 交易流水列表
            init_cash: 初始资金
            
        Returns:
            Dict[str, float]: 标准化指标字典
        """
        if len(equity_curve) == 0:
            return cls._empty_metrics()

        metrics = {}
        
        # 收益指标
        ret_metrics = cls.calc_returns(equity_curve, init_cash)
        metrics.update(ret_metrics)
        
        # 风险指标
        risk_metrics = cls.calc_risk(equity_curve)
        metrics.update(risk_metrics)
        
        # 交易统计
        trade_metrics = cls.calc_trade_stats(trades)
        metrics.update(trade_metrics)
        
        return metrics

    @classmethod
    def calc_returns(
        cls,
        equity_curve: pd.DataFrame,
        init_cash: float
    ) -> Dict[str, float]:
        """
        计算收益指标
        
        Returns:
            {'total_return': float, 'annual_return': float}
        """
        if len(equity_curve) < 2:
            return {'total_return': 0.0, 'annual_return': 0.0}
            
        final_value = float(equity_curve['total_value'].iloc[-1])
        total_return = (final_value - init_cash) / init_cash * 100
        
        # 年化收益（复利）
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        years = max((end_date - start_date).days / 365.25, 1/365)
        annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
        }

    @classmethod
    def calc_risk(
        cls,
        equity_curve: pd.DataFrame,
        risk_free_rate: float = 0.03
    ) -> Dict[str, float]:
        """
        计算风险指标
        
        Returns:
            {
                'volatility': 年化波动率 (%),
                'downside_dev': 下行偏差 (%),
                'max_drawdown': 最大回撤 (%),
                'sharpe_ratio': 夏普比率,
                'sortino_ratio': 索提诺比率,
                'calmar_ratio': 卡玛比率,
            }
        """
        if len(equity_curve) < 2:
            return cls._empty_risk_metrics()
            
        df = equity_curve.copy().sort_values('date')
        df['daily_return'] = df['total_value'].pct_change()
        daily_returns = df['daily_return'].dropna()
        
        if len(daily_returns) == 0:
            return cls._empty_risk_metrics()
        
        # 年化波动率
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # 下行偏差
        downside_returns = daily_returns[daily_returns < 0]
        downside_dev = downside_returns.std() * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0.0
        
        # 最大回撤
        values = df['total_value'].values
        peak = np.maximum.accumulate(values)
        drawdown = (values - peak) / peak
        max_drawdown = abs(np.min(drawdown)) * 100
        
        # 年化收益率（用于计算比率）
        annual_return = daily_returns.mean() * 252 * 100
        
        # 夏普比率
        sharpe_ratio = (annual_return / 100 - risk_free_rate) / (volatility / 100) if volatility > 0 else 0.0
        
        # 索提诺比率
        sortino_ratio = (annual_return / 100 - risk_free_rate) / (downside_dev / 100) if downside_dev > 0 else 0.0
        
        # 卡玛比率
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0.0
        
        return {
            'volatility': volatility,
            'downside_dev': downside_dev,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
        }

    @classmethod
    def calc_trade_stats(cls, trades: List[TradeRecord]) -> Dict[str, float]:
        """
        计算交易统计指标
        
        Returns:
            {'win_rate': 胜率 (%), 'profit_loss_ratio': 盈亏比}
        """
        if len(trades) < 2:
            return {'win_rate': 0.0, 'profit_loss_ratio': 0.0}
        
        profits = cls._calc_trade_profits(trades)
        if len(profits) == 0:
            return {'win_rate': 0.0, 'profit_loss_ratio': 0.0}
        
        # 胜率
        wins = sum(1 for p in profits if p > 0)
        win_rate = (wins / len(profits)) * 100
        
        # 盈亏比
        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p < 0]
        
        avg_profit = np.mean(winning) if winning else 0.0
        avg_loss = abs(np.mean(losing)) if losing else 1.0
        
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0
        
        return {
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
        }

    # ==================== DCA 专用指标 ====================

    @classmethod
    def calc_dca_returns(
        cls,
        equity_curve: pd.DataFrame,
    ) -> Dict[str, float]:
        """
        计算 DCA (定投) 策略的收益率
        
        DCA 特点：
        - 累计收益率 = (期末净值 - 平均成本) / 平均成本 × 100
        - 平均成本 = 累计投入 / 累计份额
        
        行业标准算法（2026-04-14 修正）：
        - 基于"平均成本法"计算累计收益率，这是定投最常用的方法
        - 年化收益率采用复利公式：((1+r)^(1/n) - 1) × 100
        
        Args:
            equity_curve: DataFrame with date, total_value, invested_so_far, shares
            
        Returns:
            {'total_return': float, 'annual_return': float, 'avg_cost': float}
        """
        if len(equity_curve) == 0:
            return {'total_return': 0.0, 'annual_return': 0.0, 'avg_cost': 0.0}
        
        # 检查必需列
        if 'invested_so_far' not in equity_curve.columns or 'shares' not in equity_curve.columns:
            logger.warning("DCA 资金曲线缺少 invested_so_far 或 shares 列")
            return {'total_return': 0.0, 'annual_return': 0.0, 'avg_cost': 0.0}
        
        final_invested = float(equity_curve['invested_so_far'].iloc[-1])
        final_shares = float(equity_curve['shares'].iloc[-1])
        
        # 期末净值 = 期末市值 / 期末份额
        final_nav = float(equity_curve['total_value'].iloc[-1]) / final_shares if final_shares > 0 else 0.0
        
        # 平均成本 = 累计投入 / 累计份额（行业标准）
        avg_cost = final_invested / final_shares if final_shares > 0 else final_nav
        
        # 累计收益率 = (期末净值 - 平均成本) / 平均成本 × 100
        total_return = (final_nav - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0
        
        # 年化收益（复利公式）
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        years = max((end_date - start_date).days / 365.25, 1/365)
        annual_return = ((1 + total_return / 100) ** (1 / years) - 1) * 100
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'avg_cost': avg_cost,
        }

    @classmethod
    def calc_dca_risk(
        cls,
        equity_curve: pd.DataFrame,
        risk_free_rate: float = 0.03
    ) -> Dict[str, float]:
        """
        计算 DCA (定投) 策略的风险指标
        
        关键修正（2026-04-14）：
        - DCA 的风险指标必须基于【净值变化】而非市值变化
        - 净值 = 市值 / 份额
        - 日收益率 = (今日净值 - 昨日净值) / 昨日净值
        
        行业标准：
        - 最大回撤：净值从峰值回落的最大幅度
        - 夏普比率：基于净值日收益率计算
        - 波动率：净值日收益率的标准差
        
        Args:
            equity_curve: DataFrame with date, total_value, shares
            risk_free_rate: 无风险利率（默认3%）
            
        Returns:
            风险指标字典
        """
        if len(equity_curve) < 2:
            return cls._empty_risk_metrics()
        
        # 检查必需列
        if 'shares' not in equity_curve.columns:
            logger.warning("DCA 风险计算缺少 shares 列，降级为普通风险计算")
            return cls.calc_risk(equity_curve, risk_free_rate)
        
        df = equity_curve.copy().sort_values('date')
        
        # 核心：计算净值序列
        df['nav'] = df['total_value'] / df['shares']
        df['nav'] = df['nav'].replace([np.inf, -np.inf], np.nan).ffill()
        
        # 基于净值计算日收益率
        df['daily_return'] = df['nav'].pct_change()
        daily_returns = df['daily_return'].dropna()
        
        if len(daily_returns) == 0:
            return cls._empty_risk_metrics()
        
        # 年化波动率（净值日收益率标准差 × √252）
        volatility = daily_returns.std() * np.sqrt(252) * 100
        
        # 下行偏差
        downside_returns = daily_returns[daily_returns < 0]
        downside_dev = downside_returns.std() * np.sqrt(252) * 100 if len(downside_returns) > 0 else 0.0
        
        # 最大回撤（净值回撤）
        nav_values = df['nav'].values
        peak = np.maximum.accumulate(nav_values)
        drawdown = (nav_values - peak) / peak
        max_drawdown = abs(np.min(drawdown)) * 100
        
        # 年化收益率（用于计算比率）
        annual_return = daily_returns.mean() * 252 * 100
        
        # 夏普比率 = (年化收益 - 无风险利率) / 年化波动率
        sharpe_ratio = (annual_return / 100 - risk_free_rate) / (volatility / 100) if volatility > 0 else 0.0
        
        # 索提诺比率 = (年化收益 - 无风险利率) / 下行偏差
        sortino_ratio = (annual_return / 100 - risk_free_rate) / (downside_dev / 100) if downside_dev > 0 else 0.0
        
        # 卡玛比率 = 年化收益 / 最大回撤
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0.0
        
        return {
            'volatility': volatility,
            'downside_dev': downside_dev,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
        }

    # ==================== 私有工具方法 ====================

    @classmethod
    def _calc_trade_profits(cls, trades: List[TradeRecord]) -> List[float]:
        """配对买卖，计算每笔完整交易的盈亏金额"""
        profits = []
        position = 0.0
        avg_cost = 0.0

        for trade in trades:
            if trade.action == "BUY":
                new_position = position + trade.shares
                avg_cost = (
                    (position * avg_cost + trade.shares * trade.price) / new_position
                    if new_position > 0 else trade.price
                )
                position = new_position
            else:  # SELL
                if position > 0:
                    profit = (trade.price - avg_cost) * trade.shares
                    profits.append(profit)
                    position -= trade.shares
                    if position <= 0:
                        position = 0.0
                        avg_cost = 0.0

        return profits

    @classmethod
    def _empty_metrics(cls) -> Dict[str, float]:
        """返回全零指标字典"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'volatility': 0.0,
            'downside_dev': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'win_rate': 0.0,
            'profit_loss_ratio': 0.0,
        }

    @classmethod
    def _empty_risk_metrics(cls) -> Dict[str, float]:
        """返回零值风险指标字典"""
        return {
            'volatility': 0.0,
            'downside_dev': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
        }

    # 向后兼容的实例方法
    def calculate(
        self,
        equity_curve: pd.DataFrame,
        trades: List[TradeRecord],
        initial_capital: float,
        **kwargs
    ) -> Dict[str, float]:
        """实例方法包装（向后兼容）"""
        return self.calc(equity_curve, trades, initial_capital, **kwargs)
