#!/usr/bin/env python3
"""
社交媒体热点采集器
采集东方财富、淘股吧等平台的实时热点数据
"""
import json
import requests
from datetime import datetime
from typing import List, Dict
import time

# 输出文件路径
OUTPUT_FILE = '/Users/mantou/.n8n-files/social_media_hotspots.json'

class SocialMediaCollector:
    """社交媒体数据采集器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.timeout = 10

    def collect_eastmoney_hk_hot(self) -> List[Dict]:
        """采集东方财富港股热度榜（真实数据）"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 30,  # 取前30只
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',  # 按涨跌幅排序
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',  # 港股
                'fields': 'f12,f13,f14,f3,f2,f5,f6,f62'  # 代码,市场,名称,涨跌幅,最新价,成交量,成交额,主力净流入
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('rc') == 0 and 'data' in data and data['data']:
                    stocks = data['data'].get('diff', [])
                    hotspots = []

                    for idx, stock in enumerate(stocks):
                        stock_code = stock.get('f12', '')
                        stock_name = stock.get('f14', '')
                        change_pct = stock.get('f3', 0)  # 涨跌幅
                        turnover = stock.get('f6', 0)  # 成交额

                        # 热度 = 成交额(万) + 涨跌幅绝对值 * 10000
                        heat_score = int(turnover + abs(change_pct) * 10000)

                        if stock_code and stock_name:
                            hotspots.append({
                                'keyword': f"{stock_name}",
                                'heat_score': heat_score,
                                'rank': idx + 1,
                                'source': 'eastmoney_hk',
                                'stock_code': f"HK.{stock_code}",
                                'change_pct': change_pct,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                    print(f"✓ 东方财富港股: {len(hotspots)} 条")
                    return hotspots

            print(f"⚠️ 东方财富港股API返回异常")
            return []

        except Exception as e:
            print(f"东方财富港股采集失败: {e}")
            return []

    def collect_eastmoney_concepts(self) -> List[Dict]:
        """采集东方财富热门概念板块（真实数据）"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 20,
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',  # 按涨跌幅排序
                'fs': 'b:BK0707',  # 热门概念
                'fields': 'f12,f14,f3,f62,f184'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('rc') == 0 and 'data' in data and data['data']:
                    concepts = data['data'].get('diff', [])
                    hotspots = []

                    for idx, concept in enumerate(concepts):
                        concept_name = concept.get('f14', '')
                        change_pct = concept.get('f3', 0)
                        turnover = concept.get('f62', 0)

                        # 热度 = 成交额 + 涨跌幅绝对值 * 1000000
                        heat_score = int(turnover + abs(change_pct) * 1000000)

                        if concept_name:
                            hotspots.append({
                                'keyword': concept_name,
                                'heat_score': heat_score,
                                'rank': idx + 1,
                                'source': 'eastmoney_concept',
                                'change_pct': change_pct,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                    print(f"✓ 东方财富概念板块: {len(hotspots)} 条")
                    return hotspots

            print(f"⚠️ 东方财富概念板块API返回异常")
            return []

        except Exception as e:
            print(f"东方财富概念板块采集失败: {e}")
            return []

    def collect_taoguba_hot(self) -> List[Dict]:
        """采集淘股吧热门话题（尝试真实API，失败则跳过）"""
        try:
            url = "https://www.taoguba.com.cn/api/hot/getTalkList"
            response = requests.get(url, headers=self.headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'data' in data:
                    posts = data['data'].get('list', [])[:20]
                    hotspots = []

                    for idx, post in enumerate(posts):
                        title = post.get('title', '')
                        views = post.get('readCount', 0)
                        replies = post.get('replyCount', 0)

                        # 热度 = 阅读数 + 回复数 * 10
                        heat_score = views + replies * 10

                        if title:
                            hotspots.append({
                                'keyword': title,
                                'heat_score': heat_score,
                                'rank': idx + 1,
                                'source': 'taoguba',
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                    print(f"✓ 淘股吧: {len(hotspots)} 条")
                    return hotspots

            print(f"⚠️ 淘股吧API访问失败，跳过")
            return []

        except Exception as e:
            print(f"⚠️ 淘股吧采集失败（{e}），跳过")
            return []

    def collect_eastmoney_a_hot(self) -> List[Dict]:
        """采集东方财富A股热度榜（补充数据）"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 20,
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',
                'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',  # A股
                'fields': 'f12,f14,f3,f5,f6,f62'
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get('rc') == 0 and 'data' in data and data['data']:
                    stocks = data['data'].get('diff', [])
                    hotspots = []

                    for idx, stock in enumerate(stocks):
                        stock_name = stock.get('f14', '')
                        change_pct = stock.get('f3', 0)
                        turnover = stock.get('f6', 0)

                        heat_score = int(turnover + abs(change_pct) * 10000)

                        if stock_name:
                            hotspots.append({
                                'keyword': stock_name,
                                'heat_score': heat_score,
                                'rank': idx + 1,
                                'source': 'eastmoney_a',
                                'change_pct': change_pct,
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                    print(f"✓ 东方财富A股: {len(hotspots)} 条")
                    return hotspots

            print(f"⚠️ 东方财富A股API返回异常")
            return []

        except Exception as e:
            print(f"东方财富A股采集失败: {e}")
            return []

    def collect_all(self) -> Dict:
        """采集所有平台数据"""
        print(f"🔍 开始采集社交媒体热点数据... {datetime.now().strftime('%H:%M:%S')}")

        results = {
            'eastmoney_hk': self.collect_eastmoney_hk_hot(),
            'eastmoney_concept': self.collect_eastmoney_concepts(),
            'eastmoney_a': self.collect_eastmoney_a_hot(),
            'taoguba': self.collect_taoguba_hot(),
        }

        # 统计
        total_hotspots = sum(len(v) for v in results.values())
        print(f"✅ 采集完成：共 {total_hotspots} 条热点数据")

        # 添加元数据
        output = {
            'data': results,
            'metadata': {
                'total_count': total_hotspots,
                'platforms': list(results.keys()),
                'sources': '东方财富网(港股+A股+概念板块) + 淘股吧',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        return output


def main():
    """主函数"""
    collector = SocialMediaCollector()

    # 采集数据
    data = collector.collect_all()

    # 保存到文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"📁 数据已保存到: {OUTPUT_FILE}")
    print(f"📊 详情: {data['metadata']}")


if __name__ == "__main__":
    main()
