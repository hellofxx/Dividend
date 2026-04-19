"""K线图表模块

展示ETF价格K线走势与BIAS指标叠加。
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import pandas as pd

from src.judgment.indicators.bias import BIAS

class KlineChart:
    """K线图表"""
    
    def __init__(self, figsize=(12, 6)):
        """初始化K线图表
        
        Args:
            figsize: 图表大小
        """
        self.figsize = figsize
    
    def create(self, df: pd.DataFrame, chart_type: str = 'candle', bias_period: int = 20):
        """创建K线图表
        
        Args:
            df: 包含价格数据的DataFrame
            chart_type: 图表类型 ('candle' 或 'line')
            bias_period: BIAS计算周期
            
        Returns:
            plt.Figure: 图表对象
        """
        fig = plt.figure(figsize=self.figsize)
        gs = GridSpec(3, 1, height_ratios=[3, 1, 0.5])
        
        # 主K线图
        ax1 = fig.add_subplot(gs[0])
        
        if chart_type == 'candle':
            self._plot_candlestick(ax1, df)
        else:
            self._plot_line(ax1, df)
        
        # BIAS指标图
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        self._plot_bias(ax2, df, bias_period)
        
        # 设置日期格式
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.MonthLocator())
        
        # 设置布局
        plt.tight_layout()
        
        return fig
    
    def _plot_candlestick(self, ax, df):
        """绘制蜡烛图"""
        # 使用OHLC数据绘制蜡烛图
        for i, row in df.iterrows():
            color = 'red' if row['close'] >= row['open'] else 'green'
            ax.plot([row['date'], row['date']], [row['low'], row['high']], color=color)
            ax.plot([row['date'], row['date']], [row['open'], row['close']], color=color, linewidth=2)
        
        ax.set_ylabel('价格')
        ax.set_title('K线走势')
        ax.grid(True, alpha=0.3)
    
    def _plot_line(self, ax, df):
        """绘制折线图"""
        ax.plot(df['date'], df['close'], linewidth=1.5, color='blue', label='收盘价')
        ax.set_ylabel('价格')
        ax.set_title('价格走势')
        ax.grid(True, alpha=0.3)
        ax.legend()
    
    def _plot_bias(self, ax, df, period):
        """绘制BIAS指标"""
        bias = BIAS.calculate(df, period)
        ax.plot(df['date'], bias, linewidth=1, color='purple', label=f'BIAS({period})')
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=5, color='red', linestyle='--', alpha=0.5)
        ax.axhline(y=-5, color='green', linestyle='--', alpha=0.5)
        ax.set_ylabel('BIAS')
        ax.set_title('BIAS指标')
        ax.grid(True, alpha=0.3)
        ax.legend()