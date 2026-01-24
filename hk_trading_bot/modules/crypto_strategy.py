"""
Cryptocurrency-specific trading strategies
"""

from typing import Dict, Any, Optional
import numpy as np
from datetime import datetime


class CryptoTradingStrategy:
    """加密货币交易策略"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            # 加密货币特定参数
            'volatility_threshold': 0.8,  # 高波动率阈值 (80%年化)
            'volume_spike_ratio': 3.0,    # 成交量激增倍数
            'price_momentum_period': 7,   # 动量周期(天)
            'rsi_oversold_crypto': 25,    # 加密货币RSI超卖阈值(更低)
            'rsi_overbought_crypto': 80,  # 加密货币RSI超买阈值(更高)
            
            # 风险管理
            'max_position_crypto': 0.1,   # 单一加密货币最大仓位比例 (10%)
            'stop_loss_pct': 0.15,        # 止损比例 (15%)
            'take_profit_pct': 0.30,      # 止盈比例 (30%)
            
            # 市场情绪指标
            'fear_greed_threshold': 25,   # 恐惧指数阈值
            'market_cap_min': 1000000000, # 最小市值要求 (10亿美元)
            
            # 技术分析权重
            'momentum_weight': 0.4,       # 动量权重
            'mean_reversion_weight': 0.3, # 均值回归权重
            'volume_weight': 0.2,         # 成交量权重
            'volatility_weight': 0.1      # 波动率权重
        }
    
    def analyze_crypto_momentum(self, price_data: Dict[str, list], 
                              current_price: float) -> Dict[str, Any]:
        """分析加密货币动量"""
        try:
            closes = price_data.get('close', [])
            if len(closes) < self.config['price_momentum_period']:
                return {'momentum_score': 0, 'trend': 'insufficient_data'}
            
            # 计算多周期动量
            momentum_scores = []
            periods = [3, 7, 14, 30]
            
            for period in periods:
                if len(closes) >= period:
                    period_return = (closes[-1] - closes[-period]) / closes[-period]
                    momentum_scores.append(period_return)
            
            if not momentum_scores:
                return {'momentum_score': 0, 'trend': 'insufficient_data'}
            
            # 加权平均动量
            weights = [0.4, 0.3, 0.2, 0.1][:len(momentum_scores)]
            weighted_momentum = sum(m * w for m, w in zip(momentum_scores, weights))
            
            # 动量强度分类
            if weighted_momentum > 0.1:
                trend = 'strong_bullish'
                signal_strength = 'STRONG_BUY'
            elif weighted_momentum > 0.05:
                trend = 'bullish'
                signal_strength = 'BUY'
            elif weighted_momentum > -0.05:
                trend = 'sideways'
                signal_strength = 'HOLD'
            elif weighted_momentum > -0.1:
                trend = 'bearish'
                signal_strength = 'WEAK_SELL'
            else:
                trend = 'strong_bearish'
                signal_strength = 'STRONG_SELL'
            
            return {
                'momentum_score': weighted_momentum,
                'trend': trend,
                'signal_strength': signal_strength,
                'period_returns': {f'{p}d': momentum_scores[i] 
                                 for i, p in enumerate(periods[:len(momentum_scores)])},
                'confidence': min(1.0, len(closes) / 30)  # 数据充足度
            }
            
        except Exception as e:
            print(f"❌ Error analyzing crypto momentum: {e}")
            return {'momentum_score': 0, 'trend': 'error'}
    
    def analyze_volatility_breakout(self, price_data: Dict[str, list],
                                  volume_data: list = None) -> Dict[str, Any]:
        """分析波动率突破"""
        try:
            closes = price_data.get('close', [])
            highs = price_data.get('high', [])
            lows = price_data.get('low', [])
            
            if len(closes) < 20:
                return {'breakout_score': 0, 'breakout_type': 'insufficient_data'}
            
            # 计算ATR和波动率
            true_ranges = []
            for i in range(1, len(closes)):
                tr1 = highs[i] - lows[i]
                tr2 = abs(highs[i] - closes[i-1])
                tr3 = abs(lows[i] - closes[i-1])
                true_ranges.append(max(tr1, tr2, tr3))
            
            if len(true_ranges) < 14:
                return {'breakout_score': 0, 'breakout_type': 'insufficient_data'}
            
            current_atr = np.mean(true_ranges[-14:])
            historical_atr = np.mean(true_ranges[-30:-14]) if len(true_ranges) >= 30 else current_atr
            
            # ATR expansion ratio
            atr_expansion = current_atr / historical_atr if historical_atr > 0 else 1.0
            
            # 价格位置分析
            recent_high = max(highs[-20:])
            recent_low = min(lows[-20:])
            current_position = (closes[-1] - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
            
            # 成交量确认
            volume_confirmation = 1.0
            if volume_data and len(volume_data) >= 10:
                recent_avg_volume = np.mean(volume_data[-10:])
                historical_avg_volume = np.mean(volume_data[-30:-10]) if len(volume_data) >= 30 else recent_avg_volume
                volume_ratio = recent_avg_volume / historical_avg_volume if historical_avg_volume > 0 else 1.0
                volume_confirmation = min(2.0, volume_ratio)  # 最大2倍确认
            
            # 综合突破评分
            breakout_score = (
                (atr_expansion - 1) * 0.4 +  # ATR扩展
                abs(current_position - 0.5) * 2 * 0.3 +  # 价格位置偏离
                (volume_confirmation - 1) * 0.3  # 成交量确认
            )
            
            # 确定突破类型
            if current_position > 0.8 and atr_expansion > 1.2:
                breakout_type = 'upward_breakout'
                signal = 'BUY'
            elif current_position < 0.2 and atr_expansion > 1.2:
                breakout_type = 'downward_breakout'  
                signal = 'SELL'
            elif atr_expansion > 1.5:
                breakout_type = 'volatility_expansion'
                signal = 'WAIT'
            else:
                breakout_type = 'consolidation'
                signal = 'HOLD'
            
            return {
                'breakout_score': breakout_score,
                'breakout_type': breakout_type,
                'signal': signal,
                'atr_expansion': atr_expansion,
                'price_position': current_position,
                'volume_confirmation': volume_confirmation,
                'confidence': min(1.0, len(closes) / 30)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing volatility breakout: {e}")
            return {'breakout_score': 0, 'breakout_type': 'error'}
    
    def analyze_mean_reversion(self, price_data: Dict[str, list],
                             indicators: Dict[str, float]) -> Dict[str, Any]:
        """分析均值回归机会"""
        try:
            closes = price_data.get('close', [])
            if len(closes) < 50:
                return {'reversion_score': 0, 'reversion_signal': 'insufficient_data'}
            
            # 获取技术指标
            ema20 = indicators.get('ema20', np.nan)
            ema50 = indicators.get('ema50', np.nan)
            rsi = indicators.get('rsi14', np.nan)
            
            if np.isnan(ema20) or np.isnan(ema50) or np.isnan(rsi):
                return {'reversion_score': 0, 'reversion_signal': 'insufficient_indicators'}
            
            current_price = closes[-1]
            
            # 计算价格偏离度
            price_deviation_20 = (current_price - ema20) / ema20
            price_deviation_50 = (current_price - ema50) / ema50
            
            # RSI极值检测
            rsi_oversold = rsi < self.config['rsi_oversold_crypto']
            rsi_overbought = rsi > self.config['rsi_overbought_crypto']
            
            # 布林带分析（简化版）
            recent_prices = closes[-20:]
            bb_middle = np.mean(recent_prices)
            bb_std = np.std(recent_prices)
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper > bb_lower else 0.5
            
            # 均值回归评分
            reversion_score = 0
            reversion_signals = []
            
            # 价格偏离评分
            if abs(price_deviation_20) > 0.1:  # 10%以上偏离
                reversion_score += abs(price_deviation_20) * 2
                reversion_signals.append(f'Price {price_deviation_20*100:.1f}% from EMA20')
            
            # RSI极值评分
            if rsi_oversold:
                reversion_score += (self.config['rsi_oversold_crypto'] - rsi) / 10
                reversion_signals.append(f'RSI oversold ({rsi:.1f})')
            elif rsi_overbought:
                reversion_score += (rsi - self.config['rsi_overbought_crypto']) / 10
                reversion_signals.append(f'RSI overbought ({rsi:.1f})')
            
            # 布林带极值评分
            if bb_position < 0.1:  # 接近下轨
                reversion_score += 0.3
                reversion_signals.append('Near Bollinger lower band')
            elif bb_position > 0.9:  # 接近上轨
                reversion_score += 0.3
                reversion_signals.append('Near Bollinger upper band')
            
            # 确定回归信号
            if rsi_oversold and price_deviation_20 < -0.1:
                reversion_signal = 'STRONG_BUY_REVERSION'
            elif rsi_oversold or price_deviation_20 < -0.05:
                reversion_signal = 'BUY_REVERSION'
            elif rsi_overbought and price_deviation_20 > 0.1:
                reversion_signal = 'STRONG_SELL_REVERSION'
            elif rsi_overbought or price_deviation_20 > 0.05:
                reversion_signal = 'SELL_REVERSION'
            else:
                reversion_signal = 'NO_REVERSION'
            
            return {
                'reversion_score': reversion_score,
                'reversion_signal': reversion_signal,
                'price_deviation_20': price_deviation_20,
                'price_deviation_50': price_deviation_50,
                'rsi_level': rsi,
                'bb_position': bb_position,
                'signals': reversion_signals,
                'confidence': min(1.0, len(closes) / 50)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing mean reversion: {e}")
            return {'reversion_score': 0, 'reversion_signal': 'error'}
    
    def calculate_crypto_entry_signal(self, symbol: str, current_price: float,
                                    price_data: Dict[str, list],
                                    indicators: Dict[str, float],
                                    volume_data: list = None) -> Dict[str, Any]:
        """计算加密货币综合入场信号"""
        try:
            # 1. 动量分析
            momentum_analysis = self.analyze_crypto_momentum(price_data, current_price)
            
            # 2. 波动率突破分析  
            breakout_analysis = self.analyze_volatility_breakout(price_data, volume_data)
            
            # 3. 均值回归分析
            reversion_analysis = self.analyze_mean_reversion(price_data, indicators)
            
            # 4. 综合评分计算
            momentum_score = momentum_analysis.get('momentum_score', 0) * self.config['momentum_weight']
            breakout_score = breakout_analysis.get('breakout_score', 0) * self.config['volatility_weight']
            reversion_score = reversion_analysis.get('reversion_score', 0) * self.config['mean_reversion_weight']
            
            # 成交量权重
            volume_score = 0
            if volume_data and len(volume_data) >= 5:
                recent_volume = np.mean(volume_data[-5:])
                historical_volume = np.mean(volume_data[-20:-5]) if len(volume_data) >= 20 else recent_volume
                volume_ratio = recent_volume / historical_volume if historical_volume > 0 else 1.0
                volume_score = min(1.0, volume_ratio) * self.config['volume_weight']
            
            composite_score = momentum_score + breakout_score + reversion_score + volume_score
            
            # 5. 信号确定
            confidence = np.mean([
                momentum_analysis.get('confidence', 0),
                breakout_analysis.get('confidence', 0), 
                reversion_analysis.get('confidence', 0)
            ])
            
            # 综合信号判断
            if composite_score > 0.3 and momentum_analysis.get('trend') in ['bullish', 'strong_bullish']:
                overall_signal = 'STRONG_BUY'
            elif composite_score > 0.15:
                overall_signal = 'BUY'
            elif composite_score > -0.15:
                overall_signal = 'HOLD'
            elif composite_score > -0.3:
                overall_signal = 'SELL'
            else:
                overall_signal = 'STRONG_SELL'
            
            # 6. 入场价格建议
            atr = indicators.get('atr14', current_price * 0.02)  # 默认2%作为ATR
            
            if overall_signal in ['STRONG_BUY', 'BUY']:
                # 买入：当前价或略低
                entry_price = current_price - (atr * 0.5)
                stop_loss = current_price * (1 - self.config['stop_loss_pct'])
                take_profit = current_price * (1 + self.config['take_profit_pct'])
            elif overall_signal in ['STRONG_SELL', 'SELL']:
                # 卖出：当前价或略高  
                entry_price = current_price + (atr * 0.5)
                stop_loss = current_price * (1 + self.config['stop_loss_pct'])
                take_profit = current_price * (1 - self.config['take_profit_pct'])
            else:
                entry_price = current_price
                stop_loss = current_price * 0.95  # 5% 止损
                take_profit = current_price * 1.05  # 5% 止盈
            
            return {
                'symbol': symbol,
                'overall_signal': overall_signal,
                'composite_score': composite_score,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'analysis_components': {
                    'momentum': momentum_analysis,
                    'breakout': breakout_analysis,
                    'reversion': reversion_analysis
                },
                'risk_management': {
                    'position_size_pct': min(self.config['max_position_crypto'], confidence * 0.15),
                    'volatility_adjustment': min(2.0, atr / (current_price * 0.02)),  # 相对波动率调整
                    'recommended_timeframe': self._get_recommended_timeframe(overall_signal, confidence)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error calculating crypto entry signal: {e}")
            return {
                'symbol': symbol,
                'overall_signal': 'HOLD',
                'composite_score': 0,
                'confidence': 0,
                'error': str(e)
            }
    
    def _get_recommended_timeframe(self, signal: str, confidence: float) -> str:
        """获取建议持仓时间"""
        if signal in ['STRONG_BUY', 'STRONG_SELL']:
            if confidence > 0.8:
                return 'medium_term (1-4 weeks)'
            else:
                return 'short_term (3-10 days)'
        elif signal in ['BUY', 'SELL']:
            return 'short_term (3-10 days)'
        else:
            return 'wait_and_see'