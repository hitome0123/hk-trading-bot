#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenBB 数据源客户端
集成 OpenBB-Alice 到 hk-trading-bot

功能：
1. 股票报价 - 实时行情
2. 历史K线 - 日/周/月K线
3. 基本面数据 - 财务指标、估值
4. 技术指标 - 由 OpenBB 计算
5. 新闻搜索 - 多源新闻

使用前确保 OpenBB API 运行中：
  cd ~/OpenBB-Alice && source .venv/bin/activate && openbb-api
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class OpenBBClient:
    """OpenBB API 客户端"""

    def __init__(self, base_url: str = None):
        # 自动检测端口 (6900 或 6901)
        if base_url is None:
            for port in [6900, 6901]:
                try:
                    test_url = f"http://127.0.0.1:{port}/api/v1/coverage/providers"
                    urllib.request.urlopen(test_url, timeout=2)
                    base_url = f"http://127.0.0.1:{port}"
                    break
                except:
                    pass
            if base_url is None:
                base_url = "http://127.0.0.1:6900"  # 默认
        self.base_url = base_url
        self.default_provider = "yfinance"  # 港股主要用 yfinance

    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """发送 API 请求"""
        url = f"{self.base_url}{endpoint}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        try:
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/json')
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            return {"error": str(e), "results": []}

    def convert_symbol(self, code: str) -> str:
        """
        转换股票代码格式
        HK.09988 -> 9988.HK
        """
        if code.startswith("HK."):
            num = code.replace("HK.", "").lstrip("0")
            return f"{num}.HK"
        return code

    # ==================== 实时行情 ====================

    def get_quote(self, symbol: str, provider: str = None) -> Dict:
        """
        获取实时报价

        Args:
            symbol: 股票代码 (HK.09988 或 9988.HK)
            provider: 数据源 (yfinance, fmp, etc.)

        Returns:
            {
                'symbol': '9988.HK',
                'name': 'Alibaba Group',
                'last_price': 152.3,
                'open': 150.1,
                'high': 153.3,
                'low': 149.5,
                'volume': 38866026,
                'prev_close': 147.1,
                'change': 5.2,
                'change_pct': 3.54,
                'ma_50d': 155.41,
                'ma_200d': 141.16,
                'year_high': 186.2,
                'year_low': 95.7,
            }
        """
        symbol = self.convert_symbol(symbol)
        provider = provider or self.default_provider

        result = self._request("/api/v1/equity/price/quote", {
            "symbol": symbol,
            "provider": provider
        })

        if "error" in result or not result.get("results"):
            return {"error": result.get("error", "No data")}

        data = result["results"][0]

        # 计算涨跌
        last = data.get("last_price", 0)
        prev = data.get("prev_close", 0)
        change = last - prev if last and prev else 0
        change_pct = (change / prev * 100) if prev else 0

        return {
            "symbol": data.get("symbol"),
            "name": data.get("name"),
            "last_price": last,
            "open": data.get("open"),
            "high": data.get("high"),
            "low": data.get("low"),
            "volume": data.get("volume"),
            "prev_close": prev,
            "change": round(change, 3),
            "change_pct": round(change_pct, 2),
            "ma_50d": data.get("ma_50d"),
            "ma_200d": data.get("ma_200d"),
            "year_high": data.get("year_high"),
            "year_low": data.get("year_low"),
            "volume_avg": data.get("volume_average"),
            "currency": data.get("currency", "HKD"),
        }

    def get_quotes_batch(self, symbols: List[str]) -> List[Dict]:
        """批量获取报价"""
        results = []
        for symbol in symbols:
            quote = self.get_quote(symbol)
            if "error" not in quote:
                results.append(quote)
        return results

    # ==================== 历史K线 ====================

    def get_historical(self, symbol: str, days: int = 60,
                       interval: str = "1d", provider: str = None) -> List[Dict]:
        """
        获取历史K线数据

        Args:
            symbol: 股票代码
            days: 天数
            interval: 周期 (1d, 1wk, 1mo)
            provider: 数据源

        Returns:
            [{'date': '2026-02-21', 'open': 150, 'high': 155, 'low': 149, 'close': 153, 'volume': 1000000}, ...]
        """
        symbol = self.convert_symbol(symbol)
        provider = provider or self.default_provider

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        result = self._request("/api/v1/equity/price/historical", {
            "symbol": symbol,
            "provider": provider,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "interval": interval,
        })

        if "error" in result or not result.get("results"):
            return []

        klines = []
        for row in result["results"]:
            klines.append({
                "date": row.get("date", "")[:10],
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "volume": row.get("volume"),
            })

        return klines

    def calculate_vwap(self, symbol: str, days: int = 20) -> Dict:
        """
        计算 VWAP (成交量加权平均价)

        Returns:
            {
                'vwap': 155.32,
                'current': 152.3,
                'vs_vwap_pct': -1.94,
                'signal': '低于成本线',
            }
        """
        klines = self.get_historical(symbol, days=days)
        if not klines:
            return {"error": "No historical data"}

        total_value = 0
        total_volume = 0

        for k in klines:
            if k.get("close") and k.get("volume"):
                # 典型价格 = (H + L + C) / 3
                typical_price = (k["high"] + k["low"] + k["close"]) / 3
                total_value += typical_price * k["volume"]
                total_volume += k["volume"]

        if total_volume == 0:
            return {"error": "No volume data"}

        vwap = total_value / total_volume

        # 获取当前价
        quote = self.get_quote(symbol)
        current = quote.get("last_price", 0)

        if current and vwap:
            vs_pct = (current - vwap) / vwap * 100
            if vs_pct > 15:
                signal = "⚠️ 高于成本线15%+，警惕主力出货"
            elif vs_pct > 5:
                signal = "📊 高于成本线，观察主力动向"
            elif vs_pct > -5:
                signal = "✅ 接近成本线，可考虑建仓"
            else:
                signal = "🎯 低于成本线，主力被套或吸筹"
        else:
            vs_pct = 0
            signal = "无法判断"

        return {
            "vwap": round(vwap, 2),
            "current": current,
            "vs_vwap_pct": round(vs_pct, 2),
            "signal": signal,
            "days": days,
        }

    # ==================== 基本面数据 ====================

    def get_profile(self, symbol: str) -> Dict:
        """获取公司简介"""
        symbol = self.convert_symbol(symbol)
        result = self._request("/api/v1/equity/profile", {
            "symbol": symbol,
            "provider": "yfinance"
        })

        if result.get("results"):
            return result["results"][0]
        return {}

    def get_metrics(self, symbol: str) -> Dict:
        """
        获取关键财务指标

        Returns:
            {
                'pe_ratio': 15.2,
                'pb_ratio': 2.1,
                'market_cap': 1500000000000,
                'dividend_yield': 0.025,
                ...
            }
        """
        symbol = self.convert_symbol(symbol)

        # 尝试多个端点
        endpoints = [
            ("/api/v1/equity/fundamental/overview", "fmp"),
            ("/api/v1/equity/fundamental/metrics", "fmp"),
        ]

        for endpoint, provider in endpoints:
            result = self._request(endpoint, {
                "symbol": symbol,
                "provider": provider
            })
            if result.get("results"):
                return result["results"][0]

        return {}

    # ==================== 技术指标 ====================

    def get_technical_summary(self, symbol: str) -> Dict:
        """
        获取技术指标摘要

        Returns:
            {
                'ma_50': 155.4,
                'ma_200': 141.2,
                'rsi_14': 58.3,
                'trend': 'bullish',
                'support': 145.0,
                'resistance': 160.0,
            }
        """
        quote = self.get_quote(symbol)
        klines = self.get_historical(symbol, days=200)

        if not klines or len(klines) < 20:
            return {"error": "Insufficient data"}

        # 计算移动平均线
        closes = [k["close"] for k in klines if k.get("close")]

        ma_20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else None
        ma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else None
        ma_200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else None

        current = quote.get("last_price", closes[-1] if closes else 0)

        # 判断趋势
        if ma_50 and ma_200:
            if current > ma_50 > ma_200:
                trend = "bullish"
            elif current < ma_50 < ma_200:
                trend = "bearish"
            else:
                trend = "neutral"
        else:
            trend = "unknown"

        # 计算 RSI
        rsi = self._calculate_rsi(closes, 14) if len(closes) >= 15 else None

        # 支撑位和阻力位 (简单计算)
        recent = klines[-20:]
        support = min(k["low"] for k in recent if k.get("low"))
        resistance = max(k["high"] for k in recent if k.get("high"))

        return {
            "current": current,
            "ma_20": round(ma_20, 2) if ma_20 else None,
            "ma_50": round(ma_50, 2) if ma_50 else None,
            "ma_200": round(ma_200, 2) if ma_200 else None,
            "rsi_14": round(rsi, 2) if rsi else None,
            "trend": trend,
            "support": round(support, 2),
            "resistance": round(resistance, 2),
        }

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算 RSI"""
        if len(prices) < period + 1:
            return None

        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [c if c > 0 else 0 for c in changes]
        losses = [-c if c < 0 else 0 for c in changes]

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    # ==================== 新闻搜索 ====================

    def search_news(self, query: str, limit: int = 10) -> List[Dict]:
        """
        搜索新闻

        Returns:
            [{'title': '...', 'date': '...', 'url': '...', 'source': '...'}, ...]
        """
        result = self._request("/api/v1/news/company", {
            "symbol": query,
            "provider": "benzinga",
            "limit": limit,
        })

        if result.get("results"):
            news = []
            for item in result["results"][:limit]:
                news.append({
                    "title": item.get("title"),
                    "date": item.get("date", "")[:10],
                    "url": item.get("url"),
                    "source": item.get("source"),
                })
            return news

        return []

    # ==================== 综合分析 ====================

    def analyze_stock(self, symbol: str) -> Dict:
        """
        综合分析一只股票

        整合：报价 + VWAP + 技术指标
        """
        print(f"📊 OpenBB 分析: {symbol}")

        # 1. 实时报价
        quote = self.get_quote(symbol)
        if "error" in quote:
            return {"error": quote["error"]}

        # 2. VWAP 分析
        vwap = self.calculate_vwap(symbol, days=20)

        # 3. 技术指标
        technical = self.get_technical_summary(symbol)

        return {
            "symbol": symbol,
            "name": quote.get("name"),
            "quote": {
                "price": quote.get("last_price"),
                "change_pct": quote.get("change_pct"),
                "volume": quote.get("volume"),
                "year_high": quote.get("year_high"),
                "year_low": quote.get("year_low"),
            },
            "vwap": {
                "value": vwap.get("vwap"),
                "vs_pct": vwap.get("vs_vwap_pct"),
                "signal": vwap.get("signal"),
            },
            "technical": {
                "ma_50": technical.get("ma_50"),
                "ma_200": technical.get("ma_200"),
                "rsi": technical.get("rsi_14"),
                "trend": technical.get("trend"),
                "support": technical.get("support"),
                "resistance": technical.get("resistance"),
            },
        }

    def health_check(self) -> bool:
        """检查 OpenBB API 是否可用"""
        try:
            result = self._request("/api/v1/coverage/providers", {})
            # 返回结果包含提供商列表 (如 'fred', 'yfinance' 等)
            return "error" not in result and len(result) > 0
        except:
            return False


# ==================== 便捷函数 ====================

_client = None

def get_client() -> OpenBBClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = OpenBBClient()
    return _client


def openbb_quote(symbol: str) -> Dict:
    """快速获取报价"""
    return get_client().get_quote(symbol)


def openbb_vwap(symbol: str, days: int = 20) -> Dict:
    """快速计算 VWAP"""
    return get_client().calculate_vwap(symbol, days)


def openbb_analyze(symbol: str) -> Dict:
    """快速综合分析"""
    return get_client().analyze_stock(symbol)


# ==================== 命令行入口 ====================

def main():
    import sys

    if len(sys.argv) < 2:
        print("""
OpenBB 数据源客户端
==================

用法:
  python openbb_client.py quote <股票代码>     # 获取报价
  python openbb_client.py vwap <股票代码>      # VWAP分析
  python openbb_client.py analyze <股票代码>   # 综合分析
  python openbb_client.py check                # 检查API状态

示例:
  python openbb_client.py quote 9988.HK
  python openbb_client.py analyze HK.09880
        """)
        return

    cmd = sys.argv[1]
    client = OpenBBClient()

    if cmd == "check":
        if client.health_check():
            print("✅ OpenBB API 正常运行")
        else:
            print("❌ OpenBB API 不可用，请确保已启动:")
            print("   cd ~/OpenBB-Alice && source .venv/bin/activate && openbb-api")

    elif cmd == "quote" and len(sys.argv) > 2:
        symbol = sys.argv[2]
        result = client.get_quote(symbol)
        if "error" not in result:
            print(f"\n📈 {result['name']} ({result['symbol']})")
            print(f"   现价: {result['last_price']} {result['currency']}")
            print(f"   涨跌: {result['change']:+.2f} ({result['change_pct']:+.2f}%)")
            print(f"   成交量: {result['volume']:,}")
            print(f"   52周高: {result['year_high']} | 低: {result['year_low']}")
            print(f"   MA50: {result['ma_50d']} | MA200: {result['ma_200d']}")
        else:
            print(f"❌ 错误: {result['error']}")

    elif cmd == "vwap" and len(sys.argv) > 2:
        symbol = sys.argv[2]
        days = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        result = client.calculate_vwap(symbol, days)
        if "error" not in result:
            print(f"\n📊 VWAP 分析 ({days}日)")
            print(f"   主力成本: {result['vwap']}")
            print(f"   当前价格: {result['current']}")
            print(f"   vs 成本线: {result['vs_vwap_pct']:+.2f}%")
            print(f"   {result['signal']}")
        else:
            print(f"❌ 错误: {result['error']}")

    elif cmd == "analyze" and len(sys.argv) > 2:
        symbol = sys.argv[2]
        result = client.analyze_stock(symbol)
        if "error" not in result:
            print(f"\n{'='*50}")
            print(f"📊 综合分析: {result['name']} ({result['symbol']})")
            print('='*50)

            q = result['quote']
            print(f"\n【行情】")
            print(f"   现价: {q['price']} ({q['change_pct']:+.2f}%)")
            print(f"   成交量: {q['volume']:,}")
            print(f"   52周范围: {q['year_low']} - {q['year_high']}")

            v = result['vwap']
            print(f"\n【主力成本】")
            print(f"   20日VWAP: {v['value']}")
            print(f"   vs 成本线: {v['vs_pct']:+.2f}%")
            print(f"   {v['signal']}")

            t = result['technical']
            print(f"\n【技术指标】")
            print(f"   MA50: {t['ma_50']} | MA200: {t['ma_200']}")
            print(f"   RSI(14): {t['rsi']}")
            print(f"   趋势: {t['trend']}")
            print(f"   支撑: {t['support']} | 阻力: {t['resistance']}")
        else:
            print(f"❌ 错误: {result['error']}")

    else:
        print(f"未知命令: {cmd}")


if __name__ == "__main__":
    main()
