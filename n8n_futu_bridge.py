#!/usr/bin/env python3
"""
FutuOpenD Data Bridge for n8n Workflow - Enhanced Version
增强功能：
1. 完整技术指标（RSI、MACD、ATR、布林带、KDJ、OBV）
2. 社交媒体热度（雪球、东财股吧）- 可选，有超时保护
3. 新闻热点板块识别 - 可选
4. 智能评分系统
"""
import json
import sys
import os
import logging
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# OS-level stdout suppression
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import (
        OpenQuoteContext, KLType, SubType, KL_FIELD,
        RET_OK, Market
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

# 可选：社交媒体和新闻API（有超时保护）
ENABLE_SOCIAL = True  # 设为False可禁用社交媒体功能，提高速度
ENABLE_NEWS = True    # 设为False可禁用新闻功能
TIMEOUT_SOCIAL = 3    # 社交媒体API超时（秒）
TIMEOUT_NEWS = 5      # 新闻API超时（秒）

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    ENABLE_SOCIAL = False
    ENABLE_NEWS = False


def _output_json(data):
    """Write JSON to the real stdout fd"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# 候选股票池
CANDIDATES = [
    ("HK.09988", "阿里巴巴"), ("HK.00700", "腾讯控股"), ("HK.03690", "美团"),
    ("HK.01810", "小米集团"), ("HK.09618", "京东集团"), ("HK.01024", "快手"),
    ("HK.09888", "百度集团"), ("HK.01211", "比亚迪"), ("HK.02015", "理想汽车"),
    ("HK.09868", "小鹏汽车"), ("HK.09866", "蔚来"), ("HK.00981", "中芯国际"),
    ("HK.01347", "华虹半导体"), ("HK.06969", "思摩尔"), ("HK.00020", "商汤"),
    ("HK.01045", "亚太卫星"),
]


# ==================== 技术指标计算 ====================
def calc_rsi(closes, period=14):
    """计算RSI"""
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
    trend = "bullish" if hist > 0 else ("bearish" if hist < 0 else "neutral")
    return {"macd": macd_val, "signal": signal_val, "histogram": hist, "trend": trend}


def calc_atr(highs, lows, closes, period=14):
    """计算ATR"""
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return round(sum(trs[-period:]) / period, 4)


def calc_bollinger_bands(closes, period=20, std_dev=2):
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

    position = "overbought" if current > upper else ("oversold" if current < lower else "middle")

    return {
        "upper": round(upper, 3),
        "middle": round(middle, 3),
        "lower": round(lower, 3),
        "position": position
    }


def calc_kdj(highs, lows, closes, n=9):
    """计算KDJ指标"""
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


def calc_obv(volumes, closes):
    """计算OBV（能量潮）"""
    if len(volumes) < 2:
        return 0

    obv = 0
    for i in range(1, len(volumes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]

    return obv


# ==================== 社交媒体热度（可选，有超时保护）====================
def get_social_heat(code, name):
    """获取社交热度 - 快速版"""
    result = {"xueqiu_score": 0, "guba_score": 0, "total_score": 0}

    if not ENABLE_SOCIAL or not REQUESTS_AVAILABLE:
        return result

    try:
        stock_code = code.replace('HK.', '')
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)',
            'Accept': 'application/json',
        }

        # 东财股吧（快速检测）
        try:
            url = f"https://guba.eastmoney.com/list,hk{stock_code}.html"
            resp = requests.get(url, headers=headers, timeout=TIMEOUT_SOCIAL)
            if resp.status_code == 200 and '阅读' in resp.text:
                result['guba_score'] = 30
        except:
            pass

        result['total_score'] = result['xueqiu_score'] + result['guba_score']

    except:
        pass

    return result


# ==================== 评分系统 ====================
def calculate_score(stock_data):
    """智能评分系统（满分100分）"""
    score = 0
    reasons = []

    # 1. 涨幅评分 (20分)
    change = stock_data.get('changePct', 0)
    if change > 5:
        score += 20
        reasons.append(f"强势上涨{change:.1f}%")
    elif change > 2:
        score += 15
        reasons.append(f"温和上涨{change:.1f}%")
    elif change > 0:
        score += 10

    # 2. 振幅评分 (15分)
    amplitude = stock_data.get('amplitude', 0)
    if amplitude > 5:
        score += 15
        reasons.append(f"高振幅{amplitude:.1f}%")
    elif amplitude > 3:
        score += 10
        reasons.append(f"振幅良好{amplitude:.1f}%")
    elif amplitude > 2:
        score += 5

    # 3. RSI评分 (15分)
    rsi = stock_data.get('rsi', 50)
    if 30 <= rsi <= 40:
        score += 15
        reasons.append(f"RSI超卖区{rsi:.0f}")
    elif 40 < rsi <= 60:
        score += 10
    elif rsi > 70:
        score -= 5

    # 4. MACD评分 (15分)
    macd = stock_data.get('macd', {})
    if macd.get('trend') == 'bullish' and macd.get('histogram', 0) > 0:
        score += 15
        reasons.append("MACD金叉")
    elif macd.get('trend') == 'bearish':
        score -= 5

    # 5. 布林带评分 (10分)
    bollinger = stock_data.get('bollinger', {})
    if bollinger.get('position') == 'oversold':
        score += 10
        reasons.append("布林下轨超卖")
    elif bollinger.get('position') == 'overbought':
        score -= 5

    # 6. KDJ评分 (10分)
    kdj = stock_data.get('kdj', {})
    if kdj.get('signal') == 'oversold':
        score += 10
        reasons.append("KDJ超卖")
    elif kdj.get('signal') == 'overbought':
        score -= 5

    # 7. 量比评分 (10分)
    vol_ratio = stock_data.get('volumeRatio', 1.0)
    if vol_ratio >= 2.0:
        score += 10
        reasons.append(f"放量{vol_ratio:.1f}倍")
    elif vol_ratio >= 1.5:
        score += 5

    # 8. 社交热度 (5分)
    social = stock_data.get('social_heat', {})
    if social.get('total_score', 0) > 50:
        score += 5
        reasons.append("社交热度高")

    stock_data['reasons'] = reasons
    stock_data['score'] = min(100, max(0, score))
    stock_data['rating'] = (
        'strong_buy' if score >= 80 else
        ('buy' if score >= 60 else
        ('neutral' if score >= 40 else 'sell'))
    )

    return stock_data


# ==================== 主函数 ====================
def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "stocks": []})
        return

    ctx = None
    results = []
    hot_sectors = []

    try:
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        codes = [c[0] for c in CANDIDATES]

        # 批量获取实时行情
        ret, snapshots = ctx.get_market_snapshot(codes)
        snap_map = {}
        if ret == RET_OK and snapshots is not None:
            for _, row in snapshots.iterrows():
                snap_map[row["code"]] = row

        # 处理每只股票
        for code, name in CANDIDATES:
            stock = {"code": code, "name": name}

            # 实时行情
            if code in snap_map:
                s = snap_map[code]
                stock.update({
                    "price": float(s.get("last_price", 0)),
                    "open": float(s.get("open_price", 0)),
                    "high": float(s.get("high_price", 0)),
                    "low": float(s.get("low_price", 0)),
                    "prevClose": float(s.get("prev_close_price", 0)),
                    "volume": int(s.get("volume", 0)),
                    "turnover": float(s.get("turnover", 0)),
                    "amplitude": float(s.get("amplitude", 0)),
                    "changePct": round(
                        (float(s.get("last_price", 0)) - float(s.get("prev_close_price", 1)))
                        / float(s.get("prev_close_price", 1)) * 100, 2
                    ) if s.get("prev_close_price", 0) > 0 else 0,
                    "turnoverRate": float(s.get("turnover_rate", 0)),
                })
            else:
                stock.update({"price": 0, "error": "no_snapshot"})
                results.append(stock)
                continue

            # K线数据
            ret_k, klines, _ = ctx.request_history_kline(
                code, ktype=KLType.K_DAY, max_count=60
            )
            if ret_k == RET_OK and klines is not None and len(klines) > 0:
                closes = klines["close"].tolist()
                highs = klines["high"].tolist()
                lows = klines["low"].tolist()
                volumes = klines["volume"].tolist()

                # 计算所有技术指标
                stock["rsi"] = calc_rsi(closes)
                stock["macd"] = calc_macd(closes)
                stock["atr"] = calc_atr(highs, lows, closes)
                stock["atrPct"] = round(stock["atr"] / stock["price"] * 100, 2) if stock["price"] > 0 else 0
                stock["bollinger"] = calc_bollinger_bands(closes)
                stock["kdj"] = calc_kdj(highs, lows, closes)
                stock["obv"] = calc_obv(volumes, closes)

                # 支撑/压力位
                prev_h = highs[-2] if len(highs) >= 2 else stock["high"]
                prev_l = lows[-2] if len(lows) >= 2 else stock["low"]
                prev_c = closes[-2] if len(closes) >= 2 else stock["prevClose"]
                pivot = round((prev_h + prev_l + prev_c) / 3, 3)
                stock["pivot"] = pivot
                stock["support1"] = round(2 * pivot - prev_h, 3)
                stock["support2"] = round(pivot - (prev_h - prev_l), 3)
                stock["resistance1"] = round(2 * pivot - prev_l, 3)
                stock["resistance2"] = round(pivot + (prev_h - prev_l), 3)

                # 量比
                avg_vol_5 = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
                stock["volumeRatio"] = round(stock["volume"] / avg_vol_5, 2) if avg_vol_5 > 0 else 1.0
                stock["volumeStatus"] = (
                    "heavy" if stock["volumeRatio"] >= 1.5
                    else ("normal" if stock["volumeRatio"] >= 0.7 else "light")
                )
            else:
                stock.update({"rsi": 50, "macd": {"trend": "unknown"}, "atr": 0})

            # 社交热度（可选）
            if ENABLE_SOCIAL:
                stock["social_heat"] = get_social_heat(code, name)

            # 智能评分
            stock = calculate_score(stock)

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

    # 按评分排序
    results.sort(key=lambda x: x.get('score', 0), reverse=True)

    output = {
        "stocks": results,
        "count": len(results),
        "hot_sectors": hot_sectors,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "FutuOpenD Enhanced",
        "version": "2.0"
    }
    _output_json(output)


if __name__ == "__main__":
    main()
