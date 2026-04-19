"""KDJ指标计算模块

KDJ（随机指标）是一种动量指标，由K线、D线和J线组成。
"""

import pandas as pd

class KDJ:
    """KDJ指标计算器"""
    
    @staticmethod
    def calculate(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
        """计算KDJ指标
        
        Args:
            df: 包含最高价、最低价、收盘价的DataFrame
            n: 计算周期
            m1: K线平滑周期
            m2: D线平滑周期
            
        Returns:
            tuple: (K线, D线, J线)
        """
        if not all(col in df.columns for col in ['high', 'low', 'close']):
            raise ValueError('DataFrame must contain "high", "low", "close" columns')
        
        # 计算RSV
        low_n = df['low'].rolling(window=n).min()
        high_n = df['high'].rolling(window=n).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        
        # 计算K线
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        
        # 计算D线
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        
        # 计算J线
        j = 3 * k - 2 * d
        
        return k, d, j
    
    @staticmethod
    def get_signal(k: float, d: float, j: float) -> str:
        """根据KDJ值获取交易信号
        
        Args:
            k: K线值
            d: D线值
            j: J线值
            
        Returns:
            str: 交易信号
        """
        if k > d > j:
            return '超买'
        elif k < d < j:
            return '超卖'
        elif k > d and j > k:
            return '金叉'
        elif k < d and j < k:
            return '死叉'
        else:
            return '无信号'