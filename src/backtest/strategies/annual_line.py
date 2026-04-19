"""
年线乖离率策略（红利低波默认产品）

策略逻辑：
- 买入条件：乖离率 ≤ 买入阈值（默认 -3%）
- 卖出条件：乖离率 ≥ 卖出阈值（默认 10%）

重要：乖离率为负值即代表"低于年线"，无需重复判断"净值低于年线"。
"""

from typing import List
import pandas as pd

from src.core.models import TradeRule
from .base import BaseStrategy, StrategyState


class AnnualLineStrategy(BaseStrategy):
    """
    年线乖离率策略
    
    使用乖离率（bias）作为唯一判断条件，支持分批交易。
    """
    
    def __init__(
        self,
        name: str = "年线乖离率策略",
        buy_rules: List[TradeRule] = None,
        sell_rules: List[TradeRule] = None,
    ):
        super().__init__(name)
        
        # 默认买入规则：乖离率 < 0（低于年线），买入100%
        self.buy_rules = buy_rules or [
            TradeRule(
                rule_id="buy_step_1",
                trigger_type="bias_below",
                threshold=0.0,  # Bias < 0 表示低于年线
                action="BUY",
                position_ratio=1.0,
            )
        ]
        
        # 默认卖出规则：乖离率 ≥ 10%，卖出100%
        self.sell_rules = sell_rules or [
            TradeRule(
                rule_id="sell_step_1",
                trigger_type="bias_above",
                threshold=10.0,
                action="SELL",
                position_ratio=1.0,
            )
        ]
    
    def evaluate(self, row: pd.Series) -> List[TradeRule]:
        """
        评估当前市场状态
        
        Args:
            row: 当前数据行，包含 bias 字段
            
        Returns:
            触发的交易规则列表
        """
        triggered = []
        current_bias = row['bias']
        
        # 评估买入规则
        for rule in self.buy_rules:
            if self._check_trigger(rule, current_bias):
                triggered.append(rule)
        
        # 评估卖出规则
        for rule in self.sell_rules:
            if self._check_trigger(rule, current_bias):
                triggered.append(rule)
        
        return triggered
    
    def _check_trigger(self, rule: TradeRule, current_bias: float) -> bool:
        """
        检查规则是否触发
        
        重要约束：
        - 使用 rule_id 和 _triggered_today 实现防重入
        - 仅通过 bias 判断，不涉及 nav < ma_250 的冗余判断
        """
        # 防重入检查
        if self.is_triggered_today(rule.rule_id):
            return False
        
        # 触发条件判断
        is_triggered = False
        
        if rule.trigger_type == "bias_below":
            # 乖离率低于阈值（如 -3%）
            is_triggered = current_bias <= rule.threshold
        elif rule.trigger_type == "bias_above":
            # 乖离率高于阈值（如 10%）
            is_triggered = current_bias >= rule.threshold
        
        if is_triggered:
            self.mark_triggered(rule.rule_id)
        
        return is_triggered


def create_default_strategy() -> AnnualLineStrategy:
    """创建默认的红利低波策略"""
    return AnnualLineStrategy(
        name="红利低波-年线策略",
        buy_rules=[
            TradeRule(
                rule_id="buy_step_1",
                trigger_type="bias_below",
                threshold=0.0,  # Bias < 0 表示低于年线
                action="BUY",
                position_ratio=1.0,
            )
        ],
        sell_rules=[
            TradeRule(
                rule_id="sell_step_1",
                trigger_type="bias_above",
                threshold=10.0,
                action="SELL",
                position_ratio=1.0,
            )
        ],
    )


def create_batch_strategy() -> AnnualLineStrategy:
    """
    创建分批交易策略（扩展示例）
    
    第一阶买入：乖离率 ≤ -3%，买入 50% 资金
    第二阶买入：乖离率 ≤ -6%，再买入 30% 资金
    第一阶卖出：乖离率 ≥ 8%，卖出 50% 份额
    第二阶卖出：乖离率 ≥ 12%，清仓剩余 100% 份额
    """
    return AnnualLineStrategy(
        name="红利低波-分批策略",
        buy_rules=[
            TradeRule(
                rule_id="buy_step_1",
                trigger_type="bias_below",
                threshold=-3.0,
                action="BUY",
                position_ratio=0.5,
            ),
            TradeRule(
                rule_id="buy_step_2",
                trigger_type="bias_below",
                threshold=-6.0,
                action="BUY",
                position_ratio=0.3,
            ),
        ],
        sell_rules=[
            TradeRule(
                rule_id="sell_step_1",
                trigger_type="bias_above",
                threshold=8.0,
                action="SELL",
                position_ratio=0.5,
            ),
            TradeRule(
                rule_id="sell_step_2",
                trigger_type="bias_above",
                threshold=12.0,
                action="SELL",
                position_ratio=1.0,
            ),
        ],
    )
