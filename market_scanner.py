#!/usr/bin/env python3
"""
港股全市场扫描器
自动发现任何板块异动，不限于预设板块
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

try:
    from hk_trading_bot.data_providers.futu_provider import FutuProvider
    import futu as ft
    HAS_FUTU = True
except:
    HAS_FUTU = False


class MarketScanner:
    """港股全市场扫描器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
            'Accept': 'application/json',
        }
        self.provider = None

    def get_hk_market_overview(self) -> List[Dict]:
        """
        获取港股全市场行情概览
        使用东财接口获取港股涨跌幅排行
        """
        stocks = []

        # 1. 获取港股涨幅榜
        gainers = self._get_eastmoney_hk_rank('asc')  # 涨幅榜
        stocks.extend(gainers)

        # 2. 获取港股跌幅榜
        losers = self._get_eastmoney_hk_rank('desc')  # 跌幅榜
        stocks.extend(losers)

        # 去重
        seen = set()
        unique = []
        for s in stocks:
            if s['code'] not in seen:
                seen.add(s['code'])
                unique.append(s)

        return unique

    def _get_eastmoney_hk_rank(self, sort: str = 'asc', top_n: int = 100) -> List[Dict]:
        """
        东财港股涨跌幅排行
        sort: 'asc'=涨幅榜, 'desc'=跌幅榜
        """
        stocks = []

        try:
            # 东财港股行情接口
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': top_n,
                'po': 1 if sort == 'asc' else 0,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',  # 按涨跌幅排序
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',  # 港股
                'fields': 'f2,f3,f4,f5,f6,f7,f12,f14,f15,f16,f17,f18,f100'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=15)
            data = response.json()

            if data.get('data') and data['data'].get('diff'):
                for item in data['data']['diff']:
                    code = str(item.get('f12', ''))
                    name = item.get('f14', '')
                    change_pct = item.get('f3', 0)
                    price = item.get('f2', 0)
                    turnover = item.get('f6', 0)  # 成交额
                    industry = item.get('f100', '')  # 行业

                    if code and name and price and price != '-':
                        stocks.append({
                            'code': code,
                            'name': name,
                            'price': float(price) if price else 0,
                            'change_pct': float(change_pct) if change_pct else 0,
                            'turnover': float(turnover) if turnover else 0,
                            'industry': industry or '其他',
                        })

        except Exception as e:
            print(f"获取东财港股排行失败: {e}")

        return stocks

    def get_hk_sectors_from_eastmoney(self) -> List[Dict]:
        """
        获取东财港股板块行情
        """
        sectors = []

        try:
            # 港股行业板块
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 50,
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',
                'fs': 'm:128+t:+f:!50',  # 港股板块
                'fields': 'f2,f3,f4,f12,f14,f104,f105'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()

            if data.get('data') and data['data'].get('diff'):
                for item in data['data']['diff']:
                    sectors.append({
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'change_pct': float(item.get('f3', 0) or 0),
                        'up_count': int(item.get('f104', 0) or 0),
                        'down_count': int(item.get('f105', 0) or 0),
                    })

        except Exception as e:
            print(f"获取港股板块失败: {e}")

        return sectors

    def cluster_by_industry(self, stocks: List[Dict]) -> Dict[str, List[Dict]]:
        """
        按行业聚类股票
        """
        clusters = defaultdict(list)

        for stock in stocks:
            industry = stock.get('industry', '其他')
            if industry:
                clusters[industry].append(stock)

        return dict(clusters)

    def detect_hot_industries(self, min_stocks: int = 3, min_avg_change: float = 3.0) -> List[Dict]:
        """
        检测热门行业
        条件：行业内至少min_stocks只股票，平均涨幅>=min_avg_change
        """
        # 获取涨幅榜
        stocks = self._get_eastmoney_hk_rank('asc', top_n=200)

        # 按行业聚类
        clusters = self.cluster_by_industry(stocks)

        hot_industries = []
        for industry, industry_stocks in clusters.items():
            if len(industry_stocks) >= min_stocks:
                avg_change = sum(s['change_pct'] for s in industry_stocks) / len(industry_stocks)
                if avg_change >= min_avg_change:
                    # 按涨幅排序
                    industry_stocks.sort(key=lambda x: x['change_pct'], reverse=True)
                    hot_industries.append({
                        'industry': industry,
                        'avg_change': avg_change,
                        'stock_count': len(industry_stocks),
                        'total_turnover': sum(s['turnover'] for s in industry_stocks),
                        'top_stocks': industry_stocks[:5],
                        'leader': industry_stocks[0],
                    })

        # 按平均涨幅排序
        hot_industries.sort(key=lambda x: x['avg_change'], reverse=True)
        return hot_industries

    def detect_concept_clusters(self, min_change: float = 5.0) -> List[Dict]:
        """
        从大涨股票中发现概念聚类
        分析涨幅>5%的股票，找出共同特征
        """
        # 获取大涨股票
        stocks = self._get_eastmoney_hk_rank('asc', top_n=100)
        big_gainers = [s for s in stocks if s['change_pct'] >= min_change]

        if len(big_gainers) < 3:
            return []

        # 按行业统计
        industry_count = defaultdict(list)
        for s in big_gainers:
            industry_count[s['industry']].append(s)

        # 找出集中的行业（>=3只大涨）
        clusters = []
        for industry, stocks_list in industry_count.items():
            if len(stocks_list) >= 3:
                avg_change = sum(s['change_pct'] for s in stocks_list) / len(stocks_list)
                clusters.append({
                    'concept': industry,
                    'avg_change': avg_change,
                    'stock_count': len(stocks_list),
                    'stocks': stocks_list,
                    'leader': max(stocks_list, key=lambda x: x['change_pct']),
                })

        clusters.sort(key=lambda x: x['avg_change'], reverse=True)
        return clusters

    def scan_full_market(self) -> Dict:
        """
        全市场扫描，返回完整报告
        """
        result = {
            'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'hot_industries': [],
            'concept_clusters': [],
            'top_gainers': [],
            'top_losers': [],
            'alerts': [],
        }

        print("🔍 扫描港股全市场...")

        # 1. 获取涨跌幅榜
        gainers = self._get_eastmoney_hk_rank('asc', top_n=50)
        losers = self._get_eastmoney_hk_rank('desc', top_n=20)

        result['top_gainers'] = gainers[:20]
        result['top_losers'] = losers[:10]

        # 2. 检测热门行业
        print("📊 分析行业异动...")
        hot_industries = self.detect_hot_industries(min_stocks=2, min_avg_change=3.0)
        result['hot_industries'] = hot_industries

        # 3. 检测概念聚类
        print("🎯 发现概念聚类...")
        clusters = self.detect_concept_clusters(min_change=5.0)
        result['concept_clusters'] = clusters

        # 4. 生成预警
        for ind in hot_industries[:5]:
            if ind['avg_change'] >= 5.0:
                result['alerts'].append({
                    'type': 'industry',
                    'name': ind['industry'],
                    'change': ind['avg_change'],
                    'count': ind['stock_count'],
                    'leader': ind['leader'],
                    'level': 'HIGH' if ind['avg_change'] >= 7 else 'MEDIUM',
                })

        for cluster in clusters[:3]:
            result['alerts'].append({
                'type': 'concept',
                'name': cluster['concept'],
                'change': cluster['avg_change'],
                'count': cluster['stock_count'],
                'leader': cluster['leader'],
                'level': 'HIGH' if cluster['avg_change'] >= 8 else 'MEDIUM',
            })

        return result


def print_market_report():
    """打印全市场扫描报告"""
    scanner = MarketScanner()
    result = scanner.scan_full_market()

    print("\n" + "=" * 70)
    print(f"📊 港股全市场扫描报告")
    print(f"⏰ {result['scan_time']}")
    print("=" * 70)

    # 1. 预警
    if result['alerts']:
        print(f"\n🔥 【异动预警】({len(result['alerts'])}个)")
        print("-" * 70)
        for a in result['alerts']:
            level = "🔴" if a['level'] == 'HIGH' else "🟡"
            leader = a['leader']
            print(f"{level} {a['name']}: +{a['change']:.2f}% ({a['count']}只)")
            print(f"   └─ 领涨: {leader['name']} +{leader['change_pct']:.2f}%")
    else:
        print("\n✅ 暂无明显板块异动")

    # 2. 热门行业
    if result['hot_industries']:
        print(f"\n📈 【热门行业】")
        print("-" * 70)
        print(f"{'行业':<15} {'涨幅':>8} {'股票数':>6} {'领涨股':>12} {'领涨幅':>8}")
        print("-" * 70)

        for ind in result['hot_industries'][:10]:
            leader = ind['leader']
            print(f"{ind['industry']:<13} {ind['avg_change']:>+7.2f}% "
                  f"{ind['stock_count']:>5} "
                  f"{leader['name'][:8]:>12} {leader['change_pct']:>+7.2f}%")

    # 3. 概念聚类
    if result['concept_clusters']:
        print(f"\n🎯 【概念聚类】(大涨股集中的行业)")
        print("-" * 70)
        for cluster in result['concept_clusters'][:5]:
            print(f"\n📌 {cluster['concept']} (+{cluster['avg_change']:.2f}%)")
            for s in cluster['stocks'][:3]:
                print(f"   • {s['name']} ({s['code']}): +{s['change_pct']:.2f}%")

    # 4. 涨幅榜
    print(f"\n🏆 【涨幅榜 TOP10】")
    print("-" * 70)
    print(f"{'排名':<4} {'股票':<12} {'代码':<8} {'现价':>8} {'涨幅':>8} {'行业':<10}")
    print("-" * 70)

    for i, s in enumerate(result['top_gainers'][:10], 1):
        print(f"{i:<4} {s['name'][:10]:<10} {s['code']:<8} "
              f"{s['price']:>8.2f} {s['change_pct']:>+7.2f}% {s['industry'][:8]:<8}")

    # 5. 跌幅榜
    print(f"\n📉 【跌幅榜 TOP5】")
    print("-" * 70)
    for i, s in enumerate(result['top_losers'][:5], 1):
        print(f"{i}. {s['name']} ({s['code']}): {s['change_pct']:+.2f}%")

    print("\n" + "=" * 70)

    return result


def quick_scan() -> List[Dict]:
    """快速扫描，只返回预警"""
    scanner = MarketScanner()
    result = scanner.scan_full_market()
    return result['alerts']


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        alerts = quick_scan()
        if alerts:
            print(f"\n⚠️ 发现{len(alerts)}个板块异动:")
            for a in alerts:
                level = "🔴" if a['level'] == 'HIGH' else "🟡"
                print(f"{level} {a['name']}: +{a['change']:.2f}%")
        else:
            print("✅ 暂无明显板块异动")
    else:
        print_market_report()
