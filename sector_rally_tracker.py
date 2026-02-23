#!/usr/bin/env python3
"""
板块暴涨追踪器
- 监控快讯中的板块暴涨信息
- 获取板块内个股涨幅排名
- 记录每次暴涨的龙头股
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from futu import *
from futu_news_fetcher import FutuNewsFetcher

# 板块关键词映射
SECTOR_KEYWORDS = {
    "人形机器人": ["机器人", "人形", "具身智能", "优必选", "特斯拉Optimus"],
    "AI大模型": ["大模型", "AI", "人工智能", "GPT", "智谱", "MiniMax", "DeepSeek", "豆包"],
    "芯片半导体": ["芯片", "半导体", "GPU", "算力", "英伟达", "壁仞", "天数智芯", "寒武纪"],
    "新能源车": ["新能源车", "电动车", "特斯拉", "比亚迪", "蔚来", "小鹏", "理想"],
    "光伏储能": ["光伏", "储能", "太阳能", "锂电池", "宁德时代"],
    "医药生物": ["医药", "生物", "创新药", "CXO", "疫苗"],
    "消费": ["消费", "零售", "餐饮", "白酒", "茅台"],
    "互联网": ["互联网", "电商", "阿里", "腾讯", "美团", "京东", "拼多多"],
    "金融": ["银行", "保险", "券商", "金融"],
    "地产": ["房地产", "地产", "楼市"],
    "游戏": ["游戏", "网易", "腾讯游戏", "米哈游"],
    "教育": ["教育", "培训"],
    "黄金": ["黄金", "贵金属", "金价"],
    "稀土": ["稀土", "稀有金属"],
    "军工": ["军工", "国防", "航天"],
}

# 板块代表性港股
SECTOR_STOCKS = {
    "人形机器人": ["HK.09880", "HK.02432"],  # 优必选、越疆
    "AI大模型": ["HK.02513", "HK.00100", "HK.09888"],  # 智谱、MiniMax、百度
    "芯片半导体": ["HK.06082", "HK.09903", "HK.00981", "HK.02382", "HK.06809"],  # 壁仞、天数智芯、中芯、舜宇、澜起
    "新能源车": ["HK.09866", "HK.09868", "HK.02015", "HK.01211"],  # 蔚来、小鹏、理想、比亚迪
    "光伏储能": ["HK.03800", "HK.01772"],  # 协鑫科技、赣锋锂业
    "医药生物": ["HK.02269", "HK.01801", "HK.02675"],  # 药明生物、信达、精锋
    "消费": ["HK.09633", "HK.06862", "HK.09961"],  # 农夫山泉、海底捞、携程
    "互联网": ["HK.09988", "HK.00700", "HK.03690", "HK.09618"],  # 阿里、腾讯、美团、京东
    "金融": ["HK.00388", "HK.01299", "HK.02318"],  # 港交所、友邦、平安
    "地产": ["HK.02007", "HK.00688", "HK.03333"],  # 碧桂园、中海、恒大
    "游戏": ["HK.09999", "HK.00700", "HK.02400"],  # 网易、腾讯、心动
    "黄金": ["HK.02899", "HK.01818"],  # 紫金、招金
    "稀土": ["HK.01164"],  # 中广核矿业
    "军工": ["HK.02357", "HK.03969"],  # 中航科工、中国通号
}


class SectorRallyTracker:
    """板块暴涨追踪器"""

    def __init__(self):
        self.news_fetcher = FutuNewsFetcher()
        self.quote_ctx = None
        self.history_file = os.path.join(os.path.dirname(__file__), 'sector_rally_history.json')

    def connect_futu(self):
        """连接富途"""
        if self.quote_ctx is None:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        return self.quote_ctx

    def close(self):
        """关闭连接"""
        if self.quote_ctx:
            self.quote_ctx.close()
            self.quote_ctx = None

    def detect_sector_from_news(self, news_content: str) -> List[str]:
        """从新闻内容检测相关板块"""
        detected = []
        content_lower = news_content.lower()

        for sector, keywords in SECTOR_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in content_lower:
                    if sector not in detected:
                        detected.append(sector)
                    break

        return detected

    def get_sector_stocks_performance(self, sector: str) -> List[Dict]:
        """获取板块内股票涨跌幅"""
        stocks = SECTOR_STOCKS.get(sector, [])
        if not stocks:
            return []

        self.connect_futu()

        results = []
        ret, data = self.quote_ctx.get_market_snapshot(stocks)

        if ret == RET_OK:
            for _, row in data.iterrows():
                results.append({
                    'code': row['code'],
                    'name': row['name'],
                    'price': row['last_price'],
                    'change_rate': row['price_spread'] / (row['last_price'] - row['price_spread']) * 100 if row['last_price'] != row['price_spread'] else 0,
                    'turnover': row['turnover'] / 100000000,  # 亿
                    'volume_ratio': row.get('volume_ratio', 0),
                })

        # 按涨幅排序
        results.sort(key=lambda x: x['change_rate'], reverse=True)
        return results

    def scan_hot_sectors(self, hours: int = 4) -> Dict:
        """
        扫描热门板块

        Args:
            hours: 扫描最近多少小时的新闻

        Returns:
            热门板块及其龙头股
        """
        print(f"\n{'='*60}")
        print(f"🔥 扫描热门板块 (最近{hours}小时新闻)")
        print('='*60)

        # 获取新闻
        news_list = self.news_fetcher.get_flash_news(100)

        # 过滤时间
        now = datetime.now().timestamp()
        cutoff = now - (hours * 3600)
        recent_news = [n for n in news_list if n['timestamp'] >= cutoff]

        print(f"📰 获取到 {len(recent_news)} 条新闻")

        # 统计板块出现次数
        sector_count = {}
        sector_news = {}

        for news in recent_news:
            content = news['title'] + ' ' + news['content']
            sectors = self.detect_sector_from_news(content)

            for sector in sectors:
                sector_count[sector] = sector_count.get(sector, 0) + 1
                if sector not in sector_news:
                    sector_news[sector] = []
                sector_news[sector].append(news)

        if not sector_count:
            print("❌ 未检测到明显的板块热点")
            return {}

        # 按出现次数排序
        hot_sectors = sorted(sector_count.items(), key=lambda x: x[1], reverse=True)

        print(f"\n📊 板块热度排名:")
        for i, (sector, count) in enumerate(hot_sectors[:5], 1):
            print(f"   {i}. {sector}: {count}次提及")

        # 获取每个热门板块的龙头股
        result = {}

        for sector, count in hot_sectors[:3]:  # 取前3个热门板块
            print(f"\n{'─'*60}")
            print(f"🏷️ 板块: {sector} (提及{count}次)")

            # 最新相关新闻
            latest_news = sector_news[sector][0]
            print(f"📰 最新: {latest_news['title'] or latest_news['content'][:50]}...")

            # 获取板块股票涨幅
            stocks = self.get_sector_stocks_performance(sector)

            if stocks:
                print(f"\n📈 板块内股票涨幅:")
                print(f"   {'代码':<10} {'名称':<10} {'涨幅':>8} {'成交额':>10}")
                print(f"   {'-'*45}")

                for stock in stocks:
                    flag = "🔴" if stock['change_rate'] > 5 else "🟢" if stock['change_rate'] > 0 else "⚪"
                    print(f"   {stock['code'].replace('HK.',''):<10} {stock['name'][:8]:<10} {flag}{stock['change_rate']:>+6.2f}% {stock['turnover']:>8.2f}亿")

                # 找出龙头
                leader = stocks[0] if stocks else None
                result[sector] = {
                    'mention_count': count,
                    'latest_news': latest_news,
                    'stocks': stocks,
                    'leader': leader,
                    'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

        self.close()

        # 保存历史记录
        self._save_history(result)

        return result

    def _save_history(self, result: Dict):
        """保存扫描历史"""
        history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []

        # 添加新记录
        record = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sectors': {}
        }

        for sector, data in result.items():
            record['sectors'][sector] = {
                'mention_count': data['mention_count'],
                'leader': {
                    'code': data['leader']['code'] if data['leader'] else None,
                    'name': data['leader']['name'] if data['leader'] else None,
                    'change_rate': data['leader']['change_rate'] if data['leader'] else None,
                }
            }

        history.append(record)

        # 只保留最近100条
        history = history[-100:]

        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def analyze_sector_leaders(self, sector: str, days: int = 7) -> Dict:
        """
        分析某板块历史龙头

        统计最近N天内，该板块每次暴涨时的龙头股
        """
        if not os.path.exists(self.history_file):
            print("❌ 暂无历史数据")
            return {}

        with open(self.history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)

        # 统计龙头出现次数
        leader_count = {}

        for record in history:
            if sector in record.get('sectors', {}):
                leader = record['sectors'][sector].get('leader', {})
                code = leader.get('code')
                name = leader.get('name')
                if code:
                    key = f"{code}|{name}"
                    leader_count[key] = leader_count.get(key, 0) + 1

        if not leader_count:
            print(f"❌ 板块 '{sector}' 暂无历史龙头数据")
            return {}

        # 排序
        sorted_leaders = sorted(leader_count.items(), key=lambda x: x[1], reverse=True)

        print(f"\n{'='*60}")
        print(f"📊 {sector} 板块历史龙头统计")
        print('='*60)

        for i, (key, count) in enumerate(sorted_leaders[:5], 1):
            code, name = key.split('|')
            print(f"   {i}. {code.replace('HK.','')} {name}: 领涨 {count} 次")

        return {k.split('|')[0]: v for k, v in sorted_leaders}


def print_rally_summary(result: Dict):
    """打印暴涨总结"""
    if not result:
        return

    print(f"\n{'='*60}")
    print("🏆 板块龙头总结")
    print('='*60)

    for sector, data in result.items():
        leader = data.get('leader')
        if leader:
            print(f"\n{sector}:")
            print(f"   龙头: {leader['code'].replace('HK.','')} {leader['name']}")
            print(f"   涨幅: {leader['change_rate']:+.2f}%")
            print(f"   成交: {leader['turnover']:.2f}亿")


if __name__ == "__main__":
    import sys

    os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

    tracker = SectorRallyTracker()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'scan':
            # 扫描热门板块
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 4
            result = tracker.scan_hot_sectors(hours)
            print_rally_summary(result)

        elif cmd == 'leaders':
            # 分析板块历史龙头
            if len(sys.argv) > 2:
                sector = sys.argv[2]
                tracker.analyze_sector_leaders(sector)
            else:
                print("用法: python sector_rally_tracker.py leaders <板块名>")
                print("可用板块:", list(SECTOR_KEYWORDS.keys()))

        elif cmd == 'sector':
            # 查看某板块当前涨跌
            if len(sys.argv) > 2:
                sector = sys.argv[2]
                stocks = tracker.get_sector_stocks_performance(sector)
                tracker.close()

                if stocks:
                    print(f"\n📊 {sector} 板块实时涨跌:")
                    for stock in stocks:
                        flag = "🔴" if stock['change_rate'] > 5 else "🟢" if stock['change_rate'] > 0 else "⚪"
                        print(f"   {stock['code'].replace('HK.',''):<10} {stock['name'][:8]:<10} {flag}{stock['change_rate']:>+6.2f}%")
                else:
                    print(f"❌ 未找到板块: {sector}")
            else:
                print("用法: python sector_rally_tracker.py sector <板块名>")

        else:
            print("用法:")
            print("  python sector_rally_tracker.py scan [小时]      # 扫描热门板块")
            print("  python sector_rally_tracker.py sector <板块名>  # 查看板块涨跌")
            print("  python sector_rally_tracker.py leaders <板块名> # 历史龙头统计")
    else:
        # 默认扫描
        result = tracker.scan_hot_sectors(4)
        print_rally_summary(result)
