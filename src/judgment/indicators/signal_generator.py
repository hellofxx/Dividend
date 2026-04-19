"""买入信号判定系统

基于多因子综合判定模型，生成买入/卖出/观望信号。
"""

import pandas as pd

from src.judgment.indicators.bias import BIAS
from src.judgment.indicators.macd import MACD
from src.judgment.indicators.rsi import RSI
from src.judgment.indicators.kdj import KDJ
from src.judgment.indicators.bollinger import BollingerBands

class SignalGenerator:
    """信号生成器"""
    
    def __init__(self):
        """初始化信号生成器"""
        pass
    
    def generate_signal(self, df: pd.DataFrame) -> dict:
        """生成交易信号
        
        Args:
            df: 包含价格数据的DataFrame
            
        Returns:
            dict: 包含信号和依据的字典
        """
        if df.empty:
            return {
                'signal': '观望',
                'reason': '数据为空'
            }
        
        # 计算各指标
        indicators = self._calculate_indicators(df)
        
        # 综合判定
        signal, reason = self._comprehensive_judgment(indicators)
        
        return {
            'signal': signal,
            'reason': reason,
            'indicators': indicators
        }
    
    def _calculate_indicators(self, df: pd.DataFrame) -> dict:
        """计算各项指标
        
        Args:
            df: 数据
            
        Returns:
            dict: 指标字典
        """
        # 计算BIAS
        bias = BIAS.calculate(df, n=20).iloc[-1]
        bias_signal = BIAS.get_signal(bias)
        
        # 计算MACD
        dif, dea, macd_hist = MACD.calculate(df)
        macd_signal = MACD.get_signal(dif.iloc[-1], dea.iloc[-1])
        
        # 计算RSI
        rsi = RSI.calculate(df, period=14).iloc[-1]
        rsi_signal = RSI.get_signal(rsi)
        
        # 计算KDJ
        k, d, j = KDJ.calculate(df)
        kdj_signal = KDJ.get_signal(k.iloc[-1], d.iloc[-1], j.iloc[-1])
        
        # 计算布林带
        middle_band, upper_band, lower_band = BollingerBands.calculate(df)
        bollinger_signal = BollingerBands.get_signal(
            df['close'].iloc[-1], 
            upper_band.iloc[-1], 
            lower_band.iloc[-1]
        )
        
        return {
            'bias': {
                'value': bias,
                'signal': bias_signal
            },
            'macd': {
                'dif': dif.iloc[-1],
                'dea': dea.iloc[-1],
                'signal': macd_signal
            },
            'rsi': {
                'value': rsi,
                'signal': rsi_signal
            },
            'kdj': {
                'k': k.iloc[-1],
                'd': d.iloc[-1],
                'j': j.iloc[-1],
                'signal': kdj_signal
            },
            'bollinger': {
                'middle': middle_band.iloc[-1],
                'upper': upper_band.iloc[-1],
                'lower': lower_band.iloc[-1],
                'signal': bollinger_signal
            }
        }
    
    def _comprehensive_judgment(self, indicators: dict) -> tuple:
        """综合判定
        
        Args:
            indicators: 指标字典
            
        Returns:
            tuple: (信号, 依据)
        """
        reasons = []
        buy_factors = 0
        sell_factors = 0
        
        # BIAS判断
        if indicators['bias']['signal'] == '买入':
            buy_factors += 1
            reasons.append(f"BIAS指标显示买入信号 (值: {indicators['bias']['value']:.2f})")
        elif indicators['bias']['signal'] == '卖出':
            sell_factors += 1
            reasons.append(f"BIAS指标显示卖出信号 (值: {indicators['bias']['value']:.2f})")
        else:
            reasons.append(f"BIAS指标显示观望信号 (值: {indicators['bias']['value']:.2f})")
        
        # MACD判断
        if indicators['macd']['signal'] == '金叉':
            buy_factors += 1
            reasons.append("MACD出现金叉")
        elif indicators['macd']['signal'] == '死叉':
            sell_factors += 1
            reasons.append("MACD出现死叉")
        
        # RSI判断
        if indicators['rsi']['signal'] == '超卖':
            buy_factors += 1
            reasons.append(f"RSI处于超卖区域 (值: {indicators['rsi']['value']:.2f})")
        elif indicators['rsi']['signal'] == '超买':
            sell_factors += 1
            reasons.append(f"RSI处于超买区域 (值: {indicators['rsi']['value']:.2f})")
        
        # KDJ判断
        if indicators['kdj']['signal'] in ['超卖', '金叉']:
            buy_factors += 1
            reasons.append(f"KDJ显示{indicators['kdj']['signal']}信号")
        elif indicators['kdj']['signal'] in ['超买', '死叉']:
            sell_factors += 1
            reasons.append(f"KDJ显示{indicators['kdj']['signal']}信号")
        
        # 布林带判断
        if indicators['bollinger']['signal'] == '超卖':
            buy_factors += 1
            reasons.append("价格触及布林带下轨")
        elif indicators['bollinger']['signal'] == '超买':
            sell_factors += 1
            reasons.append("价格触及布林带上轨")
        
        # 综合判断
        if buy_factors >= 3:
            signal = '买入'
        elif sell_factors >= 3:
            signal = '卖出'
        else:
            signal = '观望'
        
        return signal, '; '.join(reasons)