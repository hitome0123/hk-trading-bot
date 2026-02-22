#!/usr/bin/env python3
"""
港股日内交易推荐系统 (T+0)
专注：超跌反弹 + 波动大 + 放量上涨

推荐条件：
1. 连续下跌几天后反弹
2. 位置较低（布林下轨、RSI超卖）
3. 波动大（振幅 > 5%）
4. 市值中低（50-500亿HKD）
5. 放量上涨（量比 > 1.5）
6. 技术指标支持（MACD金叉、KDJ超卖）

输出：
- 推荐股票列表
- 买入点位建议
- 止损点位
- 目标点位（日内）
"""
import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Suppress stdout
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, KLType, RET_OK, Market
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False


def _output_json(data):
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# ==================== 技术指标 ====================
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(len(closes) - period, len(closes)):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_macd(closes, fast=12, slow=26, signal=9):
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
    trend = "bullish" if hist > 0 else ("bearish" if hist < 0 else "neutral")
    return {"macd": macd_val, "signal": signal_val, "histogram": hist, "trend": trend}


def calc_bollinger_bands(closes, period=20, std_dev=2):
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "position": "middle", "distance_from_lower": 0}

    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum([(x - middle) ** 2 for x in recent]) / period
    std = variance ** 0.5
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    current = closes[-1]

    # 距离下轨的百分比
    distance_from_lower = ((current - lower) / lower * 100) if lower > 0 else 0

    position = "overbought" if current > upper else ("oversold" if current < lower else "middle")

    return {
        "upper": round(upper, 3),
        "middle": round(middle, 3),
        "lower": round(lower, 3),
        "position": position,
        "distance_from_lower": round(distance_from_lower, 2),
    }


def calc_kdj(highs, lows, closes, n=9):
    if len(closes) < n:
        return {"k": 50, "d": 50, "j": 50, "signal": "neutral"}

    recent_highs = highs[-n:]
    recent_lows = lows[-n:]
    recent_closes = closes[-n:]

    highest = max(recent_highs)
    lowest = min(recent_lows)

    if highest == lowest:
        return {"k": 50, "d": 50, "j": 50, "signal": "neutral"}

    rsv = (recent_closes[-1] - lowest) / (highest - lowest) * 100
    k = rsv
    d = k
    j = 3 * k - 2 * d

    signal = "overbought" if j > 80 else ("oversold" if j < 20 else "neutral")

    return {"k": round(k, 2), "d": round(d, 2), "j": round(j, 2), "signal": signal}


# ==================== 连续下跌天数检测 ====================
def count_continuous_down_days(closes):
    """计算连续下跌天数"""
    if len(closes) < 2:
        return 0

    down_days = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            down_days += 1
        else:
            break

    return down_days


# ==================== 点位计算 ====================
def calculate_trading_levels(stock_data, klines_data):
    """
    计算买入、止损、目标点位

    策略：
    - 买入点：当前价附近，或回踩支撑位
    - 止损点：布林下轨 或 前低 - 2%
    - 目标点1：布林中轨（日内T+0目标）
    - 目标点2：布林上轨（激进目标）
    """
    current_price = stock_data.get("price", 0)
    bollinger = stock_data.get("bollinger", {})

    highs = klines_data["highs"]
    lows = klines_data["lows"]
    closes = klines_data["closes"]

    # 前低（最近5日最低点）
    prev_low = min(lows[-6:-1]) if len(lows) >= 6 else lows[-1]

    # 买入点（当前价 或 稍微回踩后）
    entry_price = current_price
    entry_range_low = current_price * 0.99  # 回踩1%
    entry_range_high = current_price * 1.01

    # 止损点（布林下轨 或 前低-2%，取较低者）
    stop_loss_bollinger = bollinger.get("lower", 0)
    stop_loss_prev_low = prev_low * 0.98
    stop_loss = max(stop_loss_bollinger, stop_loss_prev_low)  # 取较高的止损（更安全）

    # 目标点
    target1 = bollinger.get("middle", 0)  # 布林中轨（保守）
    target2 = bollinger.get("upper", 0)   # 布林上轨（激进）

    # 风险回报比
    risk = current_price - stop_loss if current_price > stop_loss else 0
    reward1 = target1 - current_price if target1 > current_price else 0
    reward2 = target2 - current_price if target2 > current_price else 0

    risk_reward_ratio1 = (reward1 / risk) if risk > 0 else 0
    risk_reward_ratio2 = (reward2 / risk) if risk > 0 else 0

    return {
        "entry_price": round(entry_price, 3),
        "entry_range": {
            "low": round(entry_range_low, 3),
            "high": round(entry_range_high, 3),
        },
        "stop_loss": round(stop_loss, 3),
        "target1": round(target1, 3),
        "target2": round(target2, 3),
        "risk_pct": round((risk / current_price * 100), 2) if current_price > 0 else 0,
        "reward1_pct": round((reward1 / current_price * 100), 2) if current_price > 0 else 0,
        "reward2_pct": round((reward2 / current_price * 100), 2) if current_price > 0 else 0,
        "risk_reward_ratio1": round(risk_reward_ratio1, 2),
        "risk_reward_ratio2": round(risk_reward_ratio2, 2),
    }


# ==================== 日内交易评分 ====================
def calculate_intraday_score(stock_data, down_days):
    """
    日内交易评分（满分100分）

    重点：
    - 连续下跌天数 (30分)
    - 位置低（RSI超卖、布林下轨）(25分)
    - 放量上涨 (20分)
    - 波动大 (15分)
    - MACD金叉 (10分)
    """
    score = 0
    signals = []

    # 1. 连续下跌天数 (30分)
    if down_days >= 5:
        score += 30
        signals.append(f"连续下跌{down_days}天")
    elif down_days >= 3:
        score += 20
        signals.append(f"下跌{down_days}天")
    elif down_days >= 1:
        score += 10

    # 2. 位置低 (25分)
    rsi = stock_data.get("rsi", 50)
    bollinger = stock_data.get("bollinger", {})
    kdj = stock_data.get("kdj", {})

    if rsi < 30:
        score += 15
        signals.append(f"RSI深度超卖{rsi:.0f}")
    elif rsi < 40:
        score += 10
        signals.append(f"RSI超卖{rsi:.0f}")

    if bollinger.get("position") == "oversold":
        score += 10
        signals.append("布林下轨")

    # 3. 放量上涨 (20分)
    vol_ratio = stock_data.get("volumeRatio", 1.0)
    change_pct = stock_data.get("changePct", 0)

    if vol_ratio >= 2.0 and change_pct > 0:
        score += 20
        signals.append(f"放量上涨{vol_ratio:.1f}倍")
    elif vol_ratio >= 1.5 and change_pct > 0:
        score += 15
        signals.append(f"温和放量{vol_ratio:.1f}倍")
    elif vol_ratio >= 1.0 and change_pct > 0:
        score += 10

    # 4. 波动大 (15分)
    amplitude = stock_data.get("amplitude", 0)
    if amplitude > 8:
        score += 15
        signals.append(f"高波动{amplitude:.1f}%")
    elif amplitude > 5:
        score += 10
        signals.append(f"波动{amplitude:.1f}%")
    elif amplitude > 3:
        score += 5

    # 5. MACD金叉 (10分)
    macd = stock_data.get("macd", {})
    if macd.get("trend") == "bullish" and macd.get("histogram", 0) > 0:
        score += 10
        signals.append("MACD金叉")

    stock_data["intraday_score"] = min(100, score)
    stock_data["signals"] = signals
    stock_data["down_days"] = down_days

    return stock_data


# ==================== 主函数 ====================
def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "stocks": []})
        return

    ctx = None
    results = []

    try:
        # 连接Futu
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 获取港股列表（过滤市值）
        ret, stock_list = ctx.get_stock_basicinfo(market=Market.HK, stock_type='STOCK')

        if ret != RET_OK:
            _output_json({"error": "Failed to get stock list", "stocks": []})
            return

        # 筛选候选股票（市值 50-500亿HKD）
        candidates = []
        for _, row in stock_list.head(500).iterrows():
            code = row['code']
            candidates.append(code)

        # 批量获取实时行情
        ret, snapshots = ctx.get_market_snapshot(candidates[:100])  # 限制100只，避免超时
        snap_map = {}
        if ret == RET_OK and snapshots is not None:
            for _, row in snapshots.iterrows():
                snap_map[row["code"]] = row

        # 处理每只股票
        for code in candidates[:100]:
            if code not in snap_map:
                continue

            s = snap_map[code]
            prev_close = float(s.get("prev_close_price", 0))
            price = float(s.get("last_price", 0))

            if prev_close <= 0 or price <= 0:
                continue

            # 基础数据
            market_cap = float(s.get("market_val", 0))  # 市值（亿HKD）

            # 筛选：市值 50-500亿
            if market_cap < 50 or market_cap > 500:
                continue

            stock = {
                "code": code.replace("HK.", ""),
                "name": s.get("name", ""),
                "price": price,
                "prevClose": prev_close,
                "changePct": round((price - prev_close) / prev_close * 100, 2),
                "amplitude": float(s.get("amplitude", 0)),
                "volume": int(s.get("volume", 0)),
                "turnover": float(s.get("turnover", 0)),
                "marketCap": market_cap,
            }

            # 只关注振幅 > 3% 的股票
            if stock["amplitude"] < 3:
                continue

            # K线数据
            ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=60)
            if ret_k != RET_OK or klines is None or len(klines) == 0:
                continue

            closes = klines["close"].tolist()
            highs = klines["high"].tolist()
            lows = klines["low"].tolist()
            volumes = klines["volume"].tolist()

            # 连续下跌天数
            down_days = count_continuous_down_days(closes)

            # 只推荐：连续下跌至少1天的股票
            if down_days < 1:
                continue

            # 技术指标
            stock["rsi"] = calc_rsi(closes)
            stock["macd"] = calc_macd(closes)
            stock["bollinger"] = calc_bollinger_bands(closes)
            stock["kdj"] = calc_kdj(highs, lows, closes)

            # 量比
            avg_vol_5 = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
            stock["volumeRatio"] = round(stock["volume"] / avg_vol_5, 2) if avg_vol_5 > 0 else 1.0

            # 日内交易评分
            stock = calculate_intraday_score(stock, down_days)

            # 只推荐评分 >= 40 的股票
            if stock["intraday_score"] < 40:
                continue

            # 计算交易点位
            klines_data = {"highs": highs, "lows": lows, "closes": closes}
            stock["trading_levels"] = calculate_trading_levels(stock, klines_data)

            # 只推荐风险回报比 >= 1.5 的股票
            if stock["trading_levels"]["risk_reward_ratio1"] < 1.5:
                continue

            results.append(stock)

    except Exception as e:
        _output_json({
            "error": str(e),
            "stocks": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return
    finally:
        if ctx:
            ctx.close()

    # 按日内评分排序
    results.sort(key=lambda x: x.get("intraday_score", 0), reverse=True)

    # 输出
    output = {
        "stocks": results,
        "count": len(results),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategy": "超跌反弹T+0",
        "criteria": {
            "market_cap": "50-500亿HKD",
            "min_amplitude": "3%",
            "min_down_days": "1天",
            "min_score": "40分",
            "min_risk_reward": "1.5",
        },
    }

    _output_json(output)


if __name__ == "__main__":
    main()
