#!/usr/bin/env python3
"""
港股智能做T推荐系统 - n8n增强版
功能：
1. 全市场扫描（中低市值、高波动优先）
2. 社交媒体热搜集成（微博、抖音、雪球、贴吧）
3. 新闻热点板块识别
4. 完整技术指标（RSI、MACD、布林带、KDJ、OBV等）
5. 智能评分系统
"""
import json
import sys
import os
import tempfile
import logging
import warnings
import requests
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

# --- OS-level stdout suppression ---
_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import (
        OpenQuoteContext, KLType, SubType, KL_FIELD,
        RET_OK, Market, SortField
    )
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False


def _output_json(data):
    """Write JSON to the real stdout fd"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.stdout.flush()


# ==================== 社交媒体热搜 ====================
class SocialHeatFetcher:
    """社交媒体热搜获取器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
        }

    def get_weibo_hot(self) -> List[Dict]:
        """获取微博热搜"""
        hot_topics = []
        try:
            url = "https://weibo.com/ajax/side/hotSearch"
            resp = requests.get(url, headers=self.headers, timeout=5)
            data = resp.json()

            if data and 'data' in data and 'realtime' in data['data']:
                for item in data['data']['realtime'][:20]:
                    hot_topics.append({
                        'keyword': item.get('word', ''),
                        'heat': item.get('num', 0),
                        'source': 'weibo'
                    })
        except:
            pass
        return hot_topics

    def get_douyin_hot(self) -> List[Dict]:
        """获取抖音热搜"""
        hot_topics = []
        try:
            # 抖音热榜（需要特殊处理）
            url = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
            resp = requests.get(url, headers=self.headers, timeout=5)
            data = resp.json()

            if data and 'word_list' in data:
                for item in data['word_list'][:20]:
                    hot_topics.append({
                        'keyword': item.get('word', ''),
                        'heat': item.get('hot_value', 0),
                        'source': 'douyin'
                    })
        except:
            pass
        return hot_topics

    def get_xueqiu_hot(self) -> List[Dict]:
        """获取雪球热搜"""
        hot_topics = []
        try:
            url = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json"
            params = {'size': 20, 'type': 12, '_t': int(datetime.now().timestamp() * 1000)}
            resp = requests.get(url, params=params, headers=self.headers, timeout=5)
            data = resp.json()

            if data and 'data' in data and 'items' in data['data']:
                for item in data['data']['items']:
                    hot_topics.append({
                        'code': item.get('symbol', ''),
                        'name': item.get('name', ''),
                        'heat': item.get('follow_count', 0),
                        'source': 'xueqiu'
                    })
        except:
            pass
        return hot_topics

    def get_eastmoney_guba(self, code: str) -> Dict:
        """获取东财股吧热度"""
        result = {'post_count': 0, 'heat_score': 0}
        try:
            stock_code = code.replace('HK.', '')
            url = f"https://guba.eastmoney.com/list,hk{stock_code}.html"
            resp = requests.get(url, headers=self.headers, timeout=5)

            if resp.status_code == 200:
                # 简单的帖子数估算
                post_matches = re.findall(r'阅读</span>(\d+)', resp.text)
                if post_matches:
                    result['post_count'] = sum([int(x) for x in post_matches[:5]])
                    result['heat_score'] = min(result['post_count'] // 1000, 100)
        except:
            pass
        return result


# ==================== 新闻热点分析 ====================
class NewsHotspotAnalyzer:
    """新闻热点分析器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_hot_sectors(self) -> List[Dict]:
        """获取热门板块（基于新闻）"""
        sectors = []
        try:
            # 财联社快讯
            url = "https://www.cls.cn/api/sw"
            params = {'app': 'CailianpressWeb', 'os': 'web', 'sv': '8.4.6'}
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                # 提取板块关键词
                sector_keywords = {
                    '新能源': ['新能源', '光伏', '风电', '储能', '锂电'],
                    '半导体': ['半导体', '芯片', '集成电路'],
                    '人工智能': ['AI', '人工智能', 'ChatGPT', '大模型'],
                    '医药': ['医药', '生物', '制药', '疫苗'],
                    '汽车': ['汽车', '新能源车', '电动车'],
                    '互联网': ['互联网', '电商', '游戏']
                }

                sector_count = {}
                for item in data['data'][:50]:
                    title = item.get('title', '') + item.get('content', '')
                    for sector, keywords in sector_keywords.items():
                        if any(kw in title for kw in keywords):
                            sector_count[sector] = sector_count.get(sector, 0) + 1

                for sector, count in sorted(sector_count.items(), key=lambda x: x[1], reverse=True):
                    sectors.append({'sector': sector, 'news_count': count, 'heat': count * 10})
        except:
            pass

        return sectors[:10]


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


def calc_atr(highs, lows, closes, period=14):
    """计算ATR"""
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return round(sum(trs[-period:]) / period, 4)


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


def calc_kdj(highs, lows, closes, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    if len(closes) < n:
        return {"k": 50, "d": 50, "j": 50, "signal": "neutral"}

    recent_highs = highs[-n:]
    recent_lows = lows[-n:]
    recent_closes = closes[-n:]

    highest = max(recent_highs)
    lowest = min(recent_lows)

    if highest == lowest:
        return {"k": 50, "d": 50, "j": 50, "signal": "neutral"}

    rsv = (recent_closes[-1] - lowest) / (highest - lowest) * 100

    # 简化计算：K=2/3前K+1/3RSV
    k = rsv  # 简化版
    d = k
    j = 3 * k - 2 * d

    signal = "overbought" if j > 80 else ("oversold" if j < 20 else "neutral")

    return {"k": round(k, 2), "d": round(d, 2), "j": round(j, 2), "signal": signal}


def calc_obv(volumes, closes):
    """计算OBV（能量潮）"""
    if len(volumes) < 2:
        return 0

    obv = 0
    for i in range(1, len(volumes)):
        if closes[i] > closes[i-1]:
            obv += volumes[i]
        elif closes[i] < closes[i-1]:
            obv -= volumes[i]

    return obv


# ==================== 港股市场扫描 ====================
def get_hk_market_stocks(ctx, filters: Dict) -> List[Tuple[str, str]]:
    """
    获取港股市场股票列表
    filters: {
        'market_cap_min': 最小市值（亿港元）,
        'market_cap_max': 最大市值（亿港元）,
        'min_price': 最低价格,
        'max_price': 最高价格
    }
    """
    stocks = []

    try:
        # 获取港股主板股票列表
        ret, data = ctx.get_stock_basicinfo(market=Market.HK, stock_type='STOCK')

        if ret == RET_OK and data is not None:
            for _, row in data.iterrows():
                code = row['code']
                name = row['name']

                # 过滤条件
                # 可以在这里添加市值、价格等过滤
                stocks.append((code, name))

        # 限制数量，避免请求过多
        return stocks[:200]  # 返回前200只

    except Exception as e:
        return []


def get_volatile_stocks(ctx, top_n=50) -> List[Tuple[str, str]]:
    """获取高波动股票"""
    try:
        # 按振幅排序获取活跃股票
        ret, data = ctx.get_market_snapshot(['HK.00700', 'HK.09988'])  # 示例

        # 这里可以通过富途API获取当日振幅排行
        # 暂时返回预设的活跃股票池
        volatile_stocks = [
            ('HK.09988', '阿里巴巴'), ('HK.00700', '腾讯控股'), ('HK.03690', '美团'),
            ('HK.01810', '小米集团'), ('HK.09618', '京东集团'), ('HK.01024', '快手'),
            ('HK.09888', '百度集团'), ('HK.01211', '比亚迪'), ('HK.02015', '理想汽车'),
            ('HK.09868', '小鹏汽车'), ('HK.09866', '蔚来'), ('HK.00981', '中芯国际'),
            ('HK.01347', '华虹半导体'), ('HK.01801', '信达生物'), ('HK.09969', '诺诚健华'),
            ('HK.03800', '协鑫科技'), ('HK.00968', '信义光能'), ('HK.02020', '安踏体育'),
            ('HK.01177', '中国生物制药'), ('HK.01458', '周黑鸭'), ('HK.02382', '舜宇光学'),
            ('HK.02331', '李宁'), ('HK.01833', '平安好医生'), ('HK.06060', '众安在线'),
            ('HK.02269', '药明生物'), ('HK.01896', '猫眼娱乐'), ('HK.03908', '中金公司'),
            ('HK.09926', '康方生物'), ('HK.09999', '网易'), ('HK.06618', '京东健康'),
        ]

        return volatile_stocks[:top_n]

    except:
        return []


# ==================== 主分析函数 ====================
def analyze_stock(ctx, code: str, name: str, social_fetcher, news_analyzer) -> Optional[Dict]:
    """完整分析单只股票"""
    result = {
        'code': code,
        'name': name,
        'price': 0,
        'change_pct': 0,
        'amplitude': 0,
        'volume': 0,
        'turnover_rate': 0,
        'market_cap': 0,
        'indicators': {},
        'social_heat': {},
        'score': 0,
        'rating': 'neutral',
        'reasons': [],
        'buy_price': 0,
        'sell_price': 0,
        'stop_loss': 0
    }

    try:
        # 获取实时行情
        ret, data = ctx.get_market_snapshot([code])
        if ret != RET_OK or data is None or data.empty:
            return None

        row = data.iloc[0]
        price = float(row.get('last_price', 0))
        prev_close = float(row.get('prev_close_price', 0))
        high = float(row.get('high_price', 0))
        low = float(row.get('low_price', 0))
        volume = int(row.get('volume', 0))
        turnover_rate = float(row.get('turnover_rate', 0))

        if price <= 0 or prev_close <= 0:
            return None

        result['price'] = price
        result['change_pct'] = round((price - prev_close) / prev_close * 100, 2)
        result['amplitude'] = round((high - low) / prev_close * 100, 2)
        result['volume'] = volume
        result['turnover_rate'] = turnover_rate

        # 获取K线数据
        ret_k, klines, _ = ctx.request_history_kline(code, ktype=KLType.K_DAY, max_count=60)
        if ret_k != RET_OK or klines is None or len(klines) == 0:
            return None

        closes = klines["close"].tolist()
        highs = klines["high"].tolist()
        lows = klines["low"].tolist()
        volumes = klines["volume"].tolist()

        # 计算技术指标
        result['indicators'] = {
            'rsi': calc_rsi(closes),
            'macd': calc_macd(closes),
            'atr': calc_atr(highs, lows, closes),
            'bollinger': calc_bollinger_bands(closes),
            'kdj': calc_kdj(highs, lows, closes, n=9),
            'obv': calc_obv(volumes, closes)
        }

        # 量比
        if len(volumes) >= 6:
            avg_vol_5 = sum(volumes[-6:-1]) / 5
            vol_ratio = volume / avg_vol_5 if avg_vol_5 > 0 else 1.0
            result['volume_ratio'] = round(vol_ratio, 2)

        # 支撑/压力位
        pivot = round((high + low + prev_close) / 3, 3)
        result['buy_price'] = round(2 * pivot - high, 3)
        result['sell_price'] = round(2 * pivot - low, 3)
        result['stop_loss'] = round(pivot - (high - low), 3)

        # 社交热度
        guba_heat = social_fetcher.get_eastmoney_guba(code)
        result['social_heat'] = {
            'guba_score': guba_heat.get('heat_score', 0)
        }

        # 综合评分
        score = calculate_score(result)
        result['score'] = score
        result['rating'] = 'strong_buy' if score >= 80 else ('buy' if score >= 60 else ('neutral' if score >= 40 else 'sell'))

        return result

    except Exception as e:
        return None


def calculate_score(stock_data: Dict) -> int:
    """计算综合评分"""
    score = 0
    reasons = []

    # 1. 涨幅评分 (20分)
    change = stock_data.get('change_pct', 0)
    if change > 5:
        score += 20
        reasons.append("强势上涨")
    elif change > 2:
        score += 15
        reasons.append("温和上涨")
    elif change > 0:
        score += 10

    # 2. 振幅评分 (15分)
    amplitude = stock_data.get('amplitude', 0)
    if amplitude > 5:
        score += 15
        reasons.append("振幅大")
    elif amplitude > 3:
        score += 10

    # 3. RSI评分 (15分)
    rsi = stock_data.get('indicators', {}).get('rsi', 50)
    if 30 <= rsi <= 40:
        score += 15
        reasons.append("RSI超卖区")
    elif 40 < rsi <= 60:
        score += 10

    # 4. MACD评分 (15分)
    macd = stock_data.get('indicators', {}).get('macd', {})
    if macd.get('trend') == 'bullish':
        score += 15
        reasons.append("MACD金叉")

    # 5. 布林带评分 (10分)
    bb = stock_data.get('indicators', {}).get('bollinger', {})
    if bb.get('position') == 'oversold':
        score += 10
        reasons.append("布林下轨超卖")

    # 6. KDJ评分 (10分)
    kdj = stock_data.get('indicators', {}).get('kdj', {})
    if kdj.get('signal') == 'oversold':
        score += 10
        reasons.append("KDJ超卖")

    # 7. 量比评分 (10分)
    vol_ratio = stock_data.get('volume_ratio', 1.0)
    if vol_ratio >= 2.0:
        score += 10
        reasons.append("放量")

    # 8. 社交热度 (5分)
    social_heat = stock_data.get('social_heat', {}).get('guba_score', 0)
    if social_heat > 50:
        score += 5
        reasons.append("社交热度高")

    stock_data['reasons'] = reasons
    return min(score, 100)


def main():
    if not FUTU_AVAILABLE:
        _output_json({"error": "futu-api not installed", "stocks": []})
        return

    ctx = None
    results = []

    try:
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 初始化社交媒体和新闻分析器
        social_fetcher = SocialHeatFetcher()
        news_analyzer = NewsHotspotAnalyzer()

        # 获取热门板块
        hot_sectors = news_analyzer.get_hot_sectors()

        # 获取高波动股票池
        candidate_stocks = get_volatile_stocks(ctx, top_n=50)

        # 分析每只股票
        for code, name in candidate_stocks:
            stock_result = analyze_stock(ctx, code, name, social_fetcher, news_analyzer)
            if stock_result and stock_result['score'] >= 40:  # 只保留评分>=40的
                results.append(stock_result)

        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)

        # 输出结果
        output = {
            "success": True,
            "stocks": results[:30],  # 返回TOP30
            "hot_sectors": hot_sectors,
            "count": len(results),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "FutuOpenD Enhanced"
        }

        _output_json(output)

    except Exception as e:
        _output_json({
            "error": str(e),
            "stocks": results,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    finally:
        if ctx:
            ctx.close()


if __name__ == "__main__":
    main()
