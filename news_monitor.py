#!/usr/bin/env python3
"""
财经新闻监控 - 抓取港股/A股相关新闻
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import time


class NewsMonitor:
    """新闻监控"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_sina_news(self, category: str = 'hk') -> List[Dict]:
        """
        获取新浪财经新闻
        category: 'hk' 港股, 'stock' A股, 'global' 全球
        """
        news = []

        try:
            # 新浪7x24快讯
            url = "https://zhibo.sina.com.cn/api/zhibo/feed"
            params = {
                'callback': '',
                'page': 1,
                'page_size': 20,
                'zhibo_id': 152,  # 财经直播间
                'tag_id': 0,
                'dire': 'f',
                'dpc': 1
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'result' in data and 'data' in data['result']:
                feed = data['result']['data'].get('feed', {})
                for item in feed.get('list', []):
                    rich_text = item.get('rich_text', '')
                    # 提取纯文本
                    text = re.sub(r'<[^>]+>', '', rich_text)[:100]
                    if text:
                        news.append({
                            'title': text,
                            'url': '',
                            'time': item.get('create_time', '')[-8:-3],  # HH:MM
                            'source': 'sina'
                        })

        except Exception as e:
            pass

        # 备用：东财港股快讯
        if not news:
            try:
                url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
                params = {
                    'client': 'web',
                    'biz': 'web_news_col',
                    'column': '350' if category == 'hk' else '102',  # 350=港股
                    'order': 1,
                    'page_index': 1,
                    'page_size': 20
                }
                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                data = resp.json()
                if data and 'data' in data and 'list' in data['data']:
                    for item in data['data']['list']:
                        news.append({
                            'title': item.get('title', ''),
                            'url': item.get('url', ''),
                            'time': item.get('showtime', '')[-8:-3],
                            'source': 'eastmoney'
                        })
            except:
                pass

        return news

    def get_eastmoney_news(self, category: str = 'hk') -> List[Dict]:
        """
        获取东方财富新闻
        """
        news = []

        try:
            if category == 'hk':
                url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_1_.html"
            else:
                url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_ajaxResult_50_1_.html"

            resp = requests.get(url, headers=self.headers, timeout=10)
            text = resp.text

            # 解析JSONP
            match = re.search(r'var defined_list = (\[.*?\]);', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                for item in data[:20]:
                    news.append({
                        'title': item.get('title', ''),
                        'url': item.get('url_w', item.get('url_m', '')),
                        'time': item.get('showtime', '')[:5],
                        'source': 'eastmoney'
                    })

        except Exception as e:
            print(f"获取东财新闻失败: {e}")

        return news

    def get_cls_flash(self) -> List[Dict]:
        """
        获取财联社快讯
        """
        news = []

        try:
            url = "https://www.cls.cn/api/sw"
            params = {
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '8.4.6'
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                for item in data['data']:
                    title = item.get('title', '') or item.get('brief', '')[:50]
                    if title:
                        ctime = item.get('ctime', 0)
                        if isinstance(ctime, str):
                            ctime = int(ctime) if ctime.isdigit() else 0
                        level = item.get('level', 0)
                        if isinstance(level, str):
                            level = int(level) if level.isdigit() else 0
                        news.append({
                            'title': title,
                            'content': item.get('content', item.get('brief', '')),
                            'time': datetime.fromtimestamp(ctime).strftime('%H:%M') if ctime else '',
                            'important': level >= 2,
                            'source': 'cls'
                        })

        except Exception as e:
            # 备用：东财7x24快讯
            try:
                url = "https://np-listapi.eastmoney.com/comm/web/getNewsByColumns"
                params = {
                    'client': 'web',
                    'biz': 'web_news_col',
                    'column': '102',
                    'order': 1,
                    'needInteractData': 0,
                    'page_index': 1,
                    'page_size': 20
                }
                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                data = resp.json()
                if data and 'data' in data and 'list' in data['data']:
                    for item in data['data']['list']:
                        news.append({
                            'title': item.get('title', ''),
                            'time': item.get('showtime', '')[:5],
                            'important': False,
                            'source': 'eastmoney'
                        })
            except:
                pass

        return news

    def search_stock_news(self, keyword: str) -> List[Dict]:
        """搜索股票相关新闻"""
        news = []

        try:
            # 东财搜索
            url = "https://search-api-web.eastmoney.com/search/jsonp"
            params = {
                'cb': 'cb',
                'param': json.dumps({
                    'uid': '',
                    'keyword': keyword,
                    'type': ['cmsArticle'],
                    'pageIndex': 1,
                    'pageSize': 10,
                    'sort': 'default',
                    'source': 'www'
                })
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            text = resp.text

            # 解析JSONP
            match = re.search(r'cb\((.*)\)', text)
            if match:
                data = json.loads(match.group(1))
                if 'result' in data and data['result']:
                    for item in data['result'].get('cmsArticle', {}).get('list', []):
                        news.append({
                            'title': re.sub(r'<[^>]+>', '', item.get('title', '')),
                            'url': item.get('url', ''),
                            'time': item.get('publishDate', '')[:10],
                            'source': 'eastmoney'
                        })

        except Exception as e:
            print(f"搜索新闻失败: {e}")

        return news

    def get_hot_topics(self) -> List[Dict]:
        """获取热门话题"""
        topics = []

        try:
            # 东财热门板块
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 10,
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f3',
                'fs': 'm:90+t:2',  # 板块
                'fields': 'f2,f3,f12,f14',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data and data['data']:
                for item in data['data'].get('diff', []):
                    topics.append({
                        'title': item.get('f14', ''),
                        'heat': item.get('f3', 0),  # 涨跌幅作为热度
                        'change': item.get('f3', 0)
                    })

        except Exception as e:
            pass  # 静默失败

        return topics


def show_hk_news():
    """显示港股新闻"""
    monitor = NewsMonitor()

    print("\n" + "=" * 70)
    print(f"港股新闻 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    # 新浪港股
    news = monitor.get_sina_news('hk')
    if news:
        print("\n[新浪财经]")
        for n in news[:10]:
            print(f"  [{n['time']}] {n['title'][:50]}")

    # 东财港股
    news = monitor.get_eastmoney_news('hk')
    if news:
        print("\n[东方财富]")
        for n in news[:10]:
            print(f"  [{n['time']}] {n['title'][:50]}")


def show_flash():
    """显示快讯"""
    monitor = NewsMonitor()

    print("\n" + "=" * 70)
    print(f"财经快讯 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    news = monitor.get_cls_flash()

    if news:
        for n in news[:20]:
            icon = '🔴' if n.get('important') else '  '
            print(f"{icon}[{n['time']}] {n['title'][:60]}")
    else:
        print("获取快讯失败")


def search_news(keyword: str):
    """搜索新闻"""
    monitor = NewsMonitor()

    print(f"\n搜索: {keyword}")
    print("=" * 60)

    news = monitor.search_stock_news(keyword)
    if news:
        for n in news:
            print(f"  [{n['time']}] {n['title'][:50]}")
            print(f"           {n['url']}")
    else:
        print("未找到相关新闻")


def quick_scan():
    """快速扫描重要新闻"""
    monitor = NewsMonitor()

    print("\n" + "=" * 70)
    print(f"今日重要新闻 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    # 财联社快讯（只显示重要的）
    news = monitor.get_cls_flash()
    important = [n for n in news if n.get('important')]

    if important:
        print("\n🔴 重要快讯:")
        for n in important[:10]:
            print(f"  [{n['time']}] {n['title'][:60]}")
    else:
        print("\n暂无重要快讯")

    # 最新港股新闻
    print("\n📰 港股动态:")
    hk_news = monitor.get_sina_news('hk')
    for n in hk_news[:5]:
        print(f"  [{n['time']}] {n['title'][:50]}")

    # 热门话题
    topics = monitor.get_hot_topics()
    if topics:
        print("\n🔥 热门话题:")
        for t in topics[:5]:
            heat = f"{t['heat']/10000:.1f}万" if t['heat'] > 10000 else str(t['heat'])
            print(f"  {t['title']}: {heat}")

    print("\n" + "=" * 70)


def monitor_keywords(keywords: List[str], interval: int = 60):
    """监控关键词"""
    monitor = NewsMonitor()

    print(f"\n开始监控关键词: {', '.join(keywords)}")
    print(f"刷新间隔: {interval}秒")
    print("按 Ctrl+C 停止\n")

    seen_titles = set()

    while True:
        try:
            news = monitor.get_cls_flash()

            for n in news:
                title = n['title']
                if title in seen_titles:
                    continue

                # 检查是否包含关键词
                for kw in keywords:
                    if kw.lower() in title.lower():
                        seen_titles.add(title)
                        icon = '🔴' if n.get('important') else '📰'
                        print(f"{icon} [{n['time']}] [{kw}] {title}")
                        print('\a')  # 响铃
                        break

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n停止监控")
            break


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python news_monitor.py hk       - 港股新闻")
        print("  python news_monitor.py flash    - 财经快讯")
        print("  python news_monitor.py scan     - 快速扫描重要新闻")
        print("  python news_monitor.py search 腾讯  - 搜索新闻")
        print("  python news_monitor.py watch 腾讯,阿里  - 监控关键词")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'hk':
        show_hk_news()
    elif cmd == 'flash':
        show_flash()
    elif cmd == 'scan':
        quick_scan()
    elif cmd == 'search' and len(sys.argv) >= 3:
        search_news(sys.argv[2])
    elif cmd == 'watch' and len(sys.argv) >= 3:
        keywords = sys.argv[2].split(',')
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        monitor_keywords(keywords, interval)
    else:
        print("未知命令")
