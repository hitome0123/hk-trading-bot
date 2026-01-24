#!/usr/bin/env python3
"""
信达生物 (1801.HK) 离线分析脚本
使用模拟数据进行技术分析演示
"""

import sys
import os
import numpy as np
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy


def generate_realistic_data(ticker: str, days: int = 60, current_price: float = 35.5):
    """
    生成基于真实走势的模拟数据

    信达生物近期走势特征：
    - 从高位90附近下跌到35附近
    - 呈现下降趋势
    - 波动性较大
    """
    np.random.seed(1801)  # 使用股票代码作为种子

    # 从60天前开始生成数据，模拟从高位下跌的过程
    start_price = 55.0  # 60天前的价格
    prices = []
    highs = []
    lows = []
    opens = []

    price = start_price

    for i in range(days):
        # 模拟下跌趋势，带有波动
        if i < 30:
            # 前30天：缓慢下跌
            trend = -0.01  # 平均每天下跌1%
        else:
            # 后30天：稳定在低位，小幅波动
            trend = -0.002  # 平均每天下跌0.2%

        # 添加随机波动
        daily_change = trend + np.random.normal(0, 0.025)

        # 计算当日价格
        price = price * (1 + daily_change)

        # 确保最后一天的收盘价接近目标价格
        if i == days - 1:
            price = current_price

        # 计算高低价（模拟日内波动）
        daily_volatility = abs(np.random.normal(0, 0.015))
        high = price * (1 + daily_volatility)
        low = price * (1 - daily_volatility)
        open_price = price * (1 + np.random.uniform(-0.01, 0.01))

        prices.append(price)
        highs.append(high)
        lows.append(low)
        opens.append(open_price)

    return {
        'close': prices,
        'high': highs,
        'low': lows,
        'open': opens
    }


def analyze_innovent_offline():
    """离线分析信达生物"""
    ticker = "1801.HK"
    cost_price = 90.0  # 您的成本价
    current_price = 35.5  # 近期价格（参考）

    print("=" * 80)
    print(f"📊 信达生物 ({ticker}) 技术分析报告 (离线模式)")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 您的持仓成本: {cost_price:.2f} HKD")
    print("=" * 80)

    print("\n⚠️  注意：当前使用模拟数据进行演示")
    print("💡 安装 FutuOpenD 后可获取真实实时数据\n")

    # 生成模拟数据
    print("📈 生成60天历史数据...")
    price_data = generate_realistic_data(ticker, days=60, current_price=current_price)

    print(f"✅ 数据点数: {len(price_data['close'])} 天")
    print(f"   60天前价格: {price_data['close'][0]:.2f} HKD")
    print(f"   当前价格: {current_price:.2f} HKD")
    print(f"   60天涨跌: {((current_price - price_data['close'][0]) / price_data['close'][0] * 100):+.2f}%")

    # 基本信息
    print(f"\n💰 价格信息:")
    print(f"   当前价格: {current_price:.2f} HKD")
    print(f"   您的成本: {cost_price:.2f} HKD")

    # 计算盈亏
    pnl = current_price - cost_price
    pnl_pct = (pnl / cost_price) * 100
    print(f"   盈亏: {pnl:+.2f} HKD ({pnl_pct:+.2f}%)")

    if pnl > 0:
        print(f"   ✅ 当前盈利")
    elif pnl < 0:
        print(f"   ⚠️ 当前浮亏 {abs(pnl_pct):.2f}%")
    else:
        print(f"   ➡️ 持平")

    # 52周模拟数据
    week52_high = max(price_data['high'])
    week52_low = min(price_data['low'])

    print(f"\n   60天最高: {week52_high:.2f} HKD")
    print(f"   60天最低: {week52_low:.2f} HKD")

    # 计算价格位置
    if week52_high > week52_low:
        price_position = ((current_price - week52_low) / (week52_high - week52_low)) * 100
        print(f"   价格位置: {price_position:.1f}% (从60天低点)")

    # 计算技术指标
    print(f"\n📊 技术指标分析:")
    indicators_calc = TechnicalIndicators()
    indicators = indicators_calc.calculate_all_indicators(price_data)

    ema20 = indicators.get('ema20', np.nan)
    ema50 = indicators.get('ema50', np.nan)
    rsi14 = indicators.get('rsi14', np.nan)
    atr14 = indicators.get('atr14', np.nan)

    print(f"\n   📈 技术指标值:")
    if not np.isnan(ema20):
        print(f"      EMA20: {ema20:.2f} HKD")
        ema20_signal = "📈 价格在EMA20之上" if current_price > ema20 else "📉 价格在EMA20之下"
        print(f"             {ema20_signal}")
        print(f"             距离EMA20: {((current_price - ema20) / ema20 * 100):+.2f}%")

    if not np.isnan(ema50):
        print(f"      EMA50: {ema50:.2f} HKD")
        ema50_signal = "📈 价格在EMA50之上" if current_price > ema50 else "📉 价格在EMA50之下"
        print(f"             {ema50_signal}")
        print(f"             距离EMA50: {((current_price - ema50) / ema50 * 100):+.2f}%")

    if not np.isnan(ema20) and not np.isnan(ema50):
        if ema20 > ema50:
            print(f"      📈 EMA趋势: 上升趋势 (EMA20 > EMA50)")
        else:
            print(f"      📉 EMA趋势: 下降趋势 (EMA20 < EMA50)")
            print(f"             均线处于空头排列")

    if not np.isnan(rsi14):
        print(f"      RSI14: {rsi14:.2f}")
        if rsi14 < 30:
            print(f"            ⚠️ 超卖区域 (RSI < 30) - 可能反弹")
        elif rsi14 > 70:
            print(f"            ⚠️ 超买区域 (RSI > 70) - 可能回调")
        else:
            print(f"            ✅ 正常区域 (30 < RSI < 70)")

    if not np.isnan(atr14):
        print(f"      ATR14: {atr14:.2f} HKD")
        atr_pct = (atr14 / current_price) * 100
        print(f"             (波动率: {atr_pct:.2f}%)")

    # 入场分析
    print(f"\n🎯 交易信号分析:")
    entry_strategy = EntryStrategy()
    entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)

    signal = entry_analysis.get('signal', 'NO_SIGNAL')
    if signal == 'LONG':
        print(f"      信号: ✅ 买入信号 (LONG)")
    elif signal == 'WAIT':
        print(f"      信号: ⏸️ 等待信号 (WAIT)")
    else:
        print(f"      信号: ❌ 无明确信号")

    print(f"      理由: {entry_analysis.get('reason', 'N/A')}")

    suggested_entry = entry_analysis.get('entry_price', current_price)
    if suggested_entry and suggested_entry < current_price:
        print(f"      建议入场价: {suggested_entry:.2f} HKD (折扣 {((current_price - suggested_entry) / current_price * 100):.2f}%)")

    # 波动性分析
    print(f"\n📊 波动性分析:")
    closes = np.array(price_data['close'])
    returns = np.diff(closes) / closes[:-1]
    volatility = np.std(returns) * np.sqrt(252)  # 年化波动率

    print(f"   年化波动率: {volatility * 100:.1f}%")
    if volatility > 0.4:
        print(f"   风险等级: 🔴 高风险")
    elif volatility > 0.25:
        print(f"   风险等级: 🟡 中等风险")
    else:
        print(f"   风险等级: 🟢 低风险")

    # 投资建议
    print(f"\n💡 基于成本价 {cost_price:.2f} HKD 的投资建议:")
    print("=" * 80)

    suggestions = []

    # 1. 盈亏状态
    if pnl_pct < -50:
        suggestions.append("⚠️ 当前浮亏超过50%，建议：")
        suggestions.append(f"   - 目前价格 {current_price:.2f} 相比成本价 {cost_price:.2f} 已深度下跌")
        if not np.isnan(rsi14) and rsi14 < 35:
            suggestions.append("   - RSI相对低位，可考虑分批补仓摊低成本（需评估基本面）")
        suggestions.append("   - 重新评估基本面，确认公司业务和财务状况")
        suggestions.append("   - 如果基本面恶化，考虑止损；如果基本面良好，可考虑长期持有")
    elif pnl_pct < -20:
        suggestions.append("⚠️ 当前浮亏超过20%，建议：")
        suggestions.append("   - 密切关注支撑位，观察是否有企稳迹象")
        if not np.isnan(rsi14) and rsi14 < 40:
            suggestions.append("   - RSI显示相对低位，可考虑逢低加仓（谨慎操作）")

    # 2. 趋势分析
    if not np.isnan(ema20) and not np.isnan(ema50):
        if ema20 < ema50:
            suggestions.append("\n📉 技术趋势：下降趋势")
            suggestions.append("   - EMA20 < EMA50，空头排列")
            suggestions.append("   - 建议：等待趋势反转信号")
            suggestions.append(f"   - 关键阻力位：EMA20 ({ema20:.2f}) 和 EMA50 ({ema50:.2f})")
            suggestions.append("   - 若价格突破EMA20并站稳，可能是反转信号")

    # 3. RSI建议
    if not np.isnan(rsi14):
        if rsi14 < 30:
            suggestions.append("\n🔽 RSI超卖（<30）")
            suggestions.append("   - 可能接近短期底部")
            suggestions.append("   - 建议：关注反弹机会，但需确认基本面")
        elif rsi14 < 40:
            suggestions.append(f"\n➡️ RSI偏低（{rsi14:.1f}）")
            suggestions.append("   - 市场情绪偏悲观")
            suggestions.append("   - 建议：等待企稳信号")

    # 4. 风险控制建议
    suggestions.append("\n🛡️ 风险控制建议：")

    # 根据当前价格调整止损位
    if current_price < cost_price * 0.5:
        # 已经跌了50%以上，止损位设置更保守
        stop_loss = current_price * 0.85
        suggestions.append(f"   - 短期止损位: {stop_loss:.2f} HKD (当前价格的-15%)")
    else:
        stop_loss = cost_price * 0.85
        suggestions.append(f"   - 止损位建议：{stop_loss:.2f} HKD（成本价的-15%）")

    # 目标价
    target_1 = current_price * 1.20
    target_2 = current_price * 1.50
    suggestions.append(f"   - 短期目标价1: {target_1:.2f} HKD (+20%)")
    suggestions.append(f"   - 中期目标价2: {target_2:.2f} HKD (+50%)")
    suggestions.append(f"   - 回本目标: {cost_price:.2f} HKD (需上涨 {((cost_price - current_price) / current_price * 100):.1f}%)")

    suggestions.append("\n📋 操作策略建议：")
    suggestions.append("   1. 分批建仓：如果看好长期前景，可分批补仓摊低成本")
    suggestions.append("   2. 设置止损：严格执行止损纪律，控制风险")
    suggestions.append("   3. 基本面研究：重点关注公司业绩、研发管道、行业前景")
    suggestions.append("   4. 长期投资：生物医药行业需要长期视角")

    for suggestion in suggestions:
        print(suggestion)

    # 市场状态
    print(f"\n🕒 港股交易时间: 周一至周五 09:30-12:00, 13:00-16:00")

    print("\n" + "=" * 80)
    print("⚠️ 风险提示：")
    print("   1. 以上分析基于模拟数据，仅供学习参考")
    print("   2. 真实交易请使用实时数据（安装 FutuOpenD）")
    print("   3. 投资有风险，入市需谨慎")
    print("   4. 不构成任何投资建议")
    print("=" * 80)

    print("\n💡 获取实时数据：")
    print("   1. 下载安装 FutuOpenD: https://www.futuhk.com/download/openAPI")
    print("   2. 启动 FutuOpenD 并登录")
    print("   3. 运行: python test_futu_api.py")


if __name__ == "__main__":
    analyze_innovent_offline()
