#!/usr/bin/env python3
"""
港股实时信号API服务
提供HTTP接口供n8n调用
"""
from flask import Flask, jsonify
from flask_cors import CORS
import sys
import os
from datetime import datetime
from typing import List, Dict

# Suppress stdout
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, KLType, RET_OK
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

# Restore stdout for Flask
os.dup2(_stdout_fd, 1)

app = Flask(__name__)
CORS(app)

# 港股板块配置
SECTORS = {
    '商业航天': ['HK.01045', 'HK.00031'],
    'AI科技': ['HK.00020', 'HK.09888', 'HK.01024'],
    '新能源汽车': ['HK.09866', 'HK.02015', 'HK.01211', 'HK.00175', 'HK.09868'],
    '半导体': ['HK.00981', 'HK.01347'],
    '互联网': ['HK.00700', 'HK.09988', 'HK.09618', 'HK.03690', 'HK.09999'],
    '医药生物': ['HK.06160', 'HK.02269', 'HK.02359'],
    '消费': ['HK.01929', 'HK.09633', 'HK.02331', 'HK.09992'],
    '光伏': ['HK.03800', 'HK.00968', 'HK.06865'],
}


def calc_rsi_simple(closes):
    """计算RSI"""
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
    """计算布林带"""
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
    """生成交易信号"""
    closes = klines_data["closes"]
    volumes = klines_data["volumes"]

    rsi = calc_rsi_simple(closes)
    bollinger = calc_bollinger_simple(closes)

    if not bollinger:
        return None

    # 计算量比
    avg_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
    vol_ratio = stock_data["volume"] / avg_vol if avg_vol > 0 else 1.0

    signal = None
    position = bollinger["position_pct"]

    # 买入信号
    if (rsi < 40 and position < 30 and vol_ratio > 1.2 and stock_data["changePct"] > 0):
        current_price = stock_data["price"]

        # 使用百分比目标
        stop_loss = round(current_price * 0.95, 2)  # -5%
        target1 = round(current_price * 1.03, 2)    # +3% (日内目标)
        target2 = round(current_price * 1.05, 2)    # +5% (激进目标)

        if position > 50:
            target1 = round(current_price * 1.02, 2)  # +2%
            target2 = round(current_price * 1.03, 2)  # +3%

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

    # 卖出信号
    elif (rsi > 70 and position > 70):
        signal = {
            "type": "卖出",
            "strength": "强" if rsi > 80 else "中",
            "rsi": rsi,
            "bollinger_position": position,
            "reason": "超买+高位",
        }

    return signal


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "ok",
        "futu_available": FUTU_AVAILABLE,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })


@app.route('/get_signals', methods=['GET'])
def get_signals():
    """获取交易信号"""
    if not FUTU_AVAILABLE:
        return jsonify({
            "error": "futu-api not installed",
            "signals": [],
            "buy_signals": 0,
            "sell_signals": 0,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

    ctx = None
    signals = []

    try:
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 遍历所有板块的股票
        for sector, codes in SECTORS.items():
            for code in codes:
                try:
                    # 获取实时行情
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

                    # 获取K线
                    ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=30)
                    if ret_k != RET_OK or klines is None or len(klines) == 0:
                        continue

                    klines_data = {
                        "closes": klines["close"].tolist(),
                        "volumes": klines["volume"].tolist(),
                    }

                    # 生成信号
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
        return jsonify({
            "error": str(e),
            "signals": signals,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500
    finally:
        if ctx:
            ctx.close()

    # 按信号强度排序
    signals.sort(key=lambda x: (
        2 if x["signal"]["strength"] == "强" else
        (1 if x["signal"]["strength"] == "中" else 0)
    ), reverse=True)

    # 输出
    return jsonify({
        "signals": signals,
        "count": len(signals),
        "buy_signals": len([s for s in signals if s["signal"]["type"] == "买入"]),
        "sell_signals": len([s for s in signals if s["signal"]["type"] == "卖出"]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


if __name__ == "__main__":
    print("🚀 港股信号API服务启动...")
    print("📡 监听地址: http://localhost:5001")
    print("🔍 健康检查: http://localhost:5001/health")
    print("📊 获取信号: http://localhost:5001/get_signals")
    app.run(host="0.0.0.0", port=5001, debug=False)
