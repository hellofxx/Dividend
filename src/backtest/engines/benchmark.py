"""
基准对比引擎 (v5.0)

职责：解耦基准计算，不侵入主回测逻辑。

内置四种基准：
- A: 一次性买入 (Buy & Hold)
- B: 定期定额 (DCA, 每月固定金额，收益率基于实际投入本金)
- C: 沪深300指数 (跟随指数日收益率)
- D: 上证指数 (跟随指数日收益率)

v5.0 变更：
- 全部数据源统一为 AkshareProvider
- 移除对 EastmoneyProvider 的依赖
- 所有指标计算委托给 analytics 模块
"""

import logging
from typing import Dict, Optional

import pandas as pd

from src.core.models import (
    BacktestResult, CompareResult, FundData,
    StrategyConfig, TradeRecord
)
from src.core.providers.akshare_data_provider import AkshareDataProvider
from src.backtest.analytics import MetricsCalculator, ReturnsCalculator, BenchmarkMetrics

logger = logging.getLogger(__name__)


class BenchmarkEngine:
    """
    基准对比引擎

    设计原则：
    - 仅读取 FundData / IndexData，不写入
    - 超额收益 = 主策略累计收益 - 同期沪深300累计收益
    - 任何基准获取失败时降级（index_curve 置 None）
    - 所有指标计算委托给 analytics 模块
    """

    def run_all(
        self,
        config: StrategyConfig,
        main_result: BacktestResult,
        fund_data: FundData,
        provider: Optional[AkshareDataProvider] = None,
    ) -> CompareResult:
        """
        运行所有基准并生成对比结果
        """
        logger.info("开始运行基准对比...")

        if provider is None:
            provider = AkshareProvider()

        buy_hold = self._run_buy_hold(config, fund_data)
        dca = self._run_dca(config, fund_data)

        # 沪深300指数
        try:
            index_curve = self._run_index(provider, config)
        except Exception as e:
            logger.warning(f"沪深300数据获取失败，跳过: {e}")
            index_curve = None

        # 上证指数
        try:
            shanghai_curve = self._run_shanghai_index(provider, config)
        except Exception as e:
            logger.warning(f"上证指数数据获取失败，跳过: {e}")
            shanghai_curve = None

        compare_metrics = self._build_compare_table(
            main_result, buy_hold, dca, index_curve, shanghai_curve
        )

        logger.info("基准对比完成")
        return CompareResult(
            main=main_result,
            buy_hold=buy_hold,
            dca=dca,
            index_curve=index_curve,
            shanghai_curve=shanghai_curve,
            compare_metrics=compare_metrics,
        )

    # ------------------------------------------------------------------
    # 基准 A：一次性买入
    # ------------------------------------------------------------------

    def _run_buy_hold(self, config: StrategyConfig, fund_data: FundData) -> BacktestResult:
        """一次性买入：起始日全仓，持有至结束日"""
        df = self._filter_date(fund_data.df, config.start_date, config.end_date)

        if len(df) == 0:
            return self._empty_result("一次性买入")

        init_cash = config.init_cash
        start_nav = float(df.iloc[0]['nav'])
        shares = init_cash / start_nav
        cash = 0.0

        trades = [TradeRecord(
            date=df.iloc[0]['date'],
            rule_id="buy_hold",
            action="BUY",
            price=start_nav,
            shares=shares,
            cash_left=0.0,
            shares_left=shares,
        )]

        # 构建资金曲线
        equity_curve = []
        for _, row in df.iterrows():
            total_value = cash + shares * float(row['nav'])
            equity_curve.append({'date': row['date'], 'total_value': total_value})

        equity_df = pd.DataFrame(equity_curve)
        
        # 使用统一指标计算
        metrics = MetricsCalculator.calc(equity_df, trades, init_cash)

        logger.info(
            f"基准A(一次性买入): "
            f"累计 {metrics['total_return']:.2f}% | "
            f"年化 {metrics['annual_return']:.2f}%"
        )
        return BacktestResult(
            name="一次性买入",
            trades=trades,
            equity_curve=equity_df,
            metrics=metrics
        )

    # ------------------------------------------------------------------
    # 基准 B：定期定额
    # ------------------------------------------------------------------

    def _run_dca(self, config: StrategyConfig, fund_data: FundData) -> BacktestResult:
        """
        定期定额 (DCA)：每月第一个交易日固定金额买入
        
        收益率计算基于实际投入本金，使用 analytics 模块
        """
        df = self._filter_date(fund_data.df, config.start_date, config.end_date)

        if len(df) == 0:
            return self._empty_result("定期定额")

        monthly_amount = config.dca_monthly_amount
        shares = 0.0
        trades = []
        
        # 构建月度买入计划
        df['year_month'] = df['date'].dt.to_period('M')
        monthly_groups = df.groupby('year_month')
        buy_schedule = []

        # 转换为列表后排序
        for period, group in sorted(list(monthly_groups), key=lambda x: str(x[0])):
            first_row = group.iloc[0]
            buy_date = first_row['date']
            nav = float(first_row['nav'])

            if monthly_amount < nav * 0.01:
                logger.warning(f"DCA: 月投金额不足")
                continue

            buy_shares = monthly_amount / nav
            shares += buy_shares
            buy_schedule.append((buy_date, buy_shares, nav))

            trades.append(TradeRecord(
                date=buy_date,
                rule_id=f"dca_{period}",
                action="BUY",
                price=nav,
                shares=buy_shares,
                cash_left=0.0,
                shares_left=shares,
            ))

        # 构建每日资金曲线
        running_shares = 0.0
        running_invested = 0.0
        buy_idx = 0
        equity_curve = []

        for _, row in df.iterrows():
            row_date = row['date']
            
            while buy_idx < len(buy_schedule) and row_date >= buy_schedule[buy_idx][0]:
                _, b_shares, _ = buy_schedule[buy_idx]
                running_shares += b_shares
                running_invested += monthly_amount
                buy_idx += 1

            total_value = running_shares * float(row['nav'])
            equity_curve.append({
                'date': row_date,
                'total_value': total_value,
                'invested_so_far': running_invested,
                'shares': running_shares,
            })

        equity_df = pd.DataFrame(equity_curve)
        equity_df = equity_df[equity_df['total_value'] > 0].reset_index(drop=True)

        if len(equity_df) == 0:
            return self._empty_result("定期定额")

        # 使用 DCA 专用指标计算（收益 + 风险）
        dca_metrics = MetricsCalculator.calc_dca_returns(equity_df)
        
        # 补充 DCA 专用风险指标（基于净值变化）
        dca_risk = MetricsCalculator.calc_dca_risk(equity_df)
        dca_metrics.update(dca_risk)
        
        # 交易统计（DCA 无卖出，为0）
        dca_metrics['win_rate'] = 0.0
        dca_metrics['profit_loss_ratio'] = 0.0

        logger.info(
            f"基准B(定期定额): 共 {len(trades)} 次 | "
            f"月投 {monthly_amount:.0f} 元/月 | "
            f"累计收益率 {dca_metrics['total_return']:.2f}%"
        )
        return BacktestResult(
            name="定期定额",
            trades=trades,
            equity_curve=equity_df,
            metrics=dca_metrics
        )

    # ------------------------------------------------------------------
    # 基准 C：沪深300指数
    # ------------------------------------------------------------------

    def _run_index(self, provider: AkshareDataProvider, config: StrategyConfig) -> Optional[pd.DataFrame]:
        """获取沪深300同期资金曲线"""
        try:
            index_data = provider.get_index_history(
                code="000300",
                start=config.start_date,
                end=config.end_date,
            )
            
            if index_data is None or index_data.df is None:
                logger.warning("获取沪深300数据失败，数据为空")
                return None

            df = self._filter_date(index_data.df, config.start_date, config.end_date)
            if len(df) == 0:
                return None

            # 以初始资金为基数，累乘日收益率
            cash = config.init_cash
            curve = []
            for _, row in df.iterrows():
                cash = cash * (1 + float(row['daily_return']))
                curve.append({'date': row['date'], 'total_value': cash})

            index_curve = pd.DataFrame(curve)
            total_ret = ReturnsCalculator.index_total_return(index_curve)
            logger.info(f"基准C(沪深300): 同期累计 {total_ret:.2f}%")
            return index_curve

        except Exception as e:
            logger.warning(f"获取沪深300数据失败，跳过: {e}")
            return None

    # ------------------------------------------------------------------
    # 基准 D：上证指数
    # ------------------------------------------------------------------

    def _run_shanghai_index(self, provider: AkshareDataProvider, config: StrategyConfig) -> Optional[pd.DataFrame]:
        """获取上证指数（000001）同期资金曲线"""
        try:
            index_data = provider.get_index_history(
                code="000001",
                start=config.start_date,
                end=config.end_date,
            )
            
            if index_data is None or index_data.df is None:
                logger.warning("获取上证指数数据失败，数据为空")
                return None

            df = self._filter_date(index_data.df, config.start_date, config.end_date)
            if len(df) == 0:
                return None

            cash = config.init_cash
            curve = []
            for _, row in df.iterrows():
                cash = cash * (1 + float(row['daily_return']))
                curve.append({'date': row['date'], 'total_value': cash})

            shanghai_curve = pd.DataFrame(curve)
            total_ret = ReturnsCalculator.index_total_return(shanghai_curve)
            logger.info(f"基准D(上证指数): 同期累计 {total_ret:.2f}%")
            return shanghai_curve

        except Exception as e:
            logger.warning(f"获取上证指数数据失败，跳过: {e}")
            return None

    # ------------------------------------------------------------------
    # 对比表构建
    # ------------------------------------------------------------------

    def _build_compare_table(
        self,
        main_result: BacktestResult,
        buy_hold: BacktestResult,
        dca: BacktestResult,
        index_curve: Optional[pd.DataFrame],
        shanghai_curve: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """构建横向指标对比表"""
        strategies = [
            ("主策略(年线)", main_result.equity_curve),
            ("一次性买入", buy_hold.equity_curve),
            ("定期定额", dca.equity_curve),
        ]
        
        # 添加指数对比
        if index_curve is not None:
            strategies.append(("沪深300(同期)", index_curve))
        if shanghai_curve is not None:
            strategies.append(("上证指数(同期)", shanghai_curve))
        
        return BenchmarkMetrics.build_compare_table(
            strategies=strategies,
            benchmark_curve=index_curve,
            benchmark_name="沪深300(同期)"
        )

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
        """按日期范围过滤数据"""
        return df[
            (df['date'] >= pd.to_datetime(start)) &
            (df['date'] <= pd.to_datetime(end))
        ].reset_index(drop=True)

    @staticmethod
    def _build_empty_metrics() -> Dict[str, float]:
        """构建空指标字典"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'volatility': 0.0,
            'downside_dev': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'win_rate': 0.0,
            'profit_loss_ratio': 0.0,
        }

    @staticmethod
    def _empty_result(name: str) -> BacktestResult:
        """返回空结果"""
        return BacktestResult(
            name=name,
            trades=[],
            equity_curve=pd.DataFrame(columns=['date', 'total_value']),
            metrics=BenchmarkEngine._build_empty_metrics(),
        )
