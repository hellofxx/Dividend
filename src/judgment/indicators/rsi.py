"""RSI指标计算模块

RSI（Relative Strength Index）是一种动量指标，用于衡量价格变动的速度和变化。
"""

import pandas as pd

class RSI:
    """RSI指标计算器"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标
        
        Args:
            df: 包含收盘价的DataFrame
            period: 计算周期
            
        Returns:
            pd.Series: RSI值
        """
        if 'close' not in df.columns:
            raise ValueError('DataFrame must contain "close" column')
        
        # 计算价格变化
        delta = df['close'].diff()
        
        # 分离上涨和下跌
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 计算RS和RSI
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def get_signal(rsi: float) -> str:
        """根据RSI值获取交易信号
        
        Args:
            rsi: RSI值
            
        Returns:
            str: 交易信号
        """
        if rsi < 30:
            return '超卖'
        elif rsi > 70:
            return '超买'
        else:
            return '正常'