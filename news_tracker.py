#!/usr/bin/env python3
"""
港股新闻热点追踪器
实时监控财经新闻，提前发现商业航天等热点
解决：1月22日晚发布会消息未及时获取的问题
"""
import requests
import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib

# 重点追踪的关键词（按热度排序）
HOT_KEYWORDS = {
    # 商业航天 - 最高优先级
    '航天': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045', '02865', '00031']},
    '火箭': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045', '02865']},
    '卫星': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045', '02357']},
    '太空': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045', '02865']},
    '星链': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045']},
    'SpaceX': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045', '02865']},
    '穿越者': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045']},
    '蓝箭': {'priority': 1, 'sector': '商业航天', 'stocks': ['01045']},

    # AI/机器人 - 高优先级
    '人形机器人': {'priority': 1, 'sector': 'AI机器人', 'stocks': ['01810', '02382']},
    '具身智能': {'priority': 1, 'sector': 'AI机器人', 'stocks': ['01810', '00020']},
    'DeepSeek': {'priority': 1, 'sector': 'AI', 'stocks': ['09888', '00020']},
    'ChatGPT': {'priority': 2, 'sector': 'AI', 'stocks': ['09888', '00020']},
    '大模型': {'priority': 2, 'sector': 'AI', 'stocks': ['09888', '00020', '00700']},

    # 新能源/光伏
    '光伏': {'priority': 2, 'sector': '光伏', 'stocks': ['02865', '03800', '00968']},
    '太空光伏': {'priority': 1, 'sector': '商业航天', 'stocks': ['02865']},
    '钙钛矿': {'priority': 2, 'sector': '光伏', 'stocks': ['02865']},

    # 低空经济
    '低空': {'priority': 1, 'sector': '低空经济', 'stocks': ['02357', '01810']},
    'eVTOL': {'priority': 1, 'sector': '低空经济', 'stocks': ['02357']},
    '飞行汽车': {'priority': 1, 'sector': '低空经济', 'stocks': ['02357', '01810']},
    '无人机': {'priority': 2, 'sector': '低空经济', 'stocks': ['02357']},

    # 芯片
    '芯片': {'priority': 2, 'sector': '半导体', 'stocks': ['00981', '01347']},
    '半导体': {'priority': 2, 'sector': '半导体', 'stocks': ['00981', '01347']},
    '中芯': {'priority': 2, 'sector': '半导体', 'stocks': ['00981']},

    # 新能源车
    '特斯拉': {'priority': 2, 'sector': '新能源车', 'stocks': ['01211', '02015', '09866']},
    '比亚迪': {'priority': 2, 'sector': '新能源车', 'stocks': ['01211']},
    '蔚来': {'priority': 3, 'sector': '新能源车', 'stocks': ['09866']},
    '理想': {'priority': 3, 'sector': '新能源车', 'stocks': ['02015']},

    # 消费/其他
    '黄金': {'priority': 3, 'sector': '黄金', 'stocks': ['02899', '01818']},
    '茅台': {'priority': 3, 'sector': '消费', 'stocks': []},
}

# 新闻来源配置
NEWS_SOURCES = {
    'sina_finance': {
        'name': '新浪财经',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get',
        'params': {'pageid': '153', 'num': 50, 'page': 1},
    },
    'sina_hk': {
        'name': '新浪港股',
        'url': 'https://feed.mix.sina.com.cn/api/roll/get',
        'params': {'pageid': '21', 'num': 30, 'page': 1},
    },
    'cls': {
        'name': '财联社',
        'url': 'https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6',
        'params': {},
    },
}


class NewsTracker:
    """新闻热点追踪器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        self.seen_news = set()  # 已处理的新闻ID
        self.alert_history = []  # 预警历史

    def _get_news_id(self, title: str) -> str:
        """生成新闻唯一ID"""
        return hashlib.md5(title.encode()).hexdigest()[:12]

    def fetch_sina_news(self, source_key: str = 'sina_finance') -> List[Dict]:
        """获取新浪财经新闻"""
        news_list = []
        source = NEWS_SOURCES.get(source_key, NEWS_SOURCES['sina_finance'])

        try:
            response = requests.get(
                source['url'],
                params=source['params'],
                headers=self.headers,
                timeout=15
            )
            data = response.json()

            for item in data.get('result', {}).get('data', []):
                title = item.get('title', '')
                if not title:
                    continue

                news_list.append({
                    'title': title,
                    'url': item.get('url', ''),
                    'time': item.get('ctime', ''),
                    'source': source['name'],
                    'id': self._get_news_id(title),
                })

        except Exception as e:
            print(f"获取{source['name']}新闻失败: {e}")

        return news_list

    def fetch_cls_flash(self) -> List[Dict]:
        """获取财联社电报"""
        news_list = []

        try:
            # 财联社7x24快讯
            url = "https://www.cls.cn/nodeapi/updateTelegraphList"
            params = {'app': 'CailianpressWeb', 'os': 'web', 'sv': '8.4.6'}
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()

            for item in data.get('data', {}).get('roll_data', []):
                title = item.get('title', '') or item.get('content', '')[:50]
                if not title:
                    continue

                # 解析时间
                ctime = item.get('ctime', 0)
                time_str = datetime.fromtimestamp(ctime).strftime('%H:%M') if ctime else ''

                news_list.append({
                    'title': title,
                    'content': item.get('content', ''),
                    'url': f"https://www.cls.cn/detail/{item.get('id', '')}",
                    'time': time_str,
                    'source': '财联社',
                    'id': self._get_news_id(title),
                })

        except Exception as e:
            print(f"获取财联社快讯失败: {e}")

        return news_list

    def fetch_weibo_hot(self) -> List[Dict]:
        """获取微博财经热搜"""
        news_list = []

        try:
            url = "https://m.weibo.cn/api/container/getIndex"
            params = {"containerid": "106003type=25&t=3&disable_hot=1&filter_type=realtimehot"}
            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()

            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                for item in card.get("card_group", []):
                    word = item.get("desc", "")
                    if word and self._is_finance_related(word):
                        news_list.append({
                            'title': word,
                            'url': item.get('scheme', ''),
                            'time': datetime.now().strftime('%H:%M'),
                            'source': '微博热搜',
                            'hot_score': item.get('desc_extr', 0),
                            'id': self._get_news_id(word),
                        })

        except Exception as e:
            print(f"获取微博热搜失败: {e}")

        return news_list

    def _is_finance_related(self, text: str) -> bool:
        """判断是否与财经/股市相关"""
        finance_words = [
            '股', '基金', 'ETF', '涨停', '跌停', '大盘', 'A股', '港股',
            '航天', '火箭', '卫星', '太空', 'AI', '芯片', '半导体',
            '新能源', '光伏', '电池', '机器人', '华为', '特斯拉',
            '茅台', '比亚迪', '腾讯', '阿里', '小米',
        ]
        return any(w in text for w in finance_words)

    def analyze_news(self, news: Dict) -> Optional[Dict]:
        """
        分析单条新闻，返回匹配的热点信息
        """
        title = news.get('title', '') + news.get('content', '')

        matched = []
        max_priority = 999

        for keyword, info in HOT_KEYWORDS.items():
            if keyword in title:
                matched.append({
                    'keyword': keyword,
                    'sector': info['sector'],
                    'stocks': info['stocks'],
                    'priority': info['priority'],
                })
                max_priority = min(max_priority, info['priority'])

        if not matched:
            return None

        # 合并相关股票
        all_stocks = []
        sectors = set()
        keywords = []
        for m in matched:
            all_stocks.extend(m['stocks'])
            sectors.add(m['sector'])
            keywords.append(m['keyword'])

        # 去重
        all_stocks = list(dict.fromkeys(all_stocks))

        return {
            'news': news,
            'keywords': keywords,
            'sectors': list(sectors),
            'stocks': all_stocks,
            'priority': max_priority,
            'alert_level': 'HIGH' if max_priority == 1 else ('MEDIUM' if max_priority == 2 else 'LOW'),
        }

    def scan_all_sources(self) -> List[Dict]:
        """扫描所有新闻源，返回热点预警"""
        all_news = []

        # 新浪财经
        all_news.extend(self.fetch_sina_news('sina_finance'))

        # 新浪港股
        all_news.extend(self.fetch_sina_news('sina_hk'))

        # 财联社
        all_news.extend(self.fetch_cls_flash())

        # 微博热搜
        all_news.extend(self.fetch_weibo_hot())

        # 分析每条新闻
        alerts = []
        for news in all_news:
            # 跳过已处理的
            if news['id'] in self.seen_news:
                continue

            result = self.analyze_news(news)
            if result:
                alerts.append(result)
                self.seen_news.add(news['id'])

        # 按优先级排序
        alerts.sort(key=lambda x: x['priority'])

        return alerts

    def get_high_priority_alerts(self) -> List[Dict]:
        """只获取高优先级预警"""
        all_alerts = self.scan_all_sources()
        return [a for a in all_alerts if a['priority'] <= 2]


def print_news_scan():
    """打印新闻扫描报告"""
    tracker = NewsTracker()

    print("=" * 70)
    print(f"📰 港股新闻热点扫描 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    alerts = tracker.scan_all_sources()

    if not alerts:
        print("\n✅ 暂无重要财经热点")
        print("=" * 70)
        return

    # 高优先级
    high = [a for a in alerts if a['alert_level'] == 'HIGH']
    if high:
        print(f"\n🔴 【高优先级预警】({len(high)}条)")
        print("-" * 70)
        for a in high[:5]:
            news = a['news']
            print(f"⚠️ {news['title'][:45]}")
            print(f"   来源: {news['source']} | 时间: {news['time']}")
            print(f"   关键词: {', '.join(a['keywords'][:3])}")
            print(f"   相关板块: {', '.join(a['sectors'])}")
            print(f"   关注股票: {', '.join(a['stocks'][:4])}")
            print()

    # 中优先级
    medium = [a for a in alerts if a['alert_level'] == 'MEDIUM']
    if medium:
        print(f"\n🟡 【中优先级预警】({len(medium)}条)")
        print("-" * 70)
        for a in medium[:5]:
            news = a['news']
            print(f"📌 {news['title'][:50]}")
            print(f"   板块: {', '.join(a['sectors'])} | 股票: {', '.join(a['stocks'][:3])}")

    # 低优先级简要展示
    low = [a for a in alerts if a['alert_level'] == 'LOW']
    if low:
        print(f"\n🟢 【其他热点】({len(low)}条)")
        for a in low[:3]:
            print(f"   • {a['news']['title'][:40]}")

    print("\n" + "=" * 70)


def quick_news_alert() -> List[Dict]:
    """快速新闻预警（只看高优先级）"""
    tracker = NewsTracker()
    alerts = tracker.get_high_priority_alerts()

    if alerts:
        print(f"\n🔔 新闻热点预警 ({datetime.now().strftime('%H:%M')})")
        print("-" * 55)
        for a in alerts[:5]:
            news = a['news']
            level = "🔴" if a['alert_level'] == 'HIGH' else "🟡"
            print(f"{level} {news['title'][:40]}")
            print(f"   → {', '.join(a['sectors'])} | 关注: {', '.join(a['stocks'][:3])}")
    else:
        print(f"✅ [{datetime.now().strftime('%H:%M')}] 暂无重要新闻热点")

    return alerts


def news_monitor(interval: int = 120):
    """
    持续监控新闻热点
    interval: 扫描间隔(秒)，默认2分钟
    """
    tracker = NewsTracker()

    print("=" * 65)
    print(f"📰 新闻热点监控启动")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🔄 扫描间隔: {interval}秒")
    print(f"🎯 重点追踪: 商业航天/AI机器人/低空经济/光伏")
    print("=" * 65)

    while True:
        try:
            alerts = tracker.get_high_priority_alerts()

            if alerts:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n{'='*55}")
                print(f"🔔 [{now}] 发现新闻热点!")
                print(f"{'='*55}")

                for a in alerts[:3]:
                    news = a['news']
                    level = "🔴" if a['alert_level'] == 'HIGH' else "🟡"
                    print(f"{level} {news['title'][:45]}")
                    print(f"   板块: {', '.join(a['sectors'])} | 股票: {', '.join(a['stocks'][:4])}")
                    print(f"   来源: {news['source']} | {news['time']}")
                    print()
            else:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"[{now}] 监控中... 暂无新热点", end='\r')

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n监控已停止")
            break
        except Exception as e:
            print(f"\n扫描异常: {e}")
            time.sleep(30)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "monitor":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 120
            news_monitor(interval)
        elif cmd == "alert":
            quick_news_alert()
        else:
            print("用法:")
            print("  python news_tracker.py          - 完整新闻扫描")
            print("  python news_tracker.py alert    - 快速预警")
            print("  python news_tracker.py monitor  - 持续监控")
            print("  python news_tracker.py monitor 60 - 自定义间隔(秒)")
    else:
        print_news_scan()
