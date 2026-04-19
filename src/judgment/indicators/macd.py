"""MACD指标计算模块

MACD（Moving Average Convergence Divergence）是一种趋势跟踪动量指标。
"""

import pandas as pd

class MACD:
    """MACD指标计算器"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> tuple:
        """计算MACD指标
        
        Args:
            df: 包含收盘价的DataFrame
            fast_period: 快速EMA周期
            slow_period: 慢速EMA周期
            signal_period: 信号EMA周期
            
        Returns:
            tuple: (DIF, DEA, MACD柱状线)
        """
        if 'close' not in df.columns:
            raise ValueError('DataFrame must contain "close" column')
        
        # 计算快速EMA
        ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
        
        # 计算慢速EMA
        ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # 计算DIF
        dif = ema_fast - ema_slow
        
        # 计算DEA
        dea = dif.ewm(span=signal_period, adjust=False).mean()
        
        # 计算MACD柱状线
        macd_hist = (dif - dea) * 2
        
        return dif, dea, macd_hist
    
    @staticmethod
    def get_signal(dif: float, dea: float) -> str:
        """根据MACD值获取交易信号
        
        Args:
            dif: DIF值
            dea: DEA值
            
        Returns:
            str: 交易信号
        """
        if dif > dea:
            return '金叉'
        elif dif < dea:
            return '死叉'
        else:
            return '无信号'