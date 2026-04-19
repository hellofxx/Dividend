"""
策略对比图绘制 (v6.0 - 重构版)

职责：策略对比的可视化呈现
- 调用 analytics 模块计算指标
- 专注于图表绘制，不重复计算

图表布局：
  - 上方：累计收益率曲线（时间加权口径）
  - 左下：年度收益柱状图
  - 中下：风险指标雷达图
  - 右下：核心指标表格

v6.0 变更：
- 所有指标计算委托给 analytics 模块
- 本模块只负责可视化
"""

import logging
from pathlib import Path
from typing import List, Tuple, TYPE_CHECKING

import pandas as pd
import numpy as np

from ..models import CompareResult
from src.backtest.analytics import ReturnsCalculator, BenchmarkMetrics
from .themes import ThemeConfig, get_theme

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes

logger = logging.getLogger(__name__)


class CompareChart:
    """
    策略对比图
    
    职责：调用 analytics 模块获取指标，进行可视化
    """

    def __init__(self, theme: str = "professional"):
        self.theme = get_theme(theme)
        self._apply_theme()

    def _apply_theme(self):
        """应用主题"""
        import matplotlib.pyplot as plt
        plt.rcParams['figure.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.facecolor'] = self.theme.bg_color
        plt.rcParams['axes.edgecolor'] = self.theme.text_color
        plt.rcParams['axes.labelcolor'] = self.theme.text_color
        plt.rcParams['xtick.color'] = self.theme.text_color
        plt.rcParams['ytick.color'] = self.theme.text_color
        plt.rcParams['text.color'] = self.theme.text_color
        plt.rcParams['grid.color'] = self.theme.grid_color

    def create(self, compare_result: CompareResult):
        """创建专业级对比图"""
        import matplotlib.pyplot as plt
        from matplotlib import gridspec

        fig = plt.figure(figsize=(15, 9))
        gs = gridspec.GridSpec(
            2, 3,
            height_ratios=[2, 1.3],
            width_ratios=[1.1, 1, 1.1],
            hspace=0.35, wspace=0.3,
            left=0.05, right=0.98, top=0.94, bottom=0.06
        )

        # 上方大图：累计收益率曲线
        ax_main = fig.add_subplot(gs[0, :])
        self._plot_twr_curve(ax_main, compare_result)

        # 左下：年度收益柱状图
        ax_annual = fig.add_subplot(gs[1, 0])
        self._plot_annual_returns(ax_annual, compare_result)

        # 中下：风险指标雷达图
        ax_radar = fig.add_subplot(gs[1, 1], polar=True)
        self._plot_risk_radar(ax_radar, compare_result)

        # 右下：核心指标表格
        ax_table = fig.add_subplot(gs[1, 2])
        self._plot_metrics_table(ax_table, compare_result)

        return fig

    def save(self, fig, output_path: Path, dpi: int = 150) -> Path:
        """保存图表"""
        import matplotlib.pyplot as plt
        fig.savefig(output_path, dpi=dpi, facecolor=self.theme.bg_color)
        plt.close(fig)
        logger.info(f"对比图已保存: {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # 图表绘制方法
    # ------------------------------------------------------------------

    def _plot_twr_curve(self, ax, cr: CompareResult) -> None:
        """绘制时间加权收益率曲线"""
        strategies = self._get_strategy_data(cr)
        if not strategies:
            ax.text(0.5, 0.5, '无可用数据', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)
            return

        for name, df, color, ls in strategies:
            # 调用 analytics 模块计算 TWR
            twr = ReturnsCalculator.time_weighted_return(df)
            
            ax.plot(df['date'], twr,
                   color=color, linewidth=2 if name.startswith('主') else 1.5,
                   linestyle=ls, label=name, alpha=0.9)
            
            # 末端标注
            last_date = df['date'].iloc[-1]
            last_ret = float(twr.iloc[-1])
            ax.annotate(
                f'{last_ret:+.1f}%',
                xy=(last_date, last_ret),
                xytext=(pd.Timedelta(days=15), 0),
                textcoords=ax.get_xaxis_transform(),
                fontsize=9, fontweight='bold', color=color,
                va='center', ha='left',
                bbox=dict(boxstyle='round,pad=0.25', facecolor=self.theme.bg_color,
                         edgecolor=color, alpha=0.7),
            )

        ax.axhline(y=0, color=self.theme.text_color, linewidth=0.8, alpha=0.5)
        ax.set_title('累计收益率对比（时间加权）', fontsize=14,
                    color=self.theme.text_color, pad=12, fontweight='bold')
        ax.set_ylabel('累计收益率 (%)', fontsize=10, color=self.theme.text_color)
        ax.legend(loc='lower left', fontsize=9, framealpha=0.9, ncol=3)
        ax.grid(True, alpha=0.3)

    def _plot_annual_returns(self, ax, cr: CompareResult) -> None:
        """绘制年度收益率柱状图"""
        strategies = self._get_strategy_data(cr)
        if not strategies:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center',
                   transform=ax.transAxes, color=self.theme.text_color)
            return

        # 调用 analytics 模块获取年度收益
        all_annual = {}
        for name, df, color, _ in strategies:
            all_annual[name] = BenchmarkMetrics.get_annual_returns_for_chart(df)

        all_years = sorted(set(y for d in all_annual.values() for y in d.keys()))
        if not all_years:
            ax.text(0.5, 0.5, '无年度数据', ha='center', va='center',
                   transform=ax.transAxes, color=self.theme.text_color)
            return

        n_years = len(all_years)
        n_strats = len(all_annual)
        bar_width = min(0.11, 0.65 / n_strats)  # 进一步减小柱宽，避免重叠
        x = np.arange(n_years)

        colors = list(self.theme.line_colors) + ['#666688', '#E87020']

        for i, (name, annual_dict) in enumerate(all_annual.items()):
            values = [annual_dict.get(year, 0.0) for year in all_years]
            offset = (i - n_strats/2 + 0.5) * bar_width
            bars = ax.bar(x + offset, values, bar_width,
                  label=name, color=colors[i % len(colors)], alpha=0.85)
            
            # 为每个柱子添加数据标签，但仅在空间充足时
            for j, bar in enumerate(bars):
                height = bar.get_height()
                if abs(height) > 5:  # 仅为绝对值大于5%的数据添加标签
                    ax.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height > 0 else -5),
                            f'{values[j]:+.1f}%', ha='center', va='bottom' if height > 0 else 'top',
                            fontsize=6, color=self.theme.text_color)

        ax.axhline(y=0, color=self.theme.text_color, linewidth=0.8, alpha=0.5)
        ax.set_xticks(x)
        ax.set_xticklabels([str(y) for y in all_years], fontsize=8)
        ax.set_title('年度收益率 (%)', fontsize=11, color=self.theme.text_color, fontweight='bold')
        ax.set_ylabel('收益率 (%)', fontsize=8, color=self.theme.text_color)
        ax.legend(loc='lower center', fontsize=7, ncol=min(n_strats, 3),
                 framealpha=0.85, columnspacing=0.6, bbox_to_anchor=(0.5, -0.3))
        ax.grid(True, alpha=0.3, axis='y')
        ax.tick_params(axis='both', labelsize=8)
        # 调整子图布局，为图例留出空间
        ax.margins(y=0.15)

    def _plot_risk_radar(self, ax, cr: CompareResult) -> None:
        """绘制风险指标雷达图"""
        strategies = self._get_strategy_data(cr)
        if not strategies:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center',
                   transform=ax.transAxes, color=self.theme.text_color)
            return

        strategies = strategies[:4]  # 最多4个
        
        categories = ['年化收益', '夏普比率', '卡玛比率', '胜率']
        n_cats = len(categories)
        angles = np.linspace(0, 2 * np.pi, n_cats, endpoint=False).tolist()
        angles += angles[:1]

        colors = list(self.theme.line_colors) + ['#666688', '#E87020']

        for i, (name, df, color, _) in enumerate(strategies):
            # 调用 analytics 模块计算指标
            metrics = BenchmarkMetrics.calculate_all_metrics(df)
            
            # 归一化到 0-1
            values = [
                min(max(metrics.get('annual_return', 0) / 50, 0), 1),
                min(max(metrics.get('sharpe_ratio', 0) / 3, 0), 1),
                min(max(metrics.get('calmar_ratio', 0) / 3, 0), 1),
                0.6,  # 占位
            ]
            values += values[:1]

            ax.plot(angles, values, color=color, linewidth=1.5, label=name)
            ax.fill(angles, values, color=color, alpha=0.15)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=8, color=self.theme.text_color)
        ax.set_ylim(0, 1)
        ax.set_title('风险指标', fontsize=11, color=self.theme.text_color,
                    pad=15, fontweight='bold')
        ax.legend(loc='lower right', bbox_to_anchor=(1.3, 0.1),
                 fontsize=7, framealpha=0.8)

    def _plot_metrics_table(self, ax, cr: CompareResult) -> None:
        """绘制核心指标对比表格"""
        ax.axis('off')

        strategies = self._get_strategy_data(cr)
        if not strategies:
            ax.text(0.5, 0.5, '无数据', ha='center', va='center',
                   transform=ax.transAxes)
            return

        headers = ['策略', '累计收益', '年化收益', '最大回撤', '夏普', '索提诺']
        rows = [headers]

        for name, df, _, _ in strategies[:5]:
            # 调用 analytics 模块获取指标
            metrics = BenchmarkMetrics.calculate_all_metrics(df)
            
            row = [
                name[:7] + '...' if len(name) > 7 else name,  # 进一步缩短策略名称
                f"{metrics.get('total_return', 0):+.1f}%",
                f"{metrics.get('annual_return', 0):+.1f}%",
                f"{metrics.get('max_drawdown', 0):.1f}%",
                f"{metrics.get('sharpe_ratio', 0):.2f}",
                f"{metrics.get('sortino_ratio', 0):.2f}",
            ]
            rows.append(row)

        table = ax.table(
            cellText=rows[1:],
            colLabels=rows[0],
            cellLoc='center',
            loc='center',
            bbox=[0.05, 0.05, 0.9, 0.9]  # 缩小表格边界，避免溢出
        )

        table.auto_set_font_size(False)
        table.set_fontsize(7)  # 进一步减小字体大小
        table.scale(1, 1.4)  # 调整行高

        for i in range(len(headers)):
            table[(0, i)].set_facecolor(self.theme.table_header_bg)
            table[(0, i)].set_text_props(weight='bold', color=self.theme.table_header_color, fontsize=7)

        for i in range(1, len(rows)):
            for j in range(len(headers)):
                table[(i, j)].set_facecolor(self.theme.bg_color if i % 2 == 0 else self.theme.table_alt_bg)
                table[(i, j)].set_text_props(color=self.theme.text_color, fontsize=7)

        ax.set_title('核心指标对比', fontsize=11, color=self.theme.text_color,
                    fontweight='bold', pad=8)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _get_strategy_data(self, cr: CompareResult) -> List[Tuple[str, pd.DataFrame, str, str]]:
        """获取所有策略数据"""
        colors = self.theme.line_colors
        strategies = []
        
        if cr.main and len(cr.main.equity_curve) > 0:
            strategies.append((
                cr.main.name or '主策略(年线)',
                cr.main.equity_curve,
                colors[0], '-'
            ))
        
        if cr.buy_hold and len(cr.buy_hold.equity_curve) > 0:
            strategies.append((
                '一次性买入',
                cr.buy_hold.equity_curve,
                colors[1], '--'
            ))
        
        if cr.dca and len(cr.dca.equity_curve) > 0:
            strategies.append((
                '定期定额',
                cr.dca.equity_curve,
                colors[2], '-.'
            ))
        
        if cr.index_curve is not None and len(cr_curve := cr.index_curve) > 0:
            strategies.append(('沪深300', cr_curve, '#666688', ':'))
        
        if hasattr(cr, 'shanghai_curve') and cr.shanghai_curve is not None:
            strategies.append(('上证指数', cr.shanghai_curve, '#E87020', (0, (3, 2, 1, 2))))
        
        return strategies
