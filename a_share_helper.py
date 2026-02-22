#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股行情查询助手
使用 AKShare 获取沪深股票数据

用法:
    python a_share_helper.py 002400        # 查询省广集团
    python a_share_helper.py 600519        # 查询贵州茅台
    python a_share_helper.py 002400 full   # 完整分析
"""

import sys
import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def get_realtime_quote(code: str):
    """获取单只股票实时行情 - 使用更快的接口"""
    try:
        # 使用东方财富单股接口，更快
        df = ak.stock_individual_info_em(symbol=code)
        info = dict(zip(df['item'], df['value']))

        # 获取实时价格
        df2 = ak.stock_bid_ask_em(symbol=code)

        return info, df2
    except Exception as e:
        # 备用方案：使用新浪接口
        try:
            # 判断市场
            if code.startswith('6'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'

            df = ak.stock_zh_a_spot_em()
            stock = df[df['代码'] == code]
            if len(stock) > 0:
                return stock.iloc[0].to_dict(), None
        except:
            pass
        print(f"获取行情失败: {e}")
        return None, None

def get_kline(code: str, days: int = 60):
    """获取K线数据"""
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        return df.tail(days)
    except Exception as e:
        print(f"获取K线失败: {e}")
        return None

def calc_rsi(prices, period=14):
    """计算RSI"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock(code: str, full: bool = False):
    """分析股票"""
    print("="*75)
    print(f"📊 A股分析: {code}")
    print("="*75)

    # 先获取K线（这个比较稳定）
    print("正在获取数据...")
    kline = get_kline(code, 60)

    if kline is None or len(kline) == 0:
        print(f"❌ 获取K线数据失败，请检查股票代码 {code}")
        return

    # 从K线获取基本信息
    latest = kline.iloc[-1]
    price = latest['收盘']
    open_price = latest['开盘']
    high = latest['最高']
    low = latest['最低']
    volume = latest['成交量']
    turnover = latest['成交额']
    date = latest['日期']

    # 计算涨跌
    if len(kline) >= 2:
        prev_close = kline.iloc[-2]['收盘']
        change_pct = ((price / prev_close) - 1) * 100
        change_val = price - prev_close
    else:
        prev_close = open_price
        change_pct = 0
        change_val = 0

    print(f"\n【{code}】 数据日期: {date}")

    print(f"\n💰 最新行情:")
    print(f"   收盘价: {price:.2f} 元")
    print(f"   涨跌: {change_val:+.2f} ({change_pct:+.2f}%)")
    print(f"   开盘: {open_price:.2f} | 昨收: {prev_close:.2f}")
    print(f"   最高: {high:.2f} | 最低: {low:.2f}")
    print(f"   成交额: {turnover/100000000:.2f}亿")

    # 技术分析
    closes = kline['收盘']
    highs = kline['最高']
    lows = kline['最低']
    volumes = kline['成交量']

    # 均线
    ma5 = closes.tail(5).mean()
    ma10 = closes.tail(10).mean()
    ma20 = closes.tail(20).mean()
    ma60 = closes.mean()

    print(f"\n📈 均线分析:")
    print(f"   MA5:  {ma5:.2f} {'✅' if price > ma5 else '❌'}")
    print(f"   MA10: {ma10:.2f} {'✅' if price > ma10 else '❌'}")
    print(f"   MA20: {ma20:.2f} {'✅' if price > ma20 else '❌'}")
    print(f"   MA60: {ma60:.2f} {'✅' if price > ma60 else '❌'}")

    if ma5 > ma10 > ma20:
        ma_status = "✅ 多头排列"
    elif ma5 < ma10 < ma20:
        ma_status = "❌ 空头排列"
    else:
        ma_status = "🟡 交织"
    print(f"   均线状态: {ma_status}")

    # VWAP
    kline20 = kline.tail(20)
    if kline20['成交量'].sum() > 0:
        vwap = (kline20['收盘'] * kline20['成交量']).sum() / kline20['成交量'].sum()
        vs_vwap = ((price / vwap) - 1) * 100
        print(f"\n📊 VWAP成本分析:")
        print(f"   20日VWAP: {vwap:.2f}")
        print(f"   现价vs成本: {vs_vwap:+.1f}%", end="")
        if vs_vwap < -10:
            print(" ✅ 远低于成本")
        elif vs_vwap < 0:
            print(" ✅ 低于成本")
        elif vs_vwap > 30:
            print(" ⚠️ 远高于成本")
        elif vs_vwap > 15:
            print(" ⚠️ 高于成本")
        else:
            print(" 🟡 接近成本")
    else:
        vwap = price
        vs_vwap = 0

    # RSI
    rsi6 = calc_rsi(closes, 6).iloc[-1]
    rsi14 = calc_rsi(closes, 14).iloc[-1]
    print(f"\n📉 RSI指标:")
    print(f"   RSI(6):  {rsi6:.1f}")
    print(f"   RSI(14): {rsi14:.1f}", end="")
    if rsi14 > 80:
        print(" 🔴 严重超买")
    elif rsi14 > 70:
        print(" ⚠️ 超买")
    elif rsi14 < 20:
        print(" ✅ 严重超卖")
    elif rsi14 < 30:
        print(" ✅ 超卖")
    else:
        print(" 中性")

    # MACD
    ema12 = closes.ewm(span=12).mean()
    ema26 = closes.ewm(span=26).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9).mean()
    macd = (dif - dea) * 2

    print(f"\n📊 MACD指标:")
    print(f"   DIF: {dif.iloc[-1]:.3f}")
    print(f"   DEA: {dea.iloc[-1]:.3f}")
    print(f"   MACD: {macd.iloc[-1]:.3f}")
    if dif.iloc[-1] > dea.iloc[-1] and dif.iloc[-2] <= dea.iloc[-2]:
        print(f"   状态: ✅ 金叉!")
    elif dif.iloc[-1] < dea.iloc[-1] and dif.iloc[-2] >= dea.iloc[-2]:
        print(f"   状态: ❌ 死叉!")
    elif dif.iloc[-1] > dea.iloc[-1]:
        print(f"   状态: 🔴 多头")
    else:
        print(f"   状态: 🟢 空头")

    # KDJ
    low_min = lows.rolling(9).min()
    high_max = highs.rolling(9).max()
    rsv = (closes - low_min) / (high_max - low_min) * 100
    k = rsv.ewm(com=2).mean()
    d = k.ewm(com=2).mean()
    j = 3 * k - 2 * d

    print(f"\n📊 KDJ指标:")
    print(f"   K: {k.iloc[-1]:.1f} | D: {d.iloc[-1]:.1f} | J: {j.iloc[-1]:.1f}")
    if k.iloc[-1] > 80 and d.iloc[-1] > 80:
        print(f"   状态: ⚠️ 超买区")
    elif k.iloc[-1] < 20 and d.iloc[-1] < 20:
        print(f"   状态: ✅ 超卖区")
    else:
        print(f"   状态: 中性")

    # 布林带
    ma20_bb = closes.rolling(20).mean()
    std20 = closes.rolling(20).std()
    upper = ma20_bb + 2 * std20
    lower = ma20_bb - 2 * std20

    print(f"\n📊 布林带:")
    print(f"   上轨: {upper.iloc[-1]:.2f}")
    print(f"   中轨: {ma20_bb.iloc[-1]:.2f}")
    print(f"   下轨: {lower.iloc[-1]:.2f}")
    if price > upper.iloc[-1]:
        print(f"   状态: ⚠️ 突破上轨")
    elif price < lower.iloc[-1]:
        print(f"   状态: ✅ 跌破下轨(超卖)")
    else:
        print(f"   状态: 轨道内运行")

    # 涨跌幅统计
    print(f"\n📆 区间涨跌幅:")
    if len(kline) >= 6:
        change_5d = ((price / closes.iloc[-6]) - 1) * 100
        print(f"   5日: {change_5d:+.2f}%")
    if len(kline) >= 11:
        change_10d = ((price / closes.iloc[-11]) - 1) * 100
        print(f"   10日: {change_10d:+.2f}%")
    if len(kline) >= 21:
        change_20d = ((price / closes.iloc[-21]) - 1) * 100
        print(f"   20日: {change_20d:+.2f}%")

    # 关键价位
    high_5d = highs.tail(5).max()
    low_5d = lows.tail(5).min()
    high_20d = highs.tail(20).max()
    low_20d = lows.tail(20).min()

    print(f"\n📍 关键价位:")
    print(f"   压力位1: {high_5d:.2f} (5日高)")
    print(f"   压力位2: {high_20d:.2f} (20日高)")
    print(f"   ─────── 现价: {price:.2f} ───────")
    print(f"   支撑位1: {low_5d:.2f} (5日低)")
    print(f"   支撑位2: {low_20d:.2f} (20日低)")
    print(f"   止损参考: {ma20:.2f} (MA20)")

    if full:
        # 近期K线明细
        print(f"\n📉 近10日K线明细:")
        print(f"{'日期':<12} {'开盘':>8} {'最高':>8} {'最低':>8} {'收盘':>8} {'涨跌%':>8} {'成交额':>10}")
        print("-"*72)
        recent = kline.tail(10)
        for i, (_, row) in enumerate(recent.iterrows()):
            if i == 0:
                chg = 0
            else:
                prev = recent.iloc[i-1]['收盘']
                chg = ((row['收盘'] / prev) - 1) * 100
            mark = "🔴" if row['收盘'] > row['开盘'] else "🟢"
            print(f"{row['日期']:<12} {row['开盘']:>8.2f} {row['最高']:>8.2f} {row['最低']:>8.2f} {row['收盘']:>8.2f} {chg:>+7.2f}% {row['成交额']/100000000:>9.2f}亿 {mark}")

    # 综合评估
    print("\n" + "="*75)
    print("🎯 综合评估")
    print("="*75)

    score = 0
    signals = []

    # 均线
    if price > ma5:
        score += 1
        signals.append("✅ 站上MA5")
    else:
        signals.append("❌ 跌破MA5")

    if price > ma20:
        score += 1
        signals.append("✅ 站上MA20")
    else:
        signals.append("❌ 跌破MA20")

    # VWAP
    if vs_vwap < -10:
        score += 2
        signals.append(f"✅✅ 低于成本{abs(vs_vwap):.1f}%")
    elif vs_vwap < 0:
        score += 1
        signals.append(f"✅ 低于成本")
    elif vs_vwap > 30:
        score -= 1
        signals.append(f"⚠️ 远高于成本{vs_vwap:.1f}%")
    elif vs_vwap > 15:
        signals.append(f"🟡 高于成本{vs_vwap:.1f}%")

    # RSI
    if rsi14 < 30:
        score += 2
        signals.append(f"✅✅ RSI超卖({rsi14:.1f})")
    elif rsi14 < 50:
        score += 1
    elif rsi14 > 70:
        score -= 1
        signals.append(f"⚠️ RSI超买({rsi14:.1f})")

    # MACD
    if dif.iloc[-1] > dea.iloc[-1]:
        score += 1
        signals.append("✅ MACD多头")
    else:
        signals.append("❌ MACD空头")

    # 均线排列
    if ma5 > ma10 > ma20:
        score += 1
        signals.append("✅ 均线多头排列")
    elif ma5 < ma10 < ma20:
        score -= 1
        signals.append("❌ 均线空头排列")

    # 布林带
    if price < lower.iloc[-1]:
        score += 1
        signals.append("✅ 跌破布林下轨(超卖)")

    print(f"\n信号汇总:")
    for s in signals:
        print(f"   {s}")

    print(f"\n综合评分: {score}/10")
    if score >= 5:
        print("建议: 🟢 可以买入")
        print(f"   买入区间: {low_5d:.2f} - {price:.2f}")
        print(f"   止损: {min(low_20d, ma20):.2f}")
        print(f"   目标: {high_20d:.2f}")
    elif score >= 2:
        print("建议: 🟡 可小仓位参与")
        print(f"   止损: {ma20:.2f}")
    elif score >= 0:
        print("建议: 🟡 观望为主")
    else:
        print("建议: 🔴 不建议买入")

    print("\n" + "="*75)

def main():
    if len(sys.argv) < 2:
        print("="*60)
        print("A股行情查询助手")
        print("="*60)
        print("\n用法:")
        print("  python a_share_helper.py <股票代码>")
        print("  python a_share_helper.py <股票代码> full")
        print("\n例如:")
        print("  python a_share_helper.py 002400      # 省广集团")
        print("  python a_share_helper.py 600519 full # 贵州茅台(完整)")
        print("  python a_share_helper.py 000001      # 平安银行")
        return

    code = sys.argv[1]
    full = len(sys.argv) > 2 and sys.argv[2] == 'full'

    analyze_stock(code, full)

if __name__ == "__main__":
    main()
