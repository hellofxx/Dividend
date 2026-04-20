"""pandas_ta 数据格式转换模块

将项目数据格式转换为 pandas_ta 所需的标准 OHLCV 格式。
"""

import sys
sys.path.insert(0, 'src')

import pandas as pd
import numpy as np
from typing import Optional, Tuple
from datetime import datetime

try:
    import pandas_ta as ta
    HAS_PANDAS_TA = True
except ImportError:
    HAS_PANDAS_TA = False
    ta = None

class DataFrameConverter:
    """数据格式转换器 - 将项目数据转换为 pandas_ta 所需格式"""

    REQUIRED_COLUMNS = ['open', 'high', 'low', 'close', 'volume']
    OPTIONAL_COLUMNS = ['date']

    def __init__(self):
        self._warnings = []

    def convert_from_fund_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """从 FundData 格式转换

        Args:
            df: FundData 的 df 字段，包含 nav, acc_nav, ma_250, bias 等

        Returns:
            符合 pandas_ta 格式的 DataFrame
        """
        result = pd.DataFrame()

        # 检查是否有原始 OHLC 数据
        has_ohlc = all(col in df.columns for col in ['open', 'high', 'low', 'close'])

        if has_ohlc:
            # 已有完整 OHLC 数据
            result['date'] = df['date'] if 'date' in df.columns else pd.to_datetime(df.index)
            result['open'] = pd.to_numeric(df['open'], errors='coerce')
            result['high'] = pd.to_numeric(df['high'], errors='coerce')
            result['low'] = pd.to_numeric(df['low'], errors='coerce')
            result['close'] = pd.to_numeric(df['close'], errors='coerce')
            volume_val = df['volume'] if 'volume' in df.columns else 1
            result['volume'] = pd.to_numeric(volume_val, errors='coerce').fillna(1) if isinstance(volume_val, pd.Series) else pd.Series([1] * len(df))
        else:
            # 从 nav 推断 OHLC 数据
            result['date'] = df['date'] if 'date' in df.columns else pd.to_datetime(df.index)
            close = pd.to_numeric(df['nav'] if 'nav' in df.columns else df['close'], errors='coerce')

            # 根据收盘价估算其他价格
            result['close'] = close
            result['open'] = close * (1 + np.random.uniform(-0.005, 0.005, len(close)))
            result['high'] = np.maximum(close, result['open']) * (1 + np.random.uniform(0, 0.01, len(close)))
            result['low'] = np.minimum(close, result['open']) * (1 - np.random.uniform(0, 0.01, len(close)))
            volume_val = df['volume'] if 'volume' in df.columns else 1000000
            if isinstance(volume_val, pd.Series):
                result['volume'] = pd.to_numeric(volume_val, errors='coerce').fillna(1000000)
            else:
                result['volume'] = pd.Series([volume_val] * len(df), index=result.index)

            self._warnings.append("从 nav 推断 OHLC 数据，精度可能受限")

        # 保留原始指标
        if 'nav' in df.columns:
            result['nav'] = df['nav']
        if 'acc_nav' in df.columns:
            result['acc_nav'] = df['acc_nav']
        if 'ma_250' in df.columns:
            result['ma_250'] = df['ma_250']
        if 'bias' in df.columns:
            result['bias'] = df['bias']
        if 'daily_return' in df.columns:
            result['daily_return'] = df['daily_return']

        result = self._handle_missing_values(result)
        result = self._validate_data(result)

        return result

    def convert_from_index_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """从 IndexData 格式转换

        Args:
            df: IndexData 的 df 字段

        Returns:
            符合 pandas_ta 格式的 DataFrame
        """
        return self.convert_from_fund_data(df)

    def convert_from_raw_akshare(self, df: pd.DataFrame) -> pd.DataFrame:
        """从 akshare 原始数据转换

        Args:
            df: akshare 返回的原始 DataFrame

        Returns:
            符合 pandas_ta 格式的 DataFrame
        """
        result = pd.DataFrame()

        # 标准化列名
        column_mappings = {
            '日期': 'date', '开盘': 'open', '收盘': 'close',
            '最高': 'high', '最低': 'low', '成交量': 'volume',
            '成交额': 'amount', '振幅': 'amplitude',
            '涨跌幅': 'change_pct', '涨跌额': 'change', '换手率': 'turnover',
        }

        df_copy = df.copy()
        for old, new in column_mappings.items():
            if old in df_copy.columns:
                df_copy = df_copy.rename(columns={old: new})

        # 设置日期
        if 'date' in df_copy.columns:
            result['date'] = pd.to_datetime(df_copy['date'])
        else:
            result['date'] = pd.to_datetime(df_copy.iloc[:, 0])

        # 转换价格数据
        for col in ['open', 'high', 'low', 'close']:
            if col in df_copy.columns:
                result[col] = pd.to_numeric(df_copy[col], errors='coerce')

        # 处理成交量
        if 'volume' in df_copy.columns:
            result['volume'] = pd.to_numeric(df_copy['volume'], errors='coerce').fillna(0)
        else:
            result['volume'] = 0

        result = self._handle_missing_values(result)
        result = self._validate_data(result)

        return result

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值

        Args:
            df: 输入 DataFrame

        Returns:
            处理后的 DataFrame
        """
        # 前向填充价格数据
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in df.columns:
                df[col] = df[col].fillna(method='ffill')

        # 后向填充（如果前面有缺失）
        for col in price_columns:
            if col in df.columns:
                df[col] = df[col].fillna(method='bfill')

        # 成交量用0填充
        if 'volume' in df.columns:
            df['volume'] = df['volume'].fillna(0)

        return df

    def _validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数据完整性

        Args:
            df: 输入 DataFrame

        Returns:
            验证后的 DataFrame
        """
        # 检查必要列
        missing_cols = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必要列: {missing_cols}")

        # 检查数据长度
        if len(df) == 0:
            raise ValueError("数据为空")

        # 检查价格有效性
        if (df['high'] < df['low']).any():
            self._warnings.append("存在 high < low 的异常数据，已修正")
            df['high'], df['low'] = df[['high', 'low']].max(axis=1), df[['high', 'low']].min(axis=1)

        # 检查负值
        for col in ['open', 'high', 'low', 'close']:
            if (df[col] <= 0).any():
                self._warnings.append(f"存在 {col} <= 0 的异常数据")
                df = df[df[col] > 0]

        return df

    def get_warnings(self) -> list:
        """获取转换过程中的警告信息"""
        return self._warnings.copy()


def prepare_dataframe_for_pandas_ta(df: pd.DataFrame, source_format: str = 'fund') -> pd.DataFrame:
    """准备 DataFrame 用于 pandas_ta 分析

    Args:
        df: 原始 DataFrame
        source_format: 源数据格式 ('fund', 'index', 'akshare', 'raw')

    Returns:
        转换后的 DataFrame

    Raises:
        ValueError: 当数据格式不支持或转换失败时
    """
    if not HAS_PANDAS_TA:
        raise ImportError("pandas_ta 未安装，请先安装: pip install pandas-ta")

    converter = DataFrameConverter()

    if source_format == 'fund':
        result = converter.convert_from_fund_data(df)
    elif source_format == 'index':
        result = converter.convert_from_index_data(df)
    elif source_format in ('akshare', 'raw'):
        result = converter.convert_from_raw_akshare(df)
    else:
        raise ValueError(f"不支持的数据格式: {source_format}")

    # 设置日期为索引（如果还没有）
    if 'date' in result.columns:
        result = result.set_index('date')

    # 确保是 OHLCV 顺序
    ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
    existing_ohlcv = [col for col in ohlcv_cols if col in result.columns]
    other_cols = [col for col in result.columns if col not in ohlcv_cols]

    return result[existing_ohlcv + other_cols]


def calculate_technical_indicators(df: pd.DataFrame, indicators: list = None) -> pd.DataFrame:
    """使用 pandas_ta 计算技术指标

    Args:
        df: 符合 pandas_ta 格式的 DataFrame
        indicators: 要计算的指标列表，如 ['rsi', 'macd', 'bbands']

    Returns:
        包含技术指标的 DataFrame
    """
    if not HAS_PANDAS_TA:
        raise ImportError("pandas_ta 未安装")

    if indicators is None:
        indicators = ['rsi', 'macd', 'bbands', 'atr', 'adx']

    result_df = df.copy()

    for indicator in indicators:
        try:
            if indicator == 'rsi':
                result_df['rsi'] = ta.rsi(df['close'], length=14)
            elif indicator == 'macd':
                macd_df = ta.macd(df['close'])
                if macd_df is not None:
                    result_df['macd'] = macd_df.iloc[:, 0]
                    result_df['macd_signal'] = macd_df.iloc[:, 1]
                    result_df['macd_hist'] = macd_df.iloc[:, 2]
            elif indicator == 'bbands':
                bbands_df = ta.bbands(df['close'])
                if bbands_df is not None:
                    result_df['bb_upper'] = bbands_df.iloc[:, 0]
                    result_df['bb_middle'] = bbands_df.iloc[:, 1]
                    result_df['bb_lower'] = bbands_df.iloc[:, 2]
            elif indicator == 'atr':
                result_df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            elif indicator == 'adx':
                adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
                if adx_df is not None:
                    result_df['adx'] = adx_df.iloc[:, 0]
                    result_df['di_plus'] = adx_df.iloc[:, 1]
                    result_df['di_minus'] = adx_df.iloc[:, 2]
            elif indicator == 'stoch':
                stoch_df = ta.stoch(df['high'], df['low'], df['close'])
                if stoch_df is not None:
                    result_df['stoch_k'] = stoch_df.iloc[:, 0]
                    result_df['stoch_d'] = stoch_df.iloc[:, 1]
            elif indicator == 'sma':
                result_df['sma_20'] = ta.sma(df['close'], length=20)
                result_df['sma_50'] = ta.sma(df['close'], length=50)
        except Exception as e:
            print(f"计算 {indicator} 失败: {e}")

    return result_df


def validate_pandas_ta_dataframe(df: pd.DataFrame) -> Tuple[bool, str]:
    """验证 DataFrame 是否符合 pandas_ta 要求

    Args:
        df: 要验证的 DataFrame

    Returns:
        (is_valid, message) 元组
    """
    required = ['open', 'high', 'low', 'close']
    missing = [col for col in required if col not in df.columns]

    if missing:
        return False, f"缺少必要列: {missing}"

    if len(df) < 2:
        return False, "数据行数不足"

    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if (df[col] <= 0).any():
            return False, f"{col} 存在非正值"

    if (df['high'] < df['low']).any():
        return False, "存在 high < low 的异常数据"

    return True, "数据格式正确"


def demo_conversion():
    """演示数据转换"""
    print("=" * 60)
    print("pandas_ta 数据格式转换演示")
    print("=" * 60)

    # 创建示例数据
    dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
    np.random.seed(42)

    prices = 100 * np.cumprod(1 + np.random.normal(0.0005, 0.01, 100))

    # FundData 格式
    fund_df = pd.DataFrame({
        'date': dates,
        'nav': prices,
        'acc_nav': prices * 1.05,
        'ma_250': pd.Series(prices).rolling(10).mean().fillna(prices.mean()).values,
        'bias': np.random.uniform(-5, 5, 100)
    })

    print(f"\n1. 原始 FundData 格式:")
    print(fund_df.head())
    print(f"列: {list(fund_df.columns)}")

    # 转换为 pandas_ta 格式
    converter = DataFrameConverter()
    ta_df = converter.convert_from_fund_data(fund_df)

    print(f"\n2. 转换后的 pandas_ta 格式:")
    print(ta_df.head())
    print(f"列: {list(ta_df.columns)}")

    # 验证数据
    is_valid, msg = validate_pandas_ta_dataframe(ta_df)
    print(f"\n3. 数据验证: {msg}")

    # 计算技术指标
    if HAS_PANDAS_TA:
        print("\n4. 计算技术指标:")
        result_df = calculate_technical_indicators(ta_df, ['rsi', 'macd', 'bbands'])
        indicator_cols = ['rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_middle', 'bb_lower']
        available_cols = [col for col in indicator_cols if col in result_df.columns]
        print(result_df[available_cols].tail())

    # 输出警告
    warnings = converter.get_warnings()
    if warnings:
        print(f"\n5. 转换警告:")
        for warning in warnings:
            print(f"  - {warning}")

    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


if __name__ == "__main__":
    demo_conversion()