"""
港股波段分析模块 - Swing Trade Analyzer
自动计算支撑阻力位、止盈止损、波段建议
"""

import numpy as np
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class SwingLevel:
    """波段关键价位"""
    price: float
    level_type: str  # 'support' or 'resistance'
    strength: int    # 1-3, 3最强
    source: str      # 来源说明


@dataclass
class SwingPlan:
    """波段交易计划"""
    ticker: str
    current_price: float
    trend: str           # 'up', 'down', 'sideways'
    trend_strength: str  # 'strong', 'moderate', 'weak'

    # 关键价位
    entry_low: float     # 买入区间下限
    entry_high: float    # 买入区间上限
    stop_loss: float     # 止损
    take_profit_1: float # 止盈1（减半仓）
    take_profit_2: float # 止盈2（清仓）

    # 风险收益
    risk_pct: float      # 风险百分比
    reward_pct: float    # 收益百分比
    risk_reward_ratio: float  # 风险收益比

    # 信号
    signal: str          # 'BUY', 'WAIT', 'AVOID'
    confidence: str      # 'high', 'medium', 'low'
    reasons: List[str]   # 理由


class SwingAnalyzer:
    """波段分析器"""

    def __init__(self):
        # ATR倍数配置
        self.atr_stop_multiplier = 1.5    # 止损ATR倍数
        self.atr_tp1_multiplier = 1.0     # 止盈1 ATR倍数
        self.atr_tp2_multiplier = 2.0     # 止盈2 ATR倍数

        # RSI阈值
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.rsi_neutral_low = 40
        self.rsi_neutral_high = 60

    def find_support_resistance(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        current_price: float
    ) -> Tuple[List[SwingLevel], List[SwingLevel]]:
        """
        寻找支撑和阻力位
        返回: (支撑位列表, 阻力位列表)
        """
        supports = []
        resistances = []

        if len(closes) < 20:
            return supports, resistances

        # 1. 前期高低点
        recent_high = max(highs[-20:])
        recent_low = min(lows[-20:])
        period_high = max(highs[-60:]) if len(highs) >= 60 else recent_high
        period_low = min(lows[-60:]) if len(lows) >= 60 else recent_low

        # 近期高点作为阻力
        if recent_high > current_price:
            resistances.append(SwingLevel(
                price=recent_high,
                level_type='resistance',
                strength=2,
                source='20日高点'
            ))

        # 近期低点作为支撑
        if recent_low < current_price:
            supports.append(SwingLevel(
                price=recent_low,
                level_type='support',
                strength=2,
                source='20日低点'
            ))

        # 更长周期高低点
        if period_high > current_price and abs(period_high - recent_high) > current_price * 0.01:
            resistances.append(SwingLevel(
                price=period_high,
                level_type='resistance',
                strength=3,
                source='60日高点'
            ))

        if period_low < current_price and abs(period_low - recent_low) > current_price * 0.01:
            supports.append(SwingLevel(
                price=period_low,
                level_type='support',
                strength=3,
                source='60日低点'
            ))

        # 2. 整数关口
        round_levels = self._find_round_numbers(current_price)
        for level in round_levels:
            if level < current_price:
                supports.append(SwingLevel(
                    price=level,
                    level_type='support',
                    strength=1,
                    source='整数关口'
                ))
            elif level > current_price:
                resistances.append(SwingLevel(
                    price=level,
                    level_type='resistance',
                    strength=1,
                    source='整数关口'
                ))

        # 3. 密集成交区（简化版：用收盘价聚类）
        price_clusters = self._find_price_clusters(closes, current_price)
        for cluster_price, strength in price_clusters:
            if cluster_price < current_price * 0.99:
                supports.append(SwingLevel(
                    price=cluster_price,
                    level_type='support',
                    strength=strength,
                    source='密集成交区'
                ))
            elif cluster_price > current_price * 1.01:
                resistances.append(SwingLevel(
                    price=cluster_price,
                    level_type='resistance',
                    strength=strength,
                    source='密集成交区'
                ))

        # 按价格排序并去重
        supports = self._dedupe_levels(supports, current_price, is_support=True)
        resistances = self._dedupe_levels(resistances, current_price, is_support=False)

        return supports, resistances

    def _find_round_numbers(self, price: float) -> List[float]:
        """找到价格附近的整数关口"""
        levels = []

        # 根据价格大小确定整数间隔
        if price > 500:
            interval = 50
        elif price > 100:
            interval = 10
        elif price > 50:
            interval = 5
        elif price > 10:
            interval = 1
        else:
            interval = 0.5

        # 找上下各2个整数关口
        base = int(price / interval) * interval
        for i in range(-2, 3):
            level = base + i * interval
            if level > 0 and abs(level - price) / price < 0.1:  # 10%范围内
                levels.append(level)

        return levels

    def _find_price_clusters(self, closes: List[float], current_price: float) -> List[Tuple[float, int]]:
        """找到价格密集区"""
        if len(closes) < 20:
            return []

        # 简化版：将价格分桶，找出高频区间
        price_range = max(closes) - min(closes)
        if price_range == 0:
            return []

        bucket_size = price_range / 20  # 分20个桶
        buckets = {}

        for price in closes[-60:] if len(closes) >= 60 else closes:
            bucket_idx = int((price - min(closes)) / bucket_size)
            buckets[bucket_idx] = buckets.get(bucket_idx, 0) + 1

        # 找出高频桶
        clusters = []
        avg_count = len(closes[-60:] if len(closes) >= 60 else closes) / 20

        for bucket_idx, count in buckets.items():
            if count > avg_count * 1.5:  # 超过平均1.5倍
                cluster_price = min(closes) + (bucket_idx + 0.5) * bucket_size
                strength = 2 if count > avg_count * 2 else 1
                clusters.append((cluster_price, strength))

        return clusters

    def _dedupe_levels(self, levels: List[SwingLevel], current_price: float, is_support: bool) -> List[SwingLevel]:
        """去重并排序价位"""
        if not levels:
            return []

        # 按价格排序
        levels.sort(key=lambda x: x.price, reverse=not is_support)

        # 合并相近价位（1%以内）
        deduped = []
        for level in levels:
            if not deduped:
                deduped.append(level)
            else:
                last = deduped[-1]
                if abs(level.price - last.price) / current_price < 0.01:
                    # 保留强度更高的
                    if level.strength > last.strength:
                        deduped[-1] = level
                else:
                    deduped.append(level)

        # 只保留最近的3个
        return deduped[:3]

    def analyze_trend(
        self,
        current_price: float,
        ema20: float,
        ema50: float,
        rsi: float
    ) -> Tuple[str, str, List[str]]:
        """
        分析趋势
        返回: (趋势方向, 趋势强度, 理由列表)
        """
        reasons = []

        # EMA趋势判断
        ema_bullish = current_price > ema20 > ema50
        ema_bearish = current_price < ema20 < ema50
        price_above_ema20 = current_price > ema20
        ema20_above_ema50 = ema20 > ema50

        # 趋势判断
        if ema_bullish:
            trend = 'up'
            reasons.append('价格>EMA20>EMA50，多头排列')
        elif ema_bearish:
            trend = 'down'
            reasons.append('价格<EMA20<EMA50，空头排列')
        elif price_above_ema20:
            trend = 'up'
            reasons.append('价格站上EMA20')
        elif ema20_above_ema50:
            trend = 'sideways'
            reasons.append('EMA20>EMA50但价格回调')
        else:
            trend = 'down'
            reasons.append('价格低于均线系统')

        # 强度判断
        price_ema20_diff = abs(current_price - ema20) / current_price

        if ema_bullish and price_ema20_diff < 0.02:
            strength = 'strong'
            reasons.append('强势上涨，贴近EMA20')
        elif ema_bearish and price_ema20_diff < 0.02:
            strength = 'strong'
            reasons.append('强势下跌')
        elif price_ema20_diff > 0.05:
            strength = 'weak'
            reasons.append(f'偏离EMA20达{price_ema20_diff*100:.1f}%')
        else:
            strength = 'moderate'

        # RSI辅助判断
        if rsi < self.rsi_oversold:
            reasons.append(f'RSI={rsi:.1f}超卖，可能反弹')
        elif rsi > self.rsi_overbought:
            reasons.append(f'RSI={rsi:.1f}超买，注意回调')
        elif rsi < self.rsi_neutral_low:
            reasons.append(f'RSI={rsi:.1f}偏弱')
        elif rsi > self.rsi_neutral_high:
            reasons.append(f'RSI={rsi:.1f}偏强')

        return trend, strength, reasons

    def calculate_swing_plan(
        self,
        ticker: str,
        current_price: float,
        indicators: Dict[str, float],
        price_data: Dict[str, List[float]]
    ) -> SwingPlan:
        """
        计算完整的波段交易计划
        """
        ema20 = indicators.get('ema20', current_price)
        ema50 = indicators.get('ema50', current_price)
        rsi = indicators.get('rsi14', 50)
        atr = indicators.get('atr14', current_price * 0.02)

        closes = price_data.get('close', [current_price])
        highs = price_data.get('high', closes)
        lows = price_data.get('low', closes)

        # 1. 分析趋势
        trend, trend_strength, trend_reasons = self.analyze_trend(
            current_price, ema20, ema50, rsi
        )

        # 2. 找支撑阻力
        supports, resistances = self.find_support_resistance(
            highs, lows, closes, current_price
        )

        # 3. 计算关键价位
        # 止损：基于ATR
        stop_loss = current_price - self.atr_stop_multiplier * atr

        # 如果有强支撑位，考虑用支撑位作为止损参考
        if supports:
            nearest_support = supports[0].price
            # 止损设在支撑位下方一点
            support_based_stop = nearest_support * 0.99
            # 取两者中更保守的（更高的止损）
            stop_loss = max(stop_loss, support_based_stop)

        # 止盈
        take_profit_1 = current_price + self.atr_tp1_multiplier * atr
        take_profit_2 = current_price + self.atr_tp2_multiplier * atr

        # 如果有阻力位，调整止盈
        if resistances:
            nearest_resistance = resistances[0].price
            # 止盈1不超过最近阻力位
            if take_profit_1 > nearest_resistance:
                take_profit_1 = nearest_resistance * 0.995
            # 止盈2可以略超过
            if len(resistances) > 1:
                take_profit_2 = min(take_profit_2, resistances[1].price * 0.995)

        # 买入区间
        if trend == 'up':
            # 上涨趋势：回调到EMA20附近买入
            entry_low = min(current_price, ema20 * 0.99)
            entry_high = current_price * 1.005
        elif trend == 'down':
            # 下跌趋势：等更低位置
            entry_low = current_price * 0.97
            entry_high = current_price * 0.99
        else:
            # 震荡：当前价格附近
            entry_low = current_price * 0.99
            entry_high = current_price * 1.01

        # 4. 计算风险收益
        risk_pct = (current_price - stop_loss) / current_price * 100
        reward_pct = (take_profit_2 - current_price) / current_price * 100
        risk_reward_ratio = reward_pct / risk_pct if risk_pct > 0 else 0

        # 5. 生成信号
        signal, confidence, signal_reasons = self._generate_signal(
            trend, trend_strength, rsi, risk_reward_ratio,
            current_price, ema20, supports, resistances
        )

        all_reasons = trend_reasons + signal_reasons

        # 添加支撑阻力信息
        if supports:
            all_reasons.append(f'最近支撑: {supports[0].price:.2f} ({supports[0].source})')
        if resistances:
            all_reasons.append(f'最近阻力: {resistances[0].price:.2f} ({resistances[0].source})')

        return SwingPlan(
            ticker=ticker,
            current_price=current_price,
            trend=trend,
            trend_strength=trend_strength,
            entry_low=round(entry_low, 2),
            entry_high=round(entry_high, 2),
            stop_loss=round(stop_loss, 2),
            take_profit_1=round(take_profit_1, 2),
            take_profit_2=round(take_profit_2, 2),
            risk_pct=round(risk_pct, 2),
            reward_pct=round(reward_pct, 2),
            risk_reward_ratio=round(risk_reward_ratio, 2),
            signal=signal,
            confidence=confidence,
            reasons=all_reasons
        )

    def _generate_signal(
        self,
        trend: str,
        trend_strength: str,
        rsi: float,
        risk_reward_ratio: float,
        current_price: float,
        ema20: float,
        supports: List[SwingLevel],
        resistances: List[SwingLevel]
    ) -> Tuple[str, str, List[str]]:
        """生成交易信号"""
        reasons = []
        score = 0

        # 趋势得分
        if trend == 'up':
            score += 2
            if trend_strength == 'strong':
                score += 1
        elif trend == 'sideways':
            score += 1
        else:
            score -= 1

        # RSI得分
        if rsi < self.rsi_oversold:
            score += 2
            reasons.append('RSI超卖反弹机会')
        elif rsi < self.rsi_neutral_low:
            score += 1
        elif rsi > self.rsi_overbought:
            score -= 2
            reasons.append('RSI超买风险')
        elif rsi > self.rsi_neutral_high:
            score -= 1

        # 风险收益比得分
        if risk_reward_ratio >= 2:
            score += 2
            reasons.append(f'风险收益比优秀({risk_reward_ratio:.1f})')
        elif risk_reward_ratio >= 1.5:
            score += 1
            reasons.append(f'风险收益比良好({risk_reward_ratio:.1f})')
        elif risk_reward_ratio < 1:
            score -= 1
            reasons.append(f'风险收益比不佳({risk_reward_ratio:.1f})')

        # 价格位置得分
        price_to_ema20 = (current_price - ema20) / ema20
        if -0.02 <= price_to_ema20 <= 0.02:
            score += 1
            reasons.append('价格接近EMA20')
        elif price_to_ema20 < -0.03:
            score += 1
            reasons.append('价格回调到位')
        elif price_to_ema20 > 0.05:
            score -= 1
            reasons.append('价格偏离EMA20过远')

        # 支撑位得分
        if supports:
            nearest_support_dist = (current_price - supports[0].price) / current_price
            if nearest_support_dist < 0.02:
                score += 1
                reasons.append('接近强支撑位')

        # 生成信号
        if score >= 4:
            signal = 'BUY'
            confidence = 'high'
        elif score >= 2:
            signal = 'BUY'
            confidence = 'medium'
        elif score >= 0:
            signal = 'WAIT'
            confidence = 'low'
        else:
            signal = 'AVOID'
            confidence = 'low'
            reasons.append('综合评分较低')

        return signal, confidence, reasons

    def format_plan(self, plan: SwingPlan) -> str:
        """格式化输出交易计划"""
        trend_emoji = {'up': '📈', 'down': '📉', 'sideways': '➡️'}
        signal_emoji = {'BUY': '🟢', 'WAIT': '🟡', 'AVOID': '🔴'}

        lines = [
            f"\n{'='*60}",
            f"📊 {plan.ticker} 波段交易计划",
            f"{'='*60}",
            f"",
            f"💲 当前价格: {plan.current_price:.2f} HKD",
            f"{trend_emoji.get(plan.trend, '➡️')} 趋势: {plan.trend.upper()} ({plan.trend_strength})",
            f"",
            f"{'─'*40}",
            f"📍 关键价位",
            f"{'─'*40}",
            f"  买入区间: {plan.entry_low:.2f} - {plan.entry_high:.2f}",
            f"  止损价格: {plan.stop_loss:.2f} (-{plan.risk_pct:.1f}%)",
            f"  止盈1(减仓): {plan.take_profit_1:.2f} (+{((plan.take_profit_1-plan.current_price)/plan.current_price*100):.1f}%)",
            f"  止盈2(清仓): {plan.take_profit_2:.2f} (+{plan.reward_pct:.1f}%)",
            f"",
            f"{'─'*40}",
            f"⚖️ 风险收益",
            f"{'─'*40}",
            f"  风险: {plan.risk_pct:.1f}%",
            f"  收益: {plan.reward_pct:.1f}%",
            f"  风险收益比: 1:{plan.risk_reward_ratio:.1f}",
            f"",
            f"{'─'*40}",
            f"{signal_emoji.get(plan.signal, '⚪')} 交易信号: {plan.signal} (置信度: {plan.confidence})",
            f"{'─'*40}",
        ]

        if plan.reasons:
            lines.append("📝 分析理由:")
            for reason in plan.reasons:
                lines.append(f"  • {reason}")

        lines.append(f"{'='*60}")

        return '\n'.join(lines)


# 便捷函数
def analyze_swing(
    ticker: str,
    current_price: float,
    indicators: Dict[str, float],
    price_data: Dict[str, List[float]]
) -> SwingPlan:
    """便捷函数：分析波段机会"""
    analyzer = SwingAnalyzer()
    return analyzer.calculate_swing_plan(ticker, current_price, indicators, price_data)


def print_swing_plan(
    ticker: str,
    current_price: float,
    indicators: Dict[str, float],
    price_data: Dict[str, List[float]]
) -> SwingPlan:
    """便捷函数：分析并打印波段计划"""
    analyzer = SwingAnalyzer()
    plan = analyzer.calculate_swing_plan(ticker, current_price, indicators, price_data)
    print(analyzer.format_plan(plan))
    return plan
