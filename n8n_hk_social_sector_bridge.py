#!/usr/bin/env python3
"""
港股社交媒体+板块联动监控系统 for n8n
整合功能：
1. 微博/抖音/雪球热搜采集
2. 热搜关键词映射到港股板块
3. 板块异动检测
4. 中低市值高波动股票筛选
5. 完整技术指标分析
6. 智能评分系统
"""
import json
import sys
import os
import logging
import warnings
from datetime import datetime
from typing import List, Dict, Any, Optional
import time

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# OS-level stdout suppression for Futu SDK
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
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def _output_json(data):
    """输出JSON到真实stdout"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


# ==================== 港股板块配置 ====================
HK_SECTORS = {
    '商业航天': [
        ('HK.01045', '亚太卫星'),
        ('HK.00031', '航天控股'),
    ],
    '卫星通信': [
        ('HK.01045', '亚太卫星'),
        ('HK.00763', '中兴通讯'),
        ('HK.02342', '京信通信'),
    ],
    'AI人工智能': [
        ('HK.09888', '百度'),
        ('HK.00020', '商汤'),
        ('HK.01024', '快手'),
        ('HK.09618', '京东'),
        ('HK.03690', '美团'),
    ],
    '机器人': [
        ('HK.01810', '小米集团'),
        ('HK.00285', '比亚迪电子'),
    ],
    '新能源汽车': [
        ('HK.09866', '蔚来'),
        ('HK.02015', '理想汽车'),
        ('HK.01211', '比亚迪'),
        ('HK.00175', '吉利汽车'),
        ('HK.09868', '小鹏汽车'),
    ],
    '光伏太阳能': [
        ('HK.03800', '协鑫科技'),
        ('HK.00968', '信义光能'),
        ('HK.06865', '福莱特玻璃'),
    ],
    '半导体芯片': [
        ('HK.00981', '中芯国际'),
        ('HK.01347', '华虹半导体'),
    ],
    '科技互联网': [
        ('HK.00700', '腾讯控股'),
        ('HK.09988', '阿里巴巴'),
        ('HK.09888', '百度集团'),
        ('HK.09618', '京东集团'),
        ('HK.03690', '美团'),
        ('HK.09999', '网易'),
    ],
    '医药生物': [
        ('HK.06160', '百济神州'),
        ('HK.02269', '药明生物'),
        ('HK.02359', '药明康德'),
    ],
    '消费零售': [
        ('HK.01929', '周大福'),
        ('HK.09633', '农夫山泉'),
        ('HK.02331', '李宁'),
        ('HK.06862', '海底捞'),
        ('HK.09992', '泡泡玛特'),
    ],
}

# 财经相关关键词（用于过滤）
FINANCE_KEYWORDS = [
    # 基础
    "股", "A股", "港股", "美股", "基金", "ETF", "涨停", "跌停", "大盘", "指数", "板块",
    # 传统行业
    "半导体", "芯片", "新能源", "光伏", "锂电", "银行", "券商", "保险", "地产", "医药",
    # AI科技
    "科技", "AI", "人工智能", "机器人", "算力", "人形机器人", "具身智能", "大模型", "ChatGPT",
    # 航天航空
    "航天", "火箭", "卫星", "商业航天", "空间站", "低空经济", "飞行汽车", "eVTOL", "无人机",
    # 新兴概念
    "固态电池", "钠离子", "氢能", "核聚变", "小堆", "脑机接口", "合成生物", "基因编辑", "GLP-1", "减肥药",
    "量子", "6G", "星闪", "鸿蒙",
    # 龙头公司
    "特斯拉", "苹果", "华为", "小米", "比亚迪", "茅台", "宁德", "隆基", "中芯", "SpaceX",
    "腾讯", "阿里", "百度", "京东", "美团", "蔚来", "理想", "小鹏",
    # 市场情绪
    "利好", "利空", "财报", "业绩", "分红", "央行", "降息", "加息", "货币", "政策",
    "牛市", "熊市", "行情", "反弹", "回调",
]


# ==================== 社交媒体热搜采集 ====================
class SocialHotCollector:
    """社交媒体热搜采集器（港股版）"""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15",
        }
        self.timeout = 5  # 快速超时，避免拖慢整个流程

    def get_weibo_hot(self) -> List[Dict]:
        """获取微博热搜（财经相关）"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            data = response.json()

            realtime = data.get("data", {}).get("realtime", [])
            for item in realtime[:30]:
                keyword = item.get("word", "") or item.get("note", "")
                if self._is_finance_related(keyword):
                    hot_list.append({
                        "keyword": keyword,
                        "hot_score": item.get("raw_hot", 0) or item.get("num", 0),
                        "source": "微博",
                    })
        except Exception as e:
            pass  # 静默失败

        return hot_list

    def get_douyin_hot(self) -> List[Dict]:
        """获取抖音热搜（财经相关）"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            # 使用今日头条API（和抖音同源）
            url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
            headers = {
                **self.headers,
                "Referer": "https://www.toutiao.com/",
            }
            response = requests.get(url, headers=headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", [])[:30]:
                title = item.get("Title", "")
                if self._is_finance_related(title):
                    hot_list.append({
                        "keyword": title,
                        "hot_score": item.get("HotValue", 0),
                        "source": "抖音/头条",
                    })
        except Exception as e:
            pass

        return hot_list

    def get_xueqiu_hot(self) -> List[Dict]:
        """获取雪球热股（直接返回股票）"""
        hot_list = []
        if not REQUESTS_AVAILABLE:
            return hot_list

        try:
            url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
            params = {"type": "12", "size": 20}  # 12=港股
            headers = {
                **self.headers,
                "Referer": "https://xueqiu.com/",
            }
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            data = response.json()

            for item in data.get("data", {}).get("items", [])[:20]:
                hot_list.append({
                    "code": "HK." + item.get("symbol", "").replace("0", "", 1),  # HK01810 -> HK.01810
                    "name": item.get("name", ""),
                    "hot_score": item.get("followers", 0),
                    "source": "雪球",
                })
        except Exception as e:
            pass

        return hot_list

    def _is_finance_related(self, text: str) -> bool:
        """判断是否财经相关"""
        return any(kw in text for kw in FINANCE_KEYWORDS)

    def get_all_hot(self) -> Dict[str, List]:
        """获取所有平台热搜"""
        return {
            "weibo": self.get_weibo_hot(),
            "douyin": self.get_douyin_hot(),
            "xueqiu": self.get_xueqiu_hot(),
        }


# ==================== 热搜到板块映射 ====================
def map_keywords_to_sectors(keywords: List[str]) -> List[str]:
    """将热搜关键词映射到港股板块"""
    triggered_sectors = set()

    keyword_text = " ".join(keywords)

    # 映射规则
    if any(kw in keyword_text for kw in ["航天", "火箭", "卫星", "SpaceX", "星链"]):
        triggered_sectors.add("商业航天")
        triggered_sectors.add("卫星通信")

    if any(kw in keyword_text for kw in ["AI", "人工智能", "大模型", "ChatGPT", "机器人", "具身智能"]):
        triggered_sectors.add("AI人工智能")
        triggered_sectors.add("机器人")

    if any(kw in keyword_text for kw in ["新能源", "电动车", "蔚来", "理想", "小鹏", "特斯拉", "比亚迪"]):
        triggered_sectors.add("新能源汽车")

    if any(kw in keyword_text for kw in ["光伏", "太阳能", "绿电", "清洁能源"]):
        triggered_sectors.add("光伏太阳能")

    if any(kw in keyword_text for kw in ["芯片", "半导体", "中芯", "华虹", "台积电"]):
        triggered_sectors.add("半导体芯片")

    if any(kw in keyword_text for kw in ["腾讯", "阿里", "百度", "京东", "美团", "互联网", "科技"]):
        triggered_sectors.add("科技互联网")

    if any(kw in keyword_text for kw in ["医药", "生物", "创新药", "疫苗", "GLP-1", "减肥药"]):
        triggered_sectors.add("医药生物")

    if any(kw in keyword_text for kw in ["消费", "零售", "电商", "周大福", "李宁", "农夫山泉"]):
        triggered_sectors.add("消费零售")

    return list(triggered_sectors)


# ==================== 技术指标计算 ====================
def calc_rsi(closes, period=14):
    """计算RSI"""
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
    """计算MACD"""
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
    """计算布林带"""
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

    return {
        "upper": round(upper, 3),
        "middle": round(middle, 3),
        "lower": round(lower, 3),
        "position": position
    }


# ==================== 智能评分系统 ====================
def calculate_score(stock_data, hot_sectors):
    """智能评分系统（满分100分）"""
    score = 0
    reasons = []

    # 1. 涨幅评分 (20分)
    change = stock_data.get('changePct', 0)
    if change > 5:
        score += 20
        reasons.append(f"强势上涨{change:.1f}%")
    elif change > 2:
        score += 15
        reasons.append(f"温和上涨{change:.1f}%")
    elif change > 0:
        score += 10

    # 2. 振幅评分 (15分)
    amplitude = stock_data.get('amplitude', 0)
    if amplitude > 5:
        score += 15
        reasons.append(f"高振幅{amplitude:.1f}%")
    elif amplitude > 3:
        score += 10
    elif amplitude > 2:
        score += 5

    # 3. RSI评分 (15分)
    rsi = stock_data.get('rsi', 50)
    if 30 <= rsi <= 40:
        score += 15
        reasons.append(f"RSI超卖{rsi:.0f}")
    elif 40 < rsi <= 60:
        score += 10
    elif rsi > 70:
        score -= 5

    # 4. MACD评分 (15分)
    macd = stock_data.get('macd', {})
    if macd.get('trend') == 'bullish' and macd.get('histogram', 0) > 0:
        score += 15
        reasons.append("MACD金叉")
    elif macd.get('trend') == 'bearish':
        score -= 5

    # 5. 布林带评分 (10分)
    bollinger = stock_data.get('bollinger', {})
    if bollinger.get('position') == 'oversold':
        score += 10
        reasons.append("布林下轨超卖")
    elif bollinger.get('position') == 'overbought':
        score -= 5

    # 6. 量比评分 (10分)
    vol_ratio = stock_data.get('volumeRatio', 1.0)
    if vol_ratio >= 2.0:
        score += 10
        reasons.append(f"放量{vol_ratio:.1f}倍")
    elif vol_ratio >= 1.5:
        score += 5

    # 7. 热门板块加分 (15分) - 新增!
    sectors = stock_data.get('sectors', [])
    hot_sector_count = sum(1 for s in sectors if s in hot_sectors)
    if hot_sector_count > 0:
        bonus = min(15, hot_sector_count * 5)
        score += bonus
        reasons.append(f"热门板块:{','.join([s for s in sectors if s in hot_sectors])}")

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
        # 1. 采集社交媒体热搜
        collector = SocialHotCollector()
        social_data = collector.get_all_hot()

        # 提取热搜关键词
        all_keywords = []
        for platform, items in social_data.items():
            all_keywords.extend([item.get("keyword", "") for item in items if "keyword" in item])

        # 映射到板块
        hot_sectors = map_keywords_to_sectors(all_keywords)

        # 2. 收集所有候选股票（从热门板块）
        candidate_stocks = {}  # {code: [sector1, sector2, ...], ...}

        # 优先添加热门板块的股票
        for sector in hot_sectors:
            if sector in HK_SECTORS:
                for code, name in HK_SECTORS[sector]:
                    if code not in candidate_stocks:
                        candidate_stocks[code] = {"name": name, "sectors": []}
                    candidate_stocks[code]["sectors"].append(sector)

        # 如果热门板块股票不足，添加其他板块
        if len(candidate_stocks) < 20:
            for sector, stocks in HK_SECTORS.items():
                if sector not in hot_sectors:  # 非热门板块
                    for code, name in stocks:
                        if code not in candidate_stocks:
                            candidate_stocks[code] = {"name": name, "sectors": [sector]}
                        if len(candidate_stocks) >= 30:
                            break
                if len(candidate_stocks) >= 30:
                    break

        # 添加雪球热股
        xueqiu_stocks = social_data.get("xueqiu", [])
        for item in xueqiu_stocks:
            code = item.get("code", "")
            name = item.get("name", "")
            if code and code not in candidate_stocks:
                candidate_stocks[code] = {"name": name, "sectors": ["雪球热股"]}

        codes = list(candidate_stocks.keys())

        # 3. 连接Futu获取行情
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 批量获取实时行情
        ret, snapshots = ctx.get_market_snapshot(codes)
        snap_map = {}
        if ret == RET_OK and snapshots is not None:
            for _, row in snapshots.iterrows():
                snap_map[row["code"]] = row

        # 4. 处理每只股票
        for code, meta in candidate_stocks.items():
            stock = {
                "code": code.replace("HK.", ""),
                "name": meta["name"],
                "sectors": meta["sectors"],
            }

            # 实时行情
            if code in snap_map:
                s = snap_map[code]
                prev_close = float(s.get("prev_close_price", 0))
                price = float(s.get("last_price", 0))

                stock.update({
                    "price": price,
                    "open": float(s.get("open_price", 0)),
                    "high": float(s.get("high_price", 0)),
                    "low": float(s.get("low_price", 0)),
                    "prevClose": prev_close,
                    "volume": int(s.get("volume", 0)),
                    "turnover": float(s.get("turnover", 0)),
                    "amplitude": float(s.get("amplitude", 0)),
                    "changePct": round((price - prev_close) / prev_close * 100, 2) if prev_close > 0 else 0,
                    "turnoverRate": float(s.get("turnover_rate", 0)),
                    "marketCap": float(s.get("market_val", 0)),  # 市值（亿）
                })
            else:
                stock.update({"price": 0, "error": "no_snapshot"})
                results.append(stock)
                continue

            # K线数据
            ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=60)
            if ret_k == RET_OK and klines is not None and len(klines) > 0:
                closes = klines["close"].tolist()
                highs = klines["high"].tolist()
                lows = klines["low"].tolist()
                volumes = klines["volume"].tolist()

                # 技术指标
                stock["rsi"] = calc_rsi(closes)
                stock["macd"] = calc_macd(closes)
                stock["bollinger"] = calc_bollinger_bands(closes)

                # 量比
                avg_vol_5 = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else sum(volumes) / len(volumes)
                stock["volumeRatio"] = round(stock["volume"] / avg_vol_5, 2) if avg_vol_5 > 0 else 1.0
            else:
                stock.update({"rsi": 50, "macd": {"trend": "unknown"}, "bollinger": {}})

            # 智能评分（考虑热门板块）
            stock = calculate_score(stock, hot_sectors)

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

    # 5. 按评分排序
    results.sort(key=lambda x: x.get('score', 0), reverse=True)

    # 6. 筛选：优先推荐中低市值+高波动+热门板块
    priority_stocks = []
    normal_stocks = []

    for stock in results:
        market_cap = stock.get("marketCap", 0)
        amplitude = stock.get("amplitude", 0)
        is_hot_sector = any(s in hot_sectors for s in stock.get("sectors", []))

        # 优先级：中低市值(<500亿) + 高波动(>3%) + 热门板块
        if market_cap < 500 and amplitude > 3 and is_hot_sector:
            priority_stocks.append(stock)
        else:
            normal_stocks.append(stock)

    # 合并：优先股在前
    final_results = priority_stocks + normal_stocks

    output = {
        "stocks": final_results,
        "count": len(final_results),
        "hot_sectors": hot_sectors,
        "social_hot": {
            "weibo_count": len(social_data.get("weibo", [])),
            "douyin_count": len(social_data.get("douyin", [])),
            "xueqiu_count": len(social_data.get("xueqiu", [])),
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "HK Social+Sector Bridge",
        "version": "3.0",
    }
    _output_json(output)


if __name__ == "__main__":
    main()
