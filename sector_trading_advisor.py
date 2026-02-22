#!/usr/bin/env python3
"""
板块交易顾问系统
功能：
1. 扫描富途发现涨的板块
2. 抓取新浪财经资讯找原因
3. AI分析炒作周期和进场时机
4. 推荐是否适合进场
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import requests
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
import time

# Telegram配置
TELEGRAM_BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
TELEGRAM_CHAT_ID = "7082819163"

# 板块映射
SECTOR_MAP = {
    "人形机器人": ["HK.09880", "HK.02432", "HK.06600", "HK.02090"],
    "AI大模型": ["HK.02513", "HK.00100", "HK.09888", "HK.09618"],
    "GPU芯片": ["HK.06082", "HK.09903", "HK.00981", "HK.00700"],
    "互联网": ["HK.00700", "HK.09988", "HK.03690", "HK.01024"],
    "港股科技": ["HK.09999", "HK.02013", "HK.02158", "HK.06682"],
    "新能源车": ["HK.01211", "HK.02015", "HK.09868"],
    "军工": ["HK.02357", "HK.00179"],
    "生物医药": ["HK.02269", "HK.01931", "HK.02675"],
    "芯片设备": ["HK.00501", "HK.00688"],
    "云计算": ["HK.09618", "HK.00700", "HK.09888"]
}

class SectorTradingAdvisor:
    """板块交易顾问"""

    def __init__(self):
        self.quote_ctx = None
        self.sector_data = {}
        self.news_cache = []

    def connect_futu(self):
        """连接富途"""
        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            print("✅ 富途OpenD已连接", flush=True)
            return True
        except Exception as e:
            print(f"❌ 富途连接失败: {e}", flush=True)
            return False

    def scan_hot_sectors(self):
        """
        扫描今日热门板块
        返回：涨幅前3的板块
        """
        print("\n🔍 扫描热门板块...\n", flush=True)

        sector_performance = {}

        for sector, stocks in SECTOR_MAP.items():
            total_change = 0
            valid_count = 0
            stock_details = []

            for code in stocks:
                try:
                    ret, snapshot = self.quote_ctx.get_market_snapshot([code])
                    if ret == RET_OK and not snapshot.empty:
                        last_price = snapshot['last_price'].iloc[0]
                        prev_close = snapshot['prev_close_price'].iloc[0]
                        volume = snapshot['volume'].iloc[0]
                        turnover_rate = snapshot.get('turnover_rate', [0]).iloc[0] if 'turnover_rate' in snapshot.columns else 0

                        if prev_close > 0:
                            change_pct = ((last_price - prev_close) / prev_close * 100)
                            total_change += change_pct
                            valid_count += 1

                            stock_details.append({
                                'code': code,
                                'name': code.replace('HK.', ''),
                                'change_pct': change_pct,
                                'price': last_price,
                                'volume': volume,
                                'turnover_rate': turnover_rate
                            })
                except:
                    continue

                time.sleep(0.1)

            if valid_count > 0:
                avg_change = total_change / valid_count
                sector_performance[sector] = {
                    'avg_change': avg_change,
                    'stocks': stock_details,
                    'stock_count': valid_count
                }

        # 按平均涨幅排序
        sorted_sectors = sorted(
            sector_performance.items(),
            key=lambda x: x[1]['avg_change'],
            reverse=True
        )

        # 打印结果
        for i, (sector, data) in enumerate(sorted_sectors[:5], 1):
            emoji = "🔥" if data['avg_change'] > 5 else "🟢" if data['avg_change'] > 0 else "🔴"
            print(f"{i}. {emoji} {sector}: {data['avg_change']:+.2f}% (共{data['stock_count']}只)", flush=True)

        self.sector_data = dict(sorted_sectors)
        return sorted_sectors[:3]  # 返回前3热门板块

    def infer_news_from_price(self, stock_list):
        """
        【方案A】从量价数据推断隐含信息

        逻辑：
        1. 涨幅>10% + 换手率>15% = 疑似重大利好
        2. 涨幅>15% + 换手率>20% = 确认重大利好
        3. 连续大涨 = 趋势形成
        """
        inferred_news = []

        for stock in stock_list[:3]:  # 只分析前3只龙头
            change = stock['change_pct']
            turnover = stock.get('turnover_rate', 0)
            volume = stock.get('volume', 0)
            name = stock['name']

            # 信号1: 强烈异动（重大利好）
            if change > 15 and turnover > 20:
                inferred_news.append({
                    'title': f'💥 {name}暴涨{change:.1f}%且换手率{turnover:.1f}%，疑似重大利好催化（订单/并购/业绩等）',
                    'source': '量价信号（强）',
                    'confidence': 'high'
                })

            # 信号2: 明显异动（较强利好）
            elif change > 10 and turnover > 15:
                inferred_news.append({
                    'title': f'📈 {name}大涨{change:.1f}%且高换手{turnover:.1f}%，资金积极参与，可能有未公开利好',
                    'source': '量价信号（中）',
                    'confidence': 'medium'
                })

            # 信号3: 温和上涨但换手活跃
            elif change > 5 and turnover > 10:
                inferred_news.append({
                    'title': f'🔥 {name}上涨{change:.1f}%伴随活跃换手，资金关注度提升',
                    'source': '量价信号（弱）',
                    'confidence': 'low'
                })

            # 信号4: 成交额巨大（资金抢筹）
            if volume > 1e9:  # 成交额>10亿
                inferred_news.append({
                    'title': f'💰 {name}成交额{volume/1e8:.1f}亿，资金大幅流入',
                    'source': '成交额信号',
                    'confidence': 'medium'
                })

        return inferred_news

    def fetch_sector_news(self, sector_name, stock_list):
        """
        获取板块相关资讯（整合多个来源）

        来源优先级：
        1. 量价推断信号（方案A）- 最可靠
        2. Gemini联网搜索（方案B）- 获取真实新闻
        3. 新浪财经资讯 - 可能为空
        """
        all_news = []

        # 【方案A】优先：从量价推断隐含信息
        inferred_news = self.infer_news_from_price(stock_list)
        all_news.extend(inferred_news)

        # 【方案B】次要：Gemini联网搜索
        try:
            from gemini_news_search import GeminiNewsSearcher
            import os
            if os.getenv('GEMINI_API_KEY'):
                print("🔍 使用Gemini联网搜索最新资讯...")
                searcher = GeminiNewsSearcher()
                gemini_news = searcher.search_sector_news(sector_name, stock_list[:2])
                all_news.extend(gemini_news)
                print(f"✅ Gemini搜索完成，找到{len(gemini_news)}条")
        except Exception as e:
            print(f"⚠️ Gemini搜索失败: {e}")

        # 【方案C】补充：富途资金流数据
        try:
            for stock in stock_list[:2]:  # 分析前2只龙头
                ret, data = self.quote_ctx.get_capital_flow([stock['code']])
                if ret == RET_OK and not data.empty:
                    main_flow = data.iloc[0].get('main_net_inflow', 0) / 1e8  # 转换为亿
                    if abs(main_flow) > 0.1:  # 主力资金 > 1000万
                        direction = "流入" if main_flow > 0 else "流出"
                        all_news.append({
                            'title': f"💰 {stock['name']}主力资金{direction}{abs(main_flow):.2f}亿",
                            'source': '富途资金流',
                            'confidence': 'high'
                        })
        except Exception as e:
            pass  # 资金流数据可选

        # 【方案D】最新：Grok社区热度情绪
        try:
            from grok_sentiment_analyzer import GrokSentimentAnalyzer
            import os
            if os.getenv('GROK_API_KEY'):
                print("🔥 使用Grok分析社区热度...")
                grok = GrokSentimentAnalyzer()

                # 准备股票列表
                top_stocks = [
                    {'name': s['name'], 'code': s['code']}
                    for s in stock_list[:2]
                ]

                sentiment_results = grok.analyze_sector_sentiment(sector_name, top_stocks)

                # 提取关键信息
                for result in sentiment_results:
                    data = result.get('data', {})
                    if result['type'] == 'sector':
                        heat = data.get('heat_score', 0)
                        sentiment = data.get('sentiment', 'unknown')
                        topics = data.get('key_topics', [])

                        if heat > 50:  # 热度超过50才添加
                            emoji = '🔥' if heat > 70 else '🌡️'
                            all_news.append({
                                'title': f"{emoji} 社区热度{heat}/100，情绪{sentiment}，热议：{', '.join(topics[:2])}",
                                'source': 'Grok社区分析',
                                'confidence': 'high' if heat > 70 else 'medium'
                            })

                    elif result['type'] == 'stock':
                        heat = data.get('heat_score', 0)
                        sentiment = data.get('sentiment', 'unknown')
                        summary = data.get('summary', '')

                        if heat > 30:  # 个股热度门槛
                            all_news.append({
                                'title': f"🗣️ {result['name']}社区热度{heat}/100 - {summary}",
                                'source': 'Grok社区分析',
                                'confidence': 'medium'
                            })

                print(f"✅ Grok分析完成")
        except Exception as e:
            print(f"⚠️ Grok分析失败: {e}")

        # 【方案E】X API：直接获取推文数据
        try:
            from x_api_integration import XAPIClient
            import os
            if os.getenv('X_BEARER_TOKEN'):
                print("🐦 使用X API获取推文数据...")
                x_client = XAPIClient()

                # 分析板块热度
                keywords = [sector_name] + [s['name'] for s in stock_list[:2]]
                sector_heat = x_client.get_sector_heat(sector_name, keywords)

                if sector_heat['heat_score'] > 30:
                    all_news.append({
                        'title': f"🐦 X平台热度{sector_heat['heat_score']}/100，{sector_heat['mention_count']}条提及，{sector_heat['total_engagement']}次互动",
                        'source': 'X API',
                        'confidence': 'high'
                    })

                # 分析龙头股提及
                for stock in stock_list[:2]:
                    mention_data = x_client.get_stock_mentions(stock['name'], stock['code'])

                    if mention_data['mention_count'] > 5:  # 至少5次提及
                        sentiment_emoji = {
                            'positive': '📈',
                            'neutral': '➡️',
                            'negative': '📉'
                        }.get(mention_data['sentiment_preview'], '❓')

                        all_news.append({
                            'title': f"🐦 {stock['name']}被提及{mention_data['mention_count']}次 {sentiment_emoji} ({mention_data['total_likes']}赞/{mention_data['total_retweets']}转)",
                            'source': 'X API',
                            'confidence': 'medium'
                        })

                print(f"✅ X API数据获取完成")
        except Exception as e:
            print(f"⚠️ X API获取失败: {e}")

        # 【原有逻辑】次要：新浪财经资讯
        if not self.news_cache:
            try:
                url = "https://feed.mix.sina.com.cn/api/roll/get"
                params = {
                    'pageid': '153',
                    'lid': '2509',
                    'num': 50,
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
                        for item in data['result']['data']:
                            title = item.get('title', '').strip()
                            if title:
                                self.news_cache.append({
                                    'title': title,
                                    'time': item.get('intime', ''),
                                    'source': '新浪财经'
                                })
            except:
                pass

        # 匹配板块相关新闻
        keywords = [sector_name]
        for stock in stock_list[:3]:
            code = stock['code'].replace('HK.', '').lstrip('0')
            keywords.append(code)

        for news in self.news_cache:
            for keyword in keywords:
                if keyword in news['title']:
                    all_news.append(news)
                    break

        return all_news[:8]  # 返回前8条（量价+资讯）

    def analyze_sector_with_ai(self, sector_name, sector_data, news_list):
        """
        使用AI分析板块炒作周期和进场时机
        优先使用Gemini，失败时降级到规则分析

        返回：
        {
            'reason': '涨的原因',
            'cycle': '炒作周期（1-3天/5-10天/10天+）',
            'entry_timing': '进场时机判断',
            'recommendation': '买入/观望/回调买入/长期持有',
            'confidence': 0.8  # 信心指数
        }
        """
        avg_change = sector_data['avg_change']
        stocks = sector_data['stocks']
        high_volume_count = sum(1 for s in stocks if s.get('turnover_rate', 0) > 10)

        # 优先尝试Gemini分析
        try:
            from gemini_analyzer import GeminiAnalyzer
            import os
            if os.getenv('GEMINI_API_KEY'):
                print("🤖 使用Gemini 2.5 Flash分析...")
                analyzer = GeminiAnalyzer(model='gemini-2.5-flash')
                analysis = analyzer.analyze_sector_potential(sector_name, sector_data, news_list)
                print("✅ Gemini分析完成")
                return analysis
        except Exception as e:
            print(f"⚠️ Gemini分析失败，降级到规则分析: {e}")

        # 降级到规则分析
        print("📊 使用规则分析...")
        analysis = self._rule_based_analysis(sector_name, avg_change, high_volume_count, news_list)
        return analysis

    def _rule_based_analysis(self, sector_name, avg_change, high_volume_count, news_list):
        """
        基于规则的分析（简化版，可替换为GPT-4）
        增强版：能判断长期持有价值
        """
        analysis = {
            'reason': '',
            'catalyst': '',
            'cycle': '',
            'stage': '',
            'entry_timing': '',
            'recommendation': '',
            'confidence': 0.0,
            'risk': '',
            'hold_strategy': {
                'type': '短线',
                'reason': '',
                'fundamentals': '',
                'exit_signal': ''
            }
        }

        # 判断涨的原因
        has_news = len(news_list) > 0

        if has_news:
            # 有资讯支撑
            news_text = ' '.join([n['title'] for n in news_list])

            # 判断是否有长期持有价值
            long_term_keywords = ['业绩增长', '盈利', '政策', '规划', '技术突破', '龙头', '壁垒']
            has_long_term = any(kw in news_text for kw in long_term_keywords)

            if '业绩' in news_text or '盈利' in news_text:
                analysis['reason'] = '业绩驱动'
                analysis['catalyst'] = '公司业绩超预期'
                analysis['cycle'] = '10天+'
                analysis['confidence'] = 0.8

                if '增长' in news_text or '超预期' in news_text:
                    # 长期持有价值
                    analysis['hold_strategy'] = {
                        'type': '长线',
                        'reason': '业绩持续增长，有长期投资价值',
                        'fundamentals': '盈利能力强，业绩增长确定性高',
                        'exit_signal': '业绩低于预期或行业景气度下降'
                    }
                else:
                    analysis['hold_strategy'] = {
                        'type': '中线',
                        'reason': '业绩改善，中线持有',
                        'fundamentals': '业绩有所改善',
                        'exit_signal': '业绩反转或达到目标价'
                    }

            elif '政策' in news_text or '规划' in news_text:
                analysis['reason'] = '政策利好'
                analysis['catalyst'] = '政策扶持或行业规划'
                analysis['cycle'] = '10天+'
                analysis['confidence'] = 0.85

                # 政策支持通常有长期价值
                analysis['hold_strategy'] = {
                    'type': '长线',
                    'reason': '国家政策扶持，行业长期向好',
                    'fundamentals': '政策红利，行业处于上升周期',
                    'exit_signal': '政策退出或行业进入下行周期'
                }

            elif '订单' in news_text or '合作' in news_text:
                analysis['reason'] = '订单催化'
                analysis['catalyst'] = '大订单或战略合作'
                analysis['cycle'] = '5-10天'
                analysis['confidence'] = 0.75

                if '长期' in news_text or '战略' in news_text:
                    analysis['hold_strategy'] = {
                        'type': '中线',
                        'reason': '战略合作，中长期受益',
                        'fundamentals': '订单可持续性强',
                        'exit_signal': '合作进展不及预期'
                    }
                else:
                    analysis['hold_strategy'] = {
                        'type': '短线',
                        'reason': '订单催化，短期炒作',
                        'fundamentals': '单次订单，持续性待观察',
                        'exit_signal': '订单兑现后离场'
                    }
            else:
                analysis['reason'] = '概念炒作'
                analysis['catalyst'] = '热点概念'
                analysis['cycle'] = '1-3天'
                analysis['confidence'] = 0.6
                analysis['hold_strategy'] = {
                    'type': '短线',
                    'reason': '概念炒作，不建议长期持有',
                    'fundamentals': '缺乏基本面支撑',
                    'exit_signal': '概念降温立即离场'
                }
        else:
            # 无资讯，纯价格异动
            if avg_change > 10:
                analysis['reason'] = '资金抱团'
                analysis['catalyst'] = '主力资金集中买入'
                analysis['cycle'] = '1-3天'
                analysis['confidence'] = 0.5
            else:
                analysis['reason'] = '跟风炒作'
                analysis['catalyst'] = '跟随市场热点'
                analysis['cycle'] = '1-3天'
                analysis['confidence'] = 0.4

            # 无资讯只能短线
            analysis['hold_strategy'] = {
                'type': '短线',
                'reason': '无明确催化剂，仅短线博弈',
                'fundamentals': '无基本面支撑',
                'exit_signal': '快进快出，不过夜'
            }

        # 判断进场时机
        if avg_change < 5:
            analysis['stage'] = '早期'
            analysis['entry_timing'] = '板块刚启动，可以进场'
            if high_volume_count >= 2:
                analysis['recommendation'] = '买入'
            else:
                analysis['recommendation'] = '观望'
        elif avg_change < 10:
            analysis['stage'] = '中期'
            analysis['entry_timing'] = '板块已有一定涨幅，谨慎追高'
            analysis['recommendation'] = '回调买入'
        else:
            analysis['stage'] = '后期'
            analysis['entry_timing'] = '板块涨幅较大，风险较高'
            analysis['recommendation'] = '观望'

        # 风险提示
        if analysis['cycle'] == '1-3天':
            analysis['risk'] = '短线炒作，注意快进快出'
        elif analysis['cycle'] == '5-10天':
            analysis['risk'] = '中线持有，设置止损'
        else:
            analysis['risk'] = '长线布局，分批建仓'

        return analysis

    def generate_trading_advice(self, hot_sectors):
        """
        生成交易建议报告
        """
        print("\n" + "="*60, flush=True)
        print("📊 板块交易建议", flush=True)
        print("="*60 + "\n", flush=True)

        report = f"*📊 板块交易顾问报告*\n"
        report += f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"

        for i, (sector, data) in enumerate(hot_sectors, 1):
            print(f"\n🔥 {i}. {sector} (涨幅: {data['avg_change']:+.2f}%)\n", flush=True)

            # 获取资讯
            news = self.fetch_sector_news(sector, data['stocks'])
            print(f"   📰 找到 {len(news)} 条相关资讯", flush=True)

            # AI分析
            analysis = self.analyze_sector_with_ai(sector, data, news)

            # 打印分析
            print(f"   💡 原因: {analysis['reason']}", flush=True)
            print(f"   ⏱️  周期: {analysis['cycle']}", flush=True)
            print(f"   📍 阶段: {analysis['stage']}", flush=True)
            print(f"   🎯 建议: {analysis['recommendation']}", flush=True)
            print(f"   📊 信心: {analysis['confidence']*100:.0f}%", flush=True)

            # 生成Telegram报告
            emoji_map = {
                '买入': '🟢',
                '观望': '⚪',
                '回调买入': '🟡',
                '长期持有': '💎'
            }
            emoji = emoji_map.get(analysis['recommendation'], '⚪')

            report += f"*{i}. {sector} {data['avg_change']:+.2f}%*\n"
            report += f"{emoji} *{analysis['recommendation']}* (信心{analysis['confidence']*100:.0f}%)\n\n"

            # 【透明化】数据来源
            report += f"📊 *数据来源*\n"
            report += f"  • 价格: 富途实时行情\n"
            report += f"  • 资讯: {len(news)}条 ("
            sources = set([n.get('source', '未知') for n in news])
            report += ', '.join(sources) + ")\n\n"

            report += f"💡 {analysis['reason']}: {analysis['catalyst']}\n"
            report += f"⏱️ 预期周期: {analysis['cycle']}\n"
            report += f"📍 当前阶段: {analysis['stage']}\n"
            report += f"💰 {analysis['entry_timing']}\n"

            # 添加持有策略
            if 'hold_strategy' in analysis:
                hold = analysis['hold_strategy']
                if hold['type'] == '长线':
                    report += f"\n💎 **长期持有价值**\n"
                    report += f"📊 基本面: {hold['fundamentals']}\n"
                    report += f"🎯 持有理由: {hold['reason']}\n"
                    report += f"🚪 卖出信号: {hold['exit_signal']}\n"
                elif hold['type'] == '中线':
                    report += f"\n📈 中线持有 ({analysis['cycle']})\n"
                    report += f"🎯 {hold['reason']}\n"
                else:
                    report += f"\n⚡ 短线操作: {hold['reason']}\n"

            report += f"\n⚠️ 风险: {analysis['risk']}\n"

            # 添加龙头股
            top_stock = max(data['stocks'], key=lambda x: x['change_pct'])
            report += f"\n🐲 龙头: {top_stock['name']} {top_stock['change_pct']:+.2f}%\n"

            # 添加资讯详情（按来源分类）
            if news:
                report += f"\n📰 *资讯详情*\n"
                # 量价信号
                price_signals = [n for n in news if n.get('source') in ['量价信号（强）', '量价信号（中）', '量价信号（弱）']]
                if price_signals:
                    report += f"💹 量价信号:\n"
                    for n in price_signals[:2]:
                        report += f"  • {n['title']}\n"

                # 联网搜索
                search_news = [n for n in news if 'Google搜索' in n.get('source', '')]
                if search_news:
                    report += f"🔍 联网搜索:\n"
                    for n in search_news[:2]:
                        report += f"  • {n['title']}\n"

                # 资金流
                fund_news = [n for n in news if '资金流' in n.get('source', '')]
                if fund_news:
                    report += f"💰 资金动向:\n"
                    for n in fund_news[:1]:
                        report += f"  • {n['title']}\n"

                # Grok社区分析
                grok_news = [n for n in news if 'Grok' in n.get('source', '')]
                if grok_news:
                    report += f"🔥 社区热度:\n"
                    for n in grok_news[:2]:
                        report += f"  • {n['title']}\n"

            report += "\n" + "-"*30 + "\n\n"

        return report

    def send_telegram(self, message):
        """发送Telegram消息"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except:
            return False

    def close(self):
        """关闭连接"""
        if self.quote_ctx:
            self.quote_ctx.close()


def main():
    print("\n" + "="*60, flush=True)
    print("🎯 板块交易顾问系统", flush=True)
    print("="*60, flush=True)
    print("功能: 发现热门板块 → 分析炒作周期 → 推荐进场时机", flush=True)
    print("="*60 + "\n", flush=True)

    advisor = SectorTradingAdvisor()

    if not advisor.connect_futu():
        return

    # 1. 扫描热门板块
    hot_sectors = advisor.scan_hot_sectors()

    if not hot_sectors:
        print("\n⚠️ 暂无明显热门板块", flush=True)
        return

    # 2. 生成交易建议
    report = advisor.generate_trading_advice(hot_sectors)

    # 3. 推送Telegram
    print("\n📱 推送Telegram...", flush=True)
    if advisor.send_telegram(report):
        print("✅ 推送成功！", flush=True)
    else:
        print("⚠️ 推送失败", flush=True)
        print("\n报告预览:")
        print(report)

    advisor.close()
    print("\n✅ 分析完成\n", flush=True)


if __name__ == '__main__':
    main()
