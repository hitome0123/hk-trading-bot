#!/usr/bin/env python3
"""
新浪财经资讯抓取
新浪的API相对开放，稳定性好
"""
import requests
import json
import re
from datetime import datetime
from typing import List, Dict

class SinaNewsFetcher:
    """新浪财经资讯抓取器"""

    def __init__(self):
        self.base_url = "https://finance.sina.com.cn"

    def fetch_hk_stock_news(self, stock_code: str, limit=10) -> List[Dict]:
        """
        获取港股个股新闻
        stock_code: HK.09880 -> 09880
        """
        news_list = []

        try:
            # 转换代码
            if stock_code.startswith('HK.'):
                code = stock_code.replace('HK.', '')
            else:
                code = stock_code

            # 新浪港股资讯API
            url = f"https://vip.stock.finance.sina.com.cn/corp/view/vII_NewsBulletin.php"
            params = {
                'symbol': code,
                'page': 1,
                'num': limit
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                # 新浪返回的是HTML，需要解析
                html = response.text

                # 提取新闻标题和时间
                # 使用正则匹配
                pattern = r'<a[^>]*target="_blank"[^>]*>([^<]+)</a>.*?(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
                matches = re.findall(pattern, html, re.DOTALL)

                for title, pub_time in matches[:limit]:
                    clean_title = title.strip()
                    if clean_title and len(clean_title) > 5:
                        news_list.append({
                            'title': clean_title,
                            'source': '新浪财经',
                            'time': pub_time,
                            'platform': 'sina',
                            'type': 'news'
                        })

        except Exception as e:
            print(f"新浪财经抓取失败: {e}")

        return news_list

    def fetch_finance_headlines(self, limit=20) -> List[Dict]:
        """
        获取财经要闻头条
        实时更新的财经新闻
        """
        news_list = []

        try:
            # 新浪财经头条API
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                'pageid': '153',
                'lid': '2509',
                'num': limit,
                'versionNumber': '1.2.8',
                'page': 1,
                'encode': 'utf-8'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'result' in data and 'data' in data['result']:
                    for item in data['result']['data'][:limit]:
                        title = item.get('title', '').strip()
                        if title and len(title) > 5:
                            news_list.append({
                                'title': title,
                                'source': '新浪财经',
                                'time': item.get('intime', ''),
                                'platform': 'sina',
                                'type': 'headline',
                                'url': item.get('url', '')
                            })

        except Exception as e:
            print(f"新浪头条抓取失败: {e}")

        return news_list

    def fetch_stock_hot_news(self, limit=15) -> List[Dict]:
        """
        获取股市热点新闻
        """
        news_list = []

        try:
            # 新浪股市热点API
            url = "https://finance.sina.com.cn/7x24/"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                html = response.text

                # 提取7x24快讯
                # 匹配格式: <div class="bd_i_txt_c">...</div>
                pattern = r'<div class="bd_i_txt_c">.*?<a[^>]*>([^<]+)</a>.*?<span class="bd_i_time">([^<]+)</span>'
                matches = re.findall(pattern, html, re.DOTALL)

                for title, pub_time in matches[:limit]:
                    clean_title = title.strip()
                    if clean_title and len(clean_title) > 10:
                        news_list.append({
                            'title': clean_title,
                            'source': '新浪7x24',
                            'time': pub_time.strip(),
                            'platform': 'sina',
                            'type': '7x24'
                        })

        except Exception as e:
            pass

        return news_list

    def search_keyword(self, keyword: str, limit=10) -> List[Dict]:
        """
        搜索关键词相关新闻
        """
        news_list = []

        try:
            # 新浪搜索API
            url = "https://search.sina.com.cn/"
            params = {
                'q': keyword,
                'c': 'finance',
                'from': 'index',
                'ie': 'utf-8'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                html = response.text

                # 提取搜索结果
                pattern = r'<h2><a[^>]*>([^<]+)</a></h2>'
                matches = re.findall(pattern, html)

                for title in matches[:limit]:
                    clean_title = title.strip()
                    if clean_title:
                        news_list.append({
                            'title': clean_title,
                            'source': '新浪搜索',
                            'time': '',
                            'platform': 'sina',
                            'type': 'search'
                        })

        except Exception as e:
            pass

        return news_list


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试新浪财经API")
    print("="*60 + "\n")

    sina = SinaNewsFetcher()

    # 1. 财经头条
    print("📰 财经头条（前10条）:\n")
    headlines = sina.fetch_finance_headlines(limit=10)
    if headlines:
        for i, news in enumerate(headlines, 1):
            print(f"{i}. [{news['time']}] {news['title'][:70]}")
        print(f"\n✅ 共 {len(headlines)} 条")
    else:
        print("⚠️ 未获取到头条")

    # 2. 股市热点
    print("\n" + "="*60)
    print("股市热点快讯")
    print("="*60 + "\n")

    hot_news = sina.fetch_stock_hot_news(limit=10)
    if hot_news:
        for i, news in enumerate(hot_news, 1):
            print(f"{i}. [{news['time']}] {news['title'][:70]}")
        print(f"\n✅ 共 {len(hot_news)} 条")
    else:
        print("⚠️ 未获取到热点")

    # 3. 搜索个股
    print("\n" + "="*60)
    print("搜索「优必选」")
    print("="*60 + "\n")

    search_results = sina.search_keyword('优必选', limit=5)
    if search_results:
        for i, news in enumerate(search_results, 1):
            print(f"{i}. {news['title']}")
        print(f"\n✅ 共 {len(search_results)} 条")
    else:
        print("⚠️ 未找到相关新闻")

    # 4. 港股个股新闻
    print("\n" + "="*60)
    print("港股 09880 个股新闻")
    print("="*60 + "\n")

    stock_news = sina.fetch_hk_stock_news('HK.09880', limit=5)
    if stock_news:
        for i, news in enumerate(stock_news, 1):
            print(f"{i}. [{news['time']}] {news['title']}")
        print(f"\n✅ 共 {len(stock_news)} 条")
    else:
        print("⚠️ 未找到个股新闻")
