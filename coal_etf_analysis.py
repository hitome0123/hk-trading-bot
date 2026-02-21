#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
煤炭ETF月线级别技术分析
结合印尼煤炭限量事件
整合四大师方法论
数据源: A股(akshare) + 港股(futu)
"""
import sys
import os
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 设置环境变量避免protobuf错误
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

try:
    from futu import *
except ImportError:
    print("❌ 未安装futu-api")
    sys.exit(1)

try:
    import akshare as ak
except ImportError:
    print("❌ 未安装akshare")
    print("请运行: pip install akshare")
    sys.exit(1)

# 煤炭相关标的
COAL_TARGETS = {
    # A股煤炭龙头
    'SH.601088': '中国神华',
    'SH.601225': '陕西煤业',
    'SH.600188': '兖州煤业',
    'SH.601898': '中煤能源A',
    # 港股煤炭龙头
    'HK.01171': '兖煤澳大利亚',
    'HK.01898': '中煤能源H',
}

def get_akshare_monthly_kline(stock_code):
    """获取A股月K线数据（使用akshare）"""
    try:
        # 转换代码格式：SH.601088 -> 601088
        code_number = stock_code.split('.')[1]

        # 获取月K线数据
        df = ak.stock_zh_a_hist(
            symbol=code_number,
            period="monthly",
            start_date="20230101",
            end_date=datetime.now().strftime('%Y%m%d'),
            adjust="qfq"  # 前复权
        )

        if df is None or len(df) == 0:
            return None

        # 统一列名格式（与futu对齐）
        df = df.rename(columns={
            '日期': 'time_key',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'turnover'
        })

        # 转换数据类型
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

        # 只保留最近24个月
        df = df.tail(24)

        return df

    except Exception as e:
        print(f"   获取A股数据失败: {e}")
        return None

def analyze_monthly_breakout(quote_ctx, code, name):
    """月线级别突破分析（支持A股+港股）"""
    print(f"\n{'='*60}")
    print(f"📊 {name} ({code}) - 月线级别分析")
    print('='*60)

    # 根据代码前缀判断使用哪个数据源
    if code.startswith('SH.') or code.startswith('SZ.'):
        # A股：使用akshare
        monthly_kline = get_akshare_monthly_kline(code)
        if monthly_kline is None:
            print(f"❌ 无法获取{name}数据")
            return None
    else:
        # 港股/美股：使用富途
        result = quote_ctx.request_history_kline(
            code,
            start='2023-01-01',
            end=datetime.now().strftime('%Y-%m-%d'),
            ktype=KLType.K_MON,
            max_count=24
        )

        # 处理不同的返回格式
        if len(result) == 3:
            ret, monthly_kline, err_msg = result
        elif len(result) == 2:
            ret, monthly_kline = result
        else:
            print(f"❌ 无法获取{name}数据: 返回格式异常")
            return None

        if ret != RET_OK:
            print(f"❌ 无法获取{name}数据: {monthly_kline if len(result) == 2 else err_msg}")
            return None

    if len(monthly_kline) < 12:
        print(f"⚠️ 数据不足（仅{len(monthly_kline)}个月）")
        return None
    
    # 计算技术指标
    df = monthly_kline.copy()
    
    # 1. 均线系统（Minervini SEPA）
    df['MA6'] = df['close'].rolling(6).mean()   # 半年线
    df['MA12'] = df['close'].rolling(12).mean() # 年线
    df['MA24'] = df['close'].rolling(24).mean() # 两年线
    
    # 2. 52周高低点
    high_52w = df['high'].tail(12).max()  # 近12个月最高
    low_52w = df['low'].tail(12).min()    # 近12个月最低
    
    # 3. 关键价位（Livermore）
    resistance_1 = df['high'].tail(6).max()  # 半年阻力
    resistance_2 = high_52w                   # 年度阻力
    support_1 = df['low'].tail(6).min()      # 半年支撑
    support_2 = low_52w                       # 年度支撑
    
    # 4. VWAP（主力成本，月线用12个月）
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['amount'] = df['typical_price'] * df['volume']
    vwap_12 = df['amount'].tail(12).sum() / df['volume'].tail(12).sum()
    
    # 当前价格
    current = df.iloc[-1]
    current_price = current['close']
    current_volume = current['volume']
    
    # 5. 量能分析（放量突破）
    avg_volume_6m = df['volume'].tail(6).mean()
    volume_ratio = current_volume / avg_volume_6m if avg_volume_6m > 0 else 0
    
    # 6. 涨跌幅
    price_change_1m = (current_price / df.iloc[-2]['close'] - 1) * 100 if len(df) > 1 else 0
    price_change_6m = (current_price / df.iloc[-7]['close'] - 1) * 100 if len(df) > 6 else 0
    price_change_12m = (current_price / df.iloc[-13]['close'] - 1) * 100 if len(df) > 12 else 0
    
    # 打印基本信息
    print(f"\n💲 当前价格: {current_price:.2f}")
    print(f"📅 最新月份: {current['time_key']}")
    print(f"📈 近1月涨跌: {price_change_1m:+.2f}%")
    print(f"📈 近6月涨跌: {price_change_6m:+.2f}%")
    print(f"📈 近12月涨跌: {price_change_12m:+.2f}%")
    
    # Minervini SEPA 分析
    print(f"\n🎯 Minervini SEPA 趋势分析:")
    ma6 = df['MA6'].iloc[-1]
    ma12 = df['MA12'].iloc[-1]
    ma24 = df['MA24'].iloc[-1] if not pd.isna(df['MA24'].iloc[-1]) else 0
    
    sepa_score = 0
    conditions = []
    
    if current_price > ma6:
        conditions.append("✅ 现价 > MA6")
        sepa_score += 1
    else:
        conditions.append("❌ 现价 < MA6")
    
    if current_price > ma12:
        conditions.append("✅ 现价 > MA12")
        sepa_score += 1
    else:
        conditions.append("❌ 现价 < MA12")
    
    if ma24 > 0 and current_price > ma24:
        conditions.append("✅ 现价 > MA24")
        sepa_score += 1
    else:
        conditions.append("❌ 现价 < MA24")
    
    if ma6 > ma12:
        conditions.append("✅ MA6 > MA12 (多头排列)")
        sepa_score += 1
    else:
        conditions.append("❌ MA6 < MA12 (空头排列)")
    
    for cond in conditions:
        print(f"   {cond}")
    
    print(f"   评分: {sepa_score}/4")
    
    # Livermore 关键位分析
    print(f"\n🔍 Livermore 关键价位:")
    print(f"   阻力位1 (半年高): {resistance_1:.2f}")
    print(f"   阻力位2 (年度高): {resistance_2:.2f}")
    print(f"   支撑位1 (半年低): {support_1:.2f}")
    print(f"   支撑位2 (年度低): {support_2:.2f}")
    
    distance_to_resistance = (resistance_2 / current_price - 1) * 100
    distance_to_support = (current_price / support_2 - 1) * 100
    
    print(f"   距年度高点: {distance_to_resistance:+.2f}%")
    print(f"   距年度低点: {distance_to_support:+.2f}%")
    
    # VWAP 成本分析
    print(f"\n💰 VWAP 主力成本分析:")
    print(f"   12月VWAP: {vwap_12:.2f}")
    vs_vwap = (current_price / vwap_12 - 1) * 100
    print(f"   vs VWAP: {vs_vwap:+.2f}%")
    
    if vs_vwap < -10:
        print(f"   ✅ 远低于成本，主力可能被套有护盘动力")
    elif vs_vwap < 0:
        print(f"   ✅ 低于成本，有安全边际")
    elif vs_vwap < 15:
        print(f"   🟡 接近成本")
    else:
        print(f"   ⚠️ 高于成本，主力可能获利了结")
    
    # 量能分析
    print(f"\n📊 量能分析:")
    print(f"   当月成交量: {current_volume:,.0f}")
    print(f"   半年平均量: {avg_volume_6m:,.0f}")
    print(f"   量比: {volume_ratio:.2f}x")
    
    if volume_ratio > 1.5:
        print(f"   ✅ 放量（量比>{1.5}）")
    elif volume_ratio > 1.0:
        print(f"   🟡 微放量")
    else:
        print(f"   ⚠️ 缩量")
    
    # 突破分析
    print(f"\n🚀 月线突破信号分析:")
    
    breakout_score = 0
    max_score = 100
    
    # 1. 均线突破（25分）
    if sepa_score >= 3:
        breakout_score += 25
        print(f"   ✅ [25分] 均线多头排列")
    elif sepa_score == 2:
        breakout_score += 15
        print(f"   🟡 [15分] 均线部分多头")
    else:
        print(f"   ❌ [0分] 均线空头")
    
    # 2. 价格位置（25分）
    if current_price >= resistance_1 * 0.98:  # 接近或突破半年高
        breakout_score += 25
        print(f"   ✅ [25分] 突破半年高点")
    elif current_price >= resistance_1 * 0.95:
        breakout_score += 15
        print(f"   🟡 [15分] 接近半年高点")
    else:
        print(f"   ❌ [0分] 距半年高点较远")
    
    # 3. VWAP成本（20分）
    if vs_vwap <= 0:
        breakout_score += 20
        print(f"   ✅ [20分] 低于主力成本")
    elif vs_vwap <= 10:
        breakout_score += 10
        print(f"   🟡 [10分] 接近主力成本")
    else:
        print(f"   ⚠️ [0分] 高于主力成本")
    
    # 4. 量能确认（15分）
    if volume_ratio >= 1.5:
        breakout_score += 15
        print(f"   ✅ [15分] 放量突破")
    elif volume_ratio >= 1.0:
        breakout_score += 8
        print(f"   🟡 [8分] 微放量")
    else:
        print(f"   ❌ [0分] 缩量")
    
    # 5. 趋势强度（15分）
    if price_change_6m > 20:
        breakout_score += 15
        print(f"   ✅ [15分] 半年涨幅>20%，趋势强劲")
    elif price_change_6m > 10:
        breakout_score += 10
        print(f"   🟡 [10分] 半年涨幅>10%")
    elif price_change_6m > 0:
        breakout_score += 5
        print(f"   🟡 [5分] 半年上涨")
    else:
        print(f"   ❌ [0分] 半年下跌")
    
    print(f"\n⭐ 月线突破评分: {breakout_score}/{max_score}")
    
    if breakout_score >= 70:
        result = "🟢 强烈看好月线突破"
    elif breakout_score >= 50:
        result = "🟢 看好月线突破"
    elif breakout_score >= 30:
        result = "🟡 中性，观望"
    else:
        result = "🔴 不看好突破"
    
    print(f"   结论: {result}")
    
    # Williams突破价计算（如果要买入）
    if len(df) >= 2:
        last_month = df.iloc[-2]
        last_range = last_month['high'] - last_month['low']
        K = 0.6
        williams_entry = last_month['close'] + (last_range * K)
        print(f"\n💡 Williams月线突破买入价: {williams_entry:.2f}")
        print(f"   (上月收盘 {last_month['close']:.2f} + 上月振幅 {last_range:.2f} × 0.6)")
    
    return {
        'code': code,
        'name': name,
        'current_price': current_price,
        'sepa_score': sepa_score,
        'breakout_score': breakout_score,
        'vs_vwap': vs_vwap,
        'volume_ratio': volume_ratio,
        'distance_to_high': distance_to_resistance,
        'price_change_6m': price_change_6m,
    }

def main():
    print("="*60)
    print("🔥 煤炭ETF月线级别突破分析")
    print("📰 催化剂：印尼煤炭限量出口")
    print("="*60)
    
    # 连接富途OpenD
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret, data = quote_ctx.get_global_state()
    if ret != RET_OK:
        print("❌ 富途OpenD连接失败，请先启动")
        return
    
    print("✅ 富途API已连接\n")
    
    results = []
    
    for code, name in COAL_TARGETS.items():
        result = analyze_monthly_breakout(quote_ctx, code, name)
        if result:
            results.append(result)
    
    # 综合排名
    print("\n" + "="*60)
    print("📊 综合评分排名")
    print("="*60)
    
    results.sort(key=lambda x: x['breakout_score'], reverse=True)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['name']} ({r['code']})")
        print(f"   突破评分: {r['breakout_score']}/100")
        print(f"   SEPA评分: {r['sepa_score']}/4")
        print(f"   vs VWAP: {r['vs_vwap']:+.2f}%")
        print(f"   量比: {r['volume_ratio']:.2f}x")
        print(f"   半年涨幅: {r['price_change_6m']:+.2f}%")
    
    # 策略建议
    print("\n" + "="*60)
    print("💡 投资建议")
    print("="*60)
    
    if results:
        best = results[0]
        print(f"\n⭐ 最优标的: {best['name']} ({best['code']})")
        print(f"   突破评分: {best['breakout_score']}/100")
        
        if best['breakout_score'] >= 70:
            print(f"\n✅ 强烈推荐：")
            print(f"   - 月线级别技术面强势")
            print(f"   - 结合印尼煤炭限量催化剂")
            print(f"   - 建议仓位: 20-30%")
            print(f"   - 持仓周期: 1-3个月")
        elif best['breakout_score'] >= 50:
            print(f"\n🟡 谨慎看好：")
            print(f"   - 月线级别有突破迹象")
            print(f"   - 建议小仓位试探: 10-15%")
            print(f"   - 等待更明确信号")
        else:
            print(f"\n⚠️ 不建议：")
            print(f"   - 月线级别技术面偏弱")
            print(f"   - 等待更好的入场时机")
    
    # 风险提示
    print(f"\n⚠️ 风险提示:")
    print(f"   1. 月线级别持仓周期长（1-3个月）")
    print(f"   2. 大宗商品价格波动大")
    print(f"   3. 印尼政策可能反复")
    print(f"   4. 建议止损: -10%（月线级别）")
    print(f"   5. 建议分批建仓，不要一把梭")
    
    quote_ctx.close()
    print("\n✅ 分析完成")

if __name__ == '__main__':
    main()
