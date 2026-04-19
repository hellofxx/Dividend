"""MACD图表模块

展示MACD指标图，包含DIF线、DEA线和MACD柱状线。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

from src.judgment.indicators.macd import MACD

class MACDChart:
    """MACD图表"""
    
    def __init__(self, figsize=(12, 3)):
        """初始化MACD图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """创建MACD图表
        
        Args:
            df: 包含价格数据的DataFrame
            fast_period: 快速EMA周期
            slow_period: 慢速EMA周期
            signal_period: 信号EMA周期
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        ax = fig.add_subplot(111)
        
        # 计算MACD指标
        dif, dea, macd_hist = MACD.calculate(df, fast_period, slow_period, signal_period)
        
        # 绘制DIF线和DEA线
        ax.plot(df['date'], dif, linewidth=1, color='blue', label=f'DIF({fast_period},{slow_period})')
        ax.plot(df['date'], dea, linewidth=1, color='orange', label=f'DEA({signal_period})')
        
        # 绘制MACD柱状线
        for i, (date, hist) in enumerate(zip(df['date'], macd_hist)):
            color = 'red' if hist >= 0 else 'green'
            ax.bar(date, hist, color=color, alpha=0.6)
        
        # 设置日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置标签和标题
        ax.set_ylabel('MACD')
        ax.set_title(f'MACD ({fast_period},{slow_period},{signal_period})')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        
        return fig