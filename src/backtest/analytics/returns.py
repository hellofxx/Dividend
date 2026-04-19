"""
收益率计算模块 (v4.0)

职责：所有收益率相关计算的统一入口
- 累计收益率
- 年化收益率
- 日历年度收益率
- 时间加权收益率 (TWR)
- 净值法收益率（DCA专用）

设计原则：
- 每个策略类型有专用的计算方法
- 所有方法均为 @staticmethod，纯函数，无副作用
"""

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ReturnsCalculator:
    """
    收益率计算器
    
    提供多种收益率计算方法，适应不同策略类型：
    - 普通策略：基于市值的收益率
    - DCA策略：基于净值或平均成本的收益率
    - 指数对比：基于涨跌幅的收益率
    """

    # ==================== 通用收益率计算 ====================

    @staticmethod
    def total_return(equity_curve: pd.DataFrame, init_cash: float) -> float:
        """
        计算累计收益率
        
        Args:
            equity_curve: DataFrame with date, total_value
            init_cash: 初始资金
            
        Returns:
            累计收益率 (%)
        """
        if len(equity_curve) == 0 or init_cash <= 0:
            return 0.0
        final_value = float(equity_curve['total_value'].iloc[-1])
        return (final_value - init_cash) / init_cash * 100

    @staticmethod
    def annual_return(equity_curve: pd.DataFrame, init_cash: float) -> float:
        """
        计算年化收益率（复利）
        
        Returns:
            年化收益率 (%)
        """
        if len(equity_curve) < 2 or init_cash <= 0:
            return 0.0
            
        total_ret = ReturnsCalculator.total_return(equity_curve, init_cash) / 100
        
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        years = max((end_date - start_date).days / 365.25, 1/365)
        
        return ((1 + total_ret) ** (1 / years) - 1) * 100

    @staticmethod
    def calendar_year_returns(equity_curve: pd.DataFrame) -> Dict[int, float]:
        """
        计算日历年度收益率
        
        公式：年度收益率 = (年末市值 - 年初市值) / 年初市值 × 100
        
        Args:
            equity_curve: DataFrame with date, total_value
            
        Returns:
            {year: return_pct, ...}
        """
        if len(equity_curve) < 2:
            return {}
            
        df = equity_curve.copy()
        df['year'] = df['date'].dt.year
        
        annual_returns = {}
        for year, group in df.groupby('year'):
            if len(group) < 2:
                continue
            start_val = float(group['total_value'].iloc[0])
            end_val = float(group['total_value'].iloc[-1])
            if start_val > 0:
                annual_returns[int(year)] = (end_val - start_val) / start_val * 100
            else:
                annual_returns[int(year)] = 0.0
                
        return annual_returns

    # ==================== 时间加权收益率 (TWR) ====================

    @staticmethod
    def time_weighted_return(equity_curve: pd.DataFrame) -> pd.Series:
        """
        计算累计收益率序列（用于图表展示）
        
        对于普通策略：基于初始本金计算收益率
        对于 DCA 策略：基于累计投入本金计算收益率（反映真实盈亏）
        
        Args:
            equity_curve: DataFrame with date, total_value
            
        Returns:
            累计收益率序列 (%)
        """
        df = equity_curve.copy().sort_values('date')
        
        # 检测是否为 DCA 策略
        is_dca = 'shares' in df.columns and 'invested_so_far' in df.columns
        
        if is_dca:
            # DCA：基于实际投入本金计算累计收益率
            # 收益率 = (当前市值 - 累计投入) / 累计投入 × 100
            invested = df['invested_so_far'].replace(0, np.nan)
            df['cum_return'] = (df['total_value'] - invested) / invested
            df['cum_return'] = df['cum_return'].fillna(0)
        else:
            # 普通策略：基于初始本金计算
            init_value = float(df['total_value'].iloc[0]) if len(df) > 0 else 1.0
            if init_value > 0:
                df['cum_return'] = (df['total_value'] - init_value) / init_value
            else:
                df['cum_return'] = 0.0
        
        return df['cum_return'] * 100

    @staticmethod
    def time_weighted_return_annual(equity_curve: pd.DataFrame) -> Dict[int, float]:
        """
        计算日历年度时间加权收益率
        
        对于 DCA 策略，使用净值法计算年度收益
        """
        if len(equity_curve) < 2:
            return {}
            
        df = equity_curve.copy()
        df['year'] = df['date'].dt.year
        
        is_dca = 'shares' in df.columns and 'invested_so_far' in df.columns
        
        annual_returns = {}
        for year, group in df.groupby('year'):
            if len(group) < 2:
                annual_returns[int(year)] = 0.0
                continue
            
            if is_dca:
                # DCA：使用净值计算
                group = group.copy()
                group['nav'] = group['total_value'] / group['shares']
                start_nav = float(group['nav'].iloc[0])
                end_nav = float(group['nav'].iloc[-1])
                annual_returns[int(year)] = ((end_nav - start_nav) / start_nav * 100) if start_nav > 0 else 0.0
            else:
                # 普通策略
                start_val = float(group['total_value'].iloc[0])
                end_val = float(group['total_value'].iloc[-1])
                annual_returns[int(year)] = ((end_val - start_val) / start_val * 100) if start_val > 0 else 0.0
        
        return annual_returns

    # ==================== DCA 专用收益率 ====================

    @staticmethod
    def dca_total_return(equity_curve: pd.DataFrame, final_nav: float = None) -> float:
        """
        计算 DCA 累计收益率（基于平均成本）
        
        公式：(期末净值 - 平均成本) / 平均成本 × 100
        
        Args:
            equity_curve: DataFrame with date, total_value, invested_so_far, shares
            final_nav: 期末净值（可选，默认从数据计算）
            
        Returns:
            累计收益率 (%)
        """
        if len(equity_curve) == 0:
            return 0.0
            
        if 'invested_so_far' not in equity_curve.columns or 'shares' not in equity_curve.columns:
            logger.warning("DCA 数据缺少必需列")
            return 0.0
        
        final_invested = float(equity_curve['invested_so_far'].iloc[-1])
        final_shares = float(equity_curve['shares'].iloc[-1])
        
        if final_shares <= 0:
            return 0.0
            
        avg_cost = final_invested / final_shares
        
        if final_nav is None:
            final_nav = float(equity_curve['total_value'].iloc[-1]) / final_shares
        
        return (final_nav - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0

    @staticmethod
    def dca_annual_return(equity_curve: pd.DataFrame, final_nav: float = None) -> float:
        """
        计算 DCA 年化收益率
        """
        total_ret = ReturnsCalculator.dca_total_return(equity_curve, final_nav) / 100
        
        if len(equity_curve) < 2:
            return 0.0
            
        start_date = equity_curve['date'].iloc[0]
        end_date = equity_curve['date'].iloc[-1]
        years = max((end_date - start_date).days / 365.25, 1/365)
        
        return ((1 + total_ret) ** (1 / years) - 1) * 100

    @staticmethod
    def dca_year_returns(equity_curve: pd.DataFrame) -> Dict[int, float]:
        """
        计算 DCA 日历年度收益率（基于年度平均成本）
        
        公式：
        - 年末平均成本 = 年末累计投入 / 年末累计份额
        - 年度收益率 = (年末净值 - 年末平均成本) / 年末平均成本 × 100
        """
        if len(equity_curve) < 2:
            return {}
            
        if 'invested_so_far' not in equity_curve.columns or 'shares' not in equity_curve.columns:
            return ReturnsCalculator.calendar_year_returns(equity_curve)
        
        df = equity_curve.copy()
        df['year'] = df['date'].dt.year
        df['nav'] = df['total_value'] / df['shares']
        
        annual_returns = {}
        for year, group in df.groupby('year'):
            if len(group) < 2:
                annual_returns[int(year)] = 0.0
                continue
            
            end_invested = float(group['invested_so_far'].iloc[-1])
            end_shares = float(group['shares'].iloc[-1])
            end_nav = float(group['nav'].iloc[-1])
            
            if end_shares <= 0:
                annual_returns[int(year)] = 0.0
                continue
            
            avg_cost = end_invested / end_shares
            annual_returns[int(year)] = (end_nav - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0
        
        return annual_returns

    # ==================== 指数收益率 ====================

    @staticmethod
    def index_total_return(index_curve: pd.DataFrame) -> float:
        """
        计算指数累计收益率
        
        Args:
            index_curve: DataFrame with date, total_value（指数资金曲线）
            
        Returns:
            累计收益率 (%)
        """
        if len(index_curve) < 2:
            return 0.0
            
        start_val = float(index_curve['total_value'].iloc[0])
        end_val = float(index_curve['total_value'].iloc[-1])
        
        return (end_val - start_val) / start_val * 100 if start_val > 0 else 0.0

    @staticmethod
    def index_annual_return(index_curve: pd.DataFrame) -> float:
        """计算指数年化收益率"""
        total_ret = ReturnsCalculator.index_total_return(index_curve) / 100
        
        if len(index_curve) < 2:
            return 0.0
            
        start_date = index_curve['date'].iloc[0]
        end_date = index_curve['date'].iloc[-1]
        years = max((end_date - start_date).days / 365.25, 1/365)
        
        return ((1 + total_ret) ** (1 / years) - 1) * 100
