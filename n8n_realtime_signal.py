#!/usr/bin/env python3
"""
港股实时交易信号系统
实时监控 + 有信号就推送

推送内容：
- 板块
- 股票名称+代码
- 当前位置（价格+技术指标）
- 买入/卖出建议
- 仓位建议
- 止损/目标点位
"""
import json
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


def _output_json(data):
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# 港股板块配置（扩展版）
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


# ==================== 简化的技术指标 ====================
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


# ==================== 信号生成 ====================
def generate_signal(stock_data, klines_data):
    """
    生成交易信号

    买入信号：
    1. RSI < 40 (超卖)
    2. 价格靠近布林下轨 (position < 30%)
    3. 放量 (量比 > 1.2)
    4. 今日上涨 (changePct > 0)

    卖出信号：
    1. RSI > 70 (超买)
    2. 价格靠近布林上轨 (position > 70%)
    """
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

        # 日内T+0目标（用百分比，而不是布林带）
        stop_loss = round(current_price * 0.95, 2)  # -5%
        target1 = round(current_price * 1.03, 2)    # +3% (日内目标)
        target2 = round(current_price * 1.05, 2)    # +5% (激进目标)

        # 如果价格已经在布林带中轨以上，降低目标期望
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

    # 观望（接近买点）
    elif (35 < rsi < 45 and 25 < position < 35):
        signal = {
            "type": "观望（接近买点）",
            "strength": "弱",
            "rsi": rsi,
            "bollinger_position": position,
            "note": "等待进一步回调",
        }

    return signal


# ==================== 主函数 ====================
def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "signals": []})
        return

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
        _output_json({
            "error": str(e),
            "signals": signals,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return
    finally:
        if ctx:
            ctx.close()

    # 按信号强度排序
    signals.sort(key=lambda x: (
        2 if x["signal"]["strength"] == "强" else
        (1 if x["signal"]["strength"] == "中" else 0)
    ), reverse=True)

    # 输出
    output = {
        "signals": signals,
        "count": len(signals),
        "buy_signals": len([s for s in signals if s["signal"]["type"] == "买入"]),
        "sell_signals": len([s for s in signals if s["signal"]["type"] == "卖出"]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    _output_json(output)


if __name__ == "__main__":
    main()
