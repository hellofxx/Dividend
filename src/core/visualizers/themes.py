"""
主题配置

提供5套预设视觉主题：专业、现代、暗黑、柔色、鲜活。
"""

from dataclasses import dataclass
from typing import Dict, Tuple, Literal


@dataclass
class ThemeConfig:
    """主题配置"""
    name: str
    bg_color: str
    text_color: str
    grid_color: str
    line_colors: Tuple[str, ...]
    accent_color: str
    buy_color: str
    sell_color: str
    table_header_bg: str
    table_header_color: str
    table_alt_bg: str

    def apply(self):
        """应用主题到 matplotlib（懒加载）"""
        import matplotlib.pyplot as plt
        plt.rcParams['figure.facecolor'] = self.bg_color
        plt.rcParams['axes.facecolor']   = self.bg_color
        plt.rcParams['axes.edgecolor']   = self.text_color
        plt.rcParams['axes.labelcolor']  = self.text_color
        plt.rcParams['xtick.color']      = self.text_color
        plt.rcParams['ytick.color']      = self.text_color
        plt.rcParams['text.color']       = self.text_color
        plt.rcParams['grid.color']       = self.grid_color


THEMES: Dict[str, ThemeConfig] = {
    "professional": ThemeConfig(
        name="专业",
        bg_color="#FFFFFF",
        text_color="#333333",
        grid_color="#E0E0E0",
        line_colors=("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"),
        accent_color="#1f77b4",
        buy_color="#00AA00",  # 中国股市：涨红跌绿
        sell_color="#CC0000",
        table_header_bg="#1f77b4",
        table_header_color="#FFFFFF",
        table_alt_bg="#F5F5F5",
    ),
    "modern": ThemeConfig(
        name="现代",
        bg_color="#F8F9FA",
        text_color="#212529",
        grid_color="#DEE2E6",
        line_colors=("#0D6EFD", "#6610F2", "#20C997", "#DC3545", "#FD7E14"),
        accent_color="#0D6EFD",
        buy_color="#198754",
        sell_color="#DC3545",
        table_header_bg="#0D6EFD",
        table_header_color="#FFFFFF",
        table_alt_bg="#E9ECEF",
    ),
    "dark": ThemeConfig(
        name="暗黑",
        bg_color="#1E1E1E",
        text_color="#E0E0E0",
        grid_color="#404040",
        line_colors=("#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8"),
        accent_color="#4FC3F7",
        buy_color="#81C784",
        sell_color="#E57373",
        table_header_bg="#4FC3F7",
        table_header_color="#1E1E1E",
        table_alt_bg="#2D2D2D",
    ),
    "pastel": ThemeConfig(
        name="柔色",
        bg_color="#FAFAFA",
        text_color="#5D5D5D",
        grid_color="#E8E8E8",
        line_colors=("#7B9E89", "#B8A5C4", "#F4B393", "#8FA8C8", "#C8B89A"),
        accent_color="#7B9E89",
        buy_color="#7B9E89",
        sell_color="#D48C8C",
        table_header_bg="#7B9E89",
        table_header_color="#FFFFFF",
        table_alt_bg="#F0F0F0",
    ),
    "vivid": ThemeConfig(
        name="鲜活",
        bg_color="#FFFFFF",
        text_color="#2C3E50",
        grid_color="#ECF0F1",
        line_colors=("#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6"),
        accent_color="#E74C3C",
        buy_color="#2ECC71",
        sell_color="#E74C3C",
        table_header_bg="#E74C3C",
        table_header_color="#FFFFFF",
        table_alt_bg="#F9F9F9",
    ),
}


def get_theme(theme_name: str = "professional") -> ThemeConfig:
    """获取主题配置"""
    return THEMES.get(theme_name.lower(), THEMES["professional"])