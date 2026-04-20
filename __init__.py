"""
量化工作室 QuantStudio v1.2
===========================

整合红利低波回测系统 + ETF技术分析工具，支持：
- 判断模式：实时ETF技术分析 + 多因子买入信号判定
- 回测模式：量化回测分析 + 多策略基准对比
- 统一数据源：AkshareProvider
- 丰富的可视化分析图表
- 多种主题样式

标准目录结构:
- src/core/: 公共核心模块
    - models.py: 数据契约
    - providers/: 数据源层
    - utils/: 工具层
    - visualizers/: 可视化层
- src/judgment/: 判断模式 - ETF技术分析模块
- src/backtest/: 回测模式 - 量化回测模块
- configs/: 配置文件
- tests/: 测试目录
- output/: 输出目录

使用方法:
    python main.py                           # 默认进入交互式菜单
    python main.py --mode judgment           # 直接进入判断模式
    python main.py --mode backtest          # 直接进入回测模式

版本: 1.2.0
"""

__version__ = '1.2.0'
__author__ = 'AI Assistant'

# 从src.core导出核心组件
from src.core.models import (
    TradeRule,
    FundData,
    TradeRecord,
    BacktestResult,
    StrategyConfig,
    DividendMode,
    StockData,
)
from src.core.providers import (
    DataProvider,
    DataProviderFactory,
    AkshareDataProvider,
)
from src.backtest.strategies import (
    StrategyState,
    AnnualLineStrategy,
    create_default_strategy,
)
from src.backtest.engines import (
    BacktestEngine,
    BenchmarkEngine,
)
from src.core.visualizers import (
    MainChart,
    CompareChart,
    get_theme,
)
from src.backtest.ui import (
    ResultDialog,
    PreviewDialog,
    show_message,
)
from src.core.utils import (
    setup_logging,
    generate_filename,
    ensure_dir,
)

__all__ = [
    # 数据模型
    'TradeRule',
    'FundData',
    'TradeRecord',
    'BacktestResult',
    'StrategyConfig',
    'DividendMode',
    'StockData',
    # 数据源
    'DataProvider',
    'DataProviderFactory',
    'AkshareDataProvider',
    # 策略
    'StrategyState',
    'AnnualLineStrategy',
    'create_default_strategy',
    # 引擎
    'BacktestEngine',
    'BenchmarkEngine',
    # 可视化
    'MainChart',
    'CompareChart',
    'get_theme',
    # UI
    'ResultDialog',
    'PreviewDialog',
    'show_message',
    # 工具
    'setup_logging',
    'generate_filename',
    'ensure_dir',
]
