# TDD.md | 量化工作室技术设计文档

| 属性 | 内容 |
|------|------|
| 关联PRD | PRD v1.2 (量化工作室) |
| 版本 | v1.2 |
| 面向角色 | 后端开发、算法开发、测试工程师 |
| 命名规范基准 | PEP 8 / Python 标准库结构 |

## 1. 项目架构概览

### 1.1 双模式架构

```
量化工作室 QuantStudio
├── main.py                   # [统一入口] 模式选择 + 路由
│
├── src/
│   ├── core/                 # 公共核心模块
│   ├── judgment/             # 判断模式 - ETF技术分析模块
│   └── backtest/             # 回测模式 - 量化回测模块
```

### 1.2 统一入口 (`main.py`)

```python
class AppMode(Enum):
    MENU = "menu"           # 交互式菜单
    JUDGMENT = "judgment"   # 判断模式
    BACKTEST = "backtest"  # 回测模式

def main():
    args = parse_arguments()
    if args.mode == 'menu':
        return interactive_menu()
    elif args.mode == 'judgment':
        return run_judgment_mode(args)
    elif args.mode == 'backtest':
        return run_backtest_mode(args)
```

---

## 2. 标准工程目录与文件命名布局

```text
量化工作室/
├── main.py                   # [入口] 统一程序入口 v1.2
├── AGENTS.md                  # [规范] 智能体协同开发规范
├── PRD.md                     # [规范] 产品需求文档
├── TDD.md                     # [规范] 技术设计文档
│
├── configs/                   # [标准] 外部配置文件目录
│   └── default_strategy.yaml  # 默认策略的规则链配置
│
├── cache/                     # [运行时] 数据缓存
├── output/                    # [运行时] 图表与报告输出
├── tests/                     # [标准] 单元测试目录
│
├── src/                       # [标准] 核心量化框架
│   ├── core/                  # 公共核心模块
│   │   ├── __init__.py
│   │   ├── models.py          # 全局数据契约
│   │   ├── exceptions.py      # 自定义异常层级
│   │   ├── providers/         # [数据源层]
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # 抽象基类
│   │   │   └── akshare_provider.py  # Akshare统一实现
│   │   ├── utils/            # [工具层]
│   │   │   ├── __init__.py
│   │   │   ├── logger.py     # 统一日志
│   │   │   ├── fileio.py     # 路径管理
│   │   │   └── network.py    # 网络重试
│   │   └── visualizers/      # [展示层]
│   │       ├── __init__.py
│   │       ├── themes.py     # 5套预设主题
│   │       ├── main_chart.py # 主分析图
│   │       ├── compare.py    # 五线对比图
│   │       └── technical_chart.py  # 技术分析图
│   │
│   ├── judgment/             # 判断模式 - ETF技术分析模块
│   │   ├── __init__.py
│   │   ├── data/             # 数据模块
│   │   │   ├── data_provider.py
│   │   │   └── cache_manager.py
│   │   ├── indicators/       # 技术指标
│   │   │   ├── bias.py
│   │   │   ├── macd.py
│   │   │   ├── rsi.py
│   │   │   ├── kdj.py
│   │   │   ├── bollinger.py
│   │   │   └── signal_generator.py
│   │   ├── charts/           # 图表组件
│   │   │   ├── kline_chart.py
│   │   │   ├── volume_chart.py
│   │   │   ├── macd_chart.py
│   │   │   ├── rsi_chart.py
│   │   │   ├── kdj_chart.py
│   │   │   └── bollinger_chart.py
│   │   └── ui/               # 分析界面
│   │       ├── main_window.py
│   │       ├── control_panel.py
│   │       ├── info_panel.py
│   │       └── chart_panel.py
│   │
│   └── backtest/             # 回测模式 - 量化回测模块
│       ├── __init__.py
│       ├── strategies/       # [策略层]
│       │   ├── __init__.py
│       │   ├── base.py       # 策略状态机
│       │   └── annual_line.py # 年线乖离率策略
│       ├── engines/          # [引擎层]
│       │   ├── __init__.py
│       │   ├── backtest.py   # 核心回测引擎
│       │   ├── benchmark.py  # 基准对比引擎
│       │   └── metrics.py    # 兼容层
│       ├── analytics/        # [指标层]
│       │   ├── __init__.py
│       │   ├── metrics.py    # 基础指标
│       │   ├── returns.py    # 收益率计算
│       │   └── benchmark_metrics.py  # 对比指标
│       └── ui/               # [交互层]
│           ├── __init__.py
│           └── dialogs.py    # Tkinter弹窗
```

---

## 3. 核心数据契约 (`models.py`)

### 3.1 类型定义

```python
from typing import Literal

DividendMode = Literal["reinvest", "cash"]
TriggerType = Literal["bias_below", "bias_above"]
ActionType = Literal["BUY", "SELL"]
```

### 3.2 策略配置

```python
@dataclass
class TradeRule:
    """交易规则原子"""
    rule_id: str
    trigger_type: TriggerType
    threshold: float
    action: ActionType
    position_ratio: float

@dataclass
class StrategyConfig:
    """策略运行时配置"""
    fund_code: str
    start_date: str
    end_date: str
    init_cash: float
    dividend_mode: DividendMode = "reinvest"
    rules: List[TradeRule] = field(default_factory=list)
    dca_monthly_amount: float = 10000.0
```

### 3.3 数据契约

```python
@dataclass
class FundData:
    """ETF/基金行情数据"""
    code: str
    name: str
    df: pd.DataFrame  # date, nav, acc_nav, ma_250, bias
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)

@dataclass
class IndexData:
    """指数行情数据"""
    code: str
    name: str
    df: pd.DataFrame  # date, close, daily_return
```

### 3.4 结果契约

```python
@dataclass
class TradeRecord:
    date: date
    rule_id: str
    action: ActionType
    price: float
    shares: float
    cash_left: float
    shares_left: float

@dataclass
class BacktestResult:
    name: str
    trades: List[TradeRecord]
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]

@dataclass
class CompareResult:
    main: BacktestResult
    buy_hold: BacktestResult
    dca: BacktestResult
    index_curve: Optional[pd.DataFrame]
    shanghai_curve: Optional[pd.DataFrame]
    compare_metrics: pd.DataFrame
```

---

## 4. 数据源层 (`providers/`)

### 4.1 抽象接口

```python
class BaseProvider(ABC):
    @abstractmethod
    def get_etf_history(self, code: str, start: str, end: str) -> FundData: ...

    @abstractmethod
    def get_index_history(self, code: str, start: str, end: str) -> IndexData: ...

    @abstractmethod
    def get_name(self) -> str: ...
```

### 4.2 AkshareProvider 实现

```python
class AkshareProvider(BaseProvider):
    def get_etf_history(self, code, start, end) -> FundData:
        # 1. 优先前复权: ak.fund_etf_hist_em(symbol=code, adjust='qfq')
        # 2. 降级不复权: ak.stock_zh_index_daily(symbol=f'sh{code}')
        # 3. 计算 ma_250, bias
        # 4. 缓存: cache/etf_{code}_raw.pkl (永久缓存 512890)
        ...

    def get_index_history(self, code, start, end) -> IndexData:
        # 1. 优先: ak.index_zh_a_hist(symbol=code)
        # 2. 降级: ak.stock_zh_index_daily(symbol=f'sh{code}')
        # 3. 计算 daily_return
        # 4. 缓存: cache/index_{code}_raw.pkl (永久缓存 000300/000001)
        ...
```

---

## 5. 策略层 (`strategies/`)

### 5.1 策略基类

```python
class BaseStrategy(ABC):
    def __init__(self, rules: List[TradeRule], dividend_mode: DividendMode = "reinvest"):
        self.rules = rules
        self.dividend_mode = dividend_mode
        self.state = "IDLE"  # IDLE / HELD
        self._triggered_today: set[str] = set()

    def reset_daily(self):
        self._triggered_today.clear()
```

### 5.2 年线策略

```python
class AnnualLineStrategy(BaseStrategy):
    def evaluate(self, row: pd.Series) -> List[TradeRule]:
        triggered = []
        bias = row['bias']
        for rule in self.rules:
            if rule.rule_id in self._triggered_today:
                continue
            is_buy = (rule.action == "BUY" and self.state == "IDLE"
                      and rule.trigger_type == "bias_below" and bias <= rule.threshold)
            is_sell = (rule.action == "SELL" and self.state == "HELD"
                       and rule.trigger_type == "bias_above" and bias >= rule.threshold)
            if is_buy or is_sell:
                triggered.append(rule)
                self._triggered_today.add(rule.rule_id)
        return triggered
```

---

## 6. 引擎层 (`engines/`)

### 6.1 回测引擎 (`backtest.py`)

```python
class BacktestEngine:
    def run(self, config: StrategyConfig, fund_data: FundData) -> BacktestResult:
        cash, shares = config.init_cash, 0.0
        for _, row in fund_data.df.iterrows():
            self.strategy.reset_daily()
            cash, shares = self._process_dividend(row, cash, shares, ...)
            for rule in self.strategy.evaluate(row):
                cash, shares = self._execute_trade(rule, row, cash, shares)
        return self._calc_result(name, trades, equity_curve)
```

### 6.2 基准引擎 (`benchmark.py`)

```python
class BenchmarkEngine:
    def run_all(self, config, main_result, fund_data, provider) -> CompareResult:
        buy_hold = self._run_buy_hold(config, fund_data)  # 一次性买入
        dca = self._run_dca(config, fund_data)             # 定期定额
        index_curve = self._run_index(config, provider)     # 沪深300
        shanghai_curve = self._run_shanghai_index(config, provider)  # 上证指数
        compare_metrics = self._build_compare_table(...)
        return CompareResult(...)
```

---

## 7. 指标层 (`analytics/`)

### 7.1 模块结构

```text
analytics/
├── __init__.py              # 导出 MetricsCalculator, ReturnsCalculator, BenchmarkMetrics
├── metrics.py               # 基础指标（最大回撤、夏普、卡玛、胜率、盈亏比）
├── returns.py               # 收益率计算（累计、年化、TWR、DCA）
└── benchmark_metrics.py     # 多策略对比
```

### 7.2 调用关系

```
benchmark.py ──→ analytics.MetricsCalculator
compare.py ────→ analytics.BenchmarkMetrics
```

---

## 8. 判断模式技术指标 (`etf_analyzer/indicators/`)

### 8.1 指标列表

| 指标 | 文件 | 参数 | 说明 |
|------|------|------|------|
| BIAS | bias.py | period=250 | 乖离率 |
| MACD | macd.py | fast=12, slow=26, signal=9 | 指数平滑异同移动平均线 |
| RSI | rsi.py | period=14 | 相对强弱指标 |
| KDJ | kdj.py | n=9, m1=3, m2=3 | 随机指标 |
| 布林带 | bollinger.py | period=20, std=2 | Bollinger Bands |

### 8.2 买入信号判定规则

| 指标 | 买入因子 | 卖出因子 |
|------|---------|---------|
| BIAS | bias < 0 | bias > 10 |
| MACD | 金叉 (DIF上穿DEA) | 死叉 (DIF下穿DEA) |
| RSI | RSI < 30 | RSI > 70 |
| KDJ | K < 20 或 金叉 | K > 80 或 死叉 |
| 布林带 | 价格触及下轨 | 价格触及上轨 |

**综合判定**：买入因子 >= 3 → 买入信号；卖出因子 >= 3 → 卖出信号

---

## 9. 可视化层 (`visualizers/`)

### 9.1 5套预设主题

```python
THEME_PRESETS = {
    "professional": {"style": "seaborn-v0_8-whitegrid", "colors": ["#1f77b4", "#ff7f0e", ...]},
    "modern": {"style": "seaborn-v0_8-whitegrid", "colors": ["#4C72B0", "#DD8452", ...]},
    "dark": {"style": "dark_background", "colors": ["#00D4FF", "#FF6B6B", ...]},
    "pastel": {"style": "seaborn-v0_8-pastel", "colors": ["#a1c9f4", "#ffb482", ...]},
    "vivid": {"style": "seaborn-v0_8-colorblind", "colors": ["#0072B2", "#E69F00", ...]},
}
```

### 9.2 回测模式图表

| 图表 | 文件 | 内容 |
|------|------|------|
| 主分析图 | main_chart.py | 净值走势+年线+买卖点、收益曲线 |
| 策略对比图 | compare.py | 五线叠加（主策略/一次性/定投/沪深300/上证） |
| 技术分析图 | technical_chart.py | 6指标图表区 + 左侧信息栏 |

### 9.3 判断模式图表

| 图表 | 文件 | 内容 |
|------|------|------|
| K线图 | kline_chart.py | K线走势 + BIAS |
| 成交量图 | volume_chart.py | 成交量柱状图 |
| MACD图 | macd_chart.py | DIF/DEA/MACD柱状线 |
| RSI图 | rsi_chart.py | RSI指标 |
| KDJ图 | kdj_chart.py | K/D/J三线 |
| 布林带图 | bollinger_chart.py | 中轨/上轨/下轨 |

---

## 10. 交互层 (`ui/`)

### 10.1 回测模式弹窗 (`dialogs.py`)

```python
class ResultDialog:
    def show(self, result, compare_result, on_save, on_cancel, ...):
        # 结果汇总弹窗
        ...

class PreviewDialog:
    def show(self, image_path, title, on_save, on_regenerate, on_cancel, modal=False):
        # 图片预览弹窗
        # 按钮布局: side=tk.BOTTOM
        # 图片: tk.Label + PIL.ImageTk
        # 缩放: 拖拽时BILINEAR，停止后LANCZOS
```

### 10.2 判断模式界面 (`etf_analyzer/ui/`)

```python
class MainWindow:
    def __init__(self, root, etf_code: str, theme: str = 'professional'):
        # 布局: 30%左侧信息面板 + 70%右侧图表区域
        ...

class ControlPanel(ttk.Frame):
    # 顶部导航栏: ETF代码输入、刷新按钮、参数设置
    ...

class InfoPanel(ttk.Frame):
    # 左侧信息面板: ETF基本信息、BIAS指标、买入信号
    ...

class ChartPanel(ttk.Frame):
    # 右侧6图表: K线、成交量、MACD、RSI、KDJ、布林带
    ...
```

---

## 11. 命令行接口

### 11.1 统一入口参数

```bash
python main.py                           # 交互式菜单
python main.py --mode judgment          # 判断模式
python main.py --mode backtest         # 回测模式
python main.py --mode backtest --etf-code 512890 --start-date 2021-01-01
```

### 11.2 参数列表

| 参数 | 模式 | 默认值 | 说明 |
|------|------|--------|------|
| `--mode` | 通用 | menu | 运行模式 |
| `--etf-code` | 两者 | 512890 | ETF代码 |
| `--start-date` | 回测 | 2021-01-01 | 回测开始日期 |
| `--end-date` | 回测 | 2025-12-31 | 回测结束日期 |
| `--buy-threshold` | 回测 | 0.0 | 买入阈值 |
| `--sell-threshold` | 回测 | 10.0 | 卖出阈值 |
| `--dividend-mode` | 回测 | reinvest | 分红模式 |
| `--initial-capital` | 回测 | 100000.0 | 初始资金 |
| `--theme` | 两者 | professional | 可视化主题 |
| `--no-ui` | 回测 | False | 禁用弹窗 |
| `--auto-save` | 回测 | False | 自动保存 |

---

## 12. 异常规范

### 12.1 异常层级

```python
class FrameworkError(Exception): pass
class DataFetchError(FrameworkError): pass
class ConfigValidationError(FrameworkError): pass
class DividendModeError(ConfigValidationError): pass
```

### 12.2 异常处理

```python
try:
    main()
except DividendModeError as e:
    print(f"[ERROR] 分红模式配置错误：{e}")
except DataFetchError as e:
    print(f"[ERROR] 数据获取失败：{e}")
except FrameworkError as e:
    print(f"[ERROR] 策略执行异常：{e}")
except Exception as e:
    print(f"[ERROR] 程序异常退出: {e}")
```

---

## 13. 平台适配

### 13.1 matplotlib后端

```python
_no_ui = '--no-ui' in sys.argv
if not _no_ui:
    matplotlib.use('TkAgg')  # Windows原生GUI
else:
    matplotlib.use('Agg')
```

### 13.2 中文字体

```python
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False
```

### 13.3 终端字符

使用 `[OK]/[ERROR]/[WARN]` 代替特殊符号。

---

## 14. 测试策略

### 14.1 测试目录

```text
tests/
├── __init__.py
├── test_config.py           # 配置解析测试
├── test_strategy.py         # 策略逻辑测试
├── test_theme.py            # 主题配置测试
├── etf_analyzer/
│   ├── test_data.py         # 数据获取测试
│   └── test_indicators.py   # 技术指标测试
```

### 14.2 测试用例设计

| 测试项 | 测试内容 | 预期结果 |
|--------|---------|---------|
| 策略阈值测试 | bias=0时买入阈值0.0触发 | 买入信号正确 |
| 分红再投测试 | 分红按净值折算份额 | 份额增加正确 |
| DCA收益率测试 | 收益率基于actual_invested | 计算正确 |
| 超额收益测试 | 主策略-沪深300 | 差值正确 |
| 多因子判定测试 | 3个买入因子触发 | 信号正确 |

---

*文档结束*
