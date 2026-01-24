"""
Technical indicators calculation module
"""

import numpy as np
from typing import List, Dict, Any


class TechnicalIndicators:
    """计算技术指标"""
    
    @staticmethod
    def ema(prices: List[float], period: int) -> float:
        """计算指数移动平均线 (EMA)"""
        if len(prices) < period:
            return np.nan
        
        prices_array = np.array(prices)
        alpha = 2 / (period + 1)
        
        # 初始值使用SMA
        ema_values = [np.mean(prices_array[:period])]
        
        for i in range(period, len(prices_array)):
            ema_value = alpha * prices_array[i] + (1 - alpha) * ema_values[-1]
            ema_values.append(ema_value)
        
        return ema_values[-1]
    
    @staticmethod
    def rsi(prices: List[float], period: int = 14) -> float:
        """计算相对强弱指数 (RSI)"""
        if len(prices) < period + 1:
            return np.nan
        
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = deltas.copy()
        losses = deltas.copy()
        
        gains[gains < 0] = 0
        losses[losses > 0] = 0
        losses = np.abs(losses)
        
        # 计算平均收益和平均损失
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # 使用指数移动平均
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """计算平均真实波幅 (ATR)"""
        if len(highs) < period or len(lows) < period or len(closes) < period:
            return np.nan
        
        # 确保数据长度一致
        min_len = min(len(highs), len(lows), len(closes))
        highs = highs[-min_len:]
        lows = lows[-min_len:]
        closes = closes[-min_len:]
        
        true_ranges = []
        
        for i in range(1, len(highs)):
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i-1])
            tr3 = abs(lows[i] - closes[i-1])
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
        
        if len(true_ranges) < period:
            return np.nan
        
        # 计算ATR (使用简单移动平均)
        atr = np.mean(true_ranges[-period:])
        
        return atr
    
    @classmethod
    def calculate_all_indicators(cls, price_data: Dict[str, List[float]]) -> Dict[str, float]:
        """计算所有技术指标"""
        closes = price_data['close']
        highs = price_data.get('high', closes)
        lows = price_data.get('low', closes)
        
        indicators = {
            'ema20': cls.ema(closes, 20),
            'ema50': cls.ema(closes, 50),
            'rsi14': cls.rsi(closes, 14),
            'atr14': cls.atr(highs, lows, closes, 14)
        }
        
        return indicators