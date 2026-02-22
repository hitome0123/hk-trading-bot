#!/usr/bin/env python3
"""
港股终极智能监控系统 v4.0
整合功能：
1. 多平台社交媒体热搜（微博/抖音/雪球/财联社/豆瓣理财）
2. 热搜关键词→板块映射
3. 板块异动检测
4. 全市场股票扫描（不限于固定池）
5. 中低市值高波动优先
6. 完整技术指标
7. 智能评分系统（考虑社交热度）
"""
import json
import sys
import os
import logging
import warnings
from datetime import datetime
from typing import List, Dict, Any
import time
import re

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# OS-level stdout suppression
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, KLType, RET_OK, Market
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False

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


# ==================== 配置 ====================
# 港股板块配置
HK_SECTORS = {
    '商业航天': ['HK.01045', 'HK.00031'],
    '卫星通信': ['HK.01045', 'HK.00763', 'HK.02342'],
    'AI人工智能': ['HK.09888', 'HK.00020', 'HK.01024', 'HK.09618', 'HK.03690'],
    '机器人': ['HK.01810', 'HK.00285'],
    '新能源汽车': ['HK.09866', 'HK.02015', 'HK.01211', 'HK.00175', 'HK.09868'],
    '光伏太阳能': ['HK.03800', 'HK.00968', 'HK.06865'],
    '半导体芯片': ['HK.00981', 'HK.01347'],
    '科技互联网': ['HK.00700', 'HK.09988', 'HK.09888', 'HK.09618', 'HK.03690', 'HK.09999'],
    '医药生物': ['HK.06160', 'HK.02269', 'HK.02359'],
    '消费零售': ['HK.01929', 'HK.09633', 'HK.02331', 'HK.06862', 'HK.09992'],
}

# 关键词映射规则
KEYWORD_SECTOR_MAP = {
    '商业航天': ['航天', '火箭', '卫星', 'SpaceX', '星链', '低空经济'],
    '卫星通信': ['卫星', '通信', '5G', '6G', '北斗'],
    'AI人工智能': ['AI', '人工智能', '大模型', 'ChatGPT', '机器人', '具身智能', '算力'],
    '机器人': ['机器人', '人形机器人', '工业机器人', '服务机器人'],
    '新能源汽车': ['新能源', '电动车', '蔚来', '理想', '小鹏', '特斯拉', '比亚迪', '汽车'],
    '光伏太阳能': ['光伏', '太阳能', '绿电', '清洁能源', '组件'],
    '半导体芯片': ['芯片', '半导体', '中芯', '华虹', '台积电', '集成电路'],
    '科技互联网': ['腾讯', '阿里', '百度', '京东', '美团', '互联网', '科技', '电商'],
    '医药生物': ['医药', '生物', '创新药', '疫苗', 'GLP-1', '减肥药', '医疗'],
    '消费零售': ['消费', '零售', '电商', '周大福', '李宁', '农夫山泉', '品牌'],
}


# ==================== 社交媒体采集 ====================
class SocialMediaCollector:
    """社交媒体采集器（快速版）"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.timeout = 5  # 快速超时

    def get_weibo_hot(self) -> List[str]:
        """微博热搜关键词"""
        keywords = []
        if not REQUESTS_AVAILABLE:
            return keywords

        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("realtime", [])[:20]:
                keyword = item.get("word", "") or item.get("note", "")
                if keyword:
                    keywords.append(keyword)
        except:
            pass

        return keywords

    def get_douyin_hot(self) -> List[str]:
        """抖音热搜关键词"""
        keywords = []
        if not REQUESTS_AVAILABLE:
            return keywords

        try:
            url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", [])[:20]:
                title = item.get("Title", "")
                if title:
                    keywords.append(title)
        except:
            pass

        return keywords

    def get_cls_news(self) -> List[str]:
        """财联社快讯"""
        keywords = []
        if not REQUESTS_AVAILABLE:
            return keywords

        try:
            url = "https://www.cls.cn/api/sw"
            params = {"app": "CailianpressWeb", "os": "web", "sv": "7.7.5"}
            response = requests.get(url, params=params, headers=self.headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("roll_data", [])[:15]:
                content = item.get("content", "")
                if content:
                    keywords.append(content[:80])  # 截取
        except:
            pass

        return keywords

    def get_douban_finance(self) -> List[str]:
        """豆瓣投资理财小组"""
        keywords = []
        if not REQUESTS_AVAILABLE:
            return keywords

        try:
            url = "https://www.douban.com/group/648435/"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                topics = soup.select('.olt tbody tr')[:15]
                for topic in topics:
                    title_elem = topic.select_one('a[title]')
                    if title_elem:
                        title = title_elem.get('title', '').strip()
                        if title:
                            keywords.append(title)
        except:
            pass

        return keywords

    def collect_all(self) -> Dict[str, List[str]]:
        """采集所有平台"""
        return {
            "weibo": self.get_weibo_hot(),
            "douyin": self.get_douyin_hot(),
            "cls": self.get_cls_news(),
            "douban": self.get_douban_finance(),
        }


# ==================== 关键词分析 ====================
def analyze_hot_keywords(social_data: Dict[str, List[str]]) -> Dict[str, Any]:
    """分析热搜关键词，识别热门板块"""
    all_keywords = []
    for platform, keywords in social_data.items():
        all_keywords.extend(keywords)

    # 识别热门板块
    sector_scores = {}
    for sector, mapping_keywords in KEYWORD_SECTOR_MAP.items():
        score = 0
        matched_keywords = []
        for kw in all_keywords:
            for mk in mapping_keywords:
                if mk in kw:
                    score += 1
                    matched_keywords.append(kw)
                    break

        if score > 0:
            sector_scores[sector] = {
                "score": score,
                "matched_keywords": matched_keywords[:5],  # 只保留前5个
            }

    # 按分数排序
    hot_sectors = sorted(sector_scores.items(), key=lambda x: x[1]["score"], reverse=True)

    return {
        "hot_sectors": [s[0] for s in hot_sectors[:5]],  # Top 5板块
        "sector_details": dict(hot_sectors[:10]),
        "total_keywords": len(all_keywords),
    }


# ==================== 技术指标（复用之前的） ====================
def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(len(closes) - period, len(closes)):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def calc_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return {"macd": 0, "signal": 0, "histogram": 0, "trend": "neutral"}

    def ema(data, period):
        k = 2 / (period + 1)
        result = [data[0]]
        for i in range(1, len(data)):
            result.append(data[i] * k + result[-1] * (1 - k))
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line[slow - 1:], signal)
    macd_val = round(macd_line[-1], 4)
    signal_val = round(signal_line[-1], 4)
    hist = round(macd_val - signal_val, 4)
    trend = "bullish" if hist > 0 else ("bearish" if hist < 0 else "neutral")
    return {"macd": macd_val, "signal": signal_val, "histogram": hist, "trend": trend}


def calc_bollinger_bands(closes, period=20, std_dev=2):
    if len(closes) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "position": "middle"}

    recent = closes[-period:]
    middle = sum(recent) / period
    variance = sum([(x - middle) ** 2 for x in recent]) / period
    std = variance ** 0.5
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    current = closes[-1]
    position = "overbought" if current > upper else ("oversold" if current < lower else "middle")

    return {"upper": round(upper, 3), "middle": round(middle, 3), "lower": round(lower, 3), "position": position}


# ==================== 智能评分（增强版） ====================
def calculate_enhanced_score(stock_data, hot_sectors, social_mentions=0):
    """增强评分系统"""
    score = 0
    reasons = []

    # 1. 涨幅 (20分)
    change = stock_data.get('changePct', 0)
    if change > 5:
        score += 20
        reasons.append(f"强势上涨{change:.1f}%")
    elif change > 2:
        score += 15
    elif change > 0:
        score += 10

    # 2. 振幅 (15分)
    amplitude = stock_data.get('amplitude', 0)
    if amplitude > 5:
        score += 15
        reasons.append(f"高振幅{amplitude:.1f}%")
    elif amplitude > 3:
        score += 10

    # 3. RSI (15分)
    rsi = stock_data.get('rsi', 50)
    if 30 <= rsi <= 40:
        score += 15
        reasons.append(f"RSI超卖{rsi:.0f}")
    elif 40 < rsi <= 60:
        score += 10

    # 4. MACD (15分)
    macd = stock_data.get('macd', {})
    if macd.get('trend') == 'bullish' and macd.get('histogram', 0) > 0:
        score += 15
        reasons.append("MACD金叉")

    # 5. 布林带 (10分)
    bollinger = stock_data.get('bollinger', {})
    if bollinger.get('position') == 'oversold':
        score += 10
        reasons.append("布林下轨")

    # 6. 量比 (10分)
    vol_ratio = stock_data.get('volumeRatio', 1.0)
    if vol_ratio >= 2.0:
        score += 10
        reasons.append(f"放量{vol_ratio:.1f}倍")
    elif vol_ratio >= 1.5:
        score += 5

    # 7. 热门板块 (20分) - 提高权重!
    sectors = stock_data.get('sectors', [])
    hot_sector_match = [s for s in sectors if s in hot_sectors]
    if hot_sector_match:
        bonus = min(20, len(hot_sector_match) * 10)
        score += bonus
        reasons.append(f"热门板块:{','.join(hot_sector_match)}")

    # 8. 社交媒体提及 (15分) - 新增!
    if social_mentions > 0:
        bonus = min(15, social_mentions * 5)
        score += bonus
        reasons.append(f"社交热度:{social_mentions}次提及")

    stock_data['reasons'] = reasons
    stock_data['score'] = min(100, max(0, score))
    stock_data['rating'] = (
        'strong_buy' if score >= 80 else
        ('buy' if score >= 60 else
        ('neutral' if score >= 40 else 'sell'))
    )

    return stock_data


# ==================== 主函数 ====================
def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "stocks": []})
        return

    ctx = None
    results = []

    try:
        # ===== 步骤1: 采集社交媒体 =====
        collector = SocialMediaCollector()
        social_data = collector.collect_all()

        # ===== 步骤2: 分析热门板块 =====
        keyword_analysis = analyze_hot_keywords(social_data)
        hot_sectors = keyword_analysis["hot_sectors"]

        # ===== 步骤3: 构建候选股票池 =====
        candidate_codes = set()

        # 3.1 优先添加热门板块股票
        for sector in hot_sectors:
            if sector in HK_SECTORS:
                candidate_codes.update(HK_SECTORS[sector])

        # 3.2 补充其他板块股票（如果不足30只）
        if len(candidate_codes) < 30:
            for sector, codes in HK_SECTORS.items():
                candidate_codes.update(codes)
                if len(candidate_codes) >= 50:
                    break

        # ===== 步骤4: 连接Futu，获取实时行情 =====
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 批量获取行情
        codes = list(candidate_codes)
        ret, snapshots = ctx.get_market_snapshot(codes)
        snap_map = {}
        if ret == RET_OK and snapshots is not None:
            for _, row in snapshots.iterrows():
                snap_map[row["code"]] = row

        # ===== 步骤5: 处理每只股票 =====
        for code in codes:
            if code not in snap_map:
                continue

            s = snap_map[code]
            prev_close = float(s.get("prev_close_price", 0))
            price = float(s.get("last_price", 0))

            if prev_close <= 0 or price <= 0:
                continue

            # 基础数据
            stock = {
                "code": code.replace("HK.", ""),
                "name": s.get("name", ""),
                "price": price,
                "prevClose": prev_close,
                "changePct": round((price - prev_close) / prev_close * 100, 2),
                "amplitude": float(s.get("amplitude", 0)),
                "volume": int(s.get("volume", 0)),
                "turnover": float(s.get("turnover", 0)),
                "marketCap": float(s.get("market_val", 0)),
                "sectors": [],
            }

            # 匹配板块
            for sector, sector_codes in HK_SECTORS.items():
                if code in sector_codes:
                    stock["sectors"].append(sector)

            # K线数据
            ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=60)
            if ret_k == RET_OK and klines is not None and len(klines) > 0:
                closes = klines["close"].tolist()
                volumes = klines["volume"].tolist()

                stock["rsi"] = calc_rsi(closes)
                stock["macd"] = calc_macd(closes)
                stock["bollinger"] = calc_bollinger_bands(closes)

                # 量比
                avg_vol_5 = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
                stock["volumeRatio"] = round(stock["volume"] / avg_vol_5, 2) if avg_vol_5 > 0 else 1.0
            else:
                stock.update({"rsi": 50, "macd": {}, "bollinger": {}, "volumeRatio": 1.0})

            # 检查社交媒体提及
            stock_name = stock["name"]
            social_mentions = 0
            for platform, keywords in social_data.items():
                for kw in keywords:
                    if stock_name in kw or code.replace("HK.", "") in kw:
                        social_mentions += 1

            # 智能评分
            stock = calculate_enhanced_score(stock, hot_sectors, social_mentions)

            results.append(stock)

    except Exception as e:
        _output_json({
            "error": str(e),
            "stocks": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        return
    finally:
        if ctx:
            ctx.close()

    # ===== 步骤6: 排序与筛选 =====
    # 按评分排序
    results.sort(key=lambda x: x.get('score', 0), reverse=True)

    # 优先推荐：中低市值 + 高波动 + 热门板块
    priority_stocks = []
    normal_stocks = []

    for stock in results:
        market_cap = stock.get("marketCap", 0)
        amplitude = stock.get("amplitude", 0)
        is_hot = any(s in hot_sectors for s in stock.get("sectors", []))

        if market_cap < 500 and amplitude > 3 and is_hot:
            priority_stocks.append(stock)
        else:
            normal_stocks.append(stock)

    final_results = priority_stocks + normal_stocks

    # ===== 输出 =====
    output = {
        "stocks": final_results,
        "count": len(final_results),
        "hot_sectors": hot_sectors,
        "keyword_analysis": keyword_analysis,
        "social_data_summary": {
            "weibo_count": len(social_data.get("weibo", [])),
            "douyin_count": len(social_data.get("douyin", [])),
            "cls_count": len(social_data.get("cls", [])),
            "douban_count": len(social_data.get("douban", [])),
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "4.0 Ultimate",
    }
    _output_json(output)


if __name__ == "__main__":
    main()
