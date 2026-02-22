#!/usr/bin/env python3
"""
港股热度加速检测系统
专注发现：热度正在上涨中的股票/板块（不是已经最热的）

核心指标：K值（流量爆发系数）
K = (当前热度 - 过去平均热度) / 过去平均热度

K值越高 = 热度上涨越快
推荐策略：
- K > 1.0: 🚀 爆发中（强烈关注）
- 0.3 < K < 1.0: 📈 加速中（提前布局）
- K < 0.3: 平稳或下降（不推荐）
"""
import json
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

# Suppress stdout
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, KLType, RET_OK
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


def _output_json(data):
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# ==================== 热度数据库（SQLite） ====================
class HeatDatabase:
    """热度历史数据库"""

    def __init__(self, db_path="/Users/mantou/hk-trading-bot/heat_history.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        if not SQLITE_AVAILABLE:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建热度历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                source TEXT NOT NULL,
                hot_score REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                UNIQUE(keyword, source, timestamp)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_keyword_time
            ON heat_history(keyword, timestamp DESC)
        """)

        conn.commit()
        conn.close()

    def save_heat_data(self, items: List[Dict]) -> int:
        """保存热度数据"""
        if not SQLITE_AVAILABLE or not items:
            return 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = 0

        for item in items:
            keyword = item.get("keyword", "")
            source = item.get("source", "unknown")
            hot_score = float(item.get("hot_score", 0))

            if not keyword or hot_score == 0:
                continue

            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO heat_history (keyword, source, hot_score, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (keyword, source, hot_score, now))
                saved += cursor.rowcount
            except:
                pass

        conn.commit()
        conn.close()

        return saved

    def calc_k_value(self, keyword: str, source: str = "all", hours: int = 3) -> float:
        """
        计算K值（流量爆发系数）

        K = (当前热度 - 过去N小时平均热度) / 过去N小时平均热度

        返回:
            K > 1.0: 爆发中
            0.3 < K < 1.0: 加速上升
            K < 0.3: 平稳或下降
        """
        if not SQLITE_AVAILABLE:
            return 0.0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 当前热度（最新一条）
        if source == "all":
            cursor.execute("""
                SELECT hot_score FROM heat_history
                WHERE keyword = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (keyword,))
        else:
            cursor.execute("""
                SELECT hot_score FROM heat_history
                WHERE keyword = ? AND source = ?
                ORDER BY timestamp DESC LIMIT 1
            """, (keyword, source))

        current_row = cursor.fetchone()
        if not current_row:
            conn.close()
            return 0.0

        current_heat = current_row[0]

        # 过去N小时平均热度
        time_threshold = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        if source == "all":
            cursor.execute("""
                SELECT AVG(hot_score) FROM heat_history
                WHERE keyword = ? AND timestamp >= ? AND timestamp < (
                    SELECT timestamp FROM heat_history
                    WHERE keyword = ?
                    ORDER BY timestamp DESC LIMIT 1
                )
            """, (keyword, time_threshold, keyword))
        else:
            cursor.execute("""
                SELECT AVG(hot_score) FROM heat_history
                WHERE keyword = ? AND source = ? AND timestamp >= ?
            """, (keyword, source, time_threshold))

        avg_row = cursor.fetchone()
        conn.close()

        if not avg_row or not avg_row[0] or avg_row[0] == 0:
            return 0.0  # 新词，没有历史数据

        avg_heat = avg_row[0]

        # 计算K值
        k_value = (current_heat - avg_heat) / avg_heat

        return round(k_value, 2)

    def get_accelerating_keywords(self, min_k: float = 0.3) -> List[Dict]:
        """获取加速上升的关键词"""
        if not SQLITE_AVAILABLE:
            return []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 获取最近的关键词
        cursor.execute("""
            SELECT DISTINCT keyword, source FROM heat_history
            WHERE timestamp >= datetime('now', '-6 hours')
        """)

        results = []
        for row in cursor.fetchall():
            keyword, source = row
            k_value = self.calc_k_value(keyword, source)

            if k_value >= min_k:
                results.append({
                    "keyword": keyword,
                    "source": source,
                    "k_value": k_value,
                    "status": "爆发中🚀" if k_value > 1.0 else "加速中📈",
                })

        conn.close()

        # 按K值排序
        results.sort(key=lambda x: x["k_value"], reverse=True)

        return results


# ==================== 社交媒体采集（简化版） ====================
def collect_social_media() -> List[Dict]:
    """采集社交媒体数据"""
    all_data = []

    if not REQUESTS_AVAILABLE:
        return all_data

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    # 1. 抖音热榜
    try:
        url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        for item in data.get("data", [])[:30]:
            all_data.append({
                "keyword": item.get("Title", ""),
                "hot_score": item.get("HotValue", 0),
                "source": "抖音",
            })
    except:
        pass

    # 2. 微博热搜
    try:
        url = "https://weibo.com/ajax/side/hotSearch"
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()

        for item in data.get("data", {}).get("realtime", [])[:30]:
            all_data.append({
                "keyword": item.get("word", "") or item.get("note", ""),
                "hot_score": item.get("raw_hot", 0) or item.get("num", 0),
                "source": "微博",
            })
    except:
        pass

    # 3. 东财人气榜API
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": "1",
            "pz": "30",
            "po": "1",
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f62",  # 按人气排序
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            "fields": "f12,f14,f2,f3,f62",
        }
        response = requests.get(url, params=params, headers=headers, timeout=5)
        data = response.json()

        for item in data.get("data", {}).get("diff", []):
            all_data.append({
                "keyword": item.get("f14", ""),  # 股票名称
                "code": item.get("f12", ""),
                "hot_score": item.get("f62", 0),  # 人气值
                "change_pct": item.get("f3", 0),
                "source": "东财人气",
            })
    except:
        pass

    return [item for item in all_data if item.get("keyword")]


# ==================== 主函数 ====================
def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "stocks": []})
        return

    db = HeatDatabase()
    ctx = None

    try:
        # ===== 步骤1: 采集当前社交媒体数据 =====
        social_data = collect_social_media()

        # ===== 步骤2: 保存到数据库 =====
        saved_count = db.save_heat_data(social_data)

        # ===== 步骤3: 计算所有关键词的K值 =====
        keywords_with_k = []
        for item in social_data:
            keyword = item.get("keyword", "")
            source = item.get("source", "")
            if keyword:
                k_value = db.calc_k_value(keyword, source, hours=3)
                keywords_with_k.append({
                    **item,
                    "k_value": k_value,
                    "status": (
                        "🚀 爆发中" if k_value > 1.0 else
                        ("📈 加速中" if k_value > 0.3 else
                        ("➡️ 平稳" if k_value >= 0 else "📉 下降"))
                    ),
                })

        # ===== 步骤4: 获取加速上升的关键词 =====
        accelerating = db.get_accelerating_keywords(min_k=0.3)

        # ===== 步骤5: 筛选财经相关+加速中的关键词 =====
        finance_keywords = [
            "股", "A股", "港股", "基金", "涨停", "板块", "半导体", "芯片",
            "新能源", "光伏", "AI", "人工智能", "机器人", "航天", "卫星",
            "特斯拉", "比亚迪", "腾讯", "阿里", "百度", "小米", "华为",
        ]

        accelerating_finance = [
            kw for kw in accelerating
            if any(fk in kw["keyword"] for fk in finance_keywords)
        ]

        # ===== 步骤6: 连接Futu，分析相关股票 =====
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 这里可以根据加速关键词，查找相关港股
        # （简化版，实际需要关键词→股票映射）

        # ===== 输出 =====
        output = {
            "accelerating_keywords": accelerating_finance[:15],  # 加速中的财经关键词
            "all_keywords_with_k": sorted(
                keywords_with_k,
                key=lambda x: x.get("k_value", 0),
                reverse=True
            )[:30],
            "statistics": {
                "total_keywords": len(social_data),
                "saved_to_db": saved_count,
                "accelerating_count": len(accelerating),
                "accelerating_finance_count": len(accelerating_finance),
            },
            "recommendation": {
                "focus_on": [kw["keyword"] for kw in accelerating_finance[:5]],
                "avoid": [kw["keyword"] for kw in keywords_with_k if kw.get("k_value", 0) < -0.5][:5],
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "Heat Acceleration Detector v1.0",
        }

        _output_json(output)

    except Exception as e:
        _output_json({
            "error": str(e),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    finally:
        if ctx:
            ctx.close()


if __name__ == "__main__":
    main()
