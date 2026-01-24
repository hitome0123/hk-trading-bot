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

        # 板块关键词映射
        self.sector_keywords = {
            'AI人工智能': ['AI', '人工智能', '大模型', 'ChatGPT', 'GPT', '英伟达', 'NVIDIA', '算力', '芯片'],
            '商业航天': ['SpaceX', '火箭', '卫星', 'Starlink', '星链', '航天', '太空', 'Starship'],
            '新能源汽车': ['特斯拉', 'Tesla', '电动车', 'EV', '新能源车', '比亚迪', '蔚来', '小鹏', '理想'],
            '机器人': ['机器人', 'Optimus', '人形机器人', '波士顿动力', '自动化'],
            '芯片半导体': ['芯片', '半导体', '光刻机', 'ASML', '台积电', '中芯', '华为'],
            '光伏新能源': ['光伏', '太阳能', '储能', '锂电池', '宁德时代'],
            '互联网科技': ['阿里', '腾讯', '京东', '美团', '拼多多', '互联网'],
            '生物医药': ['医药', '疫苗', '创新药', 'FDA', '新药', '生物科技'],
            '消费': ['消费', '茅台', '白酒', '零售', '奢侈品'],
            '地产金融': ['地产', '房地产', '银行', '保险', '金融'],
        }

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
        us_data = self.get_us_market_performance()
        news = self.get_overnight_news()
        capital_flow = self.get_yesterday_capital_flow()
        social_heat = self.get_social_heat()

        # 板块评分
        sector_scores = {}

        # 1. 基于新闻评分
        for n in news:
            for sector in n.get('sectors', []):
                sector_scores[sector] = sector_scores.get(sector, 0) + 20

        # 2. 基于美股表现评分
        for stock in us_data.get('china_concept', []):
            change = stock.get('change_pct', 0)
            if change > 3:
                # 中概股大涨，利好相关板块
                name = stock.get('name', '').lower()
                if '阿里' in name or '京东' in name or '拼多多' in name:
                    sector_scores['互联网科技'] = sector_scores.get('互联网科技', 0) + 15
                elif '蔚来' in name or '小鹏' in name or '理想' in name:
                    sector_scores['新能源汽车'] = sector_scores.get('新能源汽车', 0) + 15
                elif '百度' in name:
                    sector_scores['AI人工智能'] = sector_scores.get('AI人工智能', 0) + 15

        # 3. 基于资金流向评分
        for flow in capital_flow:
            name = flow.get('name', '')
            inflow = flow.get('net_inflow', 0)
            if inflow > 1:  # 净流入超过1亿
                for sector, stocks in self.sector_stocks.items():
                    for code, stock_name in stocks:
                        if stock_name in name:
                            sector_scores[sector] = sector_scores.get(sector, 0) + 10
                            break

        # 排序
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)

        # 构建预测结果
        predictions = []
        for sector, score in sorted_sectors[:5]:
            stars = '⭐⭐⭐' if score >= 40 else '⭐⭐' if score >= 25 else '⭐'

            # 找出催化剂
            catalysts = []
            for n in news:
                if sector in n.get('sectors', []):
                    catalysts.append(n.get('title', '')[:30])

            predictions.append({
                'sector': sector,
                'score': score,
                'stars': stars,
                'catalysts': catalysts[:2],
                'stocks': self.sector_stocks.get(sector, [])[:3],
            })

        # 风险提示
        risks = []
        for idx in us_data.get('indices', []):
            if idx.get('change_pct', 0) < -1:
                risks.append(f"隔夜{idx.get('name', '')}下跌{abs(idx.get('change_pct', 0)):.1f}%")

        return {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'predictions': predictions,
            'capital_flow': capital_flow[:5],
            'social_heat': social_heat[:5],
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
            content += f"**{i}. {p['sector']}** {p['stars']}\n"
            if p['catalysts']:
                content += f"> 催化剂: {p['catalysts'][0]}\n"
            content += "\n"

        content += """---

#### 📊 重点关注标的

| 股票 | 代码 | 所属板块 |
|------|------|----------|
"""
        seen = set()
        for p in result['predictions'][:3]:
            for code, name in p['stocks']:
                if code not in seen:
                    content += f"| {name} | {code} | {p['sector']} |\n"
                    seen.add(code)

        content += """
---

#### 💰 昨日资金流入TOP5

| 股票 | 净流入(亿) |
|------|-----------|
"""
        for flow in result['capital_flow'][:5]:
            content += f"| {flow['name']} | +{flow['net_inflow']:.2f} |\n"

        content += """
---

#### 📈 隔夜美股表现

"""
        for idx in result['us_market']:
            change = idx.get('change_pct', 0)
            icon = '🟢' if change > 0 else '🔴' if change < 0 else '⚪'
            content += f"- {icon} {idx['name']}: {change:+.2f}%\n"

        if result['risks']:
            content += """
---

#### ⚠️ 风险提示

"""
            for risk in result['risks']:
                content += f"- {risk}\n"

        content += """
---

*数据来源: 东财+财联社+雪球*
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
