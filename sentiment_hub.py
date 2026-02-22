#!/usr/bin/env python3
"""
社区情绪分析中心 (Sentiment Hub)
整合多个数据源分析股票/板块的社区情绪

数据源:
1. Grok API - X/Twitter 实时讨论 (需要 GROK_API_KEY)
2. X API - Twitter 搜索 (需要 X_BEARER_TOKEN)
3. Reddit/WSB - ApeWisdom API (免费)
4. Gemini Search - Google 搜索社交讨论 (需要 GEMINI_API_KEY)

使用:
    python sentiment_hub.py 优必选          # 分析单只股票
    python sentiment_hub.py --sector 人形机器人   # 分析板块
    python sentiment_hub.py --list          # 分析持仓股票
"""
import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv 可选


@dataclass
class SentimentResult:
    """情绪分析结果"""
    source: str              # 数据来源
    heat_score: int          # 热度 0-100
    sentiment: str           # positive/neutral/negative
    mentions: int            # 提及次数
    topics: List[str]        # 热门话题
    summary: str             # 一句话总结
    confidence: float        # 置信度 0-1
    raw_data: Dict = None    # 原始数据


@dataclass
class StockSentiment:
    """股票综合情绪"""
    stock_name: str
    stock_code: str
    timestamp: str
    overall_heat: int        # 综合热度
    overall_sentiment: str   # 综合情绪
    sentiment_score: float   # 情绪分数 -1 到 1
    sources: List[SentimentResult]  # 各来源结果
    recommendation: str      # 情绪建议
    key_topics: List[str]    # 综合热门话题


def get_stock_name_from_futu(stock_code: str) -> Optional[str]:
    """从富途 OpenD 获取股票名称"""
    try:
        import os
        os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
        from futu import OpenQuoteContext, RET_OK

        # 标准化代码格式
        code_num = stock_code.replace('HK.', '').replace('US.', '').zfill(5)
        code = f'HK.{code_num}'

        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = quote_ctx.get_market_snapshot([code])
        quote_ctx.close()

        if ret == RET_OK and len(data) > 0:
            return data.iloc[0]['name']
        return None
    except Exception:
        return None


class SentimentHub:
    """社区情绪分析中心"""

    def __init__(self):
        """初始化，检测可用的数据源"""
        self.grok_key = os.getenv('GROK_API_KEY')
        self.x_token = os.getenv('X_BEARER_TOKEN')
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.xueqiu_cookie = os.getenv('XUEQIU_COOKIE')  # 雪球 Cookie

        self.available_sources = []
        if self.xueqiu_cookie:
            self.available_sources.append('xueqiu')
        if self.grok_key:
            self.available_sources.append('grok')
        if self.x_token:
            self.available_sources.append('x_api')
        if self.gemini_key:
            self.available_sources.append('gemini')
        if self.openai_key:
            self.available_sources.append('openai')
        # 免费数据源
        self.available_sources.append('reddit')
        self.available_sources.append('stocktwits')
        self.available_sources.append('eastmoney')

        print(f"📡 可用数据源: {', '.join(self.available_sources)}")

    def _detect_market(self, stock_code: str) -> str:
        """检测股票所属市场"""
        if not stock_code:
            return 'unknown'
        code_upper = stock_code.upper()

        # 明确前缀
        if code_upper.startswith('HK.'):
            return 'HK'
        if code_upper.startswith('US.'):
            return 'US'
        if code_upper.startswith('SH.') or code_upper.startswith('SZ.'):
            return 'CN'

        # 去掉前缀后的纯代码
        code_clean = code_upper.replace('HK.', '').replace('US.', '').replace('SH.', '').replace('SZ.', '')

        # 纯字母 = 美股 (AAPL, TSLA)
        if code_clean.isalpha():
            return 'US'

        # 纯数字判断
        if code_clean.isdigit():
            # A股: 6位数字 (600519, 000001, 300750)
            if len(code_clean) == 6:
                return 'CN'
            # 港股: 5位或更少数字 (00700, 09880, 700)
            if len(code_clean) <= 5:
                return 'HK'

        return 'unknown'

    def analyze_stock(self, stock_name: str, stock_code: str = None) -> StockSentiment:
        """
        分析单只股票的社区情绪 (支持港股/美股/A股)

        参数:
        - stock_name: 股票名称 (如 "优必选", "Apple", "贵州茅台")
        - stock_code: 股票代码 (如 "HK.09880", "US.AAPL", "SH.600519")

        返回:
        - StockSentiment: 综合情绪分析结果
        """
        market = self._detect_market(stock_code)
        market_emoji = {'HK': '🇭🇰', 'US': '🇺🇸', 'CN': '🇨🇳'}.get(market, '🌐')

        print(f"\n{'='*60}")
        print(f"🎯 分析社区情绪: {stock_name} {stock_code or ''} {market_emoji}")
        print(f"{'='*60}")

        results = []

        # === 首选：OpenAI 深度分析 (最可靠) ===
        if 'openai' in self.available_sources:
            print("\n🧠 [OpenAI] GPT-4 深度情绪分析...")
            openai_result = self._openai_analyze(stock_name, stock_code)
            if openai_result:
                results.append(openai_result)
                print(f"   热度: {openai_result.heat_score}/100 | 情绪: {openai_result.sentiment}")
                print(f"   话题: {', '.join(openai_result.topics[:3])}")
                print(f"   摘要: {openai_result.summary}")

        # === 韩国社区 ===
        # DC Inside (港股+美股)
        if market in ['HK', 'US', 'unknown']:
            print("\n🇰🇷 [DC Inside] 韩国投资社区...")
            dc_result = self._dcinside_analyze(stock_name, stock_code)
            if dc_result and dc_result.mentions > 0:
                results.append(dc_result)
                print(f"   热度: {dc_result.heat_score}/100 | {dc_result.summary}")

        # Naver Finance (韩国本土股票)
        print("\n🇰🇷 [Naver Finance] 韩国股票讨论...")
        naver_result = self._naver_finance_analyze(stock_name, stock_code)
        if naver_result:
            results.append(naver_result)
            print(f"   热度: {naver_result.heat_score}/100 | {naver_result.summary}")

        # === 雪球社区 (港股/A股/美股) ===
        if market in ['HK', 'CN', 'US', 'unknown'] and 'xueqiu' in self.available_sources:
            print("\n🐂 [雪球] 中国投资者社区...")
            xueqiu_result = self._xueqiu_analyze(stock_name, stock_code)
            if xueqiu_result and xueqiu_result.mentions > 0:
                results.append(xueqiu_result)
                print(f"   热度: {xueqiu_result.heat_score}/100 | {xueqiu_result.summary}")

        # === 美股社区 (Reddit WSB) ===
        if market in ['US', 'unknown']:
            # Reddit WSB
            print("\n🦍 [Reddit] 查询 WallStreetBets...")
            reddit_result = self._reddit_analyze(stock_name)
            if reddit_result and reddit_result.mentions > 0:
                results.append(reddit_result)
                print(f"   排名: #{reddit_result.mentions} | {reddit_result.summary}")

        # === 补充：Grok 分析 X/Twitter (如有) ===
        if 'grok' in self.available_sources:
            print("\n🤖 [Grok] 分析 X/Twitter...")
            grok_result = self._grok_analyze(stock_name, stock_code)
            if grok_result:
                results.append(grok_result)
                print(f"   热度: {grok_result.heat_score}/100 | {grok_result.summary}")

        # 综合分析
        return self._synthesize(stock_name, stock_code, results)

    def analyze_sector(self, sector_name: str, stocks: List[Dict] = None) -> Dict:
        """
        分析板块整体社区情绪

        参数:
        - sector_name: 板块名称 (如 "人形机器人")
        - stocks: 板块内股票列表 [{'name': '优必选', 'code': 'HK.09880'}, ...]

        返回:
        - 板块情绪 + 各股票情绪
        """
        print(f"\n{'='*60}")
        print(f"📊 分析板块情绪: {sector_name}")
        print(f"{'='*60}")

        sector_results = []

        # 分析板块整体
        if 'grok' in self.available_sources:
            print("\n🤖 [Grok] 分析板块热度...")
            sector_sentiment = self._grok_analyze_sector(sector_name)
            if sector_sentiment:
                sector_results.append(sector_sentiment)

        if 'gemini' in self.available_sources:
            print("\n🔍 [Gemini] 搜索板块讨论...")
            gemini_sector = self._gemini_analyze_sector(sector_name)
            if gemini_sector:
                sector_results.append(gemini_sector)

        # 分析各股票
        stock_sentiments = []
        if stocks:
            for stock in stocks[:3]:  # 最多分析3只
                result = self.analyze_stock(stock['name'], stock.get('code'))
                stock_sentiments.append(result)

        return {
            'sector': sector_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sector_sentiment': self._average_sentiment(sector_results),
            'stocks': [asdict(s) for s in stock_sentiments]
        }

    # ==================== Grok API ====================

    def _grok_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """使用 Grok 分析"""
        if not self.grok_key:
            return None

        code_str = stock_code.replace('HK.', '') if stock_code else ''

        prompt = f"""搜索 X/Twitter 上关于港股"{stock_name}"（代码：{code_str}）的最新讨论（近24小时）。

分析并返回JSON：
{{
    "heat_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "mentions": 估计提及次数,
    "key_topics": ["话题1", "话题2", "话题3"],
    "summary": "一句话总结（20字内）"
}}"""

        try:
            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.grok_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'grok-beta',
                    'messages': [
                        {'role': 'system', 'content': '你是金融社交媒体分析师，擅长分析X/Twitter上的股票讨论。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=20
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                data = json.loads(content)

                return SentimentResult(
                    source='Grok (X/Twitter)',
                    heat_score=data.get('heat_score', 0),
                    sentiment=data.get('sentiment', 'neutral'),
                    mentions=data.get('mentions', 0),
                    topics=data.get('key_topics', []),
                    summary=data.get('summary', ''),
                    confidence=0.9,
                    raw_data=data
                )
        except Exception as e:
            print(f"   ⚠️ Grok 分析失败: {e}")

        return None

    def _grok_analyze_sector(self, sector_name: str) -> Optional[SentimentResult]:
        """使用 Grok 分析板块"""
        if not self.grok_key:
            return None

        prompt = f"""搜索 X/Twitter 上关于"{sector_name}"概念/板块的最新讨论（近24小时）。

分析并返回JSON：
{{
    "heat_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "mentions": 估计提及次数,
    "key_topics": ["话题1", "话题2", "话题3"],
    "capital_attention": "high/medium/low",
    "summary": "一句话总结（20字内）"
}}"""

        try:
            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.grok_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'grok-beta',
                    'messages': [
                        {'role': 'system', 'content': '你是金融社交媒体分析师。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=20
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                data = json.loads(content)

                return SentimentResult(
                    source='Grok (板块)',
                    heat_score=data.get('heat_score', 0),
                    sentiment=data.get('sentiment', 'neutral'),
                    mentions=data.get('mentions', 0),
                    topics=data.get('key_topics', []),
                    summary=data.get('summary', ''),
                    confidence=0.85,
                    raw_data=data
                )
        except Exception as e:
            print(f"   ⚠️ Grok 板块分析失败: {e}")

        return None

    # ==================== X API ====================

    def _x_api_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """使用 X API 直接搜索"""
        if not self.x_token:
            return None

        code_short = stock_code.replace('HK.', '').lstrip('0') if stock_code else ''
        query = f'({stock_name} OR {code_short}) lang:zh'

        try:
            response = requests.get(
                'https://api.twitter.com/2/tweets/search/recent',
                headers={
                    'Authorization': f'Bearer {self.x_token}',
                    'Content-Type': 'application/json'
                },
                params={
                    'query': query,
                    'max_results': 50,
                    'tweet.fields': 'created_at,public_metrics'
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                tweets = data.get('data', [])
                meta = data.get('meta', {})

                # 统计
                total_likes = sum(t.get('public_metrics', {}).get('like_count', 0) for t in tweets)
                total_retweets = sum(t.get('public_metrics', {}).get('retweet_count', 0) for t in tweets)

                # 情绪判断
                sentiment = self._simple_sentiment(tweets)

                # 热度计算
                heat = min(int(len(tweets) * 2 + total_likes / 10), 100)

                return SentimentResult(
                    source='X API (直接)',
                    heat_score=heat,
                    sentiment=sentiment,
                    mentions=meta.get('result_count', 0),
                    topics=[],
                    summary=f'{len(tweets)}条推文, {total_likes}赞, {total_retweets}转发',
                    confidence=0.95,
                    raw_data={'tweets_count': len(tweets), 'likes': total_likes, 'retweets': total_retweets}
                )

        except Exception as e:
            print(f"   ⚠️ X API 失败: {e}")

        return None

    def _simple_sentiment(self, tweets: List[Dict]) -> str:
        """简单情绪判断"""
        positive = ['利好', '大涨', '突破', '订单', '看好', '🚀', '📈', '牛']
        negative = ['暴跌', '利空', '下跌', '📉', '熊', '跑']

        pos_count = neg_count = 0
        for t in tweets[:30]:
            text = t.get('text', '')
            if any(kw in text for kw in positive):
                pos_count += 1
            if any(kw in text for kw in negative):
                neg_count += 1

        if pos_count > neg_count * 1.5:
            return 'positive'
        elif neg_count > pos_count * 1.5:
            return 'negative'
        return 'neutral'

    # ==================== 雪球 ====================

    def _xueqiu_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """雪球情绪分析 - 使用移动端API获取行情+涨跌情绪"""
        try:
            code_num = stock_code.replace('HK.', '').replace('SH.', '').replace('SZ.', '').replace('US.', '') if stock_code else ''

            # 移动端 API 可绕过 WAF
            headers = {
                'User-Agent': 'Xueqiu iPhone 14.17',
                'Accept': 'application/json',
                'Cookie': self.xueqiu_cookie or '',
            }

            # 雪球股票代码格式
            market = self._detect_market(stock_code) if stock_code else 'unknown'
            if market == 'HK':
                xq_code = code_num.zfill(5)
            elif market == 'US':
                xq_code = code_num.upper()
            elif market == 'CN':
                xq_code = f"SH{code_num}" if code_num.startswith('6') else f"SZ{code_num}"
            else:
                xq_code = code_num.zfill(5) if code_num.isdigit() and len(code_num) <= 5 else code_num

            # 获取行情数据 (移动端 API 可用)
            quote_url = 'https://stock.xueqiu.com/v5/stock/quote.json'
            params = {'symbol': xq_code, 'extend': 'detail'}
            response = requests.get(quote_url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                quote = data.get('data', {}).get('quote', {})

                if quote:
                    # 从行情推断情绪
                    percent = quote.get('percent', 0) or 0
                    volume_ratio = quote.get('volume_ratio', 1) or 1
                    turnover_rate = quote.get('turnover_rate', 0) or 0

                    # 情绪判断
                    if percent > 3:
                        sentiment = 'positive'
                    elif percent < -3:
                        sentiment = 'negative'
                    else:
                        sentiment = 'neutral'

                    # 热度 = 换手率 + 量比
                    heat = min(int(turnover_rate * 10 + volume_ratio * 20), 100)

                    name = quote.get('name', stock_name)
                    current = quote.get('current', 0)
                    chg = quote.get('chg', 0)

                    return SentimentResult(
                        source='雪球',
                        heat_score=max(heat, 30),  # 至少30热度
                        sentiment=sentiment,
                        mentions=1,
                        topics=[f'{name} 现价{current}', f'涨跌{chg:+.2f} ({percent:+.2f}%)'],
                        summary=f'{name}: {current} ({percent:+.2f}%) 换手{turnover_rate:.1f}%',
                        confidence=0.8,
                        raw_data=quote
                    )

            return None

        except Exception as e:
            print(f"   ⚠️ 雪球分析失败: {e}")
            return None

    def _xueqiu_posts_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """雪球帖子分析 (备用 - 可能被 WAF 拦截)"""
        try:
            code_num = stock_code.replace('HK.', '').replace('SH.', '').replace('SZ.', '').replace('US.', '') if stock_code else ''

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Cookie': self.xueqiu_cookie or '',
            }

            market = self._detect_market(stock_code) if stock_code else 'unknown'
            if market == 'HK':
                xq_code = code_num.zfill(5)
            elif market == 'US':
                xq_code = code_num.upper()
            elif market == 'CN':
                xq_code = f"SH{code_num}" if code_num.startswith('6') else f"SZ{code_num}"
            else:
                xq_code = code_num

            api_url = 'https://xueqiu.com/statuses/stock_timeline.json'
            params = {'symbol': xq_code, 'count': 20, 'source': 'all'}
            response = requests.get(api_url, headers=headers, params=params, timeout=10)

            if response.status_code == 200 and not response.text.startswith('<'):
                data = response.json()
                statuses = data.get('list', [])
                if statuses:
                    total_reply = sum(s.get('reply_count', 0) for s in statuses)
                    total_like = sum(s.get('like_count', 0) for s in statuses)
                    texts = [s.get('text', '') for s in statuses]
                    sentiment = self._analyze_chinese_sentiment(texts)
                    heat = min(int(len(statuses) * 3 + total_reply / 5 + total_like / 10), 100)
                    return SentimentResult(
                        source='雪球',
                        heat_score=heat,
                        sentiment=sentiment,
                        mentions=len(statuses),
                        topics=[t[:40] for t in texts[:3] if t],
                        summary=f'{len(statuses)}条讨论, {total_reply}回复, {total_like}赞',
                        confidence=0.85
                    )

            return SentimentResult(
                source='雪球',
                heat_score=0,
                sentiment='neutral',
                mentions=0,
                topics=[],
                summary='未找到相关讨论',
                confidence=0.5
            )

        except Exception as e:
            print(f"   ⚠️ 雪球分析失败: {e}")
            return None

    # ==================== 东方财富股吧 ====================

    def _eastmoney_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """爬取东方财富股吧讨论"""
        try:
            code_num = stock_code.replace('HK.', '') if stock_code else ''

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            }

            # 直接爬取股吧页面
            # 港股格式: hk + 5位代码 (如 hk09880)
            em_code = f"hk{code_num.zfill(5)}" if len(code_num) < 5 else f"hk{code_num}"
            page_url = f'https://guba.eastmoney.com/list,{em_code}.html'

            response = requests.get(page_url, headers=headers, timeout=10)

            if response.status_code == 200:
                content = response.text

                # 提取帖子标题 (使用正则)
                import re
                # 匹配帖子标题
                title_pattern = r'<span class="l3 a3">.*?<a[^>]*>([^<]+)</a>'
                titles = re.findall(title_pattern, content, re.DOTALL)

                # 提取阅读数和评论数
                read_pattern = r'<span class="l1 a1">(\d+)</span>'
                reads = re.findall(read_pattern, content)

                comment_pattern = r'<span class="l2 a2">(\d+)</span>'
                comments = re.findall(comment_pattern, content)

                if titles:
                    total_reads = sum(int(r) for r in reads[:20]) if reads else 0
                    total_comments = sum(int(c) for c in comments[:20]) if comments else 0

                    # 情绪分析
                    sentiment = self._analyze_chinese_sentiment(titles[:20])

                    # 热度计算
                    heat = min(int(len(titles) * 2 + total_reads / 500 + total_comments / 5), 100)

                    return SentimentResult(
                        source='东方财富股吧',
                        heat_score=heat,
                        sentiment=sentiment,
                        mentions=len(titles),
                        topics=titles[:3],
                        summary=f'{len(titles)}帖子, {total_reads}阅读, {total_comments}评论',
                        confidence=0.75,
                        raw_data={'posts': len(titles), 'reads': total_reads, 'comments': total_comments}
                    )

                # 没有找到帖子
                return SentimentResult(
                    source='东方财富股吧',
                    heat_score=0,
                    sentiment='neutral',
                    mentions=0,
                    topics=[],
                    summary='未找到股吧讨论',
                    confidence=0.5
                )

            return None

        except Exception as e:
            print(f"   ⚠️ 东方财富分析失败: {e}")
            return None

    def _analyze_chinese_sentiment(self, texts: List[str]) -> str:
        """分析中文文本情绪"""
        positive_words = ['利好', '大涨', '突破', '新高', '订单', '看好', '牛', '暴涨', '翻倍', '涨停', '机会', '强势', '爆发']
        negative_words = ['利空', '暴跌', '下跌', '崩盘', '亏损', '割肉', '套牢', '熊', '跌停', '风险', '警惕', '坑']

        pos_count = neg_count = 0
        for text in texts:
            for word in positive_words:
                if word in text:
                    pos_count += 1
            for word in negative_words:
                if word in text:
                    neg_count += 1

        if pos_count > neg_count * 1.5:
            return 'positive'
        elif neg_count > pos_count * 1.5:
            return 'negative'
        return 'neutral'

    # ==================== Naver Finance 讨论区 (韩国股票社区) ====================

    def _naver_finance_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """爬取 Naver Finance 股票讨论区"""
        try:
            import re

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept-Language': 'ko-KR,ko;q=0.9',
            }

            # 韩国股票代码映射 (富途可交易的韩股)
            kr_stock_codes = {
                # 三星系列
                '삼성전자': '005930', 'samsung': '005930', '三星': '005930', '三星电子': '005930',
                '삼성전자우': '005935', 'samsung pref': '005935', '三星优先股': '005935',
                '삼성sdi': '006400', 'samsung sdi': '006400', '三星SDI': '006400',
                '삼성바이오로직스': '207940', 'samsung biologics': '207940', '三星生物': '207940',

                # SK系列
                'sk하이닉스': '000660', 'sk hynix': '000660', 'SK海力士': '000660',
                'sk이노베이션': '096770', 'sk innovation': '096770', 'SK创新': '096770',

                # 现代/起亚
                '현대차': '005380', 'hyundai': '005380', '现代汽车': '005380',
                '기아': '000270', 'kia': '000270', '起亚': '000270',
                '현대모비스': '012330', 'hyundai mobis': '012330', '现代摩比斯': '012330',

                # LG系列
                'lg전자': '066570', 'lg electronics': '066570', 'LG电子': '066570',
                'lg에너지솔루션': '373220', 'lg energy': '373220', 'LG新能源': '373220',
                'lg화학': '051910', 'lg chem': '051910', 'LG化学': '051910',

                # 互联网科技
                '네이버': '035420', 'naver': '035420', 'NAVER': '035420',
                '카카오': '035720', 'kakao': '035720', '카카오뱅크': '323410',
                '카카오페이': '377300', 'kakao pay': '377300', 'kakaopay': '377300',
                'nc소프트': '036570', 'ncsoft': '036570', 'NC软件': '036570',
                '넷마블': '251270', 'netmarble': '251270',
                '크래프톤': '259960', 'krafton': '259960', 'PUBG': '259960',

                # 钢铁/化工
                '포스코홀딩스': '005490', 'posco': '005490', '浦项钢铁': '005490',
                '포스코퓨처엠': '003670', 'posco future m': '003670',

                # 生物医药
                '셀트리온': '068270', 'celltrion': '068270', '赛特瑞恩': '068270',
                '셀트리온헬스케어': '091990', 'celltrion healthcare': '091990',
                '삼성바이오에피스': '326030', 'samsung bioepis': '326030',

                # 金融
                'kb금융': '105560', 'kb financial': '105560', 'KB金融': '105560',
                '신한지주': '055550', 'shinhan': '055550', '新韩金融': '055550',
                '하나금융지주': '086790', 'hana financial': '086790', '韩亚金融': '086790',

                # 其他热门
                '한국전력': '015760', 'kepco': '015760', '韩国电力': '015760',
                '삼성물산': '028260', 'samsung c&t': '028260', '三星物产': '028260',
                '현대건설': '000720', 'hyundai e&c': '000720', '现代建设': '000720',
            }

            # 获取韩国股票代码
            kr_code = None
            for name, code in kr_stock_codes.items():
                if name.lower() in stock_name.lower():
                    kr_code = code
                    break

            if not kr_code:
                return None  # 只支持韩国股票

            # 爬取讨论区
            url = 'https://finance.naver.com/item/board.naver'
            params = {'code': kr_code}
            resp = requests.get(url, params=params, headers=headers, timeout=10)

            if resp.status_code == 200:
                content = resp.text

                # 提取帖子标题
                titles = re.findall(r'class="title"[^>]*>\s*<a[^>]*title="([^"]+)"', content)

                # 情绪分析 (韩语)
                bullish = ['상승', '매수', '급등', '호재', '돌파', '반등', '상한가']
                bearish = ['하락', '매도', '급락', '악재', '폭락', '손절', '하한가']

                bull_count = sum(content.count(w) for w in bullish)
                bear_count = sum(content.count(w) for w in bearish)

                if bull_count > bear_count * 1.5:
                    sentiment = 'positive'
                elif bear_count > bull_count * 1.5:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'

                # 热度
                heat = min(len(titles) * 4 + bull_count + bear_count, 100)

                return SentimentResult(
                    source='Naver Finance',
                    heat_score=heat,
                    sentiment=sentiment,
                    mentions=len(titles),
                    topics=[t[:40] for t in titles[:3]],
                    summary=f'{len(titles)}个帖子, 🐂{bull_count} vs 🐻{bear_count}',
                    confidence=0.85,
                    raw_data={'posts': len(titles), 'bullish': bull_count, 'bearish': bear_count}
                )

            return None

        except Exception as e:
            print(f"   ⚠️ Naver Finance 分析失败: {e}")
            return None

    # ==================== DC Inside 미국주식갤 (韩国美股社区) ====================

    def _dcinside_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """爬取 DC Inside 美股画廊 - 韩国最大匿名美股社区"""
        try:
            import re

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept-Language': 'ko-KR,ko;q=0.9',
                'Referer': 'https://gall.dcinside.com/',
            }

            # 搜索股票相关帖子
            search_url = 'https://gall.dcinside.com/mgallery/board/lists'
            params = {
                'id': 'stockus',
                's_type': 'search_subject_memo',
                's_keyword': stock_name,
            }

            resp = requests.get(search_url, params=params, headers=headers, timeout=10)

            if resp.status_code == 200:
                # 统计关键词
                content = resp.text.lower()
                ticker = stock_code.replace('US.', '').replace('HK.', '').lower() if stock_code else stock_name.lower()

                # 提取帖子标题
                title_pattern = r'<a[^>]*href="[^"]*no=\d+[^"]*"[^>]*>([^<]+)</a>'
                titles = re.findall(title_pattern, resp.text)

                # 统计提及次数
                mentions = content.count(ticker) + content.count(stock_name.lower())

                # 提取浏览数估算热度
                views_pattern = r'<td class="gall_count">(\d+)</td>'
                views = re.findall(views_pattern, resp.text)
                total_views = sum(int(v) for v in views[:20]) if views else 0

                # 情绪分析 (韩语关键词)
                positive_kr = ['상승', '급등', '매수', '존버', '가즈아', '떡상', '불장']
                negative_kr = ['하락', '급락', '매도', '손절', '폭락', '멸망', '곡소리']

                pos_count = sum(content.count(w) for w in positive_kr)
                neg_count = sum(content.count(w) for w in negative_kr)

                if pos_count > neg_count * 1.5:
                    sentiment = 'positive'
                elif neg_count > pos_count * 1.5:
                    sentiment = 'negative'
                else:
                    sentiment = 'neutral'

                # 热度
                heat = min(int(mentions * 5 + total_views / 100), 100)

                return SentimentResult(
                    source='DC Inside 미주갤',
                    heat_score=heat,
                    sentiment=sentiment,
                    mentions=mentions,
                    topics=[t[:30] for t in titles[:3]],
                    summary=f'{mentions}次提及, {total_views}浏览, 🐂{pos_count} vs 🐻{neg_count}',
                    confidence=0.8,
                    raw_data={'mentions': mentions, 'views': total_views, 'bullish': pos_count, 'bearish': neg_count}
                )

            return None

        except Exception as e:
            print(f"   ⚠️ DC Inside 分析失败: {e}")
            return None

    # ==================== StockTwits (美股) ====================

    def _stocktwits_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """StockTwits API - 美股情绪标准平台 (免费)"""
        try:
            # 提取股票代码 (美股格式: AAPL, TSLA 等)
            ticker = stock_code.replace('US.', '') if stock_code else stock_name.upper()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            }

            # StockTwits API - 获取股票讨论流
            api_url = f'https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json'

            response = requests.get(api_url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                symbol_info = data.get('symbol', {})

                if messages:
                    # 情绪统计
                    bullish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bullish')
                    bearish = sum(1 for m in messages if m.get('entities', {}).get('sentiment', {}).get('basic') == 'Bearish')
                    total = len(messages)

                    # 计算情绪
                    if bullish > bearish * 1.5:
                        sentiment = 'positive'
                    elif bearish > bullish * 1.5:
                        sentiment = 'negative'
                    else:
                        sentiment = 'neutral'

                    # 热度 (基于消息数量和关注度)
                    watchlist_count = symbol_info.get('watchlist_count', 0)
                    heat = min(int(total * 2 + watchlist_count / 1000), 100)

                    # 提取话题
                    topics = []
                    for m in messages[:5]:
                        body = m.get('body', '')[:60]
                        if body:
                            topics.append(body)

                    return SentimentResult(
                        source='StockTwits',
                        heat_score=heat,
                        sentiment=sentiment,
                        mentions=total,
                        topics=topics[:3],
                        summary=f'{total}条讨论, 🐂{bullish} vs 🐻{bearish}, {watchlist_count}人关注',
                        confidence=0.85,
                        raw_data={'messages': total, 'bullish': bullish, 'bearish': bearish, 'watchlist': watchlist_count}
                    )

            return SentimentResult(
                source='StockTwits',
                heat_score=0,
                sentiment='neutral',
                mentions=0,
                topics=[],
                summary='未找到讨论',
                confidence=0.5
            )

        except Exception as e:
            print(f"   ⚠️ StockTwits 分析失败: {e}")
            return None

    # ==================== Reddit ====================

    def _reddit_analyze(self, stock_name: str) -> Optional[SentimentResult]:
        """使用 ApeWisdom API 查询 Reddit/WSB"""
        try:
            # ApeWisdom 提供 WSB 热门股票
            response = requests.get(
                'https://apewisdom.io/api/v1.0/filter/all-stocks/page/1',
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                # 搜索匹配的股票
                for stock in results[:50]:
                    ticker = stock.get('ticker', '')
                    name = stock.get('name', '')

                    # 匹配港股名称
                    if stock_name.lower() in name.lower() or stock_name.lower() in ticker.lower():
                        mentions = stock.get('mentions', 0)
                        upvotes = stock.get('upvotes', 0)
                        rank = stock.get('rank', 0)

                        heat = min(int(mentions / 10 + upvotes / 100), 100)

                        return SentimentResult(
                            source='Reddit (WSB)',
                            heat_score=heat,
                            sentiment='positive' if upvotes > mentions else 'neutral',
                            mentions=mentions,
                            topics=[f'#{rank} in WSB'],
                            summary=f'WSB排名#{rank}, {mentions}提及, {upvotes}赞',
                            confidence=0.7,
                            raw_data=stock
                        )

                # 未找到，返回低热度
                return SentimentResult(
                    source='Reddit (WSB)',
                    heat_score=0,
                    sentiment='neutral',
                    mentions=0,
                    topics=[],
                    summary='未在 WSB 热门中找到',
                    confidence=0.5
                )

        except Exception as e:
            print(f"   ⚠️ Reddit 查询失败: {e}")

        return None

    # ==================== Gemini ====================

    def _gemini_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """使用 Gemini 搜索社交媒体讨论"""
        if not self.gemini_key:
            return None

        try:
            from google import genai
            from google.genai.types import Tool, GoogleSearch

            client = genai.Client(api_key=self.gemini_key)

            code_str = stock_code.replace('HK.', '') if stock_code else ''
            prompt = f"""搜索港股"{stock_name}"（{code_str}）在社交媒体（微博、雪球、股吧、Twitter）上的最新讨论。

分析社区情绪并返回JSON：
{{
    "heat_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "mentions": 估计讨论量,
    "key_topics": ["话题1", "话题2"],
    "summary": "社区情绪总结（20字内）"
}}"""

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'tools': [Tool(google_search=GoogleSearch())],
                }
            )

            # 解析结果
            text = response.text
            if '{' in text:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                data = json.loads(text[json_start:json_end])

                return SentimentResult(
                    source='Gemini (社交搜索)',
                    heat_score=data.get('heat_score', 0),
                    sentiment=data.get('sentiment', 'neutral'),
                    mentions=data.get('mentions', 0),
                    topics=data.get('key_topics', []),
                    summary=data.get('summary', ''),
                    confidence=0.75,
                    raw_data=data
                )

        except Exception as e:
            print(f"   ⚠️ Gemini 分析失败: {e}")

        return None

    def _gemini_analyze_sector(self, sector_name: str) -> Optional[SentimentResult]:
        """使用 Gemini 分析板块"""
        if not self.gemini_key:
            return None

        try:
            from google import genai
            from google.genai.types import Tool, GoogleSearch

            client = genai.Client(api_key=self.gemini_key)

            prompt = f"""搜索"{sector_name}"概念在社交媒体上的最新讨论热度。

返回JSON：
{{
    "heat_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "key_topics": ["话题1", "话题2"],
    "summary": "总结"
}}"""

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'temperature': 0.3,
                    'tools': [Tool(google_search=GoogleSearch())],
                }
            )

            text = response.text
            if '{' in text:
                json_start = text.find('{')
                json_end = text.rfind('}') + 1
                data = json.loads(text[json_start:json_end])

                return SentimentResult(
                    source='Gemini (板块)',
                    heat_score=data.get('heat_score', 0),
                    sentiment=data.get('sentiment', 'neutral'),
                    mentions=0,
                    topics=data.get('key_topics', []),
                    summary=data.get('summary', ''),
                    confidence=0.7
                )

        except Exception as e:
            print(f"   ⚠️ Gemini 板块分析失败: {e}")

        return None

    # ==================== OpenAI ====================

    def _openai_analyze(self, stock_name: str, stock_code: str = None) -> Optional[SentimentResult]:
        """使用 OpenAI GPT-4 分析社交情绪 (支持港股/美股/A股)"""
        if not self.openai_key:
            return None

        market = self._detect_market(stock_code)
        code_str = stock_code or ''

        # 根据市场调整提示
        if market == 'US':
            platforms = "Reddit (r/wallstreetbets, r/stocks), Twitter/X, StockTwits, Seeking Alpha"
            market_name = "美股"
        elif market == 'CN':
            platforms = "雪球、东方财富股吧、同花顺、微博财经"
            market_name = "A股"
        else:
            platforms = "雪球、东方财富股吧、Twitter/X、微博"
            market_name = "港股"

        prompt = f"""分析{market_name}"{stock_name}"（代码：{code_str}）在社交媒体上的讨论情绪。

分析平台：{platforms}

基于你的知识，估计这只股票的社区讨论热度和情绪倾向。

返回JSON格式：
{{
    "heat_score": 0-100,
    "sentiment": "positive/neutral/negative",
    "mentions": 估计每日讨论量,
    "key_topics": ["话题1", "话题2", "话题3"],
    "summary": "社区情绪总结（20字内）"
}}"""

        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.openai_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-4o-mini',  # 便宜且快
                    'messages': [
                        {'role': 'system', 'content': '你是金融社交媒体分析师，擅长分析股票在社交媒体上的讨论热度和情绪。返回JSON格式。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500,
                    'response_format': {'type': 'json_object'}
                },
                timeout=30
            )

            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                data = json.loads(content)

                return SentimentResult(
                    source='OpenAI GPT-4',
                    heat_score=data.get('heat_score', 0),
                    sentiment=data.get('sentiment', 'neutral'),
                    mentions=data.get('mentions', 0),
                    topics=data.get('key_topics', []),
                    summary=data.get('summary', ''),
                    confidence=0.8,
                    raw_data=data
                )
            else:
                print(f"   ⚠️ OpenAI 错误: {response.status_code} - {response.text[:100]}")

        except Exception as e:
            print(f"   ⚠️ OpenAI 分析失败: {e}")

        return None

    # ==================== 综合分析 ====================

    def _synthesize(self, stock_name: str, stock_code: str, results: List[SentimentResult]) -> StockSentiment:
        """综合多来源结果"""
        if not results:
            return StockSentiment(
                stock_name=stock_name,
                stock_code=stock_code or '',
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                overall_heat=0,
                overall_sentiment='unknown',
                sentiment_score=0,
                sources=[],
                recommendation='无数据',
                key_topics=[]
            )

        # 加权平均热度
        total_weight = sum(r.confidence for r in results)
        avg_heat = int(sum(r.heat_score * r.confidence for r in results) / total_weight)

        # 情绪分数
        sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
        sentiment_score = sum(sentiment_map.get(r.sentiment, 0) * r.confidence for r in results) / total_weight

        # 综合情绪
        if sentiment_score > 0.3:
            overall_sentiment = 'positive'
        elif sentiment_score < -0.3:
            overall_sentiment = 'negative'
        else:
            overall_sentiment = 'neutral'

        # 收集话题
        all_topics = []
        for r in results:
            all_topics.extend(r.topics)
        unique_topics = list(dict.fromkeys(all_topics))[:5]

        # 建议
        if avg_heat > 70 and sentiment_score > 0.3:
            recommendation = '🔥 高热度 + 积极情绪 → 关注追涨风险'
        elif avg_heat > 50 and sentiment_score > 0:
            recommendation = '📈 中等热度 + 偏积极 → 可关注'
        elif avg_heat < 30:
            recommendation = '😴 低热度 → 社区关注度低'
        elif sentiment_score < -0.3:
            recommendation = '📉 负面情绪 → 谨慎'
        else:
            recommendation = '➡️ 中性 → 观望'

        return StockSentiment(
            stock_name=stock_name,
            stock_code=stock_code or '',
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            overall_heat=avg_heat,
            overall_sentiment=overall_sentiment,
            sentiment_score=round(sentiment_score, 2),
            sources=[asdict(r) for r in results],
            recommendation=recommendation,
            key_topics=unique_topics
        )

    def _average_sentiment(self, results: List[SentimentResult]) -> Dict:
        """平均情绪"""
        if not results:
            return {'heat': 0, 'sentiment': 'unknown'}

        avg_heat = int(sum(r.heat_score for r in results) / len(results))
        sentiments = [r.sentiment for r in results]

        pos = sentiments.count('positive')
        neg = sentiments.count('negative')

        if pos > neg:
            sentiment = 'positive'
        elif neg > pos:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {'heat': avg_heat, 'sentiment': sentiment}

    def format_report(self, result: StockSentiment) -> str:
        """格式化报告"""
        output = []
        output.append(f"\n{'='*60}")
        output.append(f"📊 社区情绪报告 - {result.stock_name} {result.stock_code}")
        output.append(f"{'='*60}")
        output.append(f"📅 {result.timestamp}")
        output.append("")

        # 核心指标
        heat_bar = '█' * (result.overall_heat // 10) + '░' * (10 - result.overall_heat // 10)
        sentiment_emoji = {'positive': '🟢', 'neutral': '⚪', 'negative': '🔴'}.get(result.overall_sentiment, '❓')

        output.append(f"🔥 热度: [{heat_bar}] {result.overall_heat}/100")
        output.append(f"{sentiment_emoji} 情绪: {result.overall_sentiment} (分数: {result.sentiment_score:+.2f})")
        output.append(f"💡 建议: {result.recommendation}")
        output.append("")

        # 热门话题
        if result.key_topics:
            output.append("📌 热门话题:")
            for topic in result.key_topics:
                output.append(f"   • {topic}")
            output.append("")

        # 各来源详情
        output.append("📡 数据来源:")
        for src in result.sources:
            output.append(f"   [{src['source']}] 热度:{src['heat_score']} | {src['sentiment']} | {src['summary'][:30]}...")

        output.append(f"\n{'='*60}")

        return "\n".join(output)


def main():
    """CLI 入口"""
    import argparse

    parser = argparse.ArgumentParser(description='社区情绪分析中心')
    parser.add_argument('stock', nargs='?', help='股票名称 (如: 优必选)')
    parser.add_argument('--code', '-c', help='股票代码 (如: HK.09880)')
    parser.add_argument('--sector', '-s', help='分析板块 (如: 人形机器人)')
    parser.add_argument('--list', '-l', action='store_true', help='分析持仓股票')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')

    args = parser.parse_args()

    hub = SentimentHub()

    if args.sector:
        # 分析板块
        result = hub.analyze_sector(args.sector)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"\n板块: {result['sector']}")
            print(f"情绪: {result['sector_sentiment']}")

    elif args.list:
        # 分析持仓
        portfolio = [
            {'name': '阿里巴巴', 'code': 'HK.09988'},
            {'name': '优必选', 'code': 'HK.09880'},
            {'name': '壁仞科技', 'code': 'HK.06082'},
            {'name': '精锋医疗', 'code': 'HK.02675'},
            {'name': 'MiniMax', 'code': 'HK.00100'},
        ]

        for stock in portfolio:
            result = hub.analyze_stock(stock['name'], stock['code'])
            print(hub.format_report(result))

    elif args.stock:
        # 分析单只股票
        stock_name = args.stock
        stock_code = args.code

        # 智能识别：如果输入的是代码格式，自动处理
        if not stock_code:
            input_val = args.stock.upper()
            # 纯数字 = 港股代码
            if input_val.isdigit() and len(input_val) <= 5:
                stock_code = input_val.zfill(5)
                stock_name = stock_code  # 用代码作为名称
            # 纯字母 = 美股代码
            elif input_val.isalpha():
                stock_code = input_val
                stock_name = stock_code
            # 6位数字 = A股代码
            elif input_val.isdigit() and len(input_val) == 6:
                stock_code = input_val
                stock_name = stock_code

        result = hub.analyze_stock(stock_name, stock_code)
        if args.json:
            print(json.dumps(asdict(result), indent=2, ensure_ascii=False))
        else:
            print(hub.format_report(result))

    else:
        # 默认分析优必选
        result = hub.analyze_stock('优必选', 'HK.09880')
        print(hub.format_report(result))


if __name__ == '__main__':
    main()
