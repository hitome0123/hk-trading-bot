#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能社区情绪分析器 (自动解析WebSearch结果)
用于Claude Code环境，自动提取股票代码、热门话题、情绪指标
"""

import re
from typing import Dict, List, Set
from datetime import datetime


class SentimentAutoAnalyzer:
    """自动情绪分析器"""

    def __init__(self):
        """初始化"""
        self.stock_patterns = {
            'us': r'\b([A-Z]{2,5})\b|\$([A-Z]{1,5})\b',  # TSLA, $NVDA
            'hk': r'\b(\d{5}\.HK)\b',                     # 00700.HK
            'korea': r'\b(\d{6}\.KS)\b',                  # 005930.KS
        }

    def extract_stocks(self, text: str, region: str = 'us') -> Set[str]:
        """
        从文本中提取股票代码

        Args:
            text: 搜索结果文本
            region: 'us', 'hk', 'korea'

        Returns:
            股票代码集合
        """
        stocks = set()
        pattern = self.stock_patterns.get(region, self.stock_patterns['us'])

        matches = re.findall(pattern, text)
        for match in matches:
            # match可能是tuple (group1, group2)
            stock = match[0] if isinstance(match, tuple) else match
            if stock and len(stock) >= 2:
                stocks.add(stock)

        return stocks

    def extract_mentions(self, text: str) -> Dict[str, int]:
        """
        提取股票提及次数

        Args:
            text: 搜索结果文本

        Returns:
            {股票代码: 提及次数}
        """
        stocks = self.extract_stocks(text, 'us')
        mentions = {}

        for stock in stocks:
            # 简单计数
            count = text.upper().count(stock.upper())
            if count > 1:  # 至少提及2次才算
                mentions[stock] = count

        return dict(sorted(mentions.items(), key=lambda x: x[1], reverse=True))

    def detect_sentiment(self, text: str) -> str:
        """
        检测情绪倾向

        Args:
            text: 搜索结果文本

        Returns:
            'bullish', 'bearish', 'neutral'
        """
        bullish_keywords = [
            'buy', 'long', 'bullish', 'moon', 'rocket', '🚀',
            'breakout', 'rally', 'surge', 'soar', 'gain',
            'calls', 'upside', 'target price raised'
        ]

        bearish_keywords = [
            'sell', 'short', 'bearish', 'crash', 'dump',
            'drop', 'fall', 'decline', 'plunge', 'puts',
            'downside', 'target price cut', 'downgrade'
        ]

        text_lower = text.lower()

        bullish_count = sum(1 for kw in bullish_keywords if kw in text_lower)
        bearish_count = sum(1 for kw in bearish_keywords if kw in text_lower)

        if bullish_count > bearish_count * 1.5:
            return 'bullish'
        elif bearish_count > bullish_count * 1.5:
            return 'bearish'
        else:
            return 'neutral'

    def extract_topics(self, text: str) -> List[str]:
        """
        提取热门话题

        Args:
            text: 搜索结果文本

        Returns:
            话题列表
        """
        topics = []

        # 常见话题关键词
        topic_keywords = {
            'AI': ['AI', 'artificial intelligence', 'machine learning', 'GPT', 'LLM'],
            '太空': ['space', 'satellite', 'rocket', 'SpaceX', 'orbit'],
            '芯片': ['chip', 'semiconductor', 'NVIDIA', 'memory', 'GPU'],
            '电动车': ['EV', 'electric vehicle', 'Tesla', 'battery'],
            '加密货币': ['crypto', 'bitcoin', 'ethereum', 'BTC', 'ETH'],
            '生物科技': ['biotech', 'drug', 'FDA', 'pharma'],
            '能源': ['energy', 'oil', 'renewable', 'solar', 'nuclear'],
        }

        text_lower = text.lower()

        for topic, keywords in topic_keywords.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    topics.append(topic)
                    break  # 找到一个关键词就够了

        return topics

    def analyze_websearch_result(self, search_result: str, region: str = 'usa') -> Dict:
        """
        综合分析WebSearch结果

        Args:
            search_result: WebSearch返回的文本
            region: 'korea', 'usa', 'musk'

        Returns:
            分析结果字典
        """
        return {
            'region': region,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'mentioned_stocks': self.extract_mentions(search_result),
            'top_stocks': list(self.extract_mentions(search_result).keys())[:10],
            'sentiment': self.detect_sentiment(search_result),
            'hot_topics': self.extract_topics(search_result),
            'stock_count': len(self.extract_stocks(search_result, 'us'))
        }

    def format_analysis_report(self, analysis: Dict) -> str:
        """
        格式化分析报告

        Args:
            analysis: analyze_websearch_result的结果

        Returns:
            格式化报告
        """
        output = []
        output.append("=" * 70)
        output.append(f"📊 {analysis['region'].upper()} 社区情绪分析")
        output.append("=" * 70)
        output.append("")
        output.append(f"📅 分析时间: {analysis['timestamp']}")
        output.append(f"🎯 提及股票总数: {analysis['stock_count']}")
        output.append("")

        # 情绪指标
        sentiment_emoji = {
            'bullish': '📈 看涨',
            'bearish': '📉 看跌',
            'neutral': '➡️ 中性'
        }
        output.append(f"【整体情绪】: {sentiment_emoji.get(analysis['sentiment'], '❓')}")
        output.append("")

        # 热门话题
        if analysis['hot_topics']:
            output.append("【热门话题】")
            for topic in analysis['hot_topics']:
                output.append(f"  • {topic}")
            output.append("")

        # 高频股票
        if analysis['mentioned_stocks']:
            output.append("【高频提及股票 Top 10】")
            for i, (stock, count) in enumerate(list(analysis['mentioned_stocks'].items())[:10], 1):
                heat = "🔥🔥🔥" if count > 10 else "🔥🔥" if count > 5 else "🔥"
                output.append(f"  {i:2d}. {stock:6s} - 提及{count:2d}次 {heat}")
            output.append("")

        output.append("=" * 70)

        return "\n".join(output)


def demo_usa_analysis():
    """演示：分析美国社区"""
    # 这是从WebSearch获取的真实数据
    usa_data = """
    WallStreetBets 2026 Index - Top 10 Stocks:
    1. ASTS (AST SpaceMobile) +241%
    2. RKLB (Rocket Lab)
    3. GOOGL (Alphabet)
    4. AMZN (Amazon)
    5. NBIS (Nebius Group)
    6. RDDT (Reddit)
    7. MU (Micron)
    8. IREN (IREN Ltd)
    9. TSLA (Tesla)
    10. PLTR (Palantir)

    Currently trending: WMT (+291% mentions)
    This week hot: GME, PLTR, TSLA, AMZN

    Bullish sentiment on space stocks ASTS and RKLB.
    AI infrastructure stocks MU and NBIS gaining traction.
    Reddit delivered 76% return in 2025, beating S&P 500's 18%.
    """

    analyzer = SentimentAutoAnalyzer()
    result = analyzer.analyze_websearch_result(usa_data, 'USA')
    report = analyzer.format_analysis_report(result)

    print(report)


def demo_musk_analysis():
    """演示：分析马斯克动态"""
    musk_data = """
    Elon Musk latest news:
    - xAI co-founders leaving (Feb 5)
    - SEC lawsuit update (Feb 3)
    - Tesla AI5 chip in deep review
    - Optimus robot engineering progress
    - SpaceX merged with xAI
    - Grok AI under UK investigation

    Musk tweet: Working on Optimus, Tesla AI5 chip, Colossus II datacenter

    Affected stocks: TSLA facing pressure from negative news
    But long-term bullish on AI and robotics development
    NVDA benefits from AI datacenter demand
    """

    analyzer = SentimentAutoAnalyzer()
    result = analyzer.analyze_websearch_result(musk_data, 'Musk')
    report = analyzer.format_analysis_report(result)

    print(report)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'demo':
        print("=" * 70)
        print("演示1: 美国社区分析")
        print("=" * 70)
        demo_usa_analysis()

        print("\n\n")

        print("=" * 70)
        print("演示2: 马斯克动态分析")
        print("=" * 70)
        demo_musk_analysis()
    else:
        print("""
用法: python sentiment_auto_analyzer.py demo

这个脚本演示如何自动解析WebSearch结果并提取:
- 高频提及股票
- 整体情绪 (看涨/看跌/中性)
- 热门话题
- 提及次数统计

在Claude Code环境中，配合WebSearch工具使用效果最佳。
        """)
