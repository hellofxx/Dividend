"""
技术分析图表 - 多指标综合展示 (v4.3)

v4.3 变更（2026-04-17）：
- 右侧最上方新增ETF收益曲线图（含250日年线），展示长期收益趋势
- 右侧从 5 个子图改为 6 个子图

v4.2 变更（2026-04-14）：
- 删除重复的"ETF收益走势"图表（与主分析图/策略对比图重复）
- 右侧从 6 个子图改为 5 个子图

v4.1 变更：
- 删除重复的"基金收益率走势"图表

v4.0 变更：
- 移除 h30269_data 参数，ETF 数据本身包含所有技术指标

布局：
- 左侧：交易统计摘要 + 核心指标
- 右侧：6 个图表纵向排列（ETF收益曲线、乖离率、MACD、RSI、KDJ、回撤）
"""

import logging
from pathlib import Path
from typing import List, Dict, TYPE_CHECKING, Tuple

import pandas as pd
import numpy as np

from ..models import BacktestResult, TradeRecord
from .themes import ThemeConfig, get_theme

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class TechnicalChart:
    """
    技术分析图表 - 6子图综合布局

    布局：
    [左侧信息栏]     [右侧图表区 - 6个子图纵向排列]
    - 交易统计       1. ETF收益曲线(含250日年线)
    - 核心指标       2. 乖离率(Bias)
    - 策略描述       3. MACD
                   4. RSI
                   5. KDJ
                   6. 回撤曲线
    """
    
    def __init__(self, theme: str = "professional"):
        self.theme = get_theme(theme)
        self._apply_theme()
    
    def _apply_theme(self):
        """应用主题到matplotlib"""
        import matplotlib.pyplot as plt
        plt.rcParams['figure.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.edgecolor'] = self.theme.text_color
        plt.rcParams['axes.labelcolor'] = self.theme.text_color
        plt.rcParams['xtick.color'] = self.theme.text_color
        plt.rcParams['ytick.color'] = self.theme.text_color
        plt.rcParams['text.color'] = self.theme.text_color
        plt.rcParams['grid.color'] = self.theme.grid_color
    
    # ------------------------------------------------------------------
    # 技术指标计算
    # ------------------------------------------------------------------

    def _calculate_macd(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标：DIF = EMA(12) - EMA(26), DEA = EMA(DIF, 9), MACD = 2*(DIF-DEA)"""
        ema12 = df['acc_nav'].ewm(span=12, adjust=False).mean()
        ema26 = df['acc_nav'].ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = 2 * (dif - dea)
        return dif, dea, macd
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """计算RSI指标：RSI = 100 - 100/(1+RS)"""
        delta = df['acc_nav'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_kdj(self, df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算KDJ指标：RSV → K → D → J = 3K-2D"""
        low_list = df['acc_nav'].rolling(window=n, min_periods=n).min()
        high_list = df['acc_nav'].rolling(window=n, min_periods=n).max()
        rsv = (df['acc_nav'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j
    
    def _calculate_drawdown(self, df: pd.DataFrame) -> pd.Series:
        """计算回撤曲线：回撤 = (当前值 - 历史最高值) / 历史最高值 * 100"""
        cummax = df['acc_nav'].cummax()
        drawdown = (df['acc_nav'] - cummax) / cummax * 100
        return drawdown
    
    # ------------------------------------------------------------------
    # 图表创建
    # ------------------------------------------------------------------

    def create(
        self,
        df: pd.DataFrame,
        result: BacktestResult,
        fund_code: str,
        fund_name: str,
    ) -> "plt.Figure":
        """
        创建技术分析图表
        
        Args:
            df: ETF数据DataFrame（含 nav, acc_nav, ma_250, bias）
            result: 回测结果
            fund_code: 基金代码
            fund_name: 基金名称
        """
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec
        
        fig = plt.figure(figsize=(18, 14))
        gs = GridSpec(6, 2, figure=fig, width_ratios=[1, 3], hspace=0.4, wspace=0.25)
        
        # ========== 左侧信息栏 ==========
        ax_info = fig.add_subplot(gs[:, 0])
        ax_info.axis('off')
        self._plot_info_panel(ax_info, df, result, fund_code, fund_name)
        
        # ========== 右侧图表区（6个图表） ==========
        # 1. ETF收益曲线(含250日年线)
        ax0 = fig.add_subplot(gs[0, 1])
        self._plot_nav_return(ax0, df)
        
        # 2. 乖离率(Bias)
        ax1 = fig.add_subplot(gs[1, 1])
        self._plot_bias(ax1, df)
        
        # 3. MACD
        ax2 = fig.add_subplot(gs[2, 1])
        self._plot_macd(ax2, df)
        
        # 4. RSI
        ax3 = fig.add_subplot(gs[3, 1])
        self._plot_rsi(ax3, df)
        
        # 5. KDJ
        ax4 = fig.add_subplot(gs[4, 1])
        self._plot_kdj(ax4, df)
        
        # 6. 回撤曲线
        ax5 = fig.add_subplot(gs[5, 1])
        self._plot_drawdown(ax5, df)
        
        ax5.set_xlabel('日期', fontsize=10)
        
        fig.suptitle(
            f'{fund_code} {fund_name} - 技术分析综合图表',
            fontsize=16, fontweight='bold',
            color=self.theme.text_color, y=0.98
        )
        
        # 不使用 tight_layout，手动调整布局
        fig.subplots_adjust(left=0.12, right=0.98, top=0.94, bottom=0.06, hspace=0.4, wspace=0.25)
        return fig
    
    # ------------------------------------------------------------------
    # 左侧信息栏
    # ------------------------------------------------------------------

    def _plot_info_panel(
        self,
        ax,
        df: pd.DataFrame,
        result: BacktestResult,
        fund_code: str,
        fund_name: str
    ):
        """绘制左侧信息栏"""
        trades = result.trades
        buy_trades = [t for t in trades if t.action == 'BUY']
        sell_trades = [t for t in trades if t.action == 'SELL']
        
        final_value = result.equity_curve['total_value'].iloc[-1] if len(result.equity_curve) > 0 else 0
        
        win_rate = result.metrics.get('win_rate', 0) * 100
        profit_loss_ratio = result.metrics.get('profit_loss_ratio', 0)
        max_drawdown = result.metrics.get('max_drawdown', 0) * 100
        total_return = result.metrics.get('total_return', 0)
        annual_return = result.metrics.get('annual_return', 0)
        sharpe = result.metrics.get('sharpe_ratio', 0)
        calmar = result.metrics.get('calmar_ratio', 0)
        
        info_lines = [
            f'=== 回测概览 ===',
            f'ETF代码: {fund_code}',
            f'ETF名称: {fund_name}',
            f'',
            f'=== 交易统计 ===',
            f'买入次数: {len(buy_trades)}',
            f'卖出次数: {len(sell_trades)}',
            f'交易次数: {len(trades)}',
            f'胜率: {win_rate:.1f}%',
            f'盈亏比: {profit_loss_ratio:.2f}',
            f'',
            f'=== 收益指标 ===',
            f'最终市值: ¥{final_value:,.2f}',
            f'累计收益: {total_return:.2f}%',
            f'年化收益: {annual_return:.2f}%',
            f'',
            f'=== 风险指标 ===',
            f'最大回撤: {max_drawdown:.2f}%',
            f'夏普比率: {sharpe:.2f}',
            f'卡玛比率: {calmar:.2f}',
            f'',
            f'=== 策略说明 ===',
            f'策略: 红利低波年线策略',
            f'买入条件: Bias < 0%',
            f'卖出条件: Bias >= 10%',
            f'均线周期: 250日',
            f'数据源: 512890前复权',
            f'',
            f'=== 图例说明 ===',
            f'● 红色圆点: 买入',
            f'● 绿色圆点: 卖出',
            f'—— 蓝色线: 累计净值',
            f'- - 橙色线: 250日年线',
        ]
        
        y_pos = 0.98
        line_height = 0.028
        
        for line in info_lines:
            if line.startswith('==='):
                ax.text(0.05, y_pos, line.replace('=== ', '').replace(' ===', ''),
                       fontsize=11, fontweight='bold',
                       color=self.theme.accent_color,
                       transform=ax.transAxes, verticalalignment='top')
                y_pos -= line_height * 1.2
            elif line == '':
                y_pos -= line_height * 0.5
            else:
                ax.text(0.05, y_pos, line,
                       fontsize=9, color=self.theme.text_color,
                       transform=ax.transAxes, verticalalignment='top')
                y_pos -= line_height
        
        # 添加边框
        for spine in ax.spines.values():
            spine.set_visible(True)
            spine.set_color(self.theme.grid_color)
    
    # ------------------------------------------------------------------
    # 右侧图表绘制
    # ------------------------------------------------------------------

    def _plot_nav_return(self, ax, df: pd.DataFrame):
        """绘制ETF收益曲线（含250日年线）"""
        ax.plot(df['date'], df['acc_nav'],
               color=self.theme.line_colors[0], linewidth=1.2,
               label='累计净值')
        
        ax.plot(df['date'], df['ma_250'],
               color=self.theme.line_colors[1], linewidth=1,
               linestyle='--', alpha=0.7,
               label='250日年线')
        
        ax.set_ylabel('累计净值', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('ETF收益曲线', fontsize=10, fontweight='bold')
        ax.legend(loc='upper left', fontsize=8)

    def _plot_bias(self, ax, df: pd.DataFrame):
        """绘制乖离率"""
        ax.plot(df['date'], df['bias'],
               color=self.theme.accent_color, linewidth=1)
        
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=-3, color='red', linestyle=':', alpha=0.7)
        ax.axhline(y=10, color='green', linestyle=':', alpha=0.7)
        
        ax.set_ylabel('乖离率(%)', fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_title('均线偏离(Bias)', fontsize=10, fontweight='bold')
        
        ax.text(0.01, 0.15, '买入<0%', transform=ax.transAxes,
               fontsize=8, color='red')
        ax.text(0.01, 0.85, '卖出≥10%', transform=ax.transAxes,
               fontsize=8, color='green')
    
    def _plot_macd(self, ax, df: pd.DataFrame):
        """绘制MACD"""
        dif, dea, macd = self._calculate_macd(df)
        
        ax.plot(df['date'], dif, label='DIF', color='#1f77b4', linewidth=1)
        ax.plot(df['date'], dea, label='DEA', color='#ff7f0e', linewidth=1)
        
        colors = ['red' if v > 0 else 'green' for v in macd]
        ax.bar(df['date'], macd, color=colors, alpha=0.5, width=1)
        
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax.set_ylabel('MACD', fontsize=9)
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_title('MACD指标', fontsize=10, fontweight='bold')
    
    def _plot_rsi(self, ax, df: pd.DataFrame):
        """绘制RSI"""
        rsi = self._calculate_rsi(df)
        
        ax.plot(df['date'], rsi, label='RSI(14)',
               color=self.theme.accent_color, linewidth=1)
        
        ax.axhline(y=70, color='red', linestyle='--', alpha=0.5, label='超买(70)')
        ax.axhline(y=30, color='green', linestyle='--', alpha=0.5, label='超卖(30)')
        ax.fill_between(df['date'], 30, 70, alpha=0.1, color='gray')
        
        ax.set_ylim(0, 100)
        ax.set_ylabel('RSI', fontsize=9)
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_title('RSI相对强弱指标', fontsize=10, fontweight='bold')
    
    def _plot_kdj(self, ax, df: pd.DataFrame):
        """绘制KDJ"""
        k, d, j = self._calculate_kdj(df)
        
        ax.plot(df['date'], k, label='K', color='#1f77b4', linewidth=1)
        ax.plot(df['date'], d, label='D', color='#ff7f0e', linewidth=1)
        ax.plot(df['date'], j, label='J', color='#d62728', linewidth=1, alpha=0.7)
        
        ax.axhline(y=80, color='red', linestyle='--', alpha=0.5)
        ax.axhline(y=20, color='green', linestyle='--', alpha=0.5)
        
        ax.set_ylabel('KDJ', fontsize=9)
        ax.legend(loc='upper left', fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_title('KDJ随机指标', fontsize=10, fontweight='bold')
    
    def _plot_drawdown(self, ax, df: pd.DataFrame):
        """绘制回撤曲线"""
        drawdown = self._calculate_drawdown(df)
        
        ax.fill_between(df['date'], drawdown, 0,
                       color='red', alpha=0.3, label='回撤')
        ax.plot(df['date'], drawdown, color='red', linewidth=1)
        
        ax.axhline(y=0, color='gray', linestyle='-', alpha=0.5)
        ax.set_ylabel('回撤(%)', fontsize=9)
        ax.set_title('回撤曲线', fontsize=10, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        max_dd = drawdown.min()
        ax.text(0.01, 0.05, f'最大回撤: {max_dd:.2f}%',
               transform=ax.transAxes, fontsize=9,
               color='red', fontweight='bold')
    
    def save(self, fig: "plt.Figure", path: str) -> None:
        """保存图表"""
        import matplotlib.pyplot as plt
        
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        fig.savefig(
            output_path, dpi=150, bbox_inches='tight',
            facecolor=self.theme.bg_color, edgecolor='none'
        )
        plt.close(fig)
        logger.info(f"技术分析图表已保存: {output_path}")
