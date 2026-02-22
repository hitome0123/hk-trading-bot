#!/usr/bin/env python3
"""
财联社（CLS）资讯抓取
专业财经快讯平台，API较开放
"""
import requests
import json
from datetime import datetime
from typing import List, Dict

class CLSNewsFetcher:
    """财联社快讯抓取器"""

    def __init__(self):
        self.base_url = "https://www.cls.cn"

    def fetch_flash_news(self, limit=20) -> List[Dict]:
        """
        获取财联社电报（实时快讯）
        不需要股票代码，获取所有最新快讯
        """
        news_list = []

        try:
            # 财联社电报API
            url = "https://www.cls.cn/api/sw"
            params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '7.7.5',
                'rever': '1'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.cls.cn/telegraph'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and 'roll_data' in data['data']:
                    for item in data['data']['roll_data'][:limit]:
                        title = item.get('title', '').strip()
                        content = item.get('content', '').strip()

                        # 合并标题和内容
                        full_text = f"{title} {content}" if title else content

                        if full_text and len(full_text) > 10:
                            news_list.append({
                                'title': full_text[:200],
                                'source': '财联社',
                                'time': self._format_time(item.get('ctime', 0)),
                                'platform': 'cls',
                                'type': 'flash'
                            })
        except Exception as e:
            print(f"财联社抓取失败: {e}")

        return news_list

    def search_stock_news(self, stock_name: str, limit=10) -> List[Dict]:
        """
        搜索特定股票的相关新闻
        """
        news_list = []

        try:
            # 财联社搜索API
            url = "https://www.cls.cn/api/search"
            params = {
                'keyword': stock_name,
                'app': 'CailianpressWeb',
                'os': 'web'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and 'article' in data['data']:
                    for item in data['data']['article'][:limit]:
                        title = item.get('title', '').strip()

                        if title:
                            news_list.append({
                                'title': title,
                                'source': '财联社',
                                'time': self._format_time(item.get('ctime', 0)),
                                'platform': 'cls',
                                'type': 'article'
                            })
        except Exception as e:
            pass

        return news_list

    def _format_time(self, timestamp):
        """格式化时间戳"""
        try:
            if timestamp > 1e10:
                timestamp = timestamp / 1000
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%m-%d %H:%M')
        except:
            return ''


class JinshiNewsFetcher:
    """金十数据快讯抓取器"""

    def fetch_flash_news(self, limit=20) -> List[Dict]:
        """
        获取金十数据快讯
        专注财经日历和快讯
        """
        news_list = []

        try:
            # 金十数据flash API
            url = "https://flash-api.jin10.com/get_flash_list"
            params = {
                'channel': '-1',
                'vip': '1'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data:
                    for item in data['data'][:limit]:
                        content = item.get('content', '').strip()

                        if content and len(content) > 10:
                            news_list.append({
                                'title': content[:200],
                                'source': '金十数据',
                                'time': item.get('time', ''),
                                'platform': 'jinshi',
                                'type': 'flash'
                            })
        except Exception as e:
            pass

        return news_list


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试财联社快讯")
    print("="*60 + "\n")

    cls = CLSNewsFetcher()

    # 1. 最新快讯
    print("📰 最新快讯（前10条）:\n")
    flash = cls.fetch_flash_news(limit=10)
    if flash:
        for i, news in enumerate(flash, 1):
            print(f"{i}. [{news['time']}] {news['title'][:80]}")
        print(f"\n✅ 共 {len(flash)} 条")
    else:
        print("⚠️ 未获取到快讯")

    # 2. 搜索特定股票
    print("\n" + "="*60)
    print("搜索「优必选」相关新闻")
    print("="*60 + "\n")

    stock_news = cls.search_stock_news('优必选', limit=5)
    if stock_news:
        for i, news in enumerate(stock_news, 1):
            print(f"{i}. [{news['time']}] {news['title']}")
        print(f"\n✅ 共 {len(stock_news)} 条")
    else:
        print("⚠️ 未找到相关新闻")

    # 3. 金十数据
    print("\n" + "="*60)
    print("测试金十数据快讯")
    print("="*60 + "\n")

    jinshi = JinshiNewsFetcher()
    jinshi_news = jinshi.fetch_flash_news(limit=10)
    if jinshi_news:
        for i, news in enumerate(jinshi_news, 1):
            print(f"{i}. [{news['time']}] {news['title'][:80]}")
        print(f"\n✅ 共 {len(jinshi_news)} 条")
    else:
        print("⚠️ 未获取到快讯")
