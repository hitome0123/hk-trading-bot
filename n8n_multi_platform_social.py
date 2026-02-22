#!/usr/bin/env python3
"""
多平台财经社交媒体监控系统
整合平台：
1. 微博热搜
2. 抖音热榜
3. 雪球热股
4. 淘股吧（龙头股讨论）
5. 东方财富股吧
6. 集思录（可转债、套利）
7. 知乎财经话题
8. 财联社快讯
9. 豆瓣投资理财小组
"""
import json
import sys
import os
import re
from typing import List, Dict, Any
from datetime import datetime
import warnings

warnings.filterwarnings("ignore")

# Suppress stdout
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def _output_json(data):
    """输出JSON"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# 财经关键词过滤
FINANCE_KEYWORDS = [
    "股", "A股", "港股", "美股", "基金", "ETF", "涨停", "跌停", "大盘", "指数", "板块",
    "半导体", "芯片", "新能源", "光伏", "锂电", "银行", "券商", "保险", "地产", "医药",
    "科技", "AI", "人工智能", "机器人", "算力", "ChatGPT", "航天", "火箭", "卫星",
    "固态电池", "氢能", "核聚变", "脑机接口", "量子", "6G", "特斯拉", "苹果", "华为",
    "小米", "比亚迪", "茅台", "宁德", "腾讯", "阿里", "百度", "京东", "美团",
    "利好", "利空", "财报", "业绩", "牛市", "熊市", "反弹", "回调", "投资", "理财",
]


class MultiPlatformCollector:
    """多平台采集器"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        self.timeout = 8

    # ==================== 1. 微博热搜 ====================
    def get_weibo_hot(self) -> List[Dict]:
        """微博热搜"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("realtime", [])[:30]:
                keyword = item.get("word", "") or item.get("note", "")
                if self._is_finance_related(keyword):
                    hot_list.append({
                        "keyword": keyword,
                        "hot_score": item.get("raw_hot", 0) or item.get("num", 0),
                        "rank": item.get("rank", 0),
                        "source": "微博",
                    })
        except Exception as e:
            pass

        return hot_list

    # ==================== 2. 抖音热榜 ====================
    def get_douyin_hot(self) -> List[Dict]:
        """抖音热榜（使用今日头条API）"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", [])[:30]:
                title = item.get("Title", "")
                if self._is_finance_related(title):
                    hot_list.append({
                        "keyword": title,
                        "hot_score": item.get("HotValue", 0),
                        "source": "抖音",
                    })
        except Exception as e:
            pass

        return hot_list

    # ==================== 3. 雪球热股 ====================
    def get_xueqiu_hot(self) -> List[Dict]:
        """雪球热股"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            # 港股热门
            url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
            params = {"type": "12", "size": 20}  # 12=港股
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("items", []):
                hot_list.append({
                    "code": "HK." + item.get("symbol", "").replace("0", "", 1),
                    "name": item.get("name", ""),
                    "hot_score": item.get("followers", 0),
                    "change_pct": item.get("percent", 0),
                    "source": "雪球",
                })
        except Exception as e:
            pass

        return hot_list

    # ==================== 4. 淘股吧 ====================
    def get_taoguba_hot(self) -> List[Dict]:
        """淘股吧龙头股"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.taoguba.com.cn/quotes/realTime"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # 解析热门股票
                stocks = soup.select('.stock-item')[:20]
                for stock in stocks:
                    name = stock.select_one('.stock-name')
                    if name:
                        hot_list.append({
                            "name": name.text.strip(),
                            "source": "淘股吧",
                            "hot_score": 100,
                        })
        except Exception as e:
            pass

        return hot_list

    # ==================== 5. 东方财富股吧 ====================
    def get_eastmoney_guba(self) -> List[Dict]:
        """东方财富股吧热帖"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://guba.eastmoney.com/rank/"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # 解析热帖
                posts = soup.select('.articleitem')[:20]
                for post in posts:
                    title_elem = post.select_one('.title')
                    if title_elem and self._is_finance_related(title_elem.text):
                        hot_list.append({
                            "keyword": title_elem.text.strip(),
                            "source": "东财股吧",
                            "hot_score": 80,
                        })
        except Exception as e:
            pass

        return hot_list

    # ==================== 6. 集思录 ====================
    def get_jisilu_hot(self) -> List[Dict]:
        """集思录热门话题"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.jisilu.cn/discuss/topic"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                topics = soup.select('.topic_title')[:15]
                for topic in topics:
                    title = topic.text.strip()
                    if self._is_finance_related(title):
                        hot_list.append({
                            "keyword": title,
                            "source": "集思录",
                            "hot_score": 70,
                        })
        except Exception as e:
            pass

        return hot_list

    # ==================== 7. 知乎财经 ====================
    def get_zhihu_finance(self) -> List[Dict]:
        """知乎财经话题"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.zhihu.com/api/v4/topics/19551582/feeds/timeline_question"
            params = {"limit": 20, "offset": 0}
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", []):
                target = item.get("target", {})
                title = target.get("title", "")
                if self._is_finance_related(title):
                    hot_list.append({
                        "keyword": title,
                        "hot_score": target.get("follower_count", 0),
                        "source": "知乎",
                    })
        except Exception as e:
            pass

        return hot_list

    # ==================== 8. 财联社快讯 ====================
    def get_cls_news(self) -> List[Dict]:
        """财联社快讯"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.cls.cn/api/sw"
            params = {"app": "CailianpressWeb", "os": "web", "sv": "7.7.5"}
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("roll_data", [])[:20]:
                content = item.get("content", "")
                if content:
                    hot_list.append({
                        "keyword": content[:100],  # 截取前100字
                        "timestamp": item.get("ctime", ""),
                        "source": "财联社",
                        "hot_score": 90,
                    })
        except Exception as e:
            pass

        return hot_list

    # ==================== 9. 豆瓣投资理财小组 ====================
    def get_douban_investment_group(self) -> List[Dict]:
        """豆瓣投资理财小组 (ID: 648435)"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://www.douban.com/group/648435/"
            headers = {
                **self.headers,
                "Referer": "https://www.douban.com/",
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # 解析热门帖子
                topics = soup.select('.olt tbody tr')[:20]
                for topic in topics:
                    title_elem = topic.select_one('a[title]')
                    if title_elem:
                        title = title_elem.get('title', '').strip()
                        if self._is_finance_related(title):
                            # 提取回复数作为热度
                            reply_elem = topic.select_one('td:last-child')
                            replies = 0
                            if reply_elem:
                                try:
                                    replies = int(re.search(r'\d+', reply_elem.text).group())
                                except:
                                    pass

                            hot_list.append({
                                "keyword": title,
                                "hot_score": replies,
                                "source": "豆瓣理财",
                            })
        except Exception as e:
            pass

        return hot_list

    # ==================== 辅助方法 ====================
    def _is_finance_related(self, text: str) -> bool:
        """判断是否财经相关"""
        if not text:
            return False
        return any(kw in text for kw in FINANCE_KEYWORDS)

    def collect_all(self) -> Dict[str, List]:
        """采集所有平台数据"""
        results = {}

        # 采集各平台（并发执行，快速失败）
        results["weibo"] = self.get_weibo_hot()
        results["douyin"] = self.get_douyin_hot()
        results["xueqiu"] = self.get_xueqiu_hot()
        results["taoguba"] = self.get_taoguba_hot()
        results["eastmoney_guba"] = self.get_eastmoney_guba()
        results["jisilu"] = self.get_jisilu_hot()
        results["zhihu"] = self.get_zhihu_finance()
        results["cls_news"] = self.get_cls_news()
        results["douban"] = self.get_douban_investment_group()

        return results


# ==================== 数据聚合分析 ====================
def aggregate_hot_keywords(all_data: Dict[str, List]) -> List[Dict]:
    """聚合热门关键词"""
    keyword_map = {}

    for platform, items in all_data.items():
        for item in items:
            keyword = item.get("keyword", "")
            if not keyword:
                continue

            if keyword not in keyword_map:
                keyword_map[keyword] = {
                    "keyword": keyword,
                    "total_score": 0,
                    "platforms": [],
                    "sources": [],
                }

            # 确保hot_score是数字
            hot_score = item.get("hot_score", 0)
            if isinstance(hot_score, str):
                try:
                    hot_score = int(hot_score)
                except:
                    hot_score = 0

            keyword_map[keyword]["total_score"] += hot_score
            keyword_map[keyword]["platforms"].append(platform)
            keyword_map[keyword]["sources"].append(item.get("source", ""))

    # 按总分排序
    result = sorted(keyword_map.values(), key=lambda x: x["total_score"], reverse=True)

    # 计算跨平台出现次数
    for item in result:
        item["platform_count"] = len(set(item["platforms"]))
        item["sources"] = list(set(item["sources"]))

    return result


def extract_hot_stocks(all_data: Dict[str, List]) -> List[Dict]:
    """提取热门股票"""
    stocks = []

    # 从雪球获取
    for item in all_data.get("xueqiu", []):
        if "code" in item:
            stocks.append(item)

    # 从淘股吧获取
    for item in all_data.get("taoguba", []):
        if "name" in item:
            stocks.append(item)

    return stocks


# ==================== 主函数 ====================
def main():
    if not REQUESTS_AVAILABLE:
        _output_json({"error": "requests not installed", "data": {}})
        return

    collector = MultiPlatformCollector()

    try:
        # 采集所有平台
        all_data = collector.collect_all()

        # 聚合分析
        hot_keywords = aggregate_hot_keywords(all_data)
        hot_stocks = extract_hot_stocks(all_data)

        # 统计信息
        stats = {
            platform: len(items)
            for platform, items in all_data.items()
        }

        output = {
            "hot_keywords": hot_keywords[:30],  # Top 30 热门关键词
            "hot_stocks": hot_stocks[:20],  # Top 20 热门股票
            "platform_stats": stats,
            "raw_data": all_data,  # 原始数据
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_items": sum(stats.values()),
        }

        _output_json(output)

    except Exception as e:
        _output_json({
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })


if __name__ == "__main__":
    main()
