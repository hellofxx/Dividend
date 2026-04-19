"""
策略基类与状态机定义
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import List, Set, Dict
import pandas as pd

from src.core.models import TradeRule


class StrategyState:
    """
    策略状态机
    
    IDLE: 空闲状态（未持仓）
    HELD: 持有状态（已持仓）
    """
    IDLE = "IDLE"
    HELD = "HELD"


class BaseStrategy(ABC):
    """
    策略基类
    
    所有策略实现必须继承此类。
    """
    
    def __init__(self, name: str):
        self.name = name
        self.state = StrategyState.IDLE
        self._triggered_today: Set[str] = set()  # 当日已触发的规则
        self._current_date: date = date.min
    
    def reset_daily(self, current_date: date) -> None:
        """
        每日重置
        
        在每个交易日开始时调用，清除当日触发记录。
        """
        if current_date != self._current_date:
            self._current_date = current_date
            self._triggered_today.clear()
    
    @abstractmethod
    def evaluate(self, row: pd.Series) -> List[TradeRule]:
        """
        评估当前市场状态，返回触发的交易规则
        
        Args:
            row: 当前日期的数据行
                必须包含: nav, ma_250, bias
                
        Returns:
            List[TradeRule]: 触发的交易规则列表（可能为空）
        """
        pass
    
    def update_state(self, new_state: str) -> None:
        """更新策略状态"""
        self.state = new_state
    
    def mark_triggered(self, rule_id: str) -> None:
        """标记规则已触发（防重入）"""
        self._triggered_today.add(rule_id)
    
    def is_triggered_today(self, rule_id: str) -> bool:
        """检查规则今日是否已触发"""
        return rule_id in self._triggered_today
