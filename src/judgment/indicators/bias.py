"""BIAS指标计算模块

BIAS（乖离率）是衡量股价偏离移动平均线程度的指标。
"""

import pandas as pd

class BIAS:
    """BIAS指标计算器"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, n: int = 20) -> pd.Series:
        """计算BIAS指标
        
        Args:
            df: 包含收盘价的DataFrame
            n: 计算周期
            
        Returns:
            pd.Series: BIAS值
        """
        if 'close' not in df.columns:
            raise ValueError('DataFrame must contain "close" column')
        
        # 计算移动平均线
        ma = df['close'].rolling(window=n).mean()
        
        # 计算BIAS
        bias = (df['close'] - ma) / ma * 100
        
        return bias
    
    @staticmethod
    def get_signal(bias: float, thresholds: tuple = (-5, 5)) -> str:
        """根据BIAS值获取交易信号
        
        Args:
            bias: BIAS值
            thresholds: (超卖阈值, 超买阈值)
            
        Returns:
            str: 交易信号
        """
        if bias < thresholds[0]:
            return '买入'
        elif bias > thresholds[1]:
            return '卖出'
        else:
            return '观望'