"""
核心回测引擎 (v3.1)

核心主循环：
1. 数据遍历（按交易日）
2. 分红处理（优先于交易信号）
3. 交易信号评估与执行
4. 资金曲线记录
5. 期末结算与指标计算

分红模式：
- reinvest：分红金额当日按净值折算为份额，复利增长
- cash：分红金额落袋为现金，下次触发买入条件时连同本金投入
"""

import logging
from typing import List, Optional, Tuple

import pandas as pd

from src.core.exceptions import StrategyError
from src.core.models import (
    BacktestResult, FundData, StrategyConfig,
    TradeRecord, DividendMode
)
from src.backtest.strategies.base import BaseStrategy, StrategyState

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    核心回测引擎

    接收 StrategyConfig（含分红模式）+ FundData，返回 BacktestResult。

    职责边界：
    - 负责资金/份额管理、分红处理、交易执行
    - 不计算超额收益率（由 benchmark.py 做差得出）
    """

    MIN_SHARES = 0.01  # 最小交易份额约束

    def __init__(self, strategy: BaseStrategy):
        self._strategy = strategy
        # 运行时状态（每次 run 前 reset）
        self._cash: float = 0.0
        self._shares: float = 0.0
        self._pending_div_cash: float = 0.0   # 分红落袋模式累积待投现金
        self._trades: List[TradeRecord] = []
        self._equity_curve: List[dict] = []

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def run(self, config: StrategyConfig, fund_data: FundData) -> BacktestResult:
        """
        执行回测

        Args:
            config: 策略完整配置（含 dividend_mode）
            fund_data: 标准化基金数据（含分红DataFrame）

        Returns:
            BacktestResult
        """
        self._validate_config(config)
        self._reset(config.init_cash)

        df = fund_data.df.copy()

        # 日期过滤
        df = df[
            (df['date'] >= pd.to_datetime(config.start_date)) &
            (df['date'] <= pd.to_datetime(config.end_date))
        ]

        if len(df) == 0:
            raise StrategyError(
                f"回测区间 {config.start_date} ~ {config.end_date} 内无有效数据"
            )

        logger.info(
            f"开始回测: {len(df)} 个交易日 | "
            f"分红模式: {config.dividend_mode} | "
            f"初始资金: {config.init_cash:,.0f}"
        )

        dividends = fund_data.dividends.copy() if fund_data.dividends is not None else pd.DataFrame()

        for _, row in df.iterrows():
            self._process_day(row, dividends, config.dividend_mode, config.rules)

        # 期末结算
        if len(df) > 0:
            last_nav = df.iloc[-1]['nav']
            final_value = self._cash + self._shares * last_nav
            # 更新最后一条曲线记录的期末市值
            if self._equity_curve:
                self._equity_curve[-1]['total_value'] = final_value

        return self._build_result(
            name=self._strategy.name,
            dividend_mode=config.dividend_mode,
            init_cash=config.init_cash,
        )

    # ------------------------------------------------------------------
    # 内部流程
    # ------------------------------------------------------------------

    def _validate_config(self, config: StrategyConfig) -> None:
        """校验配置合法性"""
        from src.core.exceptions import DividendModeError
        if config.dividend_mode not in ("reinvest", "cash"):
            raise DividendModeError(
                f"分红模式 '{config.dividend_mode}' 无效，仅支持 'reinvest' 或 'cash'。"
            )

    def _reset(self, init_cash: float) -> None:
        """重置引擎运行时状态"""
        self._cash = init_cash
        self._shares = 0.0
        self._pending_div_cash = 0.0
        self._trades = []
        self._equity_curve = []
        self._strategy.state = StrategyState.IDLE

    def _process_day(
        self,
        row: pd.Series,
        dividends: pd.DataFrame,
        dividend_mode: DividendMode,
        rules,
    ) -> None:
        """处理单个交易日"""
        current_date = row['date']
        # 关键修改：使用累计净值(acc_nav)作为交易价格，而非单位净值(nav)
        current_nav = float(row['nav'])           # 单位净值（用于市值计算）
        current_acc_nav = float(row['acc_nav'])   # 累计净值（用于交易价格）

        # 1. 每日重置防重入集合
        self._strategy.reset_daily(current_date)

        # 2. 分红处理（优先于交易信号）
        self._process_dividend(current_date, current_nav, dividends, dividend_mode)

        # 3. 策略信号评估
        triggered = self._strategy.evaluate(row)

        # 4. 执行交易 - 使用累计净值作为交易价格
        for rule in triggered:
            if rule.action == "BUY":
                # 使用累计净值作为买入价格
                self._execute_buy(rule, current_date, current_acc_nav, dividend_mode)
            else:
                # 使用累计净值作为卖出价格
                self._execute_sell(rule, current_date, current_acc_nav)

        # 5. 记录资金曲线
        total_value = self._cash + self._shares * current_nav
        self._equity_curve.append({
            'date': current_date,
            'nav': current_nav,
            'cash': self._cash,
            'shares': self._shares,
            'total_value': total_value,
        })

    def _process_dividend(
        self,
        current_date,
        current_nav: float,
        dividends: pd.DataFrame,
        mode: DividendMode,
    ) -> None:
        """
        处理分红事件

        Args:
            mode: reinvest = 折算份额; cash = 落袋为现金（下次买入时投入）
        """
        if dividends.empty or self._shares <= 0:
            return

        try:
            today_divs = dividends[
                dividends['ex_date'].dt.date == current_date.date()
            ]
        except Exception:
            return

        if today_divs.empty:
            return

        total_div_per_share = today_divs['amount'].sum()
        total_div_amount = total_div_per_share * self._shares

        if total_div_amount <= 0:
            return

        if mode == "reinvest":
            # 分红再投：按当日净值折算为份额
            new_shares = total_div_amount / current_nav
            self._shares += new_shares
            logger.info(
                f"分红再投: {current_date.date()} | "
                f"每份 {total_div_per_share:.4f} | "
                f"总额 {total_div_amount:.2f} | "
                f"新增份额 {new_shares:.4f}"
            )
        else:
            # 分红落袋：转为现金，等待下次买入时使用
            self._pending_div_cash += total_div_amount
            logger.info(
                f"分红落袋: {current_date.date()} | "
                f"每份 {total_div_per_share:.4f} | "
                f"落袋 {total_div_amount:.2f} | "
                f"待投累计 {self._pending_div_cash:.2f}"
            )

    def _execute_buy(self, rule, trade_date, price: float, dividend_mode: DividendMode) -> bool:
        """
        执行买入

        分红落袋模式：买入时将 _pending_div_cash 并入本金一起买入
        """
        # 计算可用资金：正常现金 + 落袋分红现金（仅 cash 模式）
        available_cash = self._cash
        div_cash_to_invest = 0.0
        if dividend_mode == "cash" and self._pending_div_cash > 0:
            div_cash_to_invest = self._pending_div_cash

        buy_amount = (available_cash + div_cash_to_invest) * rule.position_ratio
        shares_to_buy = buy_amount / price

        if shares_to_buy < self.MIN_SHARES:
            logger.debug(f"买入份额不足最小值: {shares_to_buy:.6f}")
            return False

        cost = shares_to_buy * price
        # 先扣除落袋分红（全部投入）
        cash_from_div = min(div_cash_to_invest * rule.position_ratio, self._pending_div_cash)
        self._pending_div_cash -= cash_from_div
        self._cash -= (cost - cash_from_div)

        self._shares += shares_to_buy
        self._strategy.update_state(StrategyState.HELD)

        self._trades.append(TradeRecord(
            date=trade_date,
            rule_id=rule.rule_id,
            action="BUY",
            price=price,
            shares=shares_to_buy,
            cash_left=self._cash,
            shares_left=self._shares,
        ))
        logger.info(f"买入: {trade_date} @ {price:.4f} | 份额 {shares_to_buy:.2f} | 剩余现金 {self._cash:.2f}")
        return True

    def _execute_sell(self, rule, trade_date, price: float) -> bool:
        """执行卖出（空仓不卖）"""
        if self._shares <= 0:
            return False

        shares_to_sell = self._shares * rule.position_ratio
        proceeds = shares_to_sell * price
        self._cash += proceeds
        self._shares -= shares_to_sell

        if self._shares <= self.MIN_SHARES:
            self._shares = 0.0
            self._strategy.update_state(StrategyState.IDLE)

        self._trades.append(TradeRecord(
            date=trade_date,
            rule_id=rule.rule_id,
            action="SELL",
            price=price,
            shares=shares_to_sell,
            cash_left=self._cash,
            shares_left=self._shares,
        ))
        logger.info(f"卖出: {trade_date} @ {price:.4f} | 份额 {shares_to_sell:.2f} | 剩余现金 {self._cash:.2f}")
        return True

    # ------------------------------------------------------------------
    # 结果构建
    # ------------------------------------------------------------------

    def _build_result(
        self,
        name: str,
        dividend_mode: DividendMode,
        init_cash: float,
    ) -> BacktestResult:
        """构建回测结果，计算所有指标"""
        from .metrics import MetricsCalculator

        equity_df = pd.DataFrame(self._equity_curve)

        # 收益分解
        breakdown = self._calc_return_breakdown(equity_df, init_cash)

        metrics = MetricsCalculator.calc(
            equity_curve=equity_df,
            trades=self._trades,
            init_cash=init_cash,
            **breakdown,
        )

        return BacktestResult(
            name=name,
            trades=list(self._trades),
            equity_curve=equity_df,
            metrics=metrics,
        )

    def _calc_return_breakdown(
        self,
        equity_df: pd.DataFrame,
        init_cash: float,
    ) -> dict:
        """
        计算收益分解：净值收益 vs 总收益

        说明：
        - total_return = (期末资产 - 初始资金) / 初始资金
        - nav_return   = (期末净值 - 期初净值) / 期初净值  (仅价格)
        - dividend_xxx = total_return - nav_return (分红贡献)
        - 再投 vs 落袋的区别体现在实际资金曲线上（已经通过 _process_dividend 分支处理）
        """
        if len(equity_df) < 2:
            return {
                'nav_return': 0.0,
                'dividend_reinvest': 0.0,
                'dividend_cash': 0.0,
                'annual_nav_return': 0.0,
                'annual_div_reinvest': 0.0,
                'annual_div_cash': 0.0,
            }

        start_nav = float(equity_df.iloc[0]['nav'])
        end_nav   = float(equity_df.iloc[-1]['nav'])
        start_date = equity_df.iloc[0]['date']
        end_date   = equity_df.iloc[-1]['date']

        years = max((end_date - start_date).days / 365.25, 1 / 365)

        # 纯净值收益（不含分红）
        nav_return = (end_nav - start_nav) / start_nav * 100

        # 总收益（资金曲线）
        final_val  = float(equity_df.iloc[-1]['total_value'])
        total_return = (final_val - init_cash) / init_cash * 100

        # 分红贡献 = 总收益 - 净值收益
        div_contribution = total_return - nav_return

        # 再投 = 分红贡献（已在资金曲线中体现，享受复利）
        dividend_reinvest = max(div_contribution, 0.0)
        # 落袋 = 分红贡献 * 折扣（落袋现金不复利，保守估计略低）
        # 若分红模式为 cash，待投现金仍在 _pending_div_cash 中未被使用，
        # 此处简化为与再投相同（均来自同一笔分红金额，差异体现在复利部分）
        dividend_cash = max(div_contribution * 0.9, 0.0)

        # 年化
        def annualize(r_pct: float) -> float:
            try:
                return ((1 + r_pct / 100) ** (1 / years) - 1) * 100
            except Exception:
                return 0.0

        return {
            'nav_return': nav_return,
            'dividend_reinvest': dividend_reinvest,
            'dividend_cash': dividend_cash,
            'annual_nav_return': annualize(nav_return),
            'annual_div_reinvest': annualize(dividend_reinvest),
            'annual_div_cash': dividend_cash / years,
        }
