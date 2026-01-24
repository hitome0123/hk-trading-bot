#!/usr/bin/env python3
"""
港股板块轮动监控 - 自动找热点板块
"""

import yfinance as yf
from datetime import datetime
from typing import Dict, List
import json

# 板块分类
SECTORS = {
    '科技互联网': [
        ('0700.HK', '腾讯'),
        ('9888.HK', '百度'),
        ('9618.HK', '京东'),
        ('3690.HK', '美团'),
        ('9999.HK', '网易'),
        ('1024.HK', '快手'),
    ],
    'AI人工智能': [
        ('9888.HK', '百度'),
        ('2513.HK', '智谱AI'),
        ('0100.HK', 'MiniMax'),
        ('0020.HK', '商汤'),
        ('1024.HK', '快手'),
    ],
    '新能源汽车': [
        ('9866.HK', '蔚来'),
        ('2015.HK', '理想'),
        ('1211.HK', '比亚迪'),
        ('0175.HK', '吉利'),
        ('9868.HK', '小鹏'),
    ],
    '半导体芯片': [
        ('0981.HK', '中芯国际'),
        ('1347.HK', '华虹'),
        ('6082.HK', '壁仞科技'),
        ('2388.HK', '中银香港'),
    ],
    '医药生物': [
        ('6160.HK', '百济神州'),
        ('2269.HK', '药明生物'),
        ('1177.HK', '中生制药'),
        ('2359.HK', '药明康德'),
    ],
    '消费零售': [
        ('1929.HK', '周大福'),
        ('9633.HK', '农夫山泉'),
        ('0291.HK', '华润啤酒'),
        ('2331.HK', '李宁'),
        ('6862.HK', '海底捞'),
    ],
    '能源石油': [
        ('0386.HK', '中石化'),
        ('0857.HK', '中石油'),
        ('0883.HK', '中海油'),
        ('2688.HK', '新奥能源'),
    ],
    '金融银行': [
        ('0005.HK', '汇丰'),
        ('1398.HK', '工商银行'),
        ('3988.HK', '中国银行'),
        ('2318.HK', '平安'),
        ('0388.HK', '港交所'),
    ],
    '地产基建': [
        ('0016.HK', '新鸿基'),
        ('0001.HK', '长和'),
        ('0688.HK', '中海外'),
        ('2007.HK', '碧桂园'),
    ],
    '电信运营': [
        ('0941.HK', '中移动'),
        ('0728.HK', '中电信'),
        ('0762.HK', '中联通'),
    ],
    '军工航空': [
        ('2357.HK', '中航科工'),
        ('3969.HK', '中国通号'),
        ('1772.HK', '赣锋锂业'),
    ],
}


def get_stock_data(ticker: str) -> Dict:
    """获取单只股票数据"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='5d')
        if len(hist) < 2:
            return None

        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = (current - prev) / prev * 100

        vol_today = hist['Volume'].iloc[-1]
        vol_avg = hist['Volume'].tail(5).mean()
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 0

        return {
            'price': current,
            'change': change,
            'vol_ratio': vol_ratio
        }
    except:
        return None


def analyze_sector(sector_name: str, stocks: List) -> Dict:
    """分析单个板块"""
    results = []

    for ticker, name in stocks:
        data = get_stock_data(ticker)
        if data:
            results.append({
                'ticker': ticker,
                'name': name,
                **data
            })

    if not results:
        return None

    # 计算板块平均涨跌幅
    avg_change = sum(r['change'] for r in results) / len(results)
    avg_vol_ratio = sum(r['vol_ratio'] for r in results) / len(results)

    # 上涨股票数
    up_count = sum(1 for r in results if r['change'] > 0)

    return {
        'name': sector_name,
        'avg_change': avg_change,
        'avg_vol_ratio': avg_vol_ratio,
        'up_count': up_count,
        'total_count': len(results),
        'stocks': sorted(results, key=lambda x: x['change'], reverse=True)
    }


def scan_all_sectors(top_n: int = 5):
    """扫描所有板块，返回最强板块"""
    print("正在扫描板块...")
    print("=" * 70)

    sector_results = []

    for sector_name, stocks in SECTORS.items():
        result = analyze_sector(sector_name, stocks)
        if result:
            sector_results.append(result)
            print(f"  {sector_name}: {result['avg_change']:+.2f}%")

    # 按涨幅排序
    sector_results.sort(key=lambda x: x['avg_change'], reverse=True)

    print("\n" + "=" * 70)
    print(f"今日板块排名 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)
    print(f"{'排名':<4} {'板块':<12} {'涨跌':>8} {'量比':>8} {'上涨/总数':>10}")
    print("-" * 70)

    for i, s in enumerate(sector_results):
        icon = '🔥' if s['avg_change'] > 2 else ('📈' if s['avg_change'] > 0 else '📉')
        print(f"{i+1:<4} {s['name']:<12} {s['avg_change']:>+7.2f}% {s['avg_vol_ratio']:>7.2f}x {s['up_count']}/{s['total_count']:>8} {icon}")

    # 显示最强板块详情
    print("\n" + "=" * 70)
    print(f"最强板块: {sector_results[0]['name']}")
    print("=" * 70)
    print(f"{'股票':<12} {'现价':>8} {'涨跌':>8} {'量比':>8}")
    print("-" * 70)

    for stock in sector_results[0]['stocks'][:5]:
        vol_icon = '🔥' if stock['vol_ratio'] > 1.2 else ''
        print(f"{stock['name']:<12} {stock['price']:>8.2f} {stock['change']:>+7.2f}% {stock['vol_ratio']:>7.2f}x {vol_icon}")

    # 找放量板块
    print("\n" + "=" * 70)
    print("放量板块 (量比 > 1.2)")
    print("=" * 70)

    vol_sectors = [s for s in sector_results if s['avg_vol_ratio'] > 1.2]
    if vol_sectors:
        for s in vol_sectors[:3]:
            print(f"  {s['name']}: 量比{s['avg_vol_ratio']:.2f}x, 涨跌{s['avg_change']:+.2f}%")
    else:
        print("  暂无明显放量板块")

    return sector_results


def find_sector_leaders():
    """找每个板块的龙头（涨幅最大+放量）"""
    print("\n" + "=" * 70)
    print("各板块龙头股")
    print("=" * 70)
    print(f"{'板块':<12} {'龙头':<10} {'涨跌':>8} {'量比':>8}")
    print("-" * 70)

    leaders = []

    for sector_name, stocks in SECTORS.items():
        result = analyze_sector(sector_name, stocks)
        if result and result['stocks']:
            leader = result['stocks'][0]  # 涨幅最大的
            leaders.append({
                'sector': sector_name,
                **leader
            })
            vol_icon = '🔥' if leader['vol_ratio'] > 1.2 else ''
            print(f"{sector_name:<12} {leader['name']:<10} {leader['change']:>+7.2f}% {leader['vol_ratio']:>7.2f}x {vol_icon}")

    # 找最强龙头
    leaders.sort(key=lambda x: x['change'], reverse=True)

    print("\n" + "=" * 70)
    print("今日最强龙头 TOP 5")
    print("=" * 70)

    for i, l in enumerate(leaders[:5]):
        print(f"{i+1}. {l['name']}({l['ticker']}): {l['change']:+.2f}% | {l['sector']}")

    return leaders


def quick_scan():
    """快速扫描，只看涨跌"""
    results = []

    all_stocks = []
    for stocks in SECTORS.values():
        all_stocks.extend(stocks)

    # 去重
    seen = set()
    unique_stocks = []
    for ticker, name in all_stocks:
        if ticker not in seen:
            seen.add(ticker)
            unique_stocks.append((ticker, name))

    print(f"快速扫描 {len(unique_stocks)} 只股票...")

    for ticker, name in unique_stocks:
        data = get_stock_data(ticker)
        if data:
            results.append({
                'ticker': ticker,
                'name': name,
                **data
            })

    # 按涨幅排序
    results.sort(key=lambda x: x['change'], reverse=True)

    print("\n" + "=" * 70)
    print("今日涨幅榜 TOP 10")
    print("=" * 70)

    for i, r in enumerate(results[:10]):
        vol_icon = '🔥' if r['vol_ratio'] > 1.2 else ''
        print(f"{i+1}. {r['name']}: {r['change']:+.2f}% | 量比{r['vol_ratio']:.2f}x {vol_icon}")

    print("\n" + "=" * 70)
    print("今日跌幅榜 TOP 5")
    print("=" * 70)

    for i, r in enumerate(results[-5:]):
        print(f"{i+1}. {r['name']}: {r['change']:+.2f}%")

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python sector_monitor.py scan     - 扫描所有板块")
        print("  python sector_monitor.py leaders  - 找各板块龙头")
        print("  python sector_monitor.py quick    - 快速涨跌榜")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'scan':
        scan_all_sectors()
    elif cmd == 'leaders':
        find_sector_leaders()
    elif cmd == 'quick':
        quick_scan()
    else:
        print("未知命令")
