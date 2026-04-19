# 红利低波基金策略回测分析系统 - 项目记忆

## 项目概况

**项目名称**: 红利低波ETF策略回测分析系统  
**版本**: v4.0 (2026-04-13 更新)  
**技术栈**: Python（study 环境）, Pandas 3.0.1, NumPy 2.4.3, Matplotlib 3.10.8, akshare  
**创建时间**: 2026-04-10  

## v4.0 核心架构

### 数据源：统一 AkshareProvider

- **唯一数据源**：akshare（东方财富/新浪）
- **默认产品**：512890（红利低波ETF前复权）
- **买入卖出判断**：使用 512890 前复权年线

### ETF 数据获取逻辑

1. 优先 `ak.fund_etf_hist_em(symbol=code, adjust='qfq')` 前复权数据
2. 失败降级 `ak.stock_zh_index_daily(symbol=f'sh{code}')` 不复权数据
3. 返回 FundData 格式（nav=close, acc_nav=close, 已计算 ma_250/bias）

### 缓存机制

- **永久缓存**：512890(ETF)、000300(沪深300)、000001(上证指数)
- **ETF 前复权数据**已包含分红，`dividends` 字段为空

### 策略对比（5线叠加）

1. 主策略(年线)
2. 一次性买入
3. 定期定额
4. 沪深300
5. 上证指数

## 命令行用法

```bash
# 默认模式（512890 红利低波ETF）
python main.py --no-ui

# 自定义参数
python main.py --etf-code 512890 --start-date 2021-01-01 --end-date 2025-12-31

# 兼容旧参数
python main.py --fund-code 512890
```

参数:
- `--etf-code`: ETF代码（默认 512890）
- `--fund-code`: 兼容旧参数（等同于 --etf-code）
- `--theme`: professional/modern/dark/pastel/vibrant
- `--start-date`: 回测开始日期（默认 2021-01-01）
- `--end-date`: 回测结束日期（默认 2025-12-31）
- `--no-ui`: 禁用弹窗

## 项目结构

```
红利低波/
├── main.py                 # 主程序入口 v4.0
├── AGENTS.md               # Agent协作配置
│
├── src/quant_core/         # 核心源码
│   ├── models.py           # 数据契约 v4.0
│   ├── providers/
│   │   ├── base.py         # 抽象基类（get_etf_history + get_index_history）
│   │   └── akshare_provider.py  # 统一数据源（ETF+指数）
│   ├── strategies/
│   │   └── annual_line.py  # 年线策略
│   ├── engines/
│   │   ├── backtest.py     # 回测引擎
│   │   ├── benchmark.py    # 基准对比引擎 v5.0
│   │   └── metrics.py      # 兼容层
│   ├── analytics/          # 指标计算中心
│   │   ├── metrics.py
│   │   ├── returns.py
│   │   └── benchmark_metrics.py
│   ├── visualizers/
│   │   ├── main_chart.py
│   │   ├── compare.py      # 策略对比图（5线叠加）
│   │   ├── technical_chart.py  # 技术分析图 v4.0（无H30269依赖）
│   │   └── themes.py
│   └── ui/
│
├── cache/                  # 数据缓存
│   ├── etf_512890_raw.pkl  # ETF 前复权数据
│   ├── index_000300_raw.pkl # 沪深300
│   └── index_000001_raw.pkl # 上证指数
│
└── output/                 # 运行输出
```

## 已删除的冗余代码

- `eastmoney.py`：旧数据源，v4.0 已弃用
- `get_h30269_history()`：H30269 指数接口，已替换为 ETF 512890
- `test_512890.py` / `test_akshare_h30269.py` / `test_verify_index.py`：临时测试脚本

## 注意事项

1. Windows终端不支持Unicode特殊字符，使用[OK]/[ERROR]/[WARN]代替
2. ETF前复权数据已包含分红，回测时 dividends 为空
3. akshare 接口可能需要重试（内置3次重试机制）
4. **tkinter Toplevel 坑**：当 parent 窗口被 withdraw() 后，不要对子窗口使用 transient()
5. **图片自适应缩放**：绑定 Configure 到 dialog 比绑定 canvas 更可靠
6. **technical_chart.py** 不再依赖 h30269_data，直接使用 ETF 数据（含 nav/acc_nav/ma_250/bias）

## 环境配置

**Conda环境**: study（已存在，直接激活）  
**激活命令**: `conda activate study`  
**依赖**: pandas, numpy, matplotlib, akshare

---

*最后更新: 2026-04-13 v4.0*
