#!/usr/bin/env python3
"""
富途快讯获取器
- 获取7×24小时实时财经快讯
- 过滤指定股票相关新闻
- 集成到交易系统
"""

import requests
import json
from datetime import datetime
from typing import Optional, List, Dict

class FutuNewsFetcher:
    """富途快讯获取器"""

    def __init__(self):
        self.base_url = "https://news.futunn.com/news-site-api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://news.futunn.com/main/live",
            "Origin": "https://news.futunn.com"
        }

    def get_flash_news(self, page_size: int = 30) -> List[Dict]:
        """
        获取快讯列表

        Args:
            page_size: 获取条数，默认30条

        Returns:
            新闻列表
        """
        url = f"{self.base_url}/main/get-flash-list?pageSize={page_size}"

        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0 and 'data' in data:
                    news_list = data['data'].get('data', {}).get('news', [])
                    return self._format_news_list(news_list)
            return []
        except Exception as e:
            print(f"获取快讯失败: {e}")
            return []

    def _format_news_list(self, news_list: List) -> List[Dict]:
        """格式化新闻列表"""
        formatted = []
        for news in news_list:
            formatted.append({
                'id': news.get('id'),
                'title': news.get('title', ''),
                'content': news.get('content', ''),
                'time': datetime.fromtimestamp(int(news.get('time', 0))).strftime('%Y-%m-%d %H:%M:%S') if news.get('time') else '',
                'timestamp': int(news.get('time', 0)),
                'url': f"https://news.futunn.com/flash/{news.get('id')}",
                'stocks': news.get('stocks', []),  # 相关股票
                'important': news.get('important', 0),  # 是否重要
            })
        return formatted

    def filter_by_stock(self, stock_code: str, news_list: Optional[List] = None) -> List[Dict]:
        """
        过滤指定股票相关新闻

        Args:
            stock_code: 股票代码，如 "09880" 或 "优必选"
            news_list: 新闻列表，不传则自动获取

        Returns:
            相关新闻列表
        """
        if news_list is None:
            news_list = self.get_flash_news(100)

        # 标准化股票代码
        code = stock_code.replace('HK.', '').replace('.HK', '')

        related = []
        for news in news_list:
            # 检查股票代码和内容
            content = (news['title'] + news['content']).lower()
            if code.lower() in content or stock_code.lower() in content:
                related.append(news)

        return related

    def get_important_news(self, hours: int = 24) -> List[Dict]:
        """
        获取重要新闻

        Args:
            hours: 获取最近多少小时的新闻

        Returns:
            重要新闻列表
        """
        news_list = self.get_flash_news(100)
        now = datetime.now().timestamp()
        cutoff = now - (hours * 3600)

        important = []
        for news in news_list:
            if news['timestamp'] >= cutoff:
                # 判断是否重要
                content = news['title'] + news['content']
                is_important = any([
                    news.get('important', 0) > 0,
                    '突破' in content,
                    '暴涨' in content,
                    '暴跌' in content,
                    '利好' in content,
                    '利空' in content,
                    '重大' in content,
                    '紧急' in content,
                    '央行' in content,
                    '美联储' in content,
                ])
                if is_important:
                    important.append(news)

        return important

    def search_keyword(self, keyword: str, page_size: int = 50) -> List[Dict]:
        """
        搜索包含关键词的新闻

        Args:
            keyword: 搜索关键词
            page_size: 搜索范围

        Returns:
            匹配的新闻列表
        """
        news_list = self.get_flash_news(page_size)
        matched = []

        for news in news_list:
            content = (news['title'] + news['content']).lower()
            if keyword.lower() in content:
                matched.append(news)

        return matched


def print_news_list(news_list: List[Dict], title: str = "快讯"):
    """打印新闻列表"""
    print(f"\n{'='*60}")
    print(f"📰 {title} (共{len(news_list)}条)")
    print('='*60)

    for i, news in enumerate(news_list, 1):
        print(f"\n{i}. [{news['time']}]")
        if news['title']:
            print(f"   📌 {news['title'][:60]}")
        print(f"   {news['content'][:100]}...")
        print(f"   🔗 {news['url']}")


if __name__ == "__main__":
    import sys

    fetcher = FutuNewsFetcher()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'latest':
            # 获取最新快讯
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            news = fetcher.get_flash_news(count)
            print_news_list(news, f"最新{count}条快讯")

        elif cmd == 'stock':
            # 搜索股票相关新闻
            if len(sys.argv) > 2:
                code = sys.argv[2]
                news = fetcher.filter_by_stock(code)
                print_news_list(news, f"股票 {code} 相关快讯")
            else:
                print("用法: python futu_news_fetcher.py stock <股票代码>")

        elif cmd == 'search':
            # 搜索关键词
            if len(sys.argv) > 2:
                keyword = sys.argv[2]
                news = fetcher.search_keyword(keyword)
                print_news_list(news, f"关键词 '{keyword}' 相关快讯")
            else:
                print("用法: python futu_news_fetcher.py search <关键词>")

        elif cmd == 'important':
            # 获取重要新闻
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            news = fetcher.get_important_news(hours)
            print_news_list(news, f"最近{hours}小时重要快讯")

        else:
            print("用法:")
            print("  python futu_news_fetcher.py latest [数量]     # 最新快讯")
            print("  python futu_news_fetcher.py stock <代码>      # 股票相关")
            print("  python futu_news_fetcher.py search <关键词>   # 搜索关键词")
            print("  python futu_news_fetcher.py important [小时]  # 重要新闻")
    else:
        # 默认显示最新10条
        news = fetcher.get_flash_news(10)
        print_news_list(news, "最新10条快讯")
