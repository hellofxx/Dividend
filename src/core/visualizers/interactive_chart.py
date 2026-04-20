"""
交互式图表绘制 - 使用Plotly

展示：净值走势+年线+买卖点、乖离率、收益曲线、核心指标
"""

import logging
from pathlib import Path
from typing import List, TYPE_CHECKING

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..models import BacktestResult, TradeRecord
from .themes import ThemeConfig, get_theme

if TYPE_CHECKING:
    import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)


class InteractiveChart:
    """
    交互式图表 - 使用Plotly和cufflinks
    
    包含：
    - 净值走势+年线+买卖点
    - 乖离率
    - 收益曲线
    - 核心指标
    """
    
    def __init__(self, theme: str = "professional"):
        self.theme = get_theme(theme)
        self._apply_theme()
    
    def _apply_theme(self):
        """应用主题配置"""
        # Plotly主题配置
        self.plotly_theme = {
            'bg_color': self.theme.bg_color,
            'text_color': self.theme.text_color,
            'line_colors': self.theme.line_colors,
            'accent_color': self.theme.accent_color,
            'buy_color': self.theme.buy_color,
            'sell_color': self.theme.sell_color,
            'grid_color': self.theme.grid_color
        }
    
    def create(
        self,
        df: pd.DataFrame,
        result: BacktestResult,
        fund_code: str,
        fund_name: str,
    ):
        """
        创建交互式图表
        """
        # 创建子图布局
        fig = make_subplots(
            rows=3, cols=2,
            specs=[
                [{'colspan': 1}, {'rowspan': 3}],  # 净值走势 + 指标面板
                [{'colspan': 1}, None],  # 乖离率
                [{'colspan': 1}, None]   # 收益曲线
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1,
            subplot_titles=(
                f'{fund_code} {fund_name}',
                '核心指标',
                '乖离率',
                '收益曲线'
            )
        )
        
        # 主图：净值走势
        self._plot_nav(fig, df, result.trades, row=1, col=1)
        
        # 副图1：乖离率
        self._plot_bias(fig, df, row=2, col=1)
        
        # 副图2：收益曲线
        self._plot_equity(fig, result, row=3, col=1)
        
        # 右侧：核心指标面板
        self._plot_metrics_panel(fig, result, fund_code, fund_name, row=1, col=2)
        
        # 应用主题
        fig.update_layout(
            height=800,
            width=1200,
            paper_bgcolor=self.plotly_theme['bg_color'],
            plot_bgcolor=self.plotly_theme['bg_color'],
            font=dict(
                color=self.plotly_theme['text_color']
            ),
            title_font=dict(
                size=16,
                color=self.plotly_theme['text_color']
            ),
            hovermode='x unified',
            showlegend=True
        )
        
        return fig
    
    def save(
        self,
        fig,
        output_path: Path,
        format: str = 'html',
    ) -> Path:
        """保存图表"""
        if format == 'html':
            output_path = output_path.with_suffix('.html')
            fig.write_html(output_path)
        else:
            output_path = output_path.with_suffix('.png')
            fig.write_image(output_path, scale=2)
        
        logger.info(f"交互式图表已保存: {output_path}")
        return output_path
    
    def _plot_nav(
        self,
        fig,
        df: pd.DataFrame,
        trades: List[TradeRecord],
        row: int,
        col: int,
    ) -> None:
        """绘制净值走势"""
        # 使用Plotly直接绘制累计净值
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['acc_nav'],
                name='累计净值',
                line=dict(
                    color=self.plotly_theme['line_colors'][0],
                    width=1.5
                )
            ),
            row=row,
            col=col
        )
        
        # 绘制年线
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['ma_250'],
                name='250日年线',
                line=dict(
                    color=self.plotly_theme['line_colors'][1],
                    width=1,
                    dash='dash'
                ),
                opacity=0.7
            ),
            row=row,
            col=col
        )
        
        # 绘制买入点
        buy_dates = [t.date for t in trades if t.action == 'BUY']
        buy_prices = [t.price for t in trades if t.action == 'BUY']
        if buy_dates:
            fig.add_trace(
                go.Scatter(
                    x=buy_dates,
                    y=buy_prices,
                    name='买入',
                    mode='markers',
                    marker=dict(
                        color='red',
                        size=6,
                        line=dict(
                            color='white',
                            width=0.5
                        )
                    )
                ),
                row=row,
                col=col
            )
        
        # 绘制卖出点
        sell_dates = [t.date for t in trades if t.action == 'SELL']
        sell_prices = [t.price for t in trades if t.action == 'SELL']
        if sell_dates:
            fig.add_trace(
                go.Scatter(
                    x=sell_dates,
                    y=sell_prices,
                    name='卖出',
                    mode='markers',
                    marker=dict(
                        color='green',
                        size=6,
                        line=dict(
                            color='white',
                            width=0.5
                        )
                    )
                ),
                row=row,
                col=col
            )
        
        # 更新轴配置
        fig.update_xaxes(
            title='日期',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
        fig.update_yaxes(
            title='累计净值',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
    
    def _plot_bias(
        self,
        fig,
        df: pd.DataFrame,
        row: int,
        col: int,
    ) -> None:
        """绘制乖离率"""
        # 使用Plotly直接绘制乖离率
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['bias'],
                name='乖离率',
                line=dict(
                    color=self.plotly_theme['accent_color'],
                    width=1
                )
            ),
            row=row,
            col=col
        )
        
        # 绘制参考线
        fig.add_hline(
            y=0,
            line=dict(
                color='gray',
                dash='dash',
                width=1
            ),
            row=row,
            col=col
        )
        fig.add_hline(
            y=-3,
            line=dict(
                color=self.plotly_theme['buy_color'],
                dash='dot',
                width=1
            ),
            row=row,
            col=col
        )
        fig.add_hline(
            y=10,
            line=dict(
                color=self.plotly_theme['sell_color'],
                dash='dot',
                width=1
            ),
            row=row,
            col=col
        )
        
        # 更新轴配置
        fig.update_xaxes(
            title='日期',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
        fig.update_yaxes(
            title='乖离率(%)',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
    
    def _plot_equity(
        self,
        fig,
        result: BacktestResult,
        row: int,
        col: int,
    ) -> None:
        """绘制收益曲线"""
        if len(result.equity_curve) > 0:
            df = result.equity_curve
            # 使用Plotly直接绘制收益曲线
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['total_value'],
                    name='资金曲线',
                    line=dict(
                        color=self.plotly_theme['accent_color'],
                        width=1.5
                    ),
                    fill='tozeroy',
                    fillcolor=f"rgba({self._hex_to_rgb(self.plotly_theme['accent_color'])}, 0.2)"
                ),
                row=row,
                col=col
            )
        
        # 更新轴配置
        fig.update_xaxes(
            title='日期',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
        fig.update_yaxes(
            title='资金(元)',
            showgrid=True,
            gridcolor=self.plotly_theme['grid_color'],
            row=row,
            col=col
        )
    
    def _plot_metrics_panel(
        self,
        fig,
        result: BacktestResult,
        fund_code: str,
        fund_name: str,
        row: int,
        col: int,
    ) -> None:
        """绘制核心指标面板"""
        metrics = result.metrics
        
        # 构建指标文本
        text = f"""
        <b>基金信息</b><br>
        基金代码: {fund_code}<br>
        基金名称: {fund_name[:15]}...<br>
        <br>
        <b>收益指标</b><br>
        累计收益: {metrics.get('total_return', 0):+.2f}%<br>
        年化收益: {metrics.get('annual_return', 0):+.2f}%<br>
        <br>
        <b>风险指标</b><br>
        最大回撤: {metrics.get('max_drawdown', 0):.2f}%<br>
        夏普比率: {metrics.get('sharpe_ratio', 0):.2f}<br>
        卡玛比率: {metrics.get('calmar_ratio', 0):.2f}<br>
        <br>
        <b>交易统计</b><br>
        胜率: {metrics.get('win_rate', 0):.1f}%<br>
        盈亏比: {metrics.get('profit_loss_ratio', 0):.2f}<br>
        交易次数: {len(result.trades)}笔
        """
        
        # 添加文本框
        fig.add_trace(
            go.Scatter(
                x=[0],
                y=[0],
                mode='text',
                text=[text],
                textposition='middle center',
                showlegend=False
            ),
            row=row,
            col=col
        )
        
        # 隐藏轴
        fig.update_xaxes(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            row=row,
            col=col
        )
        fig.update_yaxes(
            showticklabels=False,
            showgrid=False,
            zeroline=False,
            row=row,
            col=col
        )
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """将十六进制颜色转换为RGB"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
