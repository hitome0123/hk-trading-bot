#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
港股T+0交易大师策略系统

整合四位交易大师方法论:
- Mark Minervini: SEPA趋势模板 (选股筛选)
- Jesse Livermore: 关键点交易法 (支撑阻力)
- Larry Williams: 波动率突破 (入场信号)
- Victor Sperandeo: 123反转法则 (趋势反转)

目标: 5万HKD本金，日赚300元 (0.6%/日)

用法:
    python master_strategy.py 09988           # 分析单只股票
    python master_strategy.py scan            # 扫描推荐股票
    python master_strategy.py portfolio       # 分析持仓
"""

import sys
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# 尝试导入futu
try:
    from futu import *
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    print("警告: futu-api未安装，部分功能不可用")


def get_kline_futu(code, days=200):
    """从富途获取K线数据"""
    if not FUTU_AVAILABLE:
        return None
    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data, _ = quote_ctx.request_history_kline(
            code,
            start=None,
            end=None,
            max_count=days,
            ktype=KLType.K_DAY
        )
        quote_ctx.close()
        if ret == RET_OK:
            return data
    except Exception as e:
        print(f"获取K线失败: {e}")
    return None


def calculate_vwap(kline, days=20):
    """计算VWAP"""
    if kline is None or len(kline) < days:
        return None
    recent = kline.tail(days)
    typical_price = (recent['high'] + recent['low'] + recent['close']) / 3
    vwap = (typical_price * recent['volume']).sum() / recent['volume'].sum()
    return vwap


# =============================================================================
# Mark Minervini - SEPA趋势模板
# =============================================================================

def minervini_filter(kline):
    """
    Minervini趋势模板筛选
    返回: (通过条件数, 条件详情列表)
    """
    if kline is None or len(kline) < 200:
        return 0, ["❌ K线数据不足200天"]

    close = kline['close'].iloc[-1]
    high_col = 'high'
    low_col = 'low'

    # 计算均线
    ma50 = kline['close'].tail(50).mean()
    ma150 = kline['close'].tail(150).mean()
    ma200 = kline['close'].mean()

    # 52周高低点
    high_52w = kline[high_col].tail(252).max() if len(kline) >= 252 else kline[high_col].max()
    low_52w = kline[low_col].tail(252).min() if len(kline) >= 252 else kline[low_col].min()

    # MA200趋势（对比20天前）
    ma200_20ago = kline['close'].iloc[-220:-200].mean() if len(kline) >= 220 else ma200

    conditions = []
    passed = 0

    # 条件1: 现价 > MA50
    if close > ma50:
        conditions.append(f"✅ 现价({close:.2f}) > MA50({ma50:.2f})")
        passed += 1
    else:
        conditions.append(f"❌ 现价({close:.2f}) < MA50({ma50:.2f})")

    # 条件2: 现价 > MA150
    if close > ma150:
        conditions.append(f"✅ 现价 > MA150({ma150:.2f})")
        passed += 1
    else:
        conditions.append(f"❌ 现价 < MA150({ma150:.2f})")

    # 条件3: 现价 > MA200
    if close > ma200:
        conditions.append(f"✅ 现价 > MA200({ma200:.2f})")
        passed += 1
    else:
        conditions.append(f"❌ 现价 < MA200({ma200:.2f})")

    # 条件4: MA50 > MA150 > MA200
    if ma50 > ma150 > ma200:
        conditions.append("✅ 均线多头排列 MA50>MA150>MA200")
        passed += 1
    else:
        conditions.append("❌ 均线未呈多头排列")

    # 条件5: MA200上升趋势
    if ma200 > ma200_20ago:
        conditions.append("✅ MA200上升趋势")
        passed += 1
    else:
        conditions.append("❌ MA200未上升")

    # 条件6: 现价在52周高点25%范围内
    threshold_high = high_52w * 0.75
    if close >= threshold_high:
        pct_from_high = (1 - close/high_52w) * 100
        conditions.append(f"✅ 距52周高点{pct_from_high:.1f}% (阈值25%)")
        passed += 1
    else:
        pct_from_high = (1 - close/high_52w) * 100
        conditions.append(f"❌ 距52周高点{pct_from_high:.1f}% (需<25%)")

    # 条件7: 现价高于52周低点30%
    threshold_low = low_52w * 1.30
    if close >= threshold_low:
        pct_from_low = (close/low_52w - 1) * 100
        conditions.append(f"✅ 高于52周低点{pct_from_low:.1f}% (需>30%)")
        passed += 1
    else:
        pct_from_low = (close/low_52w - 1) * 100
        conditions.append(f"❌ 高于52周低点{pct_from_low:.1f}% (需>30%)")

    return passed, conditions


# =============================================================================
# Jesse Livermore - 关键点交易法
# =============================================================================

def livermore_pivot_points(kline):
    """
    计算Livermore风格的关键价位
    """
    if kline is None or len(kline) < 20:
        return None

    # 近期高低点
    high_5d = kline['high'].tail(5).max()
    low_5d = kline['low'].tail(5).min()
    high_20d = kline['high'].tail(20).max()
    low_20d = kline['low'].tail(20).min()

    # 前高前低（用于突破判断）
    prev_high = kline['high'].iloc[-10:-5].max()
    prev_low = kline['low'].iloc[-10:-5].min()

    return {
        'resistance_1': high_5d,
        'resistance_2': high_20d,
        'support_1': low_5d,
        'support_2': low_20d,
        'breakout_buy': high_20d * 1.01,
        'breakdown_sell': low_20d * 0.99,
        'prev_high': prev_high,
        'prev_low': prev_low
    }


def livermore_analysis(kline):
    """
    Livermore关键位分析
    """
    pivots = livermore_pivot_points(kline)
    if pivots is None:
        return 0, ["❌ 数据不足"]

    current = kline['close'].iloc[-1]
    score = 0
    signals = []

    # 分析当前价格位置
    if current <= pivots['support_1'] * 1.02:
        score += 20
        signals.append(f"✅ 接近支撑位1: {pivots['support_1']:.2f}")
    elif current <= pivots['support_2'] * 1.02:
        score += 15
        signals.append(f"✅ 接近支撑位2: {pivots['support_2']:.2f}")

    if current >= pivots['resistance_1'] * 0.98:
        signals.append(f"⚠️ 接近阻力位1: {pivots['resistance_1']:.2f}")
    elif current >= pivots['resistance_2'] * 0.98:
        signals.append(f"⚠️ 接近阻力位2: {pivots['resistance_2']:.2f}")

    # 突破判断
    if current > pivots['prev_high']:
        score += 15
        signals.append(f"✅ 突破前高: {pivots['prev_high']:.2f}")

    # 关键价位输出
    signals.append(f"📍 阻力位: {pivots['resistance_1']:.2f} / {pivots['resistance_2']:.2f}")
    signals.append(f"📍 支撑位: {pivots['support_1']:.2f} / {pivots['support_2']:.2f}")

    return score, signals


# =============================================================================
# Larry Williams - 波动率突破
# =============================================================================

def williams_breakout_signal(kline):
    """
    Larry Williams波动率突破信号
    返回: (信号类型, 入场价, 止损价, 止盈价, 详情)
    """
    if kline is None or len(kline) < 5:
        return 'HOLD', None, None, None, ["❌ 数据不足"]

    yesterday = kline.iloc[-2]
    today = kline.iloc[-1]

    # 计算ATR（5日平均波动率）
    atr = (kline['high'].tail(5) - kline['low'].tail(5)).mean()
    yesterday_range = yesterday['high'] - yesterday['low']

    # 动态K系数
    if yesterday_range > atr * 1.5:
        K = 0.5  # 高波动
    elif yesterday_range < atr * 0.5:
        K = 0.7  # 低波动
    else:
        K = 0.6  # 正常

    # 计算突破价
    breakout_price = yesterday['close'] + (yesterday_range * K)
    breakdown_price = yesterday['close'] - (yesterday_range * K)

    details = [
        f"📊 昨日振幅: {yesterday_range:.2f}",
        f"📊 5日ATR: {atr:.2f}",
        f"📊 K系数: {K}",
        f"📊 做多突破价: {breakout_price:.2f}",
        f"📊 做空突破价: {breakdown_price:.2f}"
    ]

    # 信号判断
    if today['high'] >= breakout_price and today['close'] > yesterday['close']:
        stop_loss = breakout_price - yesterday_range * 1.5
        take_profit = breakout_price + yesterday_range * 2
        details.append(f"✅ 波动率突破做多信号!")
        return 'BUY', breakout_price, stop_loss, take_profit, details

    elif today['low'] <= breakdown_price and today['close'] < yesterday['close']:
        stop_loss = breakdown_price + yesterday_range * 1.5
        take_profit = breakdown_price - yesterday_range * 2
        details.append(f"❌ 波动率突破做空信号!")
        return 'SELL', breakdown_price, stop_loss, take_profit, details

    else:
        details.append("🟡 暂无突破信号")
        return 'HOLD', None, None, None, details


def williams_analysis(kline):
    """Williams分析返回评分和信号"""
    signal, entry, stop, target, details = williams_breakout_signal(kline)
    score = 0
    if signal == 'BUY':
        score = 25
    elif signal == 'SELL':
        score = -10
    return score, details, signal, entry, stop, target


# =============================================================================
# Victor Sperandeo - 123反转法则
# =============================================================================

def sperandeo_123_reversal(kline):
    """
    Sperandeo 123反转法则检测
    返回: (信号, 详情列表)
    """
    if kline is None or len(kline) < 20:
        return None, ["❌ 数据不足"]

    closes = kline['close'].values
    highs = kline['high'].values
    lows = kline['low'].values

    # 找最近20日的高低点
    recent_highs = highs[-20:]
    recent_lows = lows[-20:]

    high_idx = recent_highs.argmax()
    low_idx = recent_lows.argmin()

    recent_high = recent_highs[high_idx]
    recent_low = recent_lows[low_idx]

    current = closes[-1]
    ma20 = closes[-20:].mean()

    details = [
        f"📊 20日高点: {recent_high:.2f} (第{high_idx+1}天)",
        f"📊 20日低点: {recent_low:.2f} (第{low_idx+1}天)",
        f"📊 MA20: {ma20:.2f}"
    ]

    # 判断趋势方向和反转信号
    if high_idx > low_idx:  # 低点在前，高点在后 = 上升趋势
        details.append("📈 当前趋势: 上升")

        # 检查反转信号 (上升→下降)
        if current < ma20:
            details.append("⚠️ 条件1: 跌破MA20趋势线")

            # 检查是否创新高后回落 (2B信号)
            if highs[-3:].max() >= recent_high * 0.99:
                details.append("⚠️ 条件2: 近期测试前高")

                if current < recent_low:
                    details.append("❌❌ 条件3: 跌破前低 - 123反转卖出!")
                    return 'SELL_REVERSAL', details
                else:
                    details.append("⚠️ 关注是否跌破前低")
                    return 'SELL_WARNING', details

    else:  # 高点在前，低点在后 = 下降趋势
        details.append("📉 当前趋势: 下降")

        # 检查反转信号 (下降→上升)
        if current > ma20:
            details.append("✅ 条件1: 突破MA20趋势线")

            # 检查是否创新低后反弹
            if lows[-3:].min() <= recent_low * 1.01:
                details.append("✅ 条件2: 近期测试前低")

                if current > recent_high:
                    details.append("✅✅ 条件3: 突破前高 - 123反转买入!")
                    return 'BUY_REVERSAL', details
                else:
                    details.append("✅ 关注是否突破前高")
                    return 'BUY_WARNING', details

    details.append("🟡 暂无明确反转信号")
    return None, details


def sperandeo_analysis(kline):
    """Sperandeo分析返回评分和信号"""
    signal, details = sperandeo_123_reversal(kline)
    score = 0
    if signal == 'BUY_REVERSAL':
        score = 20
    elif signal == 'BUY_WARNING':
        score = 10
    elif signal == 'SELL_REVERSAL':
        score = -20
    elif signal == 'SELL_WARNING':
        score = -10
    else:
        score = 15  # 无反转信号是好事
    return score, details, signal


# =============================================================================
# 综合分析系统
# =============================================================================

def master_strategy_analysis(code):
    """
    四大师综合策略分析
    """
    print("=" * 70)
    print(f"📊 港股大师策略分析: {code}")
    print("=" * 70)

    # 获取K线数据
    print("\n正在获取K线数据...")
    kline = get_kline_futu(code)
    if kline is None or len(kline) < 20:
        print(f"❌ 无法获取 {code} 的K线数据")
        return

    current = kline['close'].iloc[-1]
    print(f"\n当前价格: {current:.2f}")

    total_score = 0

    # 1. Minervini趋势模板分析 (满分35分)
    print("\n" + "=" * 70)
    print("📈 【Mark Minervini - SEPA趋势模板】")
    print("-" * 70)
    passed, conditions = minervini_filter(kline)
    for c in conditions:
        print(f"   {c}")
    minervini_score = passed * 5  # 每条5分，满分35
    total_score += minervini_score
    print(f"\n   Minervini评分: {passed}/7 条件通过 (+{minervini_score}分)")

    # 2. Livermore关键位分析 (满分20分)
    print("\n" + "=" * 70)
    print("📍 【Jesse Livermore - 关键点交易法】")
    print("-" * 70)
    livermore_score, livermore_signals = livermore_analysis(kline)
    for s in livermore_signals:
        print(f"   {s}")
    total_score += livermore_score
    print(f"\n   Livermore评分: +{livermore_score}分")

    # 3. Williams波动率突破 (满分25分)
    print("\n" + "=" * 70)
    print("⚡ 【Larry Williams - 波动率突破】")
    print("-" * 70)
    williams_score, williams_details, signal, entry, stop, target = williams_analysis(kline)
    for d in williams_details:
        print(f"   {d}")
    if signal == 'BUY' and entry:
        print(f"\n   💰 建议入场: {entry:.2f}")
        print(f"   🛑 止损: {stop:.2f}")
        print(f"   🎯 止盈: {target:.2f}")
    total_score += williams_score
    print(f"\n   Williams评分: {'+' if williams_score >= 0 else ''}{williams_score}分")

    # 4. Sperandeo 123反转 (满分20分)
    print("\n" + "=" * 70)
    print("🔄 【Victor Sperandeo - 123反转法则】")
    print("-" * 70)
    sperandeo_score, sperandeo_details, reversal_signal = sperandeo_analysis(kline)
    for d in sperandeo_details:
        print(f"   {d}")
    total_score += sperandeo_score
    print(f"\n   Sperandeo评分: {'+' if sperandeo_score >= 0 else ''}{sperandeo_score}分")

    # 5. VWAP成本分析
    print("\n" + "=" * 70)
    print("💰 【VWAP主力成本分析】")
    print("-" * 70)
    vwap_20 = calculate_vwap(kline, 20)
    if vwap_20:
        vs_vwap = (current / vwap_20 - 1) * 100
        print(f"   20日VWAP: {vwap_20:.2f}")
        print(f"   现价vs成本: {vs_vwap:+.1f}%")

        if vs_vwap <= -10:
            vwap_score = 15
            print("   ✅✅ 远低于主力成本，买入机会!")
        elif vs_vwap <= 0:
            vwap_score = 10
            print("   ✅ 低于主力成本")
        elif vs_vwap <= 15:
            vwap_score = 5
            print("   🟡 略高于主力成本")
        else:
            vwap_score = -5
            print("   ⚠️ 远高于主力成本，追高风险!")
        total_score += vwap_score
        print(f"\n   VWAP评分: {'+' if vwap_score >= 0 else ''}{vwap_score}分")

    # 综合评估
    print("\n" + "=" * 70)
    print("🎯 【综合评估】")
    print("=" * 70)
    print(f"\n   总评分: {total_score}/100")

    if total_score >= 70:
        recommendation = "🟢 强烈买入"
        position = "60%仓位"
    elif total_score >= 50:
        recommendation = "🟢 可以买入"
        position = "40%仓位"
    elif total_score >= 30:
        recommendation = "🟡 观望为主"
        position = "20%仓位或观望"
    else:
        recommendation = "🔴 不建议买入"
        position = "空仓"

    print(f"   建议: {recommendation}")
    print(f"   仓位: {position}")

    # T+0操作建议
    if signal == 'BUY' and total_score >= 50:
        capital = 50000
        position_size = capital * (0.6 if total_score >= 70 else 0.4 if total_score >= 50 else 0.2)
        shares = int(position_size / current / 100) * 100  # 港股100股为1手

        print(f"\n   💰 T+0操作建议 (5万本金):")
        print(f"      买入: {shares}股 @ {entry:.2f}")
        print(f"      金额: {shares * entry:.0f} HKD")
        print(f"      止损: {stop:.2f} (亏损{(entry-stop)/entry*100:.1f}%)")
        print(f"      止盈: {target:.2f} (盈利{(target-entry)/entry*100:.1f}%)")

    print("\n" + "=" * 70)


def scan_stocks():
    """扫描推荐股票"""
    print("=" * 70)
    print("📊 港股大师策略扫描")
    print("=" * 70)

    if not FUTU_AVAILABLE:
        print("❌ 需要富途OpenD支持")
        return

    # AI/机器人板块股票
    watchlist = [
        'HK.09988',  # 阿里巴巴
        'HK.09880',  # 优必选
        'HK.02252',  # 微创机器人
        'HK.02675',  # 精锋医疗
        'HK.00772',  # 阅文集团
        'HK.06082',  # 壁仞科技
        'HK.09678',  # 云知声
        'HK.02013',  # 微盟
        'HK.00700',  # 腾讯
        'HK.09618',  # 京东
        'HK.09888',  # 百度
    ]

    results = []

    for code in watchlist:
        try:
            kline = get_kline_futu(code)
            if kline is None:
                continue

            # 快速评分
            passed, _ = minervini_filter(kline)
            minervini_score = passed * 5

            livermore_score, _ = livermore_analysis(kline)
            williams_score, _, signal, _, _, _ = williams_analysis(kline)
            sperandeo_score, _, _ = sperandeo_analysis(kline)

            vwap_20 = calculate_vwap(kline, 20)
            current = kline['close'].iloc[-1]
            vs_vwap = (current / vwap_20 - 1) * 100 if vwap_20 else 0

            if vs_vwap <= -10:
                vwap_score = 15
            elif vs_vwap <= 0:
                vwap_score = 10
            elif vs_vwap <= 15:
                vwap_score = 5
            else:
                vwap_score = -5

            total_score = minervini_score + livermore_score + williams_score + sperandeo_score + vwap_score

            results.append({
                'code': code,
                'price': current,
                'score': total_score,
                'minervini': f"{passed}/7",
                'williams': signal,
                'vs_vwap': vs_vwap
            })

        except Exception as e:
            continue

    # 排序并输出
    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"\n{'代码':<12} {'现价':>8} {'评分':>6} {'Minervini':>10} {'Williams':>10} {'vs VWAP':>10}")
    print("-" * 70)

    for r in results:
        rec = "🟢" if r['score'] >= 50 else "🟡" if r['score'] >= 30 else "🔴"
        print(f"{r['code']:<12} {r['price']:>8.2f} {r['score']:>5} {rec} {r['minervini']:>10} {r['williams']:>10} {r['vs_vwap']:>+9.1f}%")

    print("\n✅ 扫描完成")


def main():
    if len(sys.argv) < 2:
        print("=" * 60)
        print("港股T+0交易大师策略系统")
        print("=" * 60)
        print("\n整合四位交易大师方法论:")
        print("  - Mark Minervini: SEPA趋势模板")
        print("  - Jesse Livermore: 关键点交易法")
        print("  - Larry Williams: 波动率突破")
        print("  - Victor Sperandeo: 123反转法则")
        print("\n用法:")
        print("  python master_strategy.py 09988      # 分析单只股票")
        print("  python master_strategy.py HK.09988   # 带市场前缀")
        print("  python master_strategy.py scan       # 扫描推荐股票")
        return

    cmd = sys.argv[1]

    if cmd == 'scan':
        scan_stocks()
    else:
        # 分析单只股票
        code = cmd
        if not code.startswith('HK.'):
            code = f'HK.{code}'
        master_strategy_analysis(code)


if __name__ == "__main__":
    main()
