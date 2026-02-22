#!/usr/bin/env python3
"""
生成信号并保存到文件
n8n通过读取文件获取数据
"""
import json
import os
from datetime import datetime

# 导入原有的信号生成逻辑
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

# Suppress stdout during import
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, KLType, RET_OK
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

os.dup2(_stdout_fd, 1)

# 港股板块配置（扩展版）
SECTORS = {
    '商业航天': ['HK.01045', 'HK.00031', 'HK.02333'],
    'AI科技': ['HK.00020', 'HK.09888', 'HK.01024', 'HK.09626', 'HK.01833'],
    '新能源汽车': ['HK.09866', 'HK.02015', 'HK.01211', 'HK.00175', 'HK.09868', 'HK.01958', 'HK.02238'],
    '半导体': ['HK.00981', 'HK.01347', 'HK.01478', 'HK.02231'],
    '互联网': ['HK.00700', 'HK.09988', 'HK.09618', 'HK.03690', 'HK.09999', 'HK.09961', 'HK.03888'],
    '医药生物': ['HK.06160', 'HK.02269', 'HK.02359', 'HK.01093', 'HK.01177', 'HK.02607'],
    '消费': ['HK.01929', 'HK.09633', 'HK.02331', 'HK.09992', 'HK.01810', 'HK.09869'],
    '光伏': ['HK.03800', 'HK.00968', 'HK.06865', 'HK.00451'],
    '锂电池': ['HK.01772', 'HK.02460', 'HK.03931'],
    '游戏': ['HK.01024', 'HK.09999', 'HK.00285'],
    '地产': ['HK.02007', 'HK.01109', 'HK.01093'],
    '券商': ['HK.06098', 'HK.06066', 'HK.03908'],
}

OUTPUT_FILE = '/Users/mantou/.n8n-files/hk_signals.json'


def calc_rsi_simple(closes):
    if len(closes) < 15:
        return 50
    period = 14
    gains = losses = 0
    for i in range(len(closes) - period, len(closes)):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_bollinger_simple(closes):
    if len(closes) < 20:
        return None
    period = 20
    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum([(x - middle) ** 2 for x in recent]) / period
    std = variance ** 0.5
    upper = middle + 2 * std
    lower = middle - 2 * std
    current = closes[-1]
    return {
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "current": current,
        "position_pct": round((current - lower) / (upper - lower) * 100, 1) if upper > lower else 50,
    }


def generate_signal(stock_data, klines_data):
    closes = klines_data["closes"]
    volumes = klines_data["volumes"]

    rsi = calc_rsi_simple(closes)
    bollinger = calc_bollinger_simple(closes)

    if not bollinger:
        return None

    avg_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
    vol_ratio = stock_data["volume"] / avg_vol if avg_vol > 0 else 1.0

    signal = None
    position = bollinger["position_pct"]

    if (rsi < 40 and position < 30 and vol_ratio > 1.2 and stock_data["changePct"] > 0):
        current_price = stock_data["price"]
        stop_loss = round(current_price * 0.95, 2)
        target1 = round(current_price * 1.03, 2)
        target2 = round(current_price * 1.05, 2)

        if position > 50:
            target1 = round(current_price * 1.02, 2)
            target2 = round(current_price * 1.03, 2)

        signal = {
            "type": "买入",
            "strength": "强" if (rsi < 30 and position < 20) else "中",
            "rsi": rsi,
            "bollinger_position": position,
            "vol_ratio": round(vol_ratio, 2),
            "entry_price": current_price,
            "stop_loss": stop_loss,
            "target1": target1,
            "target2": target2,
            "suggested_position": "20%" if rsi < 30 else "10-15%",
            "note": "已突破布林带，谨慎追高" if position > 100 else "",
        }
    elif (rsi > 70 and position > 70):
        signal = {
            "type": "卖出",
            "strength": "强" if rsi > 80 else "中",
            "rsi": rsi,
            "bollinger_position": position,
            "reason": "超买+高位",
        }

    return signal


def main():
    if not FUTU_AVAILABLE:
        result = {
            "error": "futu-api not installed",
            "signals": [],
            "buy_signals": 0,
            "sell_signals": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return

    ctx = None
    signals = []

    try:
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        for sector, codes in SECTORS.items():
            for code in codes:
                try:
                    ret, snapshot = ctx.get_market_snapshot([code])
                    if ret != RET_OK or snapshot is None or len(snapshot) == 0:
                        continue

                    s = snapshot.iloc[0]
                    prev_close = float(s.get("prev_close_price", 0))
                    price = float(s.get("last_price", 0))

                    if prev_close <= 0 or price <= 0:
                        continue

                    stock_data = {
                        "code": code.replace("HK.", ""),
                        "name": s.get("name", ""),
                        "sector": sector,
                        "price": price,
                        "changePct": round((price - prev_close) / prev_close * 100, 2),
                        "volume": int(s.get("volume", 0)),
                        "turnover": float(s.get("turnover", 0)),
                    }

                    ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=30)
                    if ret_k != RET_OK or klines is None or len(klines) == 0:
                        continue

                    klines_data = {
                        "closes": klines["close"].tolist(),
                        "volumes": klines["volume"].tolist(),
                    }

                    signal = generate_signal(stock_data, klines_data)

                    if signal:
                        signals.append({
                            **stock_data,
                            "signal": signal,
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        })

                except Exception as e:
                    continue

    except Exception as e:
        result = {
            "error": str(e),
            "signals": signals,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return
    finally:
        if ctx:
            ctx.close()

    signals.sort(key=lambda x: (
        2 if x["signal"]["strength"] == "强" else
        (1 if x["signal"]["strength"] == "中" else 0)
    ), reverse=True)

    result = {
        "signals": signals,
        "count": len(signals),
        "buy_signals": len([s for s in signals if s["signal"]["type"] == "买入"]),
        "sell_signals": len([s for s in signals if s["signal"]["type"] == "卖出"]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # 写入文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✅ 信号已保存到: {OUTPUT_FILE}")
    print(f"📊 信号数: {result['count']}, 买入: {result['buy_signals']}, 卖出: {result['sell_signals']}")


if __name__ == "__main__":
    main()
