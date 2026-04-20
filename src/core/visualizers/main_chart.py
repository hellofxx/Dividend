"""
主分析图绘制 - 简洁直观版本

展示：净值走势+年线+买卖点、乖离率、收益曲线、核心指标
"""

import logging
from pathlib import Path
from typing import List, TYPE_CHECKING

import pandas as pd

from ..models import BacktestResult, TradeRecord
from .themes import get_theme

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class MainChart:
    """
    主分析图 - 简洁三栏布局
    
    [左] 净值走势+年线+买卖点
    [中] 乖离率+收益曲线
    [右] 核心指标摘要
    """
    
    def __init__(self, theme: str = "professional"):
        self.theme = get_theme(theme)
        self._apply_theme()
    
    def _apply_theme(self):
        """应用主题到matplotlib（懒加载）"""
        import matplotlib.pyplot as plt
        # 确保中文字体正确设置
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
        plt.rcParams['axes.unicode_minus'] = False
        # 应用主题颜色
        plt.rcParams['figure.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.edgecolor'] = self.theme.text_color
        plt.rcParams['axes.labelcolor'] = self.theme.text_color
        plt.rcParams['xtick.color'] = self.theme.text_color
        plt.rcParams['ytick.color'] = self.theme.text_color
        plt.rcParams['text.color'] = self.theme.text_color
        plt.rcParams['grid.color'] = self.theme.grid_color
    
    def create(
        self,
        df: pd.DataFrame,
        result: BacktestResult,
        fund_code: str,
        fund_name: str,
    ):
        """
        创建主分析图
        """
        import matplotlib.pyplot as plt
        # 简洁两栏布局: [左主图 | 右指标]
        fig = plt.figure(figsize=(14, 8))
        
        # 主图区域: 净值走势 (左上)
        ax_nav = fig.add_axes((0.08, 0.55, 0.55, 0.38))
        self._plot_nav(ax_nav, df, result.trades, fund_code, fund_name)
        
        # 副图1: 乖离率 (左中)
        ax_bias = fig.add_axes((0.08, 0.32, 0.55, 0.20), sharex=ax_nav)
        self._plot_bias(ax_bias, df)
        
        # 副图2: 收益曲线 (左下)
        ax_equity = fig.add_axes((0.08, 0.08, 0.55, 0.20), sharex=ax_nav)
        self._plot_equity(ax_equity, result)
        
        # 右侧: 核心指标面板
        ax_metrics = fig.add_axes((0.68, 0.08, 0.28, 0.85))
        self._plot_metrics_panel(ax_metrics, result, fund_code, fund_name)
        
        return fig
    
    def save(
        self,
        fig,
        output_path: Path,
        dpi: int = 150,
    ) -> Path:
        """保存图表"""
        import matplotlib.pyplot as plt
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight',
                   facecolor=self.theme.bg_color)
        plt.close(fig)
        logger.info(f"图表已保存: {output_path}")
        return output_path
    
    def _plot_nav(
        self,
        ax,
        df: pd.DataFrame,
        trades: List[TradeRecord],
        fund_code: str,
        fund_name: str,
    ) -> None:
        """绘制净值走势 - 包含基金代码和全称，使用累计净值"""
        # 使用累计净值绘制走势（关键修改：所有年线判断、图表生成使用累计净值）
        ax.plot(df['date'], df['acc_nav'], 
               color=self.theme.line_colors[0],
               linewidth=1.5, label='累计净值')
        
        # 年线 - 基于累计净值计算的250日均线
        ax.plot(df['date'], df['ma_250'], 
               color=self.theme.line_colors[1],
               linewidth=1, linestyle='--', 
               label='250日年线(累计净值)', alpha=0.7)
        
        # 买卖点 - 小红点表示买入，小绿点表示卖出
        # 注意：交易价格t.price是当时的累计净值
        buy_dates = [t.date for t in trades if t.action == 'BUY']
        buy_prices = [t.price for t in trades if t.action == 'BUY']
        sell_dates = [t.date for t in trades if t.action == 'SELL']
        sell_prices = [t.price for t in trades if t.action == 'SELL']
        
        # 使用小红点表示买入，小绿点表示卖出
        if buy_dates:
            ax.scatter(buy_dates, buy_prices, 
                      color='red',
                      marker='o', s=60, zorder=5, label='买入',
                      edgecolors='white', linewidths=0.5)
        if sell_dates:
            ax.scatter(sell_dates, sell_prices, 
                      color='green',
                      marker='o', s=60, zorder=5, label='卖出',
                      edgecolors='white', linewidths=0.5)
        
        # 标题显示基金代码和全称
        display_name = fund_name if fund_name else f"基金{fund_code}"
        ax.set_title(f'{fund_code} {display_name}', 
                    fontsize=14, fontweight='bold',
                    color=self.theme.text_color)
        
        ax.set_ylabel('累计净值', color=self.theme.text_color)
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', labelbottom=False)
    
    def _plot_bias(self, ax, df: pd.DataFrame) -> None:
        """绘制乖离率"""
        ax.plot(df['date'], df['bias'], 
               color=self.theme.accent_color, linewidth=1)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=-3, color=self.theme.buy_color, 
                  linestyle=':', alpha=0.7)
        ax.axhline(y=10, color=self.theme.sell_color, 
                  linestyle=':', alpha=0.7)
        
        ax.set_ylabel('乖离率(%)', fontsize=9, color=self.theme.text_color)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', labelbottom=False)
        
        # 标注阈值 - 更新为实际策略参数
        ax.text(0.02, 0.15, '买入<0%', transform=ax.transAxes,
               fontsize=8, color='red',
               bbox=dict(boxstyle='round', facecolor=self.theme.bg_color, alpha=0.8))
        ax.text(0.02, 0.85, '卖出≥10%', transform=ax.transAxes,
               fontsize=8, color='green',
               bbox=dict(boxstyle='round', facecolor=self.theme.bg_color, alpha=0.8))
    
    def _plot_equity(self, ax, result: BacktestResult) -> None:
        """绘制收益曲线"""
        if len(result.equity_curve) > 0:
            df = result.equity_curve
            ax.plot(df['date'], df['total_value'], 
                   color=self.theme.accent_color, linewidth=1.5)
            ax.fill_between(df['date'], df['total_value'], 
                           alpha=0.2, color=self.theme.accent_color)
            
            # 标注最终收益
            final_value = df['total_value'].iloc[-1]
            ax.text(0.98, 0.95, f'{final_value:,.0f}元',
                   transform=ax.transAxes, ha='right',
                   fontsize=10, fontweight='bold',
                   color=self.theme.accent_color)
        
        ax.set_ylabel('资金(元)', fontsize=9, color=self.theme.text_color)
        ax.set_xlabel('日期', fontsize=9, color=self.theme.text_color)
        ax.grid(True, alpha=0.3)
    
    def _plot_metrics_panel(
        self,
        ax,
        result: BacktestResult,
        fund_code: str,
        fund_name: str,
    ) -> None:
        """绘制右侧指标面板"""
        ax.axis('off')
        
        metrics = result.metrics
        
        # 面板内容
        lines = [
            ('═══ 核心指标 ═══', 'header'),
            ('', 'space'),
            (f'基金代码: {fund_code}', 'label'),
            (f'基金名称: {fund_name[:15]}...' if len(fund_name) > 15 else f'基金名称: {fund_name}', 'label'),
            ('', 'space'),
            ('═══ 收益指标 ═══', 'header'),
            ('', 'space'),
            (f"累计收益: {metrics.get('total_return', 0):+.2f}%", 'return'),
            (f"年化收益: {metrics.get('annual_return', 0):+.2f}%", 'return'),
            ('', 'space'),
            ('═══ 风险指标 ═══', 'header'),
            ('', 'space'),
            (f"最大回撤: {metrics.get('max_drawdown', 0):.2f}%", 'risk'),
            (f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}", 'normal'),
            (f"卡玛比率: {metrics.get('calmar_ratio', 0):.2f}", 'normal'),
            ('', 'space'),
            ('═══ 交易统计 ═══', 'header'),
            ('', 'space'),
            (f"胜率: {metrics.get('win_rate', 0):.1f}%", 'normal'),
            (f"盈亏比: {metrics.get('profit_loss_ratio', 0):.2f}", 'normal'),
            (f"交易次数: {len(result.trades)}笔", 'normal'),
        ]
        
        # 绘制文本
        y_pos = 0.95
        for text, style in lines:
            if style == 'header':
                ax.text(0.5, y_pos, text, ha='center', va='top',
                       fontsize=11, fontweight='bold',
                       color=self.theme.accent_color,
                       transform=ax.transAxes)
                y_pos -= 0.06
            elif style == 'space':
                y_pos -= 0.03
            elif style == 'return':
                value = float(text.split(':')[1].strip().replace('%', ''))
                color = self.theme.buy_color if value >= 0 else self.theme.sell_color
                ax.text(0.1, y_pos, text, ha='left', va='top',
                       fontsize=10, fontweight='bold', color=color,
                       transform=ax.transAxes)
                y_pos -= 0.05
            elif style == 'risk':
                ax.text(0.1, y_pos, text, ha='left', va='top',
                       fontsize=10, color=self.theme.sell_color,
                       transform=ax.transAxes)
                y_pos -= 0.05
            else:
                ax.text(0.1, y_pos, text, ha='left', va='top',
                       fontsize=10, color=self.theme.text_color,
                       transform=ax.transAxes)
                y_pos -= 0.05
