#!/usr/bin/env python3
"""
X (Twitter) API 集成
获取港股相关推文、提及次数、互动数据
"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class XAPIClient:
    """X (Twitter) API 客户端"""

    def __init__(self, bearer_token: str = None):
        """
        初始化X API客户端

        参数：
        - bearer_token: X API Bearer Token (或从环境变量X_BEARER_TOKEN获取)
        """
        self.bearer_token = bearer_token or os.getenv('X_BEARER_TOKEN')
        if not self.bearer_token:
            raise ValueError("未找到X API Token，请设置X_BEARER_TOKEN环境变量")

        self.base_url = 'https://api.twitter.com/2'
        self.headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }

    def search_recent_tweets(self, query: str, max_results: int = 10) -> Dict:
        """
        搜索最近7天的推文

        参数：
        - query: 搜索关键词（如：优必选 OR UBTECH）
        - max_results: 返回结果数量（10-100）

        返回：
        {
            'tweets': [...],
            'total_count': 123,
            'mentions': 456
        }
        """
        try:
            endpoint = f'{self.base_url}/tweets/search/recent'

            params = {
                'query': query,
                'max_results': min(max_results, 100),
                'tweet.fields': 'created_at,public_metrics,author_id,lang',
                'expansions': 'author_id',
                'user.fields': 'username,verified'
            }

            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_tweet_response(data)
            elif response.status_code == 429:
                print("⚠️ X API 配额用完，请稍后再试")
                return self._empty_result()
            else:
                print(f"⚠️ X API错误: {response.status_code}")
                return self._empty_result()

        except Exception as e:
            print(f"⚠️ X API请求失败: {e}")
            return self._empty_result()

    def get_stock_mentions(self, stock_name: str, stock_code: str) -> Dict:
        """
        获取港股提及数据

        参数：
        - stock_name: 股票名称（如：优必选）
        - stock_code: 股票代码（如：09880）

        返回：
        {
            'mention_count': 123,
            'total_likes': 456,
            'total_retweets': 789,
            'sentiment_preview': 'positive/neutral/negative',
            'top_tweets': [...]
        }
        """
        # 构建搜索查询
        code_short = stock_code.replace('HK.', '').lstrip('0')
        query = f'({stock_name} OR {code_short} OR ${code_short}) lang:zh'

        result = self.search_recent_tweets(query, max_results=50)

        if result['total_count'] == 0:
            return self._empty_mention_result()

        # 统计互动数据
        total_likes = 0
        total_retweets = 0
        top_tweets = []

        for tweet in result['tweets']:
            metrics = tweet.get('public_metrics', {})
            total_likes += metrics.get('like_count', 0)
            total_retweets += metrics.get('retweet_count', 0)

            # 保存高互动推文
            if metrics.get('like_count', 0) > 10:
                top_tweets.append({
                    'text': tweet.get('text', ''),
                    'likes': metrics.get('like_count', 0),
                    'retweets': metrics.get('retweet_count', 0),
                    'created_at': tweet.get('created_at', '')
                })

        # 简单情绪预判（基于关键词）
        sentiment = self._predict_sentiment(result['tweets'])

        return {
            'mention_count': result['total_count'],
            'total_likes': total_likes,
            'total_retweets': total_retweets,
            'sentiment_preview': sentiment,
            'top_tweets': sorted(top_tweets, key=lambda x: x['likes'], reverse=True)[:3]
        }

    def get_sector_heat(self, sector_name: str, keywords: List[str]) -> Dict:
        """
        获取板块整体热度

        参数：
        - sector_name: 板块名称（如：人形机器人）
        - keywords: 相关关键词列表

        返回：
        {
            'heat_score': 0-100,
            'mention_count': 123,
            'total_engagement': 456
        }
        """
        # 构建OR查询
        keyword_query = ' OR '.join([f'"{kw}"' for kw in keywords])
        query = f'({keyword_query}) lang:zh'

        result = self.search_recent_tweets(query, max_results=100)

        if result['total_count'] == 0:
            return {'heat_score': 0, 'mention_count': 0, 'total_engagement': 0}

        # 计算总互动
        total_engagement = 0
        for tweet in result['tweets']:
            metrics = tweet.get('public_metrics', {})
            total_engagement += (
                metrics.get('like_count', 0) +
                metrics.get('retweet_count', 0) * 2 +
                metrics.get('reply_count', 0)
            )

        # 热度评分（0-100）
        # 基于提及次数和互动量
        mention_score = min(result['total_count'] / 50 * 50, 50)  # 50次提及=50分
        engagement_score = min(total_engagement / 1000 * 50, 50)  # 1000互动=50分
        heat_score = int(mention_score + engagement_score)

        return {
            'heat_score': heat_score,
            'mention_count': result['total_count'],
            'total_engagement': total_engagement
        }

    def _parse_tweet_response(self, data: Dict) -> Dict:
        """解析X API响应"""
        tweets = data.get('data', [])
        meta = data.get('meta', {})

        return {
            'tweets': tweets,
            'total_count': meta.get('result_count', 0),
            'mentions': len(tweets)
        }

    def _predict_sentiment(self, tweets: List[Dict]) -> str:
        """
        简单情绪预判（基于关键词）
        """
        positive_keywords = ['利好', '大涨', '突破', '订单', '看好', '牛', '🚀', '📈']
        negative_keywords = ['暴跌', '利空', '下跌', '熊', '📉', '跑路']

        positive_count = 0
        negative_count = 0

        for tweet in tweets[:20]:  # 只看前20条
            text = tweet.get('text', '').lower()
            if any(kw in text for kw in positive_keywords):
                positive_count += 1
            if any(kw in text for kw in negative_keywords):
                negative_count += 1

        if positive_count > negative_count * 1.5:
            return 'positive'
        elif negative_count > positive_count * 1.5:
            return 'negative'
        else:
            return 'neutral'

    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'tweets': [],
            'total_count': 0,
            'mentions': 0
        }

    def _empty_mention_result(self) -> Dict:
        """返回空提及结果"""
        return {
            'mention_count': 0,
            'total_likes': 0,
            'total_retweets': 0,
            'sentiment_preview': 'unknown',
            'top_tweets': []
        }


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试X API集成")
    print("="*60 + "\n")

    # 检查Token
    bearer_token = os.getenv('X_BEARER_TOKEN')
    if not bearer_token:
        print("❌ 未设置X_BEARER_TOKEN环境变量")
        print("\n请先配置：")
        print("export X_BEARER_TOKEN='your-x-bearer-token'")
        print("\n获取方式：")
        print("1. 访问 https://developer.twitter.com/")
        print("2. 创建项目和App")
        print("3. 获取Bearer Token")
        exit(1)

    client = XAPIClient(bearer_token)

    # 测试1: 搜索优必选
    print("🧪 测试1: 搜索优必选相关推文...\n")
    result = client.get_stock_mentions("优必选", "09880")

    print(f"提及次数: {result['mention_count']}")
    print(f"总点赞: {result['total_likes']}")
    print(f"总转发: {result['total_retweets']}")
    print(f"情绪预判: {result['sentiment_preview']}")

    if result['top_tweets']:
        print(f"\n📌 热门推文:")
        for i, tweet in enumerate(result['top_tweets'], 1):
            print(f"\n{i}. {tweet['text'][:100]}...")
            print(f"   👍 {tweet['likes']} | 🔄 {tweet['retweets']}")

    # 测试2: 板块热度
    print("\n" + "="*60)
    print("🧪 测试2: 人形机器人板块热度...\n")

    heat = client.get_sector_heat("人形机器人", ["人形机器人", "优必选", "特斯拉机器人"])

    print(f"热度评分: {heat['heat_score']}/100")
    print(f"提及次数: {heat['mention_count']}")
    print(f"总互动: {heat['total_engagement']}")

    print("\n✅ 测试完成")
