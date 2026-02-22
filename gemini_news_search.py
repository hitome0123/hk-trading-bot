#!/usr/bin/env python3
"""
【方案B】Gemini联网搜索 - 利用Google Search grounding获取实时新闻
"""
import os
import json
from google import genai
from google.genai.types import Tool, GoogleSearch

class GeminiNewsSearcher:
    """使用Gemini的Google Search功能搜索实时新闻"""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("需要设置GEMINI_API_KEY环境变量")

        self.client = genai.Client(api_key=self.api_key)

    def search_stock_news(self, stock_name, stock_code, sector_name):
        """
        使用Gemini搜索港股最新新闻

        参数：
        - stock_name: 股票名称（如"优必选"）
        - stock_code: 股票代码（如"09880"）
        - sector_name: 板块名称（如"人形机器人"）

        返回：
        [
            {
                'title': '新闻标题',
                'summary': '摘要',
                'source': 'Google搜索',
                'confidence': 'high'
            },
            ...
        ]
        """
        try:
            # 构建搜索提示词
            search_query = f"""搜索港股{stock_name}（股票代码{stock_code}）今天或最近3天的最新新闻。

重点关注：
1. 订单、合同、业务进展
2. 业绩预告、财报
3. 政策支持、行业利好
4. 并购、重组、合作
5. 技术突破、产品发布

只返回与{stock_name}直接相关的重要新闻，忽略无关信息。

返回JSON格式：
{{
  "news": [
    {{
      "title": "新闻标题",
      "summary": "一句话摘要（20字内）",
      "date": "日期",
      "impact": "利好/利空/中性"
    }}
  ]
}}"""

            # 使用Google Search grounding
            # 注意：Google Search不能和JSON模式同时使用
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=search_query,
                config={
                    'temperature': 0.3,
                    'tools': [Tool(google_search=GoogleSearch())],  # 启用Google搜索
                }
            )

            # 解析结果（文本格式）
            text = response.text

            # 尝试从文本中提取JSON
            news_list = []
            try:
                # 查找JSON部分
                if '{' in text and '}' in text:
                    json_start = text.find('{')
                    json_end = text.rfind('}') + 1
                    json_str = text[json_start:json_end]
                    result = json.loads(json_str)

                    if 'news' in result and isinstance(result['news'], list):
                        for item in result['news'][:3]:
                            news_list.append({
                                'title': f"🔍 {item.get('title', '')}",
                                'summary': item.get('summary', ''),
                                'source': 'Google搜索',
                                'confidence': 'high' if item.get('impact') == '利好' else 'medium'
                            })
                else:
                    # 如果没有JSON，直接返回摘要
                    if len(text) > 20:
                        news_list.append({
                            'title': f"🔍 搜索到{stock_name}相关信息",
                            'summary': text[:100],
                            'source': 'Google搜索',
                            'confidence': 'medium'
                        })
            except:
                # JSON解析失败，返回文本摘要
                if text and len(text) > 20:
                    news_list.append({
                        'title': f"🔍 {stock_name}最新动态",
                        'summary': text[:100],
                        'source': 'Google搜索',
                        'confidence': 'low'
                    })

            return news_list

        except Exception as e:
            print(f"⚠️ Gemini搜索失败: {e}")
            return []

    def search_sector_news(self, sector_name, top_stocks):
        """
        搜索整个板块的新闻

        参数：
        - sector_name: 板块名称
        - top_stocks: 龙头股票列表

        返回：新闻列表
        """
        all_news = []

        # 搜索板块级新闻
        try:
            search_query = f"""搜索"{sector_name}"板块今天或最近3天的行业新闻。

重点关注：
1. 行业政策、监管变化
2. 重大订单、项目
3. 技术突破、应用进展
4. 市场趋势、资金动向

返回JSON格式：
{{
  "news": [
    {{"title": "标题", "summary": "摘要", "impact": "利好/利空"}}
  ]
}}"""

            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=search_query,
                config={
                    'temperature': 0.3,
                    'tools': [Tool(google_search=GoogleSearch())],
                }
            )

            text = response.text
            try:
                if '{' in text:
                    json_start = text.find('{')
                    json_end = text.rfind('}') + 1
                    result = json.loads(text[json_start:json_end])
                    if 'news' in result:
                        for item in result['news'][:2]:
                            all_news.append({
                                'title': f"📊 {item.get('title', '')}",
                                'source': 'Google搜索（板块）',
                                'confidence': 'medium'
                            })
                else:
                    if text and len(text) > 20:
                        all_news.append({
                            'title': f"📊 {sector_name}板块动态",
                            'summary': text[:80],
                            'source': 'Google搜索（板块）',
                            'confidence': 'low'
                        })
            except:
                pass
        except:
            pass

        # 搜索龙头股新闻
        for stock in top_stocks[:2]:  # 只搜索前2只龙头
            stock_code = stock['code'].replace('HK.', '').lstrip('0')
            stock_news = self.search_stock_news(stock['name'], stock_code, sector_name)
            all_news.extend(stock_news)

        return all_news[:5]  # 最多5条


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试Gemini联网搜索")
    print("="*60 + "\n")

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ 未设置GEMINI_API_KEY")
        exit(1)

    searcher = GeminiNewsSearcher()

    # 测试搜索优必选新闻
    print("🔍 搜索优必选最新新闻...\n")
    news = searcher.search_stock_news("优必选", "09880", "人形机器人")

    if news:
        print(f"✅ 找到 {len(news)} 条新闻:\n")
        for item in news:
            print(f"  {item['title']}")
            if 'summary' in item:
                print(f"    摘要: {item['summary']}")
            print()
    else:
        print("❌ 未找到相关新闻")
