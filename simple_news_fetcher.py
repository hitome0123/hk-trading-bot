#!/usr/bin/env python3
"""
简化版资讯抓取 - 使用富途API和东方财富公告
避开反爬虫限制，使用官方API
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import requests
import json
import re
from datetime import datetime
from typing import List, Dict

class SimpleNewsFetcher:
    """简化版资讯抓取器 - 使用官方API"""

    def __init__(self):
        self.quote_ctx = None

    def connect_futu(self):
        """连接富途"""
        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            return True
        except:
            return False

    def fetch_futu_broker_news(self, stock_code: str, limit=5) -> List[Dict]:
        """
        从富途获取券商资讯
        这是最可靠的港股资讯来源
        """
        news_list = []

        if not self.quote_ctx:
            return news_list

        try:
            # 富途获取资讯（券商研报、公告）
            ret, data = self.quote_ctx.request_history_kline(stock_code, start=None, end=None, max_count=5, fields=[KL_FIELD.ALL])

            # 注：富途OpenAPI的公告接口可能需要付费版本
            # 这里提供基础框架，实际使用需要根据你的富途版本调整

        except:
            pass

        return news_list

    def fetch_eastmoney_announcement(self, stock_code: str, limit=5) -> List[Dict]:
        """
        从东方财富获取公司公告
        这是公开API，比较稳定
        """
        news_list = []

        try:
            # 转换股票代码
            if stock_code.startswith('HK.'):
                code_num = stock_code.replace('HK.', '')
                market = 'hk'
            elif stock_code.startswith('SH.'):
                code_num = stock_code.replace('SH.', '')
                market = 'sh'
            elif stock_code.startswith('SZ.'):
                code_num = stock_code.replace('SZ.', '')
                market = 'sz'
            else:
                return news_list

            # 东方财富公告API（更稳定的接口）
            url = f"https://np-anotice-stock.eastmoney.com/api/security/ann"
            params = {
                'sr': -1,
                'page_size': limit,
                'page_index': 1,
                'ann_type': 'A',
                'client_source': 'web',
                'stock_list': f'{market}{code_num}'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://data.eastmoney.com/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'list' in data['data']:
                    for item in data['data']['list'][:limit]:
                        title = item.get('title', '').strip()
                        if title and len(title) > 5:
                            news_list.append({
                                'title': title,
                                'source': '东财公告',
                                'time': item.get('notice_date', '')[:10],
                                'platform': 'eastmoney',
                                'type': 'announcement'
                            })
        except:
            pass

        return news_list

    def fetch_eastmoney_research(self, stock_code: str, limit=3) -> List[Dict]:
        """
        从东方财富获取研报摘要
        """
        news_list = []

        try:
            # 转换股票代码
            code_num = stock_code.replace('HK.', '').replace('SH.', '').replace('SZ.', '')

            # 东方财富研报API
            url = f"https://reportapi.eastmoney.com/report/list"
            params = {
                'cb': 'datatable',
                'pageSize': limit,
                'code': code_num
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                # JSONP格式，提取JSON部分
                text = response.text
                match = re.search(r'datatable\((.*)\)', text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                    if 'data' in data:
                        for item in data['data'][:limit]:
                            title = item.get('title', '').strip()
                            if title:
                                news_list.append({
                                    'title': title,
                                    'source': '机构研报',
                                    'time': item.get('publishDate', '')[:10],
                                    'platform': 'eastmoney',
                                    'type': 'research'
                                })
        except:
            pass

        return news_list

    def fetch_all_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """
        综合获取资讯
        优先级：公告 > 研报 > 其他
        """
        all_news = []

        # 1. 公司公告（最重要）
        announcements = self.fetch_eastmoney_announcement(stock_code)
        all_news.extend(announcements)

        # 2. 券商研报
        research = self.fetch_eastmoney_research(stock_code)
        all_news.extend(research)

        # 去重
        seen = set()
        unique_news = []
        for news in all_news:
            title = news['title']
            if title not in seen:
                seen.add(title)
                unique_news.append(news)

        return unique_news[:10]

    def close(self):
        if self.quote_ctx:
            self.quote_ctx.close()


# 测试
if __name__ == '__main__':
    print("="*60)
    print("测试简化版资讯抓取")
    print("="*60 + "\n")

    fetcher = SimpleNewsFetcher()

    test_codes = [
        ('HK.09880', '优必选'),
        ('HK.02432', '天弘基金'),
        ('HK.02513', '智谱')
    ]

    for code, name in test_codes:
        print(f"\n{'='*60}")
        print(f"测试: {name} ({code})")
        print(f"{'='*60}\n")

        news = fetcher.fetch_all_news(code, name)

        if news:
            print(f"✅ 找到 {len(news)} 条资讯:\n")
            for i, item in enumerate(news, 1):
                print(f"{i}. [{item['source']}] {item['title']}")
                if item.get('time'):
                    print(f"   {item['time']}")
                print()
        else:
            print("⚠️ 未找到资讯\n")

    fetcher.close()
