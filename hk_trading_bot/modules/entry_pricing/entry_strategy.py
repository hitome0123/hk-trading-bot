"""
Entry pricing strategy module
"""

from typing import Dict, Any
import numpy as np


class EntryStrategy:
    """建仓价格策略"""
    
    @staticmethod
    def calculate_entry_price(current_price: float, indicators: Dict[str, float], 
                            config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        计算建仓价格
        
        策略逻辑:
        1. EMA20 > EMA50 且 RSI < 70: 趋势向上但不过热，可以建仓
        2. EMA20 < EMA50 且 RSI < 30: 趋势向下但超卖，可以抄底
        3. 使用ATR确定入场价格的缓冲区间
        
        Args:
            current_price: 当前价格
            indicators: 技术指标字典
            config: 策略配置参数
        
        Returns:
            包含建仓价格和相关信息的字典
        """
        if config is None:
            config = {
                'atr_multiplier': 0.5,  # ATR倍数，用于计算缓冲区间
                'max_discount': 0.02,   # 最大折扣比例
                'rsi_oversold': 30,     # RSI超卖阈值
                'rsi_overbought': 70    # RSI超买阈值
            }
        
        ema20 = indicators.get('ema20', np.nan)
        ema50 = indicators.get('ema50', np.nan)
        rsi14 = indicators.get('rsi14', np.nan)
        atr14 = indicators.get('atr14', np.nan)
        
        # 检查指标是否有效
        if any(np.isnan(x) for x in [ema20, ema50, rsi14, atr14]):
            return {
                'entry_price': None,
                'signal': 'NO_SIGNAL',
                'reason': 'Insufficient indicator data',
                'current_price': current_price
            }
        
        # 判断市场趋势
        trend_bullish = ema20 > ema50
        trend_bearish = ema20 < ema50
        
        # ATR缓冲区间
        atr_buffer = atr14 * config['atr_multiplier']
        
        signal = 'NO_SIGNAL'
        entry_price = None
        reason = ''
        
        if trend_bullish and rsi14 < config['rsi_overbought']:
            # 上升趋势，未超买 - 回调入场
            signal = 'LONG'
            entry_price = current_price - atr_buffer
            reason = f'Bullish trend (EMA20>{ema20:.2f} > EMA50>{ema50:.2f}), RSI not overbought ({rsi14:.1f})'
            
        elif trend_bearish and rsi14 < config['rsi_oversold']:
            # 下降趋势，超卖 - 抄底入场
            signal = 'LONG'
            entry_price = current_price - (atr_buffer * 0.5)  # 更小的缓冲，因为是抄底
            reason = f'Oversold bounce opportunity (RSI={rsi14:.1f} < {config["rsi_oversold"]})'
            
        elif rsi14 > config['rsi_overbought']:
            signal = 'WAIT'
            reason = f'Market overbought (RSI={rsi14:.1f} > {config["rsi_overbought"]})'
            
        else:
            signal = 'WAIT'
            reason = f'No clear signal (EMA20={ema20:.2f}, EMA50={ema50:.2f}, RSI={rsi14:.1f})'
        
        # 确保建仓价不会太低
        if entry_price is not None:
            max_discount_price = current_price * (1 - config['max_discount'])
            entry_price = max(entry_price, max_discount_price)
        
        return {
            'entry_price': entry_price,
            'signal': signal,
            'reason': reason,
            'current_price': current_price,
            'indicators': {
                'ema20': ema20,
                'ema50': ema50,
                'rsi14': rsi14,
                'atr14': atr14
            },
            'atr_buffer': atr_buffer
        }