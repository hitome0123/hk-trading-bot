#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量扫描港股，找出出现买点信号的股票
使用YFinance数据源
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from datetime import datetime
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

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

def analyze_stock(provider, code, name):
    """分析单只股票"""
    try:
        # 获取当前价格
        current_price = provider.get_current_price(code)
        if current_price is None or current_price <= 0:
            return None

        # 获取历史数据
        history_dict = provider.get_price_data(code, days=60)
        if history_dict is None or len(history_dict.get('close', [])) < 50:
            return None

        # 转换为Series
        closes = pd.Series(history_dict['close'])
        highs = pd.Series(history_dict['high'])
        lows = pd.Series(history_dict['low'])

        # 计算指标
        ema20 = calculate_ema(closes, 20).iloc[-1]
        ema50 = calculate_ema(closes, 50).iloc[-1]
        rsi14 = calculate_rsi(closes, 14).iloc[-1]

        # 计算涨跌幅
        if len(closes) >= 2:
            yesterday_close = closes.iloc[-2]
            change_rate = (current_price - yesterday_close) / yesterday_close * 100
        else:
            change_rate = 0

        # 价格相对均线位置
        price_vs_ema20 = (current_price - ema20) / ema20 * 100

        # 趋势判断
        trend = 1 if ema20 > ema50 else -1

        # 买点信号检测
        signals = []
        score = 0

        # 信号1: RSI超卖反弹
        if rsi14 < 35:
            signals.append("RSI超卖")
            score += 3
        elif rsi14 < 45:
            signals.append("RSI偏弱")
            score += 1

        # 信号2: 跌破均线后反弹
        if current_price < ema20 and len(closes) >= 2:
            yesterday_close = closes.iloc[-2]
            if current_price > yesterday_close:
                signals.append("跌破均线反弹")
                score += 2

        # 信号3: 突破均线，趋势向上
        if current_price > ema20 and price_vs_ema20 < 2 and trend > 0:
            signals.append("突破均线")
            score += 2

        # 信号4: 大阳线突破
        if change_rate > 5:
            signals.append("大阳线突破")
            score += 3

        # 信号5: 远低于均线（支撑位）
        if price_vs_ema20 < -5:
            signals.append("超跌反弹")
            score += 2
        elif price_vs_ema20 < -3:
            signals.append("接近支撑")
            score += 1

        # 只返回有信号的股票
        if score >= 2:
            return {
                'code': code,
                'name': name,
                'price': current_price,
                'change': change_rate,
                'rsi': rsi14,
                'ema20': ema20,
                'ema50': ema50,
                'vs_ema20': price_vs_ema20,
                'trend': '上升' if trend > 0 else '下降',
                'signals': signals,
                'score': score
            }

        return None

    except Exception as e:
        return None

def main():
    """主函数"""
    print("🔍 扫描港股市场，寻找买点信号...")
    print(f"⏰ 扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 初始化数据源
    provider = YFinanceProvider()

    # 要扫描的股票列表
    stocks = [
        # 用户持仓
        ('1929.HK', '周大福'),
        ('0386.HK', '中石化'),
        ('1024.HK', '快手'),
        ('9618.HK', '京东'),
        ('2357.HK', '中航科工'),
        ('6082.HK', '壁仞科技'),
        ('0981.HK', '中芯国际'),

        # 科技互联网
        ('0700.HK', '腾讯'),
        ('9988.HK', '阿里巴巴'),
        ('9888.HK', '百度'),
        ('3690.HK', '美团'),
        ('1810.HK', '小米'),
        ('9999.HK', '网易'),

        # AI人工智能
        ('0020.HK', '商汤'),
        ('2382.HK', '舜宇光学'),
        ('9880.HK', '优必选'),

        # 新能源汽车
        ('1211.HK', '比亚迪'),
        ('0175.HK', '吉利'),
        ('9866.HK', '蔚来'),
        ('2015.HK', '理想'),
        ('9868.HK', '小鹏'),

        # 消费零售
        ('9633.HK', '农夫山泉'),
        ('2331.HK', '李宁'),
        ('6862.HK', '海底捞'),
        ('9992.HK', '泡泡玛特'),

        # 医药生物
        ('6160.HK', '百济神州'),
        ('2269.HK', '药明生物'),
        ('1177.HK', '中生制药'),
        ('1801.HK', '信达生物'),

        # 半导体
        ('1347.HK', '华虹半导体'),
        ('0763.HK', '中兴通讯'),

        # 金融
        ('2318.HK', '平安'),
        ('0388.HK', '港交所'),

        # 其他热门
        ('2899.HK', '紫金矿业'),
        ('0968.HK', '信义光能'),
        ('3800.HK', '协鑫科技'),
    ]

    results = []
    processed = 0

    for code, name in stocks:
        processed += 1
        print(f"[{processed}/{len(stocks)}] 分析 {code} {name}...", end='\r')

        result = analyze_stock(provider, code, name)
        if result:
            results.append(result)

    print("\n" + "="*80)

    # 按评分排序
    results.sort(key=lambda x: x['score'], reverse=True)

    if not results:
        print("❌ 未找到符合条件的买点信号")
        return

    print(f"✅ 找到 {len(results)} 个买点机会\n")
    print("="*80)

    # 显示结果
    for i, stock in enumerate(results, 1):
        print(f"\n{i}. {stock['name']} ({stock['code']}) - ⭐评分: {stock['score']}")
        print(f"   💲 当前价: {stock['price']:.2f} HKD | 涨跌: {stock['change']:+.2f}%")
        print(f"   📈 RSI: {stock['rsi']:.1f} | 趋势: {stock['trend']}")
        print(f"   📊 vs EMA20: {stock['vs_ema20']:+.1f}%")
        print(f"   🎯 买点信号: {', '.join(stock['signals'])}")

        # 给出操作建议
        if stock['score'] >= 5:
            suggestion = "🟢 强烈推荐买入"
        elif stock['score'] >= 3:
            suggestion = "🟡 可以考虑"
        else:
            suggestion = "⚪ 观察为主"
        print(f"   💡 建议: {suggestion}")

    print("\n" + "="*80)
    print("📝 说明:")
    print("   - 评分≥5: 强烈推荐，多个买点信号共振")
    print("   - 评分3-4: 可以考虑，有明确买点信号")
    print("   - 评分2: 观察为主，信号较弱")
    print("="*80)

if __name__ == "__main__":
    main()
