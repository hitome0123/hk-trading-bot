#!/usr/bin/env python3
"""
Grok社区热度情绪分析器
从X/Twitter获取实时社区讨论和情绪分析
"""
import os
import requests
from typing import List, Dict

class GrokSentimentAnalyzer:
    """使用Grok API分析社区热度和情绪"""

    def __init__(self, api_key: str = None):
        """
        初始化Grok分析器

        参数：
        - api_key: Grok API Key (或从环境变量GROK_API_KEY获取)
        """
        self.api_key = api_key or os.getenv('GROK_API_KEY')
        if not self.api_key:
            raise ValueError("未找到Grok API Key，请设置GROK_API_KEY环境变量")

        self.base_url = 'https://api.x.ai/v1'
        self.model = 'grok-beta'

    def analyze_stock_sentiment(self, stock_name: str, stock_code: str) -> Dict:
        """
        分析单个股票的社区热度和情绪

        参数：
        - stock_name: 股票名称（如：优必选）
        - stock_code: 股票代码（如：09880）

        返回：
        {
            'heat_score': 0-100,  # 热度分数
            'sentiment': 'positive/neutral/negative',  # 情绪
            'key_topics': ['话题1', '话题2'],  # 关键话题
            'mentions': 123,  # 提及次数
            'summary': '总结'
        }
        """
        prompt = f"""
搜索X/Twitter上关于港股"{stock_name}"（代码：{stock_code}）的最新讨论（近24小时）。

请分析：
1. 讨论热度（0-100分）
2. 整体情绪（positive/neutral/negative）
3. 主要讨论话题（最多3个）
4. 大约提及次数
5. 一句话总结

返回JSON格式：
{{
    "heat_score": 85,
    "sentiment": "positive",
    "key_topics": ["特斯拉订单", "春晚机器人", "股价大涨"],
    "mentions": 1500,
    "summary": "社区热议特斯拉大订单，情绪非常乐观"
}}
"""

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是专业的金融社交媒体分析师，擅长从X/Twitter提取港股讨论热度和情绪。'
                        },
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']

                # 尝试解析JSON
                import json
                sentiment_data = json.loads(content)
                return sentiment_data
            else:
                print(f"⚠️ Grok API错误: {response.status_code}")
                return self._empty_result()

        except Exception as e:
            print(f"⚠️ Grok分析失败: {e}")
            return self._empty_result()

    def analyze_sector_sentiment(self, sector_name: str, top_stocks: List[Dict]) -> List[Dict]:
        """
        分析整个板块的社区热度

        参数：
        - sector_name: 板块名称（如：人形机器人）
        - top_stocks: 板块内龙头股列表 [{'name': '优必选', 'code': 'HK.09880'}, ...]

        返回：
        板块整体情绪分析 + 各龙头股情绪
        """
        sentiment_list = []

        # 分析板块整体
        print(f"  🤖 Grok分析: {sector_name}板块社区情绪...")

        sector_prompt = f"""
搜索X/Twitter上关于"{sector_name}"概念的最新讨论（近24小时）。

请分析：
1. 板块整体热度（0-100分）
2. 社区情绪（positive/neutral/negative）
3. 热议话题（最多3个）
4. 资金关注度（high/medium/low）

返回JSON格式：
{{
    "heat_score": 90,
    "sentiment": "positive",
    "key_topics": ["政策利好", "龙头突破", "资金抢筹"],
    "capital_attention": "high",
    "summary": "板块受政策催化，资金大幅流入"
}}
"""

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': '你是专业的金融社交媒体分析师。'
                        },
                        {
                            'role': 'user',
                            'content': sector_prompt
                        }
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=15
            )

            if response.status_code == 200:
                import json
                result = response.json()
                content = result['choices'][0]['message']['content']
                sector_sentiment = json.loads(content)

                sentiment_list.append({
                    'type': 'sector',
                    'name': sector_name,
                    'data': sector_sentiment
                })

                print(f"    ✅ 板块热度: {sector_sentiment.get('heat_score', 0)}/100")
                print(f"    ✅ 社区情绪: {sector_sentiment.get('sentiment', 'unknown')}")

        except Exception as e:
            print(f"    ⚠️ 板块分析失败: {e}")

        # 分析龙头股（最多2只）
        for stock in top_stocks[:2]:
            stock_name = stock.get('name', '')
            stock_code = stock.get('code', '').replace('HK.', '')

            print(f"  🤖 Grok分析: {stock_name}...")

            stock_sentiment = self.analyze_stock_sentiment(stock_name, stock_code)
            sentiment_list.append({
                'type': 'stock',
                'name': stock_name,
                'code': stock_code,
                'data': stock_sentiment
            })

            if stock_sentiment.get('heat_score', 0) > 0:
                print(f"    ✅ 热度: {stock_sentiment['heat_score']}/100")
                print(f"    ✅ 情绪: {stock_sentiment['sentiment']}")

        return sentiment_list

    def _empty_result(self) -> Dict:
        """返回空结果"""
        return {
            'heat_score': 0,
            'sentiment': 'unknown',
            'key_topics': [],
            'mentions': 0,
            'summary': '数据获取失败'
        }


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试Grok社区热度分析")
    print("="*60 + "\n")

    # 检查API Key
    api_key = os.getenv('GROK_API_KEY')
    if not api_key:
        print("❌ 未设置GROK_API_KEY环境变量")
        print("\n请先配置：")
        print("export GROK_API_KEY='your-grok-api-key'")
        exit(1)

    analyzer = GrokSentimentAnalyzer(api_key)

    # 测试单股分析
    print("🧪 测试1: 分析优必选...")
    result = analyzer.analyze_stock_sentiment("优必选", "09880")
    print(f"\n结果:")
    print(f"  热度: {result['heat_score']}/100")
    print(f"  情绪: {result['sentiment']}")
    print(f"  话题: {', '.join(result['key_topics'])}")
    print(f"  总结: {result['summary']}")

    # 测试板块分析
    print("\n" + "="*60)
    print("🧪 测试2: 分析人形机器人板块...")

    top_stocks = [
        {'name': '优必选', 'code': 'HK.09880'},
        {'name': '大族机器人', 'code': 'HK.02445'}
    ]

    sector_results = analyzer.analyze_sector_sentiment("人形机器人", top_stocks)

    print(f"\n✅ 分析完成，共{len(sector_results)}项")
