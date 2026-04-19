"""
核心数据契约定义 (v4.0)

所有模块间通信必须通过这些Dataclass，禁止直接传递原始DataFrame或dict。

v4.0 变更：
- 默认产品改为 512890（红利低波ETF前复权）
- 数据源统一为 AkshareProvider
"""

from dataclasses import dataclass, field
from typing import List, Dict, Literal, Optional
from datetime import date
import pandas as pd


# ============================================================
# 类型别名
# ============================================================
DividendMode = Literal["reinvest", "cash"]   # 分红模式
TriggerType = Literal["bias_below", "bias_above"]
ActionType = Literal["BUY", "SELL"]


# ============================================================
# 策略配置与规则
# ============================================================

@dataclass
class TradeRule:
    """
    交易规则原子

    Attributes:
        rule_id: 唯一标识，用于防重入 (如 "buy_step_1")
        trigger_type: 触发类型 (bias_below/bias_above)
        threshold: 阈值 (买入默认0.0，卖出默认10.0)
        action: 交易动作 (BUY/SELL)
        position_ratio: 仓位比例 (0.0 ~ 1.0)
    """
    rule_id: str
    trigger_type: TriggerType
    threshold: float
    action: ActionType
    position_ratio: float


@dataclass
class StrategyConfig:
    """策略运行时的完整配置"""
    fund_code: str
    start_date: str
    end_date: str
    init_cash: float
    dividend_mode: DividendMode = "reinvest"   # 默认分红再投
    rules: List[TradeRule] = field(default_factory=list)
    dca_monthly_amount: float = 10000.0          # 定投月金额（默认10000元/月，逐月累加）


# ============================================================
# 数据源契约
# ============================================================

@dataclass
class FundData:
    """
    标准化基金行情数据

    Attributes:
        code: 基金代码
        name: 基金名称
        df: 净值数据DataFrame
            必须包含列: date(datetime), nav(float), acc_nav(float), ma_250(float), bias(float)
        dividends: 分红数据DataFrame
            必须包含列: ex_date(datetime), amount(float)
    """
    code: str
    name: str
    df: pd.DataFrame
    dividends: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __post_init__(self):
        """验证数据格式"""
        required_cols = ['date', 'nav', 'ma_250', 'bias']
        if not all(col in self.df.columns for col in required_cols):
            missing = [c for c in required_cols if c not in self.df.columns]
            raise ValueError(f"FundData.df 缺少必需列: {missing}")


@dataclass
class IndexData:
    """
    标准化指数行情数据（沪深300等）

    Attributes:
        code: 指数代码，如 "000300"
        name: 指数名称，如 "沪深300"
        df: 行情DataFrame，列: date(datetime), close(float), daily_return(float)
    """
    code: str
    name: str
    df: pd.DataFrame


# ============================================================
# 交易与回测结果契约
# ============================================================

@dataclass
class TradeRecord:
    """
    交易流水

    Attributes:
        date: 交易日期
        rule_id: 触发的规则ID
        action: 交易动作 (BUY/SELL)
        price: 成交价格
        shares: 成交份额
        cash_left: 交易后剩余现金
        shares_left: 交易后持有份额
    """
    date: date
    rule_id: str
    action: ActionType
    price: float
    shares: float
    cash_left: float
    shares_left: float


@dataclass
class BacktestResult:
    """
    单策略回测引擎输出

    Attributes:
        name: 策略名称
        trades: 交易流水列表
        equity_curve: 资金曲线DataFrame (列: date, total_value)
        metrics: 7大核心指标 + 收益分解字典
    """
    name: str
    trades: List[TradeRecord]
    equity_curve: pd.DataFrame
    metrics: Dict[str, float]

    def get_metric(self, key: str, default: float = 0.0) -> float:
        """安全获取指标值"""
        return self.metrics.get(key, default)


@dataclass
class CompareResult:
    """
    多策略对比结果汇总

    Attributes:
        main: 主策略结果
        buy_hold: 基准A：一次性买入
        dca: 基准B：定期定额
        index_curve: 基准C：沪深300资金曲线（获取失败时为None）
        shanghai_curve: 基准D：上证指数资金曲线（获取失败时为None）
        compare_metrics: 横向对比表（含超额收益率）
    """
    main: BacktestResult
    buy_hold: BacktestResult
    dca: BacktestResult
    index_curve: Optional[pd.DataFrame]         # 沪深300曲线，可能为None
    shanghai_curve: Optional[pd.DataFrame]      # 上证指数曲线，可能为None
    compare_metrics: pd.DataFrame               # 横向指标对比表
