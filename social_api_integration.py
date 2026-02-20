#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
社交媒体API集成 - Reddit + Twitter/X

使用现成工具:
1. Reddit: PRAW + ApeWisdom API
2. Twitter/X: 由于API太贵，使用WebSearch替代
3. 情绪分析: VADER (Valence Aware Dictionary)

安装依赖:
pip install praw vaderSentiment requests
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

# 检查依赖
try:
    import praw
    HAS_PRAW = True
except ImportError:
    HAS_PRAW = False
    print("⚠️ 未安装PRAW，Reddit功能不可用")
    print("   安装: pip install praw")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    HAS_VADER = True
except ImportError:
    HAS_VADER = False
    print("⚠️ 未安装VADER，情绪分析不可用")
    print("   安装: pip install vaderSentiment")


class RedditSentimentTracker:
    """
    Reddit情绪追踪器

    使用方案1: PRAW API (需要Reddit API credentials)
    使用方案2: ApeWisdom API (免费，无需认证)
    """

    def __init__(self, use_praw: bool = False):
        """
        初始化

        Args:
            use_praw: 是否使用PRAW (需配置credentials)
        """
        self.use_praw = use_praw and HAS_PRAW
        self.reddit = None

        if self.use_praw:
            # PRAW配置 (需要在 https://www.reddit.com/prefs/apps 创建应用)
            self.reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID', 'YOUR_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET', 'YOUR_SECRET'),
                user_agent='hk-trading-bot/1.0'
            )

        # VADER情绪分析器
        self.vader = SentimentIntensityAnalyzer() if HAS_VADER else None

    def get_wsb_trending_via_apewisdom(self) -> Dict:
        """
        通过ApeWisdom API获取WallStreetBets热门股票 (免费，无需认证)

        API文档: https://apewisdom.io/api/

        Returns:
            热门股票数据
        """
        try:
            url = "https://apewisdom.io/api/v1.0/filter/all-stocks/page/1"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 解析数据
            results = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'ApeWisdom API',
                'stocks': []
            }

            if 'results' in data:
                for stock in data['results'][:20]:  # 取前20
                    results['stocks'].append({
                        'ticker': stock.get('ticker', ''),
                        'name': stock.get('name', ''),
                        'mentions': stock.get('mentions', 0),
                        'rank': stock.get('rank', 0),
                        'upvotes': stock.get('upvotes', 0),
                        'rank_24h_ago': stock.get('rank_24h_ago', 0),
                    })

            return results

        except Exception as e:
            return {'error': f'ApeWisdom API请求失败: {str(e)}'}

    def get_wsb_hot_via_praw(self, limit: int = 25) -> List[Dict]:
        """
        通过PRAW直接获取WallStreetBets热帖 (需要API credentials)

        Args:
            limit: 获取帖子数量

        Returns:
            帖子列表
        """
        if not self.reddit:
            return [{'error': 'PRAW未配置'}]

        try:
            subreddit = self.reddit.subreddit('wallstreetbets')
            posts = []

            for submission in subreddit.hot(limit=limit):
                # 情绪分析
                sentiment_score = None
                if self.vader:
                    scores = self.vader.polarity_scores(submission.title + ' ' + submission.selftext)
                    sentiment_score = scores['compound']  # -1 (负面) 到 +1 (正面)

                posts.append({
                    'title': submission.title,
                    'score': submission.score,
                    'upvote_ratio': submission.upvote_ratio,
                    'num_comments': submission.num_comments,
                    'created_utc': submission.created_utc,
                    'url': submission.url,
                    'sentiment': sentiment_score
                })

            return posts

        except Exception as e:
            return [{'error': f'PRAW请求失败: {str(e)}'}]

    def format_apewisdom_report(self, data: Dict) -> str:
        """格式化ApeWisdom报告"""
        if 'error' in data:
            return f"❌ 错误: {data['error']}"

        output = []
        output.append("=" * 70)
        output.append("📊 WallStreetBets 热门股票排行 (ApeWisdom)")
        output.append("=" * 70)
        output.append("")
        output.append(f"📅 更新时间: {data['timestamp']}")
        output.append(f"📡 数据来源: {data['source']}")
        output.append("")

        output.append(f"{'排名':<6} {'代码':<8} {'提及次数':<12} {'点赞':<10} {'24h变化':<10}")
        output.append("-" * 70)

        for stock in data['stocks']:
            rank = stock['rank']
            ticker = stock['ticker']
            mentions = stock['mentions']
            upvotes = stock['upvotes']
            rank_change = stock['rank_24h_ago'] - rank if stock['rank_24h_ago'] > 0 else 0

            change_emoji = "📈" if rank_change > 0 else "📉" if rank_change < 0 else "➡️"
            heat_emoji = "🔥🔥🔥" if mentions > 1000 else "🔥🔥" if mentions > 500 else "🔥" if mentions > 100 else ""

            output.append(f"#{rank:<5} {ticker:<8} {mentions:<12} {upvotes:<10} {change_emoji} {rank_change:+3d} {heat_emoji}")

        output.append("")
        output.append("=" * 70)
        output.append("💡 说明: 排名基于Reddit r/wallstreetbets的24小时提及次数")
        output.append("=" * 70)

        return "\n".join(output)


class TwitterMuskTracker:
    """
    马斯克推特追踪器

    注意: X API太贵 ($200-5000/月)
    建议使用WebSearch或第三方scraping服务
    """

    def __init__(self):
        """初始化"""
        self.musk_user_id = "elonmusk"

    def get_musk_tweets_via_websearch_hint(self) -> str:
        """
        获取马斯克推文 - WebSearch方案 (推荐)

        Returns:
            WebSearch查询建议
        """
        queries = {
            'latest': 'Elon Musk twitter latest tweets today',
            'tesla': 'Elon Musk Tesla tweet stock',
            'ai': 'Elon Musk AI xAI Grok tweet',
            'crypto': 'Elon Musk bitcoin dogecoin tweet'
        }

        output = []
        output.append("=" * 70)
        output.append("🔍 马斯克推特追踪 - WebSearch方案")
        output.append("=" * 70)
        output.append("")
        output.append("由于X API费用高昂 ($200-5000/月)，建议使用WebSearch")
        output.append("")
        output.append("【推荐查询】")

        for i, (key, query) in enumerate(queries.items(), 1):
            output.append(f"  {i}. {key}: {query}")

        output.append("")
        output.append("=" * 70)
        output.append("💡 替代方案:")
        output.append("   1. 使用Claude Code的WebSearch工具 (最简单)")
        output.append("   2. 第三方scraping服务 (如SociaVault, ~$10/10k推文)")
        output.append("   3. 官方X API (太贵，不推荐个人用户)")
        output.append("=" * 70)

        return "\n".join(output)

    def analyze_musk_impact(self, tweet_text: str) -> Dict:
        """
        分析马斯克推文影响 (需要VADER)

        Args:
            tweet_text: 推文内容

        Returns:
            影响分析
        """
        if not HAS_VADER:
            return {'error': 'VADER未安装'}

        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(tweet_text)

        # 提取股票代码
        import re
        stock_pattern = r'\$([A-Z]{1,5})\b|\\b([A-Z]{2,5})\b'
        mentioned_stocks = re.findall(stock_pattern, tweet_text)
        stocks = list(set([s[0] or s[1] for s in mentioned_stocks if s[0] or s[1]]))

        return {
            'sentiment': scores,
            'mentioned_stocks': stocks,
            'impact_level': 'high' if abs(scores['compound']) > 0.5 else 'medium' if abs(scores['compound']) > 0.2 else 'low',
            'bullish': scores['compound'] > 0.2,
            'bearish': scores['compound'] < -0.2
        }


def demo_reddit_apewisdom():
    """演示: ApeWisdom API"""
    tracker = RedditSentimentTracker(use_praw=False)
    data = tracker.get_wsb_trending_via_apewisdom()
    report = tracker.format_apewisdom_report(data)
    print(report)


def demo_musk_tracker():
    """演示: 马斯克追踪器"""
    tracker = TwitterMuskTracker()
    hint = tracker.get_musk_tweets_via_websearch_hint()
    print(hint)

    # 模拟分析一条推文
    if HAS_VADER:
        print("\n\n")
        print("=" * 70)
        print("演示: 推文影响分析")
        print("=" * 70)
        print("")

        sample_tweet = "Tesla AI5 chip is going to be amazing! Full self-driving coming soon. $TSLA"
        result = tracker.analyze_musk_impact(sample_tweet)

        print(f"推文内容: {sample_tweet}")
        print(f"情绪得分: {result['sentiment']['compound']:.2f} (-1负面 到 +1正面)")
        print(f"提及股票: {result['mentioned_stocks']}")
        print(f"影响级别: {result['impact_level']}")
        print(f"看涨: {'✅' if result['bullish'] else '❌'}")
        print(f"看跌: {'✅' if result['bearish'] else '❌'}")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
用法: python social_api_integration.py <command>

命令:
  reddit      - 获取Reddit WallStreetBets热门股票 (ApeWisdom API)
  musk        - 马斯克推特追踪提示
  demo        - 完整演示

依赖安装:
  pip install praw vaderSentiment requests

配置说明:
  Reddit PRAW (可选):
    1. 访问 https://www.reddit.com/prefs/apps
    2. 创建应用获取 client_id 和 client_secret
    3. 设置环境变量:
       export REDDIT_CLIENT_ID='your_id'
       export REDDIT_CLIENT_SECRET='your_secret'

  ApeWisdom API (推荐):
    - 无需配置，直接使用

  Twitter/X (不推荐):
    - API太贵 ($200-5000/月)
    - 建议使用WebSearch替代
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'reddit':
        demo_reddit_apewisdom()
    elif cmd == 'musk':
        demo_musk_tracker()
    elif cmd == 'demo':
        print("=" * 70)
        print("演示1: Reddit WallStreetBets (ApeWisdom API)")
        print("=" * 70)
        demo_reddit_apewisdom()

        print("\n\n")

        print("=" * 70)
        print("演示2: 马斯克推特追踪")
        print("=" * 70)
        demo_musk_tracker()
    else:
        print(f"❌ 未知命令: {cmd}")


if __name__ == "__main__":
    main()
