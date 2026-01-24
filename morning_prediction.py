#!/usr/bin/env python3
"""
盘前预判系统
每天09:00自动分析隔夜消息，预测今日热点板块
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import re

from dingtalk_notifier import DingTalkNotifier


class MorningPrediction:
    """盘前预判系统"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.notifier = DingTalkNotifier()

        # 板块关键词映射 (扩展版)
        self.sector_keywords = {
            'AI人工智能': ['AI', '人工智能', '大模型', 'ChatGPT', 'GPT', '英伟达', 'NVIDIA', '算力', '芯片', 'DeepSeek', '智能', '机器学习', 'AGI', '智算'],
            '商业航天': ['SpaceX', '火箭', '卫星', 'Starlink', '星链', '航天', '太空', 'Starship', '北斗', '遥感', '低轨'],
            '新能源汽车': ['特斯拉', 'Tesla', '电动车', 'EV', '新能源车', '比亚迪', '蔚来', '小鹏', '理想', '充电桩', '固态电池', '智能驾驶', '自动驾驶'],
            '机器人': ['机器人', 'Optimus', '人形机器人', '波士顿动力', '自动化', '工业机器人', '服务机器人', '具身智能'],
            '芯片半导体': ['芯片', '半导体', '光刻机', 'ASML', '台积电', '中芯', '华为', '先进制程', '国产替代', 'GPU', 'CPU'],
            '光伏新能源': ['光伏', '太阳能', '储能', '锂电池', '宁德时代', '风电', '氢能', '绿电', '碳中和'],
            '互联网科技': ['阿里', '腾讯', '京东', '美团', '拼多多', '互联网', '电商', '直播', '短视频'],
            '生物医药': ['医药', '疫苗', '创新药', 'FDA', '新药', '生物科技', 'GLP-1', '减肥药', '基因'],
            '消费': ['消费', '茅台', '白酒', '零售', '奢侈品', '免税', '旅游', '餐饮'],
            '地产金融': ['地产', '房地产', '银行', '保险', '金融', '降息', '利率'],
            '军工国防': ['军工', '国防', '导弹', '战斗机', '舰船', '军贸'],
            '数据要素': ['数据', '数字经济', '数据交易', '隐私计算', '数据安全'],
        }

        # 官媒来源 (权重更高)
        self.official_sources = [
            '工信部', '发改委', '科技部', '国务院', '央行', '证监会',
            '财政部', '商务部', '工业和信息化部', '国资委', '新华社', '人民日报'
        ]

        # 港股标的映射
        self.sector_stocks = {
            'AI人工智能': [('09888', '百度'), ('00020', '商汤'), ('01810', '小米'), ('09888', '百度')],
            '商业航天': [('01045', '亚太卫星'), ('00471', '中播数据'), ('02357', '中航科工')],
            '新能源汽车': [('01211', '比亚迪'), ('02015', '理想'), ('09868', '小鹏'), ('09866', '蔚来')],
            '机器人': [('01810', '小米'), ('02382', '舜宇光学')],
            '芯片半导体': [('00981', '中芯国际'), ('01347', '华虹半导体')],
            '光伏新能源': [('03800', '协鑫科技'), ('00968', '信义光能')],
            '互联网科技': [('09988', '阿里'), ('00700', '腾讯'), ('03690', '美团'), ('09618', '京东')],
            '生物医药': [('01801', '信达生物'), ('02269', '药明生物')],
        }

    def get_us_market_performance(self) -> Dict:
        """获取隔夜美股表现"""
        result = {
            'indices': [],
            'hot_stocks': [],
            'china_concept': []
        }

        try:
            # 美股指数
            url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
            params = {
                'fltt': '2',
                'secids': '100.NDX,100.DJIA,100.SPX',  # 纳斯达克、道琼斯、标普
                'fields': 'f2,f3,f4,f12,f14'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('diff'):
                for item in data['data']['diff']:
                    result['indices'].append({
                        'name': item.get('f14', ''),
                        'price': item.get('f2', 0),
                        'change_pct': item.get('f3', 0) / 100 if item.get('f3') else 0,
                    })

            # 热门中概股
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '20',
                'fs': 'm:105,m:106,m:107',  # 美股
                'fields': 'f2,f3,f12,f14',
                'fid': 'f3',
                'po': '1'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            china_keywords = ['阿里', '百度', '京东', '拼多多', '蔚来', '小鹏', '理想', '哔哩', 'B站', '腾讯']
            if data.get('data', {}).get('diff'):
                for item in data['data']['diff']:
                    name = item.get('f14', '')
                    for kw in china_keywords:
                        if kw in name:
                            result['china_concept'].append({
                                'code': item.get('f12', ''),
                                'name': name,
                                'change_pct': item.get('f3', 0) / 100 if item.get('f3') else 0,
                            })
                            break

        except Exception as e:
            print(f"获取美股数据失败: {e}")

        return result

    def get_overnight_news(self) -> List[Dict]:
        """获取隔夜重要新闻"""
        news_list = []

        try:
            # 财联社快讯
            url = "https://www.cls.cn/nodeapi/updateTelegraphList"
            params = {'app': 'CailianpressWeb', 'os': 'web', 'sv': '7.7.5'}
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('roll_data'):
                for item in data['data']['roll_data'][:30]:
                    content = item.get('content', '')
                    title = item.get('title', '') or content[:50]

                    # 检查是否匹配热点关键词
                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw.lower() in content.lower() or kw.lower() in title.lower():
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        news_list.append({
                            'title': title,
                            'content': content[:100],
                            'sectors': list(set(matched_sectors)),
                            'time': item.get('ctime', ''),
                        })
        except Exception as e:
            print(f"获取新闻失败: {e}")

        return news_list[:10]

    def get_official_news(self) -> List[Dict]:
        """获取官媒新闻 (工信部/发改委等)"""
        news_list = []

        try:
            # 新华网财经
            url = "http://qc.wa.news.cn/nodeart/list?nid=11147664&pgnum=1&cnt=20&tp=1&orderby=1"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('list'):
                for item in data['data']['list'][:15]:
                    title = item.get('Title', '')
                    content = item.get('Abstract', '') or title

                    # 检查是否来自官媒
                    is_official = any(src in title or src in content for src in self.official_sources)

                    # 匹配板块
                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in content or kw in title:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        news_list.append({
                            'title': title[:50],
                            'content': content[:100],
                            'sectors': list(set(matched_sectors)),
                            'is_official': is_official,
                            'source': '新华网',
                            'weight': 30 if is_official else 15,  # 官媒权重更高
                        })
        except Exception as e:
            print(f"获取官媒新闻失败: {e}")

        return news_list[:8]

    def get_douyin_trending(self) -> List[Dict]:
        """获取抖音热搜"""
        trending = []

        try:
            # 抖音热搜API (第三方)
            url = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
            resp = requests.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X)',
                'Referer': 'https://www.douyin.com/'
            }, timeout=10)
            data = resp.json()

            if data.get('word_list'):
                for item in data['word_list'][:20]:
                    word = item.get('word', '')

                    # 匹配板块
                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in word:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        trending.append({
                            'word': word,
                            'hot_value': item.get('hot_value', 0),
                            'sectors': list(set(matched_sectors)),
                            'source': '抖音热搜',
                        })
        except Exception as e:
            print(f"获取抖音热搜失败: {e}")

        # 备用：今日热榜API
        if not trending:
            try:
                url = "https://api.vvhan.com/api/hotlist/douyinHot"
                resp = requests.get(url, headers=self.headers, timeout=10)
                data = resp.json()

                if data.get('success') and data.get('data'):
                    for item in data['data'][:20]:
                        title = item.get('title', '')

                        matched_sectors = []
                        for sector, keywords in self.sector_keywords.items():
                            for kw in keywords:
                                if kw in title:
                                    matched_sectors.append(sector)
                                    break

                        if matched_sectors:
                            trending.append({
                                'word': title,
                                'hot_value': item.get('hot', 0),
                                'sectors': list(set(matched_sectors)),
                                'source': '抖音热搜',
                            })
            except:
                pass

        return trending[:5]

    def get_xiaohongshu_trends(self) -> List[Dict]:
        """获取小红书热门话题"""
        trends = []

        try:
            # 小红书热门话题 (第三方API)
            url = "https://api.vvhan.com/api/hotlist/xiaohongshuHot"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('success') and data.get('data'):
                for item in data['data'][:20]:
                    title = item.get('title', '')

                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in title:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        trends.append({
                            'word': title,
                            'hot_value': item.get('hot', 0),
                            'sectors': list(set(matched_sectors)),
                            'source': '小红书',
                        })
        except Exception as e:
            print(f"获取小红书热门失败: {e}")

        return trends[:5]

    def get_weibo_trending(self) -> List[Dict]:
        """获取微博热搜"""
        trending = []

        try:
            url = "https://api.vvhan.com/api/hotlist/wbHot"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('success') and data.get('data'):
                for item in data['data'][:30]:
                    title = item.get('title', '')

                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in title:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        trending.append({
                            'word': title,
                            'hot_value': item.get('hot', 0),
                            'sectors': list(set(matched_sectors)),
                            'source': '微博热搜',
                        })
        except Exception as e:
            print(f"获取微博热搜失败: {e}")

        return trending[:5]

    def get_xueqiu_hot(self) -> List[Dict]:
        """获取雪球热帖"""
        hot_list = []

        try:
            # 雪球热帖
            url = "https://xueqiu.com/statuses/hot/listV2.json"
            params = {'since_id': '-1', 'max_id': '-1', 'size': '20'}
            headers = {
                **self.headers,
                'Cookie': 'xq_a_token=test;',
                'Referer': 'https://xueqiu.com/'
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()

            if data.get('items'):
                for item in data['items'][:20]:
                    text = item.get('original_status', {}).get('text', '') or item.get('text', '')
                    title = item.get('original_status', {}).get('title', '') or text[:50]

                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in text or kw in title:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        hot_list.append({
                            'word': title[:30],
                            'hot_value': item.get('reply_count', 0) + item.get('retweet_count', 0),
                            'sectors': list(set(matched_sectors)),
                            'source': '雪球热帖',
                        })
        except Exception as e:
            print(f"获取雪球热帖失败: {e}")

        return hot_list[:5]

    def get_guba_hot(self) -> List[Dict]:
        """获取东财股吧热帖"""
        hot_list = []

        try:
            # 东财股吧热门
            url = "https://guba.eastmoney.com/interface/GetData.aspx"
            params = {
                'path': 'rank/hot',
                'top': '20'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)

            # 尝试解析
            text = resp.text
            import re
            # 提取标题
            titles = re.findall(r'"Title":"([^"]+)"', text)

            for title in titles[:20]:
                matched_sectors = []
                for sector, keywords in self.sector_keywords.items():
                    for kw in keywords:
                        if kw in title:
                            matched_sectors.append(sector)
                            break

                if matched_sectors:
                    hot_list.append({
                        'word': title[:30],
                        'sectors': list(set(matched_sectors)),
                        'source': '东财股吧',
                    })
        except Exception as e:
            print(f"获取东财股吧失败: {e}")

        # 备用：东财人气榜
        if not hot_list:
            try:
                url = "https://push2.eastmoney.com/api/qt/clist/get"
                params = {
                    'pn': '1', 'pz': '20', 'fs': 'm:128',
                    'fields': 'f12,f14', 'fid': 'f3', 'po': '1'
                }
                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                data = resp.json()

                if data.get('data', {}).get('diff'):
                    for item in data['data']['diff'][:10]:
                        name = item.get('f14', '')
                        for sector, stocks in self.sector_stocks.items():
                            for code, stock_name in stocks:
                                if stock_name in name:
                                    hot_list.append({
                                        'word': f"{name}被热议",
                                        'sectors': [sector],
                                        'source': '东财股吧',
                                    })
                                    break
            except:
                pass

        return hot_list[:5]

    def get_ths_hot(self) -> List[Dict]:
        """获取同花顺热股/概念"""
        hot_list = []

        try:
            # 同花顺热门概念
            url = "https://eq.10jqka.com.cn/open/api/hot_list"
            params = {'type': 'concept', 'list_type': 'rise'}
            headers = {
                **self.headers,
                'Referer': 'https://www.10jqka.com.cn/'
            }
            resp = requests.get(url, params=params, headers=headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('list'):
                for item in data['data']['list'][:15]:
                    name = item.get('name', '')

                    matched_sectors = []
                    for sector, keywords in self.sector_keywords.items():
                        for kw in keywords:
                            if kw in name:
                                matched_sectors.append(sector)
                                break

                    if matched_sectors:
                        hot_list.append({
                            'word': name,
                            'hot_value': item.get('rise', 0),
                            'sectors': list(set(matched_sectors)),
                            'source': '同花顺概念',
                        })
        except Exception as e:
            print(f"获取同花顺热股失败: {e}")

        # 备用：同花顺问财热词
        if not hot_list:
            try:
                url = "https://www.iwencai.com/gateway/urp/v7/landing/getDataList"
                resp = requests.get(url, headers=self.headers, timeout=10)
                data = resp.json()

                if data.get('data'):
                    for item in data['data'][:10]:
                        word = item.get('word', '')

                        matched_sectors = []
                        for sector, keywords in self.sector_keywords.items():
                            for kw in keywords:
                                if kw in word:
                                    matched_sectors.append(sector)
                                    break

                        if matched_sectors:
                            hot_list.append({
                                'word': word,
                                'sectors': list(set(matched_sectors)),
                                'source': '同花顺问财',
                            })
            except:
                pass

        return hot_list[:5]

    def get_yesterday_capital_flow(self) -> List[Dict]:
        """获取昨日资金流向"""
        flows = []

        try:
            # 港股资金流向
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': '1',
                'pz': '50',
                'fs': 'm:128',  # 港股
                'fields': 'f12,f14,f62,f184,f66',  # 代码,名称,主力净流入,主力净流入占比,超大单
                'fid': 'f62',
                'po': '1'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('diff'):
                for item in data['data']['diff'][:20]:
                    net_inflow = item.get('f62', 0)
                    if isinstance(net_inflow, str) and net_inflow == '-':
                        continue
                    if net_inflow and net_inflow > 0:
                        flows.append({
                            'code': item.get('f12', ''),
                            'name': item.get('f14', ''),
                            'net_inflow': net_inflow / 100000000,  # 转为亿
                            'inflow_ratio': item.get('f184', 0) / 100 if item.get('f184') else 0,
                        })

        except Exception as e:
            print(f"获取资金流向失败: {e}")

        return flows[:10]

    def get_social_heat(self) -> List[Dict]:
        """获取社交媒体热度"""
        heat_list = []

        try:
            # 雪球热股
            url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
            params = {'size': '20', 'type': '12'}
            headers = {
                **self.headers,
                'Cookie': 'xq_a_token=test'  # 简单cookie
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()

            if data.get('data', {}).get('items'):
                for item in data['data']['items']:
                    symbol = item.get('symbol', '')
                    if symbol.startswith('HK') or symbol.isdigit():
                        heat_list.append({
                            'code': symbol.replace('HK', ''),
                            'name': item.get('name', ''),
                            'heat': item.get('value', 0),
                        })
        except Exception as e:
            print(f"获取社交热度失败: {e}")

        return heat_list[:10]

    def analyze_and_predict(self) -> Dict:
        """分析并预测今日热点"""
        print("📊 正在分析隔夜数据...")

        # 收集数据
        print("  - 获取美股数据...")
        us_data = self.get_us_market_performance()

        print("  - 获取财经新闻...")
        news = self.get_overnight_news()

        print("  - 获取官媒新闻...")
        official_news = self.get_official_news()

        print("  - 获取抖音热搜...")
        douyin = self.get_douyin_trending()

        print("  - 获取小红书热门...")
        xiaohongshu = self.get_xiaohongshu_trends()

        print("  - 获取微博热搜...")
        weibo = self.get_weibo_trending()

        print("  - 获取雪球热帖...")
        xueqiu = self.get_xueqiu_hot()

        print("  - 获取东财股吧...")
        guba = self.get_guba_hot()

        print("  - 获取同花顺热股...")
        ths = self.get_ths_hot()

        print("  - 获取资金流向...")
        capital_flow = self.get_yesterday_capital_flow()

        print("  - 获取社交热度...")
        social_heat = self.get_social_heat()

        # 板块评分 (带来源追踪)
        sector_scores = {}
        sector_sources = {}  # 记录每个板块的信号来源

        def add_score(sector, points, source):
            sector_scores[sector] = sector_scores.get(sector, 0) + points
            if sector not in sector_sources:
                sector_sources[sector] = []
            sector_sources[sector].append(source)

        # 1. 财经新闻评分 (+20)
        for n in news:
            for sector in n.get('sectors', []):
                add_score(sector, 20, f"财联社: {n.get('title', '')[:20]}")

        # 2. 官媒新闻评分 (+30，权重最高)
        for n in official_news:
            weight = n.get('weight', 15)
            for sector in n.get('sectors', []):
                source_name = "官媒" if n.get('is_official') else "新华网"
                add_score(sector, weight, f"{source_name}: {n.get('title', '')[:20]}")

        # 3. 抖音热搜评分 (+25，流量风向标)
        for t in douyin:
            for sector in t.get('sectors', []):
                add_score(sector, 25, f"抖音热搜: {t.get('word', '')[:15]}")

        # 4. 小红书热门评分 (+20，年轻消费风向)
        for t in xiaohongshu:
            for sector in t.get('sectors', []):
                add_score(sector, 20, f"小红书: {t.get('word', '')[:15]}")

        # 5. 微博热搜评分 (+20)
        for t in weibo:
            for sector in t.get('sectors', []):
                add_score(sector, 20, f"微博热搜: {t.get('word', '')[:15]}")

        # 6. 基于美股表现评分 (+15)
        for stock in us_data.get('china_concept', []):
            change = stock.get('change_pct', 0)
            if change > 3:
                name = stock.get('name', '').lower()
                if '阿里' in name or '京东' in name or '拼多多' in name:
                    add_score('互联网科技', 15, f"中概股: {stock.get('name', '')} +{change:.1f}%")
                elif '蔚来' in name or '小鹏' in name or '理想' in name:
                    add_score('新能源汽车', 15, f"中概股: {stock.get('name', '')} +{change:.1f}%")
                elif '百度' in name:
                    add_score('AI人工智能', 15, f"中概股: {stock.get('name', '')} +{change:.1f}%")

        # 7. 基于资金流向评分 (+10)
        for flow in capital_flow:
            name = flow.get('name', '')
            inflow = flow.get('net_inflow', 0)
            if inflow > 1:
                for sector, stocks in self.sector_stocks.items():
                    for code, stock_name in stocks:
                        if stock_name in name:
                            add_score(sector, 10, f"资金流入: {name} +{inflow:.1f}亿")
                            break

        # 8. 雪球热帖评分 (+20，投资社区风向)
        for t in xueqiu:
            for sector in t.get('sectors', []):
                add_score(sector, 20, f"雪球热帖: {t.get('word', '')[:15]}")

        # 9. 东财股吧评分 (+15，散户情绪)
        for t in guba:
            for sector in t.get('sectors', []):
                add_score(sector, 15, f"东财股吧: {t.get('word', '')[:15]}")

        # 10. 同花顺概念评分 (+25，专业概念热度)
        for t in ths:
            for sector in t.get('sectors', []):
                add_score(sector, 25, f"同花顺: {t.get('word', '')[:15]}")

        # 排序
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建预测结果
        predictions = []
        for sector, score in sorted_sectors[:6]:
            stars = '⭐⭐⭐' if score >= 60 else '⭐⭐' if score >= 35 else '⭐'

            # 获取信号来源
            sources = sector_sources.get(sector, [])[:3]

            predictions.append({
                'sector': sector,
                'score': score,
                'stars': stars,
                'sources': sources,
                'stocks': self.sector_stocks.get(sector, [])[:3],
            })

        # 风险提示
        risks = []
        for idx in us_data.get('indices', []):
            if idx.get('change_pct', 0) < -1:
                risks.append(f"隔夜{idx.get('name', '')}下跌{abs(idx.get('change_pct', 0)):.1f}%")

        # 汇总热搜数据 (所有渠道)
        all_trending = douyin + xiaohongshu + weibo + xueqiu + guba + ths

        return {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'predictions': predictions,
            'capital_flow': capital_flow[:5],
            'social_heat': social_heat[:5],
            'trending': all_trending[:10],
            'risks': risks,
            'us_market': us_data.get('indices', []),
        }

    def format_report(self, result: Dict) -> str:
        """格式化报告"""
        content = f"""### 📅 {result['time']} 盘前预判

---

#### 🔮 今日预测热点

"""
        for i, p in enumerate(result['predictions'][:5], 1):
            content += f"**{i}. {p['sector']}** {p['stars']} (评分:{p['score']})\n"
            # 显示信号来源
            if p.get('sources'):
                for src in p['sources'][:2]:
                    content += f"> - {src}\n"
            content += "\n"

        # 热搜词云
        trending = result.get('trending', [])
        if trending:
            content += """---

#### 🔥 社交媒体热搜

"""
            for t in trending[:10]:
                source_icon = {
                    '抖音热搜': '📱', '小红书': '📕', '微博热搜': '💬',
                    '雪球热帖': '❄️', '东财股吧': '💹', '同花顺概念': '🔥', '同花顺问财': '🔍'
                }.get(t.get('source', ''), '📰')
                content += f"- {source_icon} **{t.get('word', '')[:20]}** ({t.get('source', '')})\n"

        content += """
---

#### 📊 重点关注标的

| 股票 | 代码 | 所属板块 |
|------|------|----------|
"""
        seen = set()
        for p in result['predictions'][:3]:
            for code, name in p.get('stocks', []):
                if code not in seen:
                    content += f"| {name} | {code} | {p['sector']} |\n"
                    seen.add(code)

        content += """
---

#### 💰 昨日资金流入TOP5

| 股票 | 净流入(亿) |
|------|-----------|
"""
        for flow in result.get('capital_flow', [])[:5]:
            content += f"| {flow['name']} | +{flow['net_inflow']:.2f} |\n"

        content += """
---

#### 📈 隔夜美股表现

"""
        for idx in result.get('us_market', []):
            change = idx.get('change_pct', 0)
            icon = '🟢' if change > 0 else '🔴' if change < 0 else '⚪'
            content += f"- {icon} {idx['name']}: {change:+.2f}%\n"

        if result.get('risks'):
            content += """
---

#### ⚠️ 风险提示

"""
            for risk in result['risks']:
                content += f"- {risk}\n"

        content += """
---

*数据来源: 东财+财联社+雪球+同花顺+抖音+小红书+微博*
"""
        return content

    def run(self, push: bool = True) -> str:
        """运行盘前预判"""
        print("🌅 开始盘前预判分析...")

        result = self.analyze_and_predict()
        report = self.format_report(result)

        print(report)

        if push:
            print("\n📤 推送到钉钉...")
            self.notifier.send_markdown("📅 盘前预判", report)
            print("✅ 推送完成!")

        return report


def main():
    import sys
    predictor = MorningPrediction()
    push = 'push' in sys.argv or '--push' in sys.argv
    predictor.run(push=push)


if __name__ == '__main__':
    main()
