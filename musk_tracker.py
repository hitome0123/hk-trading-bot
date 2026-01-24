#!/usr/bin/env python3
"""
马斯克动态追踪器
追踪马斯克推文、采访、新闻，分析相关板块
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import requests
import re
import json
from datetime import datetime
from typing import Dict, List

# 马斯克相关关键词 -> 板块映射
MUSK_KEYWORDS = {
    # 特斯拉相关
    'tesla': ['新能源汽车', '电动车', '锂电池'],
    'model': ['新能源汽车', '电动车'],
    'cybertruck': ['新能源汽车', '电动车'],
    'fsd': ['自动驾驶', '智能汽车'],
    'autopilot': ['自动驾驶', '智能汽车'],
    'supercharger': ['充电桩', '新能源'],

    # SpaceX相关
    'spacex': ['商业航天', '卫星'],
    'starship': ['商业航天', '火箭'],
    'falcon': ['商业航天', '火箭'],
    'starlink': ['卫星互联网', '通信'],
    'rocket': ['商业航天', '航天'],
    'mars': ['商业航天', '航天'],
    'launch': ['商业航天', '航天'],

    # AI相关
    'grok': ['AI', '人工智能', '大模型'],
    'xai': ['AI', '人工智能'],
    'ai': ['AI', '人工智能', '算力'],
    'robot': ['机器人', '人形机器人'],
    'optimus': ['机器人', '人形机器人'],
    'bot': ['机器人'],

    # 加密货币
    'doge': ['加密货币', '狗狗币'],
    'bitcoin': ['加密货币', '比特币'],
    'crypto': ['加密货币'],

    # Neuralink
    'neuralink': ['脑机接口', '医疗科技'],
    'brain': ['脑机接口'],

    # Boring Company
    'boring': ['隧道', '基建'],
    'tunnel': ['隧道', '基建'],

    # X/Twitter
    'twitter': ['社交媒体', '互联网'],

    # 能源
    'solar': ['光伏', '太阳能'],
    'battery': ['锂电池', '储能'],
    'energy': ['新能源', '储能'],
    'powerwall': ['储能', '新能源'],
}

# 板块对应的港股
SECTOR_STOCKS = {
    '新能源汽车': [('01211', '比亚迪'), ('02015', '理想汽车'), ('09868', '小鹏'), ('09866', '蔚来')],
    '电动车': [('01211', '比亚迪'), ('02015', '理想汽车')],
    '锂电池': [('01211', '比亚迪'), ('03800', '协鑫科技')],
    '商业航天': [('01045', '亚太卫星'), ('02357', '中航科工'), ('00031', '航天控股')],
    '卫星互联网': [('01045', '亚太卫星'), ('00471', '中播数据')],
    '卫星': [('01045', '亚太卫星')],
    'AI': [('09888', '百度'), ('00020', '商汤'), ('09888', '百度')],
    '人工智能': [('09888', '百度'), ('00020', '商汤'), ('06082', '壁仞科技')],
    '机器人': [('02382', '蓝思科技'), ('01810', '小米')],
    '人形机器人': [('02382', '蓝思科技')],
    '光伏': [('03800', '协鑫科技'), ('00968', '信义光能')],
    '太阳能': [('03800', '协鑫科技'), ('00968', '信义光能')],
    '储能': [('03800', '协鑫科技')],
    '芯片': [('00981', '中芯国际'), ('01347', '华虹半导体')],
    '算力': [('00981', '中芯国际'), ('06082', '壁仞科技')],
    '自动驾驶': [('01211', '比亚迪'), ('02015', '理想汽车')],
}


class MuskTracker:
    """马斯克动态追踪器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/html',
        }

    def search_musk_news(self) -> List[Dict]:
        """搜索马斯克相关新闻"""
        news_list = []

        # 1. 搜狐财经搜索
        try:
            url = "https://search.sohu.com/news"
            params = {'keyword': '马斯克', 'pageNo': 1}
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            # 简单提取标题
            titles = re.findall(r'<h4[^>]*>.*?<a[^>]*>([^<]+)</a>', resp.text)
            for t in titles[:5]:
                if '马斯克' in t or 'Musk' in t:
                    news_list.append({'title': t, 'source': '搜狐'})
        except:
            pass

        # 2. 新浪财经
        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                'pageid': '153', 'lid': '2509', 'k': '马斯克',
                'num': 10, 'page': 1
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            if data.get('result') and data['result'].get('data'):
                for item in data['result']['data'][:5]:
                    title = item.get('title', '')
                    if title:
                        news_list.append({'title': title, 'source': '新浪财经'})
        except:
            pass

        # 3. 东财搜索
        try:
            url = "https://searchapi.eastmoney.com/api/suggest/get"
            params = {'input': '马斯克', 'type': '14', 'count': 10}
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
        except:
            pass

        return news_list

    def search_twitter_trends(self) -> List[Dict]:
        """获取X/Twitter上马斯克相关趋势（通过第三方）"""
        trends = []

        # 使用新闻源追踪马斯克推特内容
        try:
            # 尝试获取马斯克最新动态的新闻报道
            keywords = ['Elon Musk tweet', 'Musk said', 'Musk announces']
            for kw in keywords:
                url = f"https://news.google.com/rss/search?q={kw}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
                # 这里可以解析RSS获取新闻
        except:
            pass

        return trends

    def analyze_text_for_sectors(self, text: str) -> List[str]:
        """分析文本，提取相关板块"""
        text_lower = text.lower()
        sectors = set()

        for keyword, sector_list in MUSK_KEYWORDS.items():
            if keyword in text_lower:
                sectors.update(sector_list)

        return list(sectors)

    def get_sector_stocks(self, sectors: List[str]) -> List[Dict]:
        """获取板块对应的港股"""
        stocks = []
        seen = set()

        for sector in sectors:
            if sector in SECTOR_STOCKS:
                for code, name in SECTOR_STOCKS[sector]:
                    if code not in seen:
                        stocks.append({'code': code, 'name': name, 'sector': sector})
                        seen.add(code)

        return stocks

    def get_musk_report(self) -> Dict:
        """生成马斯克动态报告"""
        report = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'news': [],
            'sectors': [],
            'stocks': [],
        }

        # 获取新闻
        news = self.search_musk_news()
        report['news'] = news[:8]

        # 分析所有新闻标题，提取板块
        all_sectors = set()
        for n in news:
            sectors = self.analyze_text_for_sectors(n['title'])
            all_sectors.update(sectors)

        # 如果没有分析出板块，添加默认关注板块
        if not all_sectors:
            all_sectors = {'商业航天', '新能源汽车', 'AI', '机器人'}

        report['sectors'] = list(all_sectors)
        report['stocks'] = self.get_sector_stocks(list(all_sectors))

        return report

    def format_report(self, report: Dict) -> str:
        """格式化报告为Markdown"""
        content = f"""### 🚀 马斯克动态追踪

**更新时间:** {report['time']}

---

#### 📰 最新相关新闻

"""
        if report['news']:
            for i, n in enumerate(report['news'][:6], 1):
                content += f"{i}. {n['title'][:45]}... ({n['source']})\n"
        else:
            content += "暂无最新新闻\n"

        content += "\n---\n\n#### 🎯 关联板块\n\n"
        for sector in report['sectors'][:8]:
            content += f"• **{sector}**\n"

        content += "\n---\n\n#### 📈 关注港股\n\n"
        if report['stocks']:
            content += "| 股票 | 代码 | 关联板块 |\n"
            content += "|------|------|----------|\n"
            for s in report['stocks'][:8]:
                content += f"| {s['name']} | {s['code']} | {s['sector']} |\n"

        content += """
---

#### 💡 马斯克常关注领域

- **SpaceX/Starlink** → 商业航天、卫星互联网
- **Tesla** → 新能源汽车、自动驾驶、储能
- **xAI/Grok** → AI、大模型
- **Optimus** → 人形机器人
- **Neuralink** → 脑机接口

---

*持续追踪马斯克动态，第一时间发现投资机会*
"""
        return content


def get_musk_update():
    """获取马斯克动态更新"""
    tracker = MuskTracker()
    report = tracker.get_musk_report()
    return tracker.format_report(report)


def push_musk_update():
    """推送马斯克动态到钉钉"""
    from dingtalk_notifier import DingTalkNotifier

    tracker = MuskTracker()
    report = tracker.get_musk_report()
    content = tracker.format_report(report)

    notifier = DingTalkNotifier()
    notifier.send_markdown("🚀 马斯克动态", content)
    print("✅ 已推送马斯克动态到钉钉")

    return content


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'push':
        content = push_musk_update()
        print(content)
    else:
        tracker = MuskTracker()
        report = tracker.get_musk_report()
        print(tracker.format_report(report))
