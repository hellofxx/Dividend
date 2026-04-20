# AGENTS.md | 量化工作室智能体协同开发规范

> **配置说明**：本文件用于指导 AI Agent 在量化工作室项目中扮演不同角色进行协同开发。所有 Agent 必须严格遵守【全局上下文】的约束，并仅在自己的【职责边界】内产出代码。

---

## 🚨 全局上下文约束

### 运行环境

**默认运行环境：Conda study**
- 所有代码必须在 **Conda study 环境** 中开发和运行
- VSCode 终端启动后执行：`conda activate study`
- 依赖清单：`pandas`, `numpy`, `matplotlib`, `akshare`, `pyyaml`
- 性能优化依赖：`numba` (0.60.0+), `plotly` (5.24.0+), `pandas_ta` (0.3.14+), `seaborn` (0.13.0+), `cufflinks` (0.17.3+)
- Python 版本：3.9+

**环境检查命令**：
```bash
conda activate study
python -c "import pandas, numpy, matplotlib, akshare, numba, plotly, pandas_ta, seaborn, cufflinks; print('[OK] Environment ready')"
```

---

### 业务红线

1. **逻辑精简**：乖离率为负值即代表"低于年线"，策略判断时**绝对禁止**出现 `if nav < ma and bias < 0` 这种冗余代码，直接判断 `if bias <= threshold` 即可。
   - **默认买入条件**：Bias < 0（低于年线即买入），threshold 默认值为 `0.0`

2. **指标锁定**：系统仅计算且仅展示 7 个核心指标（累计收益率、年化收益率、最大回撤、夏普比率、卡玛比率、胜率、盈亏比），禁止自行发挥添加波动率、换手率等指标。
   - **新增**：收益分解指标（净值收益、分红再投、分红落袋）用于展示，不计入核心 7 指标。
   - **新增**：对标指标（沪深300同期收益率、超额收益率）必须展示。

3. **分红默认值与逻辑**：系统默认分红模式为 **`reinvest`（分红再投）**。若用户配置为 `cash`（分红落袋），则分红金额转化为现金持有，不计息，后续作为增量资金投入。

4. **平台限定**：仅面向 Windows VSCode，严禁引入任何跨平台字体探测逻辑（如 `fc-list`）。

5. **数据缓存**：数据获取（含ETF与沪深300/上证指数）必须实现本地缓存机制，优先从本地读取，减少网络请求。ETF/核心指数永久缓存。

6. **定投收益率基数**：定期定额(DCA)基准的收益率**必须基于实际投入本金 (actual_invested)** 计算，不得使用 init_cash 作为基数。这是定投与一次性买入产生差异的核心原因。

7. **统一数据源**：系统唯一数据源为 **AkshareProvider**（akshare 库），严禁引入其他数据源。所有数据获取必须通过 `get_etf_history()` 和 `get_index_history()` 接口。

8. **ETF 前复权数据**：默认产品为 512890（红利低波ETF前复权），ETF 前复权数据已包含分红，`dividends` 字段为空。

9. **终端兼容**：Windows终端不支持Unicode特殊字符，使用 [OK]/[ERROR]/[WARN] 代替 ✓ ✗ 等符号。

10. **双模式架构**：系统分为**判断模式**（实时技术分析）和**回测模式**（量化回测），两者共享数据层但业务逻辑独立。

---

### 技术红线

1. **目录与命名**：严格遵循 `src/core/` 的标准包结构。文件名必须 `snake_case`，类名必须 `CapWords`（如 `AnnualLineStrategy`）。

2. **通信契约**：跨模块（如 Provider 传给 Engine）**唯一合法载体**是 `models.py` 中定义的 Dataclass，禁止直接传递原始 `pd.DataFrame` 或 `dict`。

3. **依赖方向**：`strategies/` 禁止导入 `engines/` 或 `visualizers/`；`visualizers/` 禁止调用 `engines/` 的计算方法。

4. **GUI 注入**：`matplotlib.use('TkAgg')` 必须在工程入口最顶层执行，且中文字体直接硬编码为 `['Microsoft YaHei']`。

5. **基准解耦红线**：主回测引擎 `backtest.py` **严禁**包含任何基准策略（一次性买入、定投、沪深300）的计算逻辑，基准计算必须由独立的 `benchmark.py` 处理。

6. **指标计算中心化红线**：
   - 所有金融、基金、股票相关指标**必须统一定义在 `analytics/` 模块**
   - `engines/metrics.py` 仅作为兼容层，禁止在引擎层实现新的指标计算逻辑
   - `visualizers/compare.py` 只负责可视化，禁止在可视化层实现指标计算

7. **数据源统一红线**：
   - 数据获取层**唯一实现**为 `providers/akshare_provider.py`
   - BaseProvider 抽象方法为 `get_etf_history()` + `get_index_history()`

---

## 🤖 智能体角色定义

### 1. Agent: Architect (架构师)

- **职责**：搭建项目骨架，初始化配置文件，定义全局数据契约。
- **输入**：TDD 第 1、2 章目录结构与数据契约。
- **执行动作**：
  1. 创建项目根目录及所有子目录（`src/`, `tests/`, `configs/`, `output/`, `cache/`）。
  2. 生成所有 `__init__.py` 文件。
  3. 生成统一的入口程序 `main.py`，支持 `--mode judgment/backtest` 切换。
  4. 生成 `src/core/models.py`，定义所有 Dataclass（`DividendMode`、`IndexData`、`CompareResult`、`StrategyConfig`）。
  5. 生成 `src/core/exceptions.py`，定义异常层级。

- **禁止**：编写任何具体的业务逻辑代码或算法实现。

### 2. Agent: DataProvider (数据源开发者)

- **职责**：实现 akshare 统一数据源，支持 ETF 前复权数据与指数数据获取，增强数据完整性校验和缓存机制。
- **输入**：TDD 第 3 章。
- **执行动作**：
  1. 实现 `src/core/providers/base.py` 抽象基类。
  2. 实现 `src/core/providers/akshare_provider.py`（**唯一数据源实现**）。
  3. **ETF 数据获取**：
     - 优先 `ak.fund_etf_hist_em(symbol=code, adjust='qfq')` 前复权数据
     - 失败降级 `ak.stock_zh_index_daily(symbol=f'sh{code}')` 不复权数据
  4. **指数数据获取**：优先 `ak.index_zh_a_hist()`，失败降级新浪源。
  5. **ma_250 和 bias 计算**：在 `_process_etf_data()` 中计算。
  6. **累计净值计算**：在 `_process_etf_data()` 中计算 `acc_nav`。
  7. **缓存机制**：
     - 永久缓存 512890、000300、000001
     - 实现缓存数据完整性检查
     - 实现回测区间数据处理逻辑
  8. **数据完整性校验**：
     - 数据连续性检查
     - 字段完整性验证
     - 数据格式一致性校验
  9. **异常处理机制**：
     - 内置3次重试机制
     - 网络异常自动重试
     - 接口失败自动降级
     - 清晰的错误提示

- **禁止**：引入非 akshare 数据源。

### 3. Agent: Strategist (策略开发者)

- **职责**：实现策略状态机与分批交易规则解析。
- **输入**：PRD 2.3 节、TDD 第 4 章。
- **执行动作**：
  1. 实现 `src/backtest/strategies/base.py`，包含 `IDLE/HELD` 状态机。
  2. 实现 `src/backtest/strategies/annual_line.py`。
  3. **默认买入条件**：设置默认买入阈值为 `0.0`（即 Bias < 0）。
  4. 在 `evaluate()` 方法中实现**防重入**和**分批买卖**。

- **禁止**：在此模块中计算资金余额、份额或处理分红折算。

### 4. Agent: BacktestEngine (回测引擎开发者)

- **职责**：实现主策略核心回测循环、资金管理与分红处理逻辑。
- **输入**：PRD 2.3 节、TDD 第 5.1 章。
- **执行动作**：
  1. 实现 `src/backtest/engines/backtest.py`。
  2. **回测主循环**：遍历每个交易日，调用 `Strategy.evaluate()`。
  3. **资金管理**：按 `rule.position_ratio` 计算买卖量，遵守最小单位约束（0.01份）。
  4. **分红处理**：`reinvest` 模式增加份额，`cash` 模式增加现金。
  5. **期末结算**：回测结束日若仍持仓，按最后一天净值计算浮动市值。

- **绝对禁止**：在此模块中编写任何关于"一次性买入"、"定投"、"沪深300"的计算代码。

### 5. Agent: BenchmarkEngine (基准引擎开发者)

- **职责**：实现多策略横向对比逻辑与超额收益计算。
- **输入**：PRD 2.4 节、TDD 第 5.2 章。
- **执行动作**：
  1. 实现 `src/backtest/engines/benchmark.py`。
  2. **基准A：一次性买入**：起始日全仓买入持有至结束日。
  3. **基准B：定期定额**：每月首交易日固定投入 10000 元，收益率基于 actual_invested。
  4. **基准C：沪深300指数**：以初始资金为基数，按 `daily_return` 滚动计算。
  5. **基准D：上证指数**：同沪深300逻辑。
  6. **超额收益计算**：`主策略累计收益率 - 沪深300同期累计收益率`。
  7. **结果汇总**：使用 `backtest.analytics.BenchmarkMetrics.calculate_all_metrics()` 生成横向对比表。

- **约束**：所有指标计算必须通过 `analytics` 模块。

### 6. Agent: MetricsCalculator (指标计算器)

- **职责**：实现纯数学指标计算，无副作用。
- **输入**：PRD 2.4.2 节、TDD 第 5.3 章。
- **执行动作**：
  1. 实现 `src/backtest/analytics/metrics.py`：基础指标（夏普、最大回撤、胜率等）
  2. 实现 `src/backtest/analytics/returns.py`：收益率专用
  3. 实现 `src/backtest/analytics/benchmark_metrics.py`：多策略对比专用
  4. **7大核心指标计算**：累计收益率、年化收益率、最大回撤、夏普比率、卡玛比率、胜率、盈亏比。
  5. **收益分解指标**：净值收益率、分红再投、分红落袋及其年化版本。

- **禁止**：在此模块中计算"超额收益率"，超额收益由 BenchmarkEngine 得出。

### 7. Agent: UI Developer (界面开发者)

- **职责**：实现 Windows 弹窗交互、多线叠加可视化、主题管理与图片自适应缩放，优化图表可视化效果。
- **输入**：PRD 第 2.5、3 章及 TDD 第 6 章。
- **执行动作**：
  1. 实现 `src/backtest/ui/dialogs.py`（回测模式弹窗）。
  2. **5套预设视觉主题**：在 `core/visualizers/themes.py` 中实现。
  3. **策略对比图**：五线叠加资金曲线图，使用seaborn增强美观度。
  4. **交互式图表**：使用Plotly实现交互式净值走势和技术指标图表。
  5. **PreviewDialog 布局与性能**：
     - 按钮布局：`side=tk.BOTTOM`
     - 图片显示：tk.Label + PIL.ImageTk
     - 分层缩放：拖拽时 BILINEAR，停止后 LANCZOS
  6. **4弹窗同时展示模式**。

### 8. Agent: ETFAnalyzer Developer (技术分析开发者)

- **职责**：实现判断模式（ETF技术分析工具）的界面与技术指标，优化技术指标计算效率。
- **输入**：PRD 2.1 节、TDD 第 8 章。
- **执行动作**：
  1. 实现 `src/judgment/indicators/` 下的技术指标，使用pandas_ta库提升计算效率，添加降级方案：
     - `bias.py`：乖离率（period=250）
     - `macd.py`：MACD(12,26,9)
     - `rsi.py`：RSI(14)
     - `kdj.py`：KDJ(9,3,3)
     - `bollinger.py`：布林带(20,2)
  2. 实现 `src/judgment/charts/` 下的图表组件：
     - `kline_chart.py`、`macd_chart.py`、`rsi_chart.py`、`kdj_chart.py`、`bollinger_chart.py`
  3. 实现 `src/judgment/ui/` 下的界面：
     - `main_window.py`：主窗口（30%左侧信息面板 + 70%右侧图表区域）
     - `control_panel.py`：顶部导航栏
     - `info_panel.py`：左侧信息面板
     - `chart_panel.py`：右侧5图表面板
  4. 实现 `src/judgment/indicators/signal_generator.py`：多因子综合判定买入信号。

- **买入信号判定规则**：
  | 指标 | 买入因子 | 卖出因子 |
  |------|---------|---------|
  | BIAS | bias < 0 | bias > 10 |
  | MACD | 金叉 | 死叉 |
  | RSI | RSI < 30 | RSI > 70 |
  | KDJ | K < 20 或 金叉 | K > 80 或 死叉 |
  | 布林带 | 价格触及下轨 | 价格触及上轨 |

- **综合判定**：买入因子 >= 3 → 买入信号；卖出因子 >= 3 → 卖出信号。

- **禁止**：在此模块中实现回测逻辑。

### 9. Agent: Integration Developer (集成开发者)

- **职责**：实现 `main.py` 统一入口，整合两个模式。
- **输入**：PRD 第 1.2 节。
- **执行动作**：
  1. 实现 `main.py`：
     - 支持 `--mode menu/judgment/backtest` 参数
     - `interactive_menu()`：交互式菜单
     - `run_judgment_mode(args)`：调用 ETFAnalyzer UI
     - `run_backtest_mode(args)`：调用回测引擎
  2. 确保两个模式共享 `src/core/providers/` 数据层。

- **禁止**：在统一入口中混入业务逻辑。

---

## 📋 项目入口规范

### 统一入口 (`main.py`)

```bash
# 默认进入交互式菜单
python main.py

# 直接进入指定模式
python main.py --mode judgment
python main.py --mode backtest

# 带参数
python main.py --mode backtest --etf-code 512890 --start-date 2021-01-01
```

---

## 📊 验收检查清单

在提交代码前，请确认以下检查项：

### 代码规范
- [ ] 文件名遵循 `snake_case`，类名遵循 `CapWords`
- [ ] 所有跨模块调用使用 `models.py` 中定义的 Dataclass
- [ ] `strategies/` 不导入 `engines/` 或 `visualizers/`
- [ ] `matplotlib.use('TkAgg')` 在入口最顶层设置

### 业务逻辑
- [ ] 买入判断使用 `bias <= threshold`，无冗余判断
- [ ] DCA 收益率基于 `actual_invested` 计算
- [ ] 分红模式 `reinvest` 增加份额，`cash` 增加现金
- [ ] 基准计算在 `benchmark.py`，不在 `backtest.py`

### 可视化
- [ ] 按钮布局使用 `side=tk.BOTTOM`
- [ ] 图片显示使用 `tk.Label`
- [ ] 拖拽时 BILINEAR，停止后 LANCZOS

### 指标计算
- [ ] 7大核心指标在 `analytics/` 模块
- [ ] `engines/metrics.py` 为兼容层
- [ ] 超额收益在 `BenchmarkEngine` 计算

---

*文档版本：v1.5 | 最后更新：2026-04-20*
