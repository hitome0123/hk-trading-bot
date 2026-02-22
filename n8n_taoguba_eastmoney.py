#!/usr/bin/env python3
"""
淘股吧 + 东财股吧 专用采集器
解决HTML解析问题
"""
import json
import sys
import os
import re
from typing import List, Dict

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


def get_taoguba_hot() -> List[Dict]:
    """淘股吧热门股票"""
    hot_list = []
    if not REQUESTS_AVAILABLE:
        return hot_list

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.taoguba.com.cn/",
        }

        # 方法1: 实时热榜
        url = "https://www.taoguba.com.cn/quotes/realTime"
        response = requests.get(url, headers=headers, timeout=8)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试多种选择器
            selectors = [
                '.stock-item',
                '.realtime-item',
                'div[class*="stock"]',
                'tr[class*="stock"]',
                'a[href*="/stock/"]',
            ]

            for selector in selectors:
                items = soup.select(selector)
                if items:
                    for item in items[:20]:
                        # 提取股票名称
                        name = None
                        for tag in item.select('a, span, td'):
                            text = tag.text.strip()
                            if text and len(text) < 20 and re.search(r'[\u4e00-\u9fa5]', text):
                                name = text
                                break

                        if name:
                            hot_list.append({
                                "keyword": name,
                                "source": "淘股吧",
                                "hot_score": 100,
                            })
                    break

        # 方法2: 使用API（如果有）
        if not hot_list:
            api_url = "https://www.taoguba.com.cn/api/path/to/hotstock"
            try:
                response = requests.get(api_url, headers=headers, timeout=5)
                data = response.json()
                # 根据实际API结构解析
            except:
                pass

    except Exception as e:
        pass

    return hot_list


def get_eastmoney_guba_hot() -> List[Dict]:
    """东方财富股吧热帖"""
    hot_list = []
    if not REQUESTS_AVAILABLE:
        return hot_list

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://guba.eastmoney.com/",
        }

        # 东财股吧人气榜
        url = "https://guba.eastmoney.com/rank/"
        response = requests.get(url, headers=headers, timeout=8)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            # 尝试多种选择器
            selectors = [
                '.articleitem .title',
                'span.title',
                'a.title',
                'div.title',
                '.topic-title',
                'tbody tr td a',
            ]

            for selector in selectors:
                items = soup.select(selector)
                if items:
                    for item in items[:20]:
                        title = item.text.strip()
                        if title and len(title) > 5:
                            hot_list.append({
                                "keyword": title,
                                "source": "东财股吧",
                                "hot_score": 80,
                            })
                    break

        # 备用: 东财人气股票榜（使用akshare）
        if not hot_list:
            try:
                import akshare as ak
                df = ak.stock_hot_rank_em()
                if df is not None and len(df) > 0:
                    for _, row in df.head(20).iterrows():
                        name = row.get("股票名称", row.get("名称", ""))
                        if name:
                            hot_list.append({
                                "keyword": name,
                                "code": row.get("代码", ""),
                                "rank": int(row.get("当前排名", 0)),
                                "source": "东财人气榜",
                                "hot_score": 100 - int(row.get("当前排名", 0)),
                            })
            except:
                pass

    except Exception as e:
        pass

    return hot_list


def get_eastmoney_api_hot() -> List[Dict]:
    """东方财富API - 人气榜"""
    hot_list = []
    if not REQUESTS_AVAILABLE:
        return hot_list

    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://quote.eastmoney.com/",
        }

        # 东财人气榜API
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "20",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 沪深A股
            "fields": "f12,f14,f2,f3,f62",
        }

        response = requests.get(url, params=params, headers=headers, timeout=8)
        data = response.json()

        diff = data.get("data", {}).get("diff", [])
        for item in diff:
            hot_list.append({
                "keyword": item.get("f14", ""),  # 股票名称
                "code": item.get("f12", ""),     # 股票代码
                "price": item.get("f2", 0),      # 最新价
                "change_pct": item.get("f3", 0), # 涨跌幅
                "hot_score": item.get("f62", 0), # 人气
                "source": "东财API",
            })

    except Exception as e:
        pass

    return hot_list


def main():
    if not REQUESTS_AVAILABLE:
        _output_json({"error": "requests not installed", "data": {}})
        return

    try:
        taoguba = get_taoguba_hot()
        eastmoney_guba = get_eastmoney_guba_hot()
        eastmoney_api = get_eastmoney_api_hot()

        output = {
            "taoguba": taoguba,
            "eastmoney_guba": eastmoney_guba,
            "eastmoney_api": eastmoney_api,
            "total": len(taoguba) + len(eastmoney_guba) + len(eastmoney_api),
        }

        _output_json(output)

    except Exception as e:
        _output_json({"error": str(e), "data": {}})


if __name__ == "__main__":
    main()
