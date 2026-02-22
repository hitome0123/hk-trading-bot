#!/usr/bin/env python3
"""
港股日内2000元策略 - 基于Larry Williams波段交易法
本金：10-20万
目标：日赚2000元（1-2%日收益）
策略：高频小波段（0.5-2%单次，3-5次/天，胜率70%）

核心方法论：
1. Larry Williams - 窄幅震荡后突破
2. Oliver Velez - ABCD形态
3. 严格风控 - 单笔止损0.5%，日亏损上限1%
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

try:
    from futu import OpenQuoteContext, KLType, RET_OK, Market, SubType
    from hk_trading_bot.data_providers.futu_provider import FutuProvider
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    print("⚠️ 富途API未安装")


class IntradayStrategy2000:
    """日内2000元策略"""

    def __init__(self, capital: float = 150000):
        """
        Args:
            capital: 本金（默认15万）
        """
        self.capital = capital
        self.daily_target = 2000  # 日目标2000元
        self.daily_target_pct = (self.daily_target / self.capital) * 100  # 1.33%

        # 风控参数
        self.max_position_pct = 30  # 单笔最大仓位30%
        self.stop_loss_pct = 0.5    # 单笔止损0.5%
        self.daily_loss_limit_pct = 1.0  # 日亏损上限1%
        self.daily_loss_limit_amount = self.capital * (self.daily_loss_limit_pct / 100)

        # 交易参数
        self.max_trades_per_day = 5  # 每日最多5次交易
        self.min_volume_ratio = 1.5  # 最小量比1.5
        self.rsi_range = (40, 70)    # RSI健康区间

        # 状态跟踪
        self.today_trades = 0
        self.today_pnl = 0.0
        self.consecutive_losses = 0

        # 富途连接
        self.provider = None
        self.connected = False

    def connect_futu(self) -> bool:
        """连接富途OpenD"""
        if not FUTU_AVAILABLE:
            return False
        try:
            self.provider = FutuProvider()
            self.provider.connect()
            self.connected = True
            print("✅ 富途OpenD已连接")
            return True
        except Exception as e:
            print(f"❌ 富途连接失败: {e}")
            return False

    def disconnect_futu(self):
        """断开富途连接"""
        if self.provider:
            self.provider.disconnect()
            self.connected = False

    def check_trading_allowed(self) -> tuple[bool, str]:
        """
        检查是否允许交易
        Returns:
            (是否允许, 原因)
        """
        # 1. 检查日交易次数
        if self.today_trades >= self.max_trades_per_day:
            return False, f"已达每日交易上限({self.max_trades_per_day}次)"

        # 2. 检查日亏损
        if self.today_pnl <= -self.daily_loss_limit_amount:
            return False, f"已达日亏损上限(-{self.daily_loss_limit_amount:.0f}元)"

        # 3. 检查连续亏损
        if self.consecutive_losses >= 2:
            return False, "连续2次亏损，暂停交易30分钟"

        # 4. 检查时间（港股交易时间）
        now = datetime.now()
        hour, minute = now.hour, now.minute

        # 开盘观察期（9:30-10:00）
        if hour == 9 and minute < 60:
            return False, "开盘观察期，不急于入场"

        # 午休时间（12:00-13:00）
        if hour == 12:
            return False, "午休时间"

        # 尾盘时间（15:30后不开新仓）
        if hour >= 15 and minute >= 30:
            return False, "尾盘不开新仓"

        return True, "OK"

    def calculate_indicators(self, kline_data: List[Dict]) -> Dict[str, Any]:
        """
        计算技术指标
        Args:
            kline_data: K线数据（时间从旧到新）
        Returns:
            技术指标字典
        """
        if len(kline_data) < 30:
            return {"error": "数据不足"}

        closes = [k["close"] for k in kline_data]
        highs = [k["high"] for k in kline_data]
        lows = [k["low"] for k in kline_data]
        volumes = [k["volume"] for k in kline_data]

        indicators = {}

        # 1. RSI (14周期)
        indicators["rsi"] = self._calc_rsi(closes, 14)

        # 2. MACD (12, 26, 9)
        indicators["macd"] = self._calc_macd(closes, 12, 26, 9)

        # 3. ATR (14周期) - Larry Williams波动率
        indicators["atr"] = self._calc_atr(highs, lows, closes, 14)

        # 4. 成交量比
        recent_volume = volumes[-1]
        avg_volume_5 = sum(volumes[-6:-1]) / 5
        indicators["volume_ratio"] = recent_volume / avg_volume_5 if avg_volume_5 > 0 else 1.0

        # 5. 布林带
        indicators["bollinger"] = self._calc_bollinger_bands(closes, 20, 2)

        # 6. EMA20
        indicators["ema20"] = self._calc_ema(closes, 20)

        # 7. 价格形态
        indicators["pattern"] = self._detect_pattern(kline_data)

        return indicators

    def _calc_rsi(self, closes: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(closes) < period + 1:
            return 50.0

        gains, losses = 0.0, 0.0
        for i in range(len(closes) - period, len(closes)):
            change = closes[i] - closes[i - 1]
            if change > 0:
                gains += change
            else:
                losses -= change

        avg_gain = gains / period
        avg_loss = losses / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 2)

    def _calc_macd(self, closes: List[float], fast: int, slow: int, signal: int) -> Dict:
        """计算MACD"""
        if len(closes) < slow + signal:
            return {"macd": 0, "signal": 0, "histogram": 0, "trend": "neutral"}

        def ema(data, period):
            k = 2 / (period + 1)
            result = [data[0]]
            for i in range(1, len(data)):
                result.append(data[i] * k + result[-1] * (1 - k))
            return result

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = ema(macd_line[slow - 1:], signal)

        macd_val = round(macd_line[-1], 4)
        signal_val = round(signal_line[-1], 4)
        hist = round(macd_val - signal_val, 4)
        trend = "bullish" if hist > 0 else "bearish" if hist < 0 else "neutral"

        return {
            "macd": macd_val,
            "signal": signal_val,
            "histogram": hist,
            "trend": trend
        }

    def _calc_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """计算ATR（平均真实波幅）"""
        if len(highs) < period + 1:
            return 0.0

        trs = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            trs.append(tr)

        return round(sum(trs[-period:]) / period, 4)

    def _calc_bollinger_bands(self, closes: List[float], period: int = 20, std_dev: int = 2) -> Dict:
        """计算布林带"""
        if len(closes) < period:
            return {"upper": 0, "middle": 0, "lower": 0, "position": "middle"}

        recent = closes[-period:]
        middle = sum(recent) / period
        variance = sum([(x - middle) ** 2 for x in recent]) / period
        std = variance ** 0.5

        upper = middle + (std_dev * std)
        lower = middle - (std_dev * std)
        current = closes[-1]

        if current <= lower:
            position = "lower"
        elif current >= upper:
            position = "upper"
        else:
            position = "middle"

        return {
            "upper": round(upper, 2),
            "middle": round(middle, 2),
            "lower": round(lower, 2),
            "position": position
        }

    def _calc_ema(self, closes: List[float], period: int) -> float:
        """计算EMA"""
        if len(closes) < period:
            return closes[-1] if closes else 0.0

        k = 2 / (period + 1)
        ema = closes[0]
        for price in closes[1:]:
            ema = price * k + ema * (1 - k)

        return round(ema, 2)

    def _detect_pattern(self, kline_data: List[Dict]) -> Dict[str, Any]:
        """
        检测价格形态
        1. 窄幅震荡（Larry Williams）
        2. ABCD形态（Oliver Velez）
        """
        if len(kline_data) < 10:
            return {"type": "none"}

        closes = [k["close"] for k in kline_data]
        highs = [k["high"] for k in kline_data]
        lows = [k["low"] for k in kline_data]

        # 检测窄幅震荡（最近5根K线波动<2%）
        recent_high = max(highs[-5:])
        recent_low = min(lows[-5:])
        amplitude = ((recent_high - recent_low) / recent_low) * 100

        if amplitude < 2.0:
            return {
                "type": "narrow_range",
                "description": "窄幅震荡（等待突破）",
                "amplitude": round(amplitude, 2)
            }

        # 检测ABCD形态（简化版）
        # A点：最近10根K线的最低点
        # B点：A点之后的最高点
        # C点：B点之后的回调（50-61.8%）
        # D点：目标位（B点 + AB的1.5倍）
        a_idx = lows[-10:].index(min(lows[-10:]))
        a_price = lows[-(10 - a_idx)]

        if a_idx < len(lows[-10:]) - 2:
            b_idx = a_idx + highs[-(10 - a_idx):].index(max(highs[-(10 - a_idx):]))
            b_price = highs[-(10 - b_idx)]

            if b_idx < len(highs) - 1:
                c_price = closes[-1]
                retracement = ((b_price - c_price) / (b_price - a_price)) * 100

                if 50 <= retracement <= 61.8:
                    d_price = b_price + (b_price - a_price) * 1.5
                    return {
                        "type": "abcd",
                        "description": "ABCD形态（C点确认）",
                        "a_price": round(a_price, 2),
                        "b_price": round(b_price, 2),
                        "c_price": round(c_price, 2),
                        "d_price": round(d_price, 2),
                        "retracement": round(retracement, 1)
                    }

        return {"type": "none"}

    def check_entry_signal(self, code: str, indicators: Dict) -> tuple[bool, str, Dict]:
        """
        检查入场信号（3个条件必须同时满足）
        Returns:
            (是否入场, 原因, 交易计划)
        """
        reasons = []
        score = 0

        # 条件1：价格形态
        pattern = indicators.get("pattern", {})
        if pattern.get("type") == "narrow_range":
            reasons.append("✓ 窄幅震荡后突破")
            score += 30
        elif pattern.get("type") == "abcd":
            reasons.append("✓ ABCD形态C点确认")
            score += 35
        else:
            return False, "价格形态不符合", {}

        # 条件2：成交量确认
        volume_ratio = indicators.get("volume_ratio", 1.0)
        if volume_ratio >= self.min_volume_ratio:
            reasons.append(f"✓ 放量确认（量比{volume_ratio:.1f}x）")
            score += 25
        else:
            return False, f"成交量不足（量比{volume_ratio:.1f} < 1.5）", {}

        # 条件3：技术指标
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", {})
        ema20 = indicators.get("ema20", 0)
        current_price = indicators.get("current_price", 0)

        if self.rsi_range[0] <= rsi <= self.rsi_range[1]:
            reasons.append(f"✓ RSI正常区间（{rsi:.1f}）")
            score += 15
        else:
            return False, f"RSI不在健康区间（{rsi:.1f}）", {}

        if macd.get("trend") == "bullish" and macd.get("histogram", 0) > 0:
            reasons.append("✓ MACD金叉且柱子为正")
            score += 20
        elif macd.get("trend") == "bullish":
            reasons.append("✓ MACD金叉")
            score += 10

        if current_price > ema20:
            reasons.append(f"✓ 价格站上EMA20")
            score += 10

        # 计算交易计划
        if score >= 70:
            trade_plan = self._calculate_trade_plan(code, indicators)
            return True, "; ".join(reasons), trade_plan
        else:
            return False, f"信号评分不足（{score}/100）", {}

    def _calculate_trade_plan(self, code: str, indicators: Dict) -> Dict:
        """
        计算交易计划
        """
        current_price = indicators.get("current_price", 0)
        atr = indicators.get("atr", 0)

        # 仓位计算（30%本金）
        position_value = self.capital * (self.max_position_pct / 100)
        shares = int(position_value / current_price / 100) * 100  # 港股每手100股

        # 止损价（当前价 - 0.5%）
        stop_loss = current_price * (1 - self.stop_loss_pct / 100)

        # 目标价（根据形态类型）
        pattern = indicators.get("pattern", {})
        if pattern.get("type") == "abcd":
            # ABCD形态：目标价D点
            target_price = pattern.get("d_price", current_price * 1.015)
        else:
            # 其他形态：目标价 = 当前价 + 1.5 * ATR
            target_price = current_price + (1.5 * atr)

        # 确保最小收益1%
        if target_price < current_price * 1.01:
            target_price = current_price * 1.015

        # 风险收益比
        risk = current_price - stop_loss
        reward = target_price - current_price
        risk_reward_ratio = reward / risk if risk > 0 else 0

        return {
            "code": code,
            "entry_price": round(current_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target_price": round(target_price, 2),
            "shares": shares,
            "position_value": round(position_value, 2),
            "risk_amount": round(shares * 100 * risk, 2),
            "reward_amount": round(shares * 100 * reward, 2),
            "risk_reward_ratio": f"1:{risk_reward_ratio:.2f}",
            "expected_profit_pct": round(((target_price - current_price) / current_price) * 100, 2)
        }

    def check_exit_signal(self, position: Dict, current_price: float) -> tuple[bool, str]:
        """
        检查出场信号
        Args:
            position: 持仓信息
            current_price: 当前价格
        Returns:
            (是否出场, 原因)
        """
        entry_price = position.get("entry_price", 0)
        stop_loss = position.get("stop_loss", 0)
        target_price = position.get("target_price", 0)
        entry_time = position.get("entry_time", datetime.now())

        # 1. 目标位到达
        if current_price >= target_price:
            return True, "目标位到达"

        # 2. 止损触发
        if current_price <= stop_loss:
            return True, "止损触发"

        # 3. 时间止损（持仓2小时未达目标，减仓50%）
        hold_time = (datetime.now() - entry_time).total_seconds() / 3600
        if hold_time >= 2.0:
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            if pnl_pct < 1.0:
                return True, "时间止损（2小时未达目标）"

        # 4. 尾盘规则（15:45前清仓）
        now = datetime.now()
        if now.hour == 15 and now.minute >= 45:
            return True, "尾盘清仓"

        # 5. 盈利保护
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        if pnl_pct >= 1.5:
            return True, "盈利1.5%保护性止盈"

        return False, "持仓中"

    def scan_stocks(self, stock_pool: List[str]) -> List[Dict]:
        """
        扫描股票池，生成交易信号
        Args:
            stock_pool: 股票代码列表 ["HK.00700", "HK.01810", ...]
        Returns:
            交易信号列表
        """
        if not self.connected:
            print("❌ 未连接富途OpenD")
            return []

        # 检查是否允许交易
        allowed, reason = self.check_trading_allowed()
        if not allowed:
            print(f"⚠️ 不允许交易: {reason}")
            return []

        signals = []

        for code in stock_pool:
            try:
                # 获取K线数据（5分钟K线，最近50根）
                kline_data = self._get_kline_data(code, KLType.K_5M, 50)
                if not kline_data:
                    continue

                # 计算技术指标
                indicators = self.calculate_indicators(kline_data)
                if "error" in indicators:
                    continue

                # 添加当前价格
                indicators["current_price"] = kline_data[-1]["close"]

                # 检查入场信号
                should_enter, reason, trade_plan = self.check_entry_signal(code, indicators)

                if should_enter:
                    signal = {
                        "code": code,
                        "name": self._get_stock_name(code),
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "reason": reason,
                        "trade_plan": trade_plan,
                        "indicators": {
                            "rsi": indicators.get("rsi"),
                            "macd": indicators.get("macd"),
                            "volume_ratio": indicators.get("volume_ratio"),
                            "pattern": indicators.get("pattern")
                        }
                    }
                    signals.append(signal)

            except Exception as e:
                print(f"⚠️ 扫描 {code} 失败: {e}")
                continue

        return signals

    def _get_kline_data(self, code: str, ktype: KLType, num: int) -> List[Dict]:
        """获取K线数据"""
        try:
            ret, data = self.provider.quote_ctx.get_cur_kline(code, num, ktype)
            if ret == RET_OK:
                return data.to_dict('records')
            return []
        except Exception as e:
            print(f"获取K线失败: {e}")
            return []

    def _get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        try:
            ret, data = self.provider.quote_ctx.get_stock_basicinfo(Market.HK, [code])
            if ret == RET_OK and len(data) > 0:
                return data.iloc[0]['name']
            return code
        except:
            return code


if __name__ == "__main__":
    # 测试
    strategy = IntradayStrategy2000(capital=150000)

    if strategy.connect_futu():
        # 港股标的池（大盘股+中小盘股）
        stock_pool = [
            "HK.00700",  # 腾讯
            "HK.09988",  # 阿里
            "HK.03690",  # 美团
            "HK.01810",  # 小米
            "HK.01211",  # 比亚迪
            "HK.02015",  # 理想汽车
            "HK.09866",  # 蔚来
        ]

        print("🔍 扫描交易信号...")
        signals = strategy.scan_stocks(stock_pool)

        if signals:
            print(f"\n✅ 发现 {len(signals)} 个交易信号:\n")
            for sig in signals:
                print(f"【{sig['name']}】{sig['code']}")
                print(f"  理由: {sig['reason']}")
                print(f"  买入: {sig['trade_plan']['entry_price']}")
                print(f"  止损: {sig['trade_plan']['stop_loss']}")
                print(f"  目标: {sig['trade_plan']['target_price']}")
                print(f"  风险收益比: {sig['trade_plan']['risk_reward_ratio']}")
                print()
        else:
            print("⚠️ 暂无交易信号")

        strategy.disconnect_futu()
