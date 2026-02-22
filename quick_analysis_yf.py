#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速分析指定股票的买入时机和价格
结合技术指标和hk-stock-daily-profit技能
使用YFinance数据源
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from datetime import datetime
import pandas as pd
import numpy as np

def calculate_ema(prices, period):
    """计算EMA"""
    return prices.ewm(span=period, adjust=False).mean()

def calculate_rsi(prices, period=14):
    """计算RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(high, low, close, period=14):
    """计算ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def analyze_stock(provider, code):
    """分析单只股票"""
    print(f"\n{'='*70}")
    print(f"📊 分析 {code}")
    print(f"{'='*70}")

    try:
        # 获取当前价格
        current_price = provider.get_current_price(code)
        if current_price is None or current_price <= 0:
            print(f"❌ 无法获取有效价格")
            return None

        print(f"\n💲 当前价格: {current_price:.2f} HKD")

        # 获取历史数据（60天）
        history_dict = provider.get_price_data(code, days=60)
        if history_dict is None or len(history_dict.get('close', [])) < 50:
            print(f"❌ 历史数据不足")
            return None

        # 转换为Series
        closes = pd.Series(history_dict['close'])
        highs = pd.Series(history_dict['high'])
        lows = pd.Series(history_dict['low'])

        # 计算今日涨跌
        if len(closes) >= 2:
            yesterday_close = closes.iloc[-2]
            change_rate = (current_price - yesterday_close) / yesterday_close * 100
            print(f"📈 今日涨跌: {change_rate:+.2f}%")

        ema20 = calculate_ema(closes, 20).iloc[-1]
        ema50 = calculate_ema(closes, 50).iloc[-1]
        rsi14 = calculate_rsi(closes, 14).iloc[-1]
        atr14 = calculate_atr(highs, lows, closes, 14).iloc[-1]

        print(f"\n📈 技术指标:")
        print(f"   EMA20: {ema20:.2f}")
        print(f"   EMA50: {ema50:.2f}")
        print(f"   RSI14: {rsi14:.1f}")
        print(f"   ATR14: {atr14:.2f}")

        # 趋势判断
        print(f"\n🎯 技术分析:")

        # 1. 趋势方向
        if ema20 > ema50:
            trend = "上升趋势 ✅"
            trend_signal = 1
        else:
            trend = "下降趋势 ⚠️"
            trend_signal = -1
        print(f"   趋势: {trend}")

        # 2. RSI状态
        if rsi14 < 30:
            rsi_status = "超卖 🟢 (抄底机会)"
            rsi_signal = 2
        elif rsi14 > 70:
            rsi_status = "超买 🔴 (谨慎追高)"
            rsi_signal = -2
        elif rsi14 < 50:
            rsi_status = "偏弱"
            rsi_signal = 0
        else:
            rsi_status = "偏强"
            rsi_signal = 1
        print(f"   RSI: {rsi_status}")

        # 3. 价格相对均线位置
        price_vs_ema20 = (current_price - ema20) / ema20 * 100
        if price_vs_ema20 > 3:
            position = "远高于均线 ⚠️ (可能回调)"
        elif price_vs_ema20 > 0:
            position = "略高于均线"
        elif price_vs_ema20 > -3:
            position = "略低于均线 🟢 (接近支撑)"
        else:
            position = "远低于均线 🟢 (支撑位)"
        print(f"   位置: {position} ({price_vs_ema20:+.1f}%)")

        # 买点判断（基于Larry Williams三步骤）
        print(f"\n🎯 买点分析 (基于hk-stock-daily-profit技能):")

        signals = []

        # 买点1: 跌破均线后反弹
        if current_price < ema20 and len(closes) >= 2:
            yesterday_close = closes.iloc[-2]
            if current_price > yesterday_close:
                signals.append("✅ 买点1: 跌破均线后反弹")

        # 买点2: 突破重要阻力位（EMA20）
        if current_price > ema20 and price_vs_ema20 < 2 and trend_signal > 0:
            signals.append("✅ 买点2: 突破均线，趋势向上")

        # 买点3: RSI超卖反弹
        if rsi14 < 35:
            signals.append("✅ 买点3: RSI超卖，反弹机会")

        # 买点4: 大阳线突破
        if len(closes) >= 2:
            yesterday_close = closes.iloc[-2]
            change_rate = (current_price - yesterday_close) / yesterday_close * 100
            if change_rate > 5:
                signals.append("✅ 买点4: 大阳线突破")

        if signals:
            for sig in signals:
                print(f"   {sig}")
        else:
            print(f"   ⚠️ 当前无明确买点信号")

        # 建议买入价格（基于技能的ATR缓冲法）
        print(f"\n💰 建议买入价格:")

        # 基准价：当前价或EMA20（取较低者）
        base_price = min(current_price, ema20)

        # 使用0.5倍ATR作为缓冲
        atr_buffer = atr14 * 0.5
        entry_price = base_price - atr_buffer

        # 折扣率
        discount = (current_price - entry_price) / current_price * 100

        print(f"   推荐价格: {entry_price:.2f} HKD")
        print(f"   当前折扣: {discount:.1f}%")

        if entry_price >= current_price * 0.98:
            print(f"   ✅ 可以当前价附近买入")
            buy_now = True
        else:
            print(f"   ⏳ 建议等待回调至 {entry_price:.2f} 附近")
            buy_now = False

        # 止损位和目标位
        stop_loss = entry_price * 0.92  # 8%止损
        target1 = entry_price * 1.05    # 5%目标
        target2 = entry_price * 1.07    # 7%目标

        print(f"\n🎯 操作计划:")
        print(f"   买入价: {entry_price:.2f}")
        print(f"   止损价: {stop_loss:.2f} (-8%)")
        print(f"   目标1: {target1:.2f} (+5%)")
        print(f"   目标2: {target2:.2f} (+7%)")

        # 综合评分
        total_signal = trend_signal + rsi_signal + len(signals)

        print(f"\n⭐ 综合评分: ", end="")
        if total_signal >= 3:
            print(f"🟢 强烈推荐 ({total_signal}分)")
            rating = "强烈推荐"
        elif total_signal >= 1:
            print(f"🟡 可以考虑 ({total_signal}分)")
            rating = "可以考虑"
        else:
            print(f"🔴 暂不推荐 ({total_signal}分)")
            rating = "暂不推荐"

        # 仓位建议
        print(f"\n💼 仓位建议 (5万本金):")
        position_size = 35000  # 70%仓位
        shares = int(position_size / entry_price / 100) * 100  # 港股100股一手
        actual_cost = shares * entry_price

        print(f"   建议仓位: 70% (3.5万)")
        print(f"   买入股数: {shares} 股 ({shares/100:.0f}手)")
        print(f"   实际成本: {actual_cost:.0f} HKD")

        return {
            'code': code,
            'price': current_price,
            'entry': entry_price,
            'signal': total_signal,
            'rating': rating,
            'buy_now': buy_now,
            'stop_loss': stop_loss,
            'target1': target1,
            'target2': target2
        }

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """主函数"""
    # 默认股票池
    stocks = [
        ('0700.HK', '腾讯控股'),
        ('1024.HK', '快手科技'),
        ('1810.HK', '小米集团'),
    ]

    # 如果命令行有参数，使用命令行参数
    if len(sys.argv) > 1:
        custom_stocks = []
        for arg in sys.argv[1:]:
            if not arg.endswith('.HK'):
                arg = arg + '.HK'
            custom_stocks.append((arg, arg))
        stocks = custom_stocks

    provider = YFinanceProvider()

    print("✅ 使用 YFinance 数据源")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []
    for code, name in stocks:
        try:
            result = analyze_stock(provider, code)
            if result:
                result['name'] = name
                results.append(result)
        except Exception as e:
            print(f"❌ 分析{code}失败: {e}")
            continue

    # 按评分排序
    if results:
        print(f"\n{'='*70}")
        print(f"📊 今日推荐排序 (按综合评分)")
        print(f"{'='*70}")

        results.sort(key=lambda x: x['signal'], reverse=True)

        for i, r in enumerate(results, 1):
            stars = "🟢" if r['signal'] >= 3 else "🟡" if r['signal'] >= 1 else "🔴"
            action = "立即买入" if r['buy_now'] else "等待回调"
            print(f"\n{i}. {stars} {r['name']} ({r['code']}) - {r['rating']}")
            print(f"   当前价: {r['price']:.2f} | 建议买入: {r['entry']:.2f} | 评分: {r['signal']}")
            print(f"   操作: {action} | 止损: {r['stop_loss']:.2f} | 目标: {r['target1']:.2f}-{r['target2']:.2f}")

        print(f"\n{'='*70}")
        print(f"💡 提示: 基于hk-stock-daily-profit技能的Larry Williams三步骤")
        print(f"⚠️ 风险提醒: 单日最大亏损不超过2000元，严格止损！")
        print(f"{'='*70}")

if __name__ == '__main__':
    main()
