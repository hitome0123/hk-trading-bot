#!/usr/bin/env python3
"""
实时追踪系统 - 热点猎手
盘中实时捕捉异动，整合富途API+技术指标+缩量上涨检测
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests
import numpy as np

try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False
    print("⚠️ 未安装futu-api，使用东财API备用")

from dingtalk_notifier import DingTalkNotifier


class TechnicalIndicator:
    """技术指标计算"""

    @staticmethod
    def calculate_ma(prices: List[float], period: int) -> float:
        """计算均线"""
        if len(prices) < period:
            return 0
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> float:
        """计算RSI"""
        if len(prices) < period + 1:
            return 50

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calculate_macd(prices: List[float]) -> Tuple[float, float, float]:
        """计算MACD (DIF, DEA, MACD柱)"""
        if len(prices) < 26:
            return 0, 0, 0

        # EMA12
        ema12 = prices[-12]
        for p in prices[-12:]:
            ema12 = ema12 * (11/13) + p * (2/13)

        # EMA26
        ema26 = prices[-26]
        for p in prices[-26:]:
            ema26 = ema26 * (25/27) + p * (2/27)

        dif = ema12 - ema26

        # DEA (9日EMA of DIF)
        dea = dif  # 简化处理
        macd = (dif - dea) * 2

        return dif, dea, macd

    @staticmethod
    def calculate_bollinger(prices: List[float], period: int = 20) -> Tuple[float, float, float]:
        """计算布林带 (上轨, 中轨, 下轨)"""
        if len(prices) < period:
            return 0, 0, 0

        ma = sum(prices[-period:]) / period
        std = np.std(prices[-period:])

        upper = ma + 2 * std
        lower = ma - 2 * std

        return upper, ma, lower

    @staticmethod
    def detect_volume_shrink_up(
        prices: List[float],
        volumes: List[float],
        current_price: float,
        current_volume: float
    ) -> Tuple[bool, str]:
        """
        检测缩量上涨
        条件: 价格上涨 + 成交量低于前5日均量的70%
        """
        if len(prices) < 5 or len(volumes) < 5:
            return False, ""

        prev_price = prices[-1]
        avg_volume = sum(volumes[-5:]) / 5

        is_price_up = current_price > prev_price
        is_volume_shrink = current_volume < avg_volume * 0.7
        price_change = (current_price - prev_price) / prev_price * 100

        if is_price_up and is_volume_shrink and price_change > 0.5:
            return True, f"缩量上涨 涨{price_change:.1f}% 量缩{(1-current_volume/avg_volume)*100:.0f}%"

        return False, ""


class RealtimeHunter:
    """实时热点猎手"""

    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.notifier = DingTalkNotifier()
        self.notified = set()  # 已推送记录，避免重复

        # 富途连接
        self.quote_ctx = None
        self.futu_connected = False

        # 监控股票池
        self.watchlist = [
            # AI
            'HK.09888', 'HK.00020', 'HK.01810',
            # 商业航天
            'HK.01045', 'HK.00471', 'HK.02357',
            # 新能源车
            'HK.01211', 'HK.02015', 'HK.09868', 'HK.09866',
            # 芯片
            'HK.00981', 'HK.01347',
            # 互联网
            'HK.09988', 'HK.00700', 'HK.03690', 'HK.09618', 'HK.01024',
            # 光伏
            'HK.03800', 'HK.00968',
        ]

        # 板块映射
        self.stock_sector = {
            'HK.09888': 'AI人工智能', 'HK.00020': 'AI人工智能', 'HK.01810': '机器人',
            'HK.01045': '商业航天', 'HK.00471': '商业航天', 'HK.02357': '商业航天',
            'HK.01211': '新能源汽车', 'HK.02015': '新能源汽车', 'HK.09868': '新能源汽车', 'HK.09866': '新能源汽车',
            'HK.00981': '芯片半导体', 'HK.01347': '芯片半导体',
            'HK.09988': '互联网', 'HK.00700': '互联网', 'HK.03690': '互联网', 'HK.09618': '互联网', 'HK.01024': '互联网',
            'HK.03800': '光伏', 'HK.00968': '光伏',
        }

        self.ti = TechnicalIndicator()

    def connect_futu(self) -> bool:
        """连接富途API"""
        if not HAS_FUTU:
            return False

        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            self.futu_connected = True
            print("✅ 富途API连接成功")
            return True
        except Exception as e:
            print(f"⚠️ 富途连接失败: {e}")
            self.futu_connected = False
            return False

    def disconnect_futu(self):
        """断开富途连接"""
        if self.quote_ctx:
            self.quote_ctx.close()

    def get_realtime_quote_futu(self, codes: List[str]) -> Dict[str, Dict]:
        """从富途获取实时行情"""
        if not self.futu_connected:
            return {}

        result = {}
        try:
            ret, data = self.quote_ctx.get_stock_quote(codes)
            if ret == RET_OK:
                for _, row in data.iterrows():
                    code = row['code']
                    result[code] = {
                        'price': row['last_price'],
                        'prev_close': row['prev_close_price'],
                        'high': row['high_price'],
                        'low': row['low_price'],
                        'volume': row['volume'],
                        'turnover': row['turnover'],
                        'change_pct': (row['last_price'] - row['prev_close_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                        'amplitude': (row['high_price'] - row['low_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                    }
        except Exception as e:
            print(f"富途行情获取失败: {e}")

        return result

    def get_kline_futu(self, code: str, days: int = 30) -> Tuple[List[float], List[float]]:
        """从富途获取K线数据"""
        prices = []
        volumes = []

        if not self.futu_connected:
            return prices, volumes

        try:
            ret, data, _ = self.quote_ctx.request_history_kline(
                code, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=days
            )
            if ret == RET_OK and not data.empty:
                prices = data['close'].tolist()
                volumes = data['volume'].tolist()
        except Exception as e:
            print(f"获取K线失败: {e}")

        return prices, volumes

    def get_realtime_quote_eastmoney(self, code: str) -> Dict:
        """从东财获取行情（备用）"""
        try:
            stock_code = code.replace('HK.', '')
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': f'116.{stock_code}',
                'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f60,f168,f169,f170,f171'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data'):
                d = data['data']
                price = d.get('f43', 0) / 1000
                prev = d.get('f60', 0) / 1000

                return {
                    'price': price,
                    'prev_close': prev,
                    'high': d.get('f44', 0) / 1000,
                    'low': d.get('f45', 0) / 1000,
                    'volume': d.get('f47', 0),
                    'change_pct': d.get('f170', 0) / 100,
                    'amplitude': d.get('f171', 0) / 100,
                    'vol_ratio': d.get('f50', 0) / 100,
                }
        except Exception as e:
            print(f"东财行情失败: {e}")

        return {}

    def calculate_entry_exit(self, quote: Dict, prices: List[float]) -> Dict:
        """计算进出场点位"""
        price = quote.get('price', 0)
        high = quote.get('high', price)
        low = quote.get('low', price)
        prev_close = quote.get('prev_close', price)

        if not price or price <= 0:
            return {}

        # 枢轴点
        pivot = (high + low + prev_close) / 3
        s1 = round(2 * pivot - high, 3)  # 支撑1
        s2 = round(pivot - (high - low), 3)  # 支撑2
        r1 = round(2 * pivot - low, 3)  # 压力1
        r2 = round(pivot + (high - low), 3)  # 压力2

        # 均线位置
        ma5 = self.ti.calculate_ma(prices, 5) if len(prices) >= 5 else price
        ma10 = self.ti.calculate_ma(prices, 10) if len(prices) >= 10 else price
        ma20 = self.ti.calculate_ma(prices, 20) if len(prices) >= 20 else price

        # RSI
        rsi = self.ti.calculate_rsi(prices + [price])

        # 布林带
        upper, mid, lower = self.ti.calculate_bollinger(prices + [price])

        # 综合买入位 = max(s1, lower, ma20) 附近
        buy_zone_low = round(max(s1, lower * 0.98, ma20 * 0.98), 2)
        buy_zone_high = round(s1 * 1.02, 2)

        # 综合卖出位 = min(r1, upper)
        sell_zone_low = round(r1, 2)
        sell_zone_high = round(min(r2, upper), 2)

        # 止损 = s2 下方2%
        stop_loss = round(s2 * 0.98, 2)

        # 预期收益
        expected_profit = round((sell_zone_low - buy_zone_high) / buy_zone_high * 100, 1) if buy_zone_high > 0 else 0

        # 信号强度
        signal_strength = 0
        reasons = []

        # RSI超卖加分
        if rsi < 30:
            signal_strength += 2
            reasons.append("RSI超卖")
        elif rsi < 40:
            signal_strength += 1
            reasons.append("RSI偏低")

        # 价格在支撑位附近加分
        if price <= s1 * 1.02:
            signal_strength += 2
            reasons.append("接近支撑")

        # MA多头排列加分
        if ma5 > ma10 > ma20:
            signal_strength += 1
            reasons.append("均线多头")

        # 涨幅适中加分
        change = quote.get('change_pct', 0)
        if 0 < change < 5:
            signal_strength += 1
            reasons.append("涨幅适中")

        stars = '⭐⭐⭐' if signal_strength >= 4 else '⭐⭐' if signal_strength >= 2 else '⭐'

        return {
            'buy_zone': (buy_zone_low, buy_zone_high),
            'sell_zone': (sell_zone_low, sell_zone_high),
            'stop_loss': stop_loss,
            'expected_profit': expected_profit,
            'rsi': round(rsi, 1),
            'ma5': round(ma5, 2),
            'ma10': round(ma10, 2),
            'ma20': round(ma20, 2),
            'signal_strength': signal_strength,
            'stars': stars,
            'reasons': reasons,
        }

    def scan_all(self) -> List[Dict]:
        """扫描所有监控股票"""
        results = []

        # 获取实时行情
        if self.futu_connected:
            quotes = self.get_realtime_quote_futu(self.watchlist)
        else:
            quotes = {}
            for code in self.watchlist:
                q = self.get_realtime_quote_eastmoney(code)
                if q:
                    quotes[code] = q

        # 逐个分析
        for code in self.watchlist:
            quote = quotes.get(code)
            if not quote:
                continue

            # 获取历史K线
            prices, volumes = self.get_kline_futu(code) if self.futu_connected else ([], [])

            # 计算进出场点位
            entry_exit = self.calculate_entry_exit(quote, prices)

            # 检测缩量上涨
            is_shrink_up, shrink_reason = False, ""
            if prices and volumes:
                is_shrink_up, shrink_reason = self.ti.detect_volume_shrink_up(
                    prices, volumes, quote['price'], quote.get('volume', 0)
                )

            # 构建结果
            stock_name = self.get_stock_name(code)
            sector = self.stock_sector.get(code, '')

            result = {
                'code': code.replace('HK.', ''),
                'name': stock_name,
                'sector': sector,
                'price': quote['price'],
                'change_pct': quote.get('change_pct', 0),
                'volume': quote.get('volume', 0),
                'is_shrink_up': is_shrink_up,
                'shrink_reason': shrink_reason,
                **entry_exit,
            }

            # 有效结果才加入
            if entry_exit:
                results.append(result)

        # 排序：缩量上涨优先，然后按信号强度
        results.sort(key=lambda x: (x.get('is_shrink_up', False), x.get('signal_strength', 0)), reverse=True)

        return results

    def get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        names = {
            'HK.09888': '百度', 'HK.00020': '商汤', 'HK.01810': '小米',
            'HK.01045': '亚太卫星', 'HK.00471': '中播数据', 'HK.02357': '中航科工',
            'HK.01211': '比亚迪', 'HK.02015': '理想', 'HK.09868': '小鹏', 'HK.09866': '蔚来',
            'HK.00981': '中芯国际', 'HK.01347': '华虹',
            'HK.09988': '阿里', 'HK.00700': '腾讯', 'HK.03690': '美团', 'HK.09618': '京东', 'HK.01024': '快手',
            'HK.03800': '协鑫科技', 'HK.00968': '信义光能',
        }
        return names.get(code, code)

    def format_alert(self, results: List[Dict]) -> str:
        """格式化预警信息"""
        now = datetime.now().strftime('%H:%M:%S')

        content = f"""### 🎯 实时追踪 {now}

---

#### 🔥 缩量上涨 (首推)

"""
        shrink_up = [r for r in results if r.get('is_shrink_up')]
        if shrink_up:
            for r in shrink_up[:3]:
                content += f"**{r['name']}** ({r['code']}) - {r['sector']}\n"
                content += f"- 现价: {r['price']:.2f} | 涨幅: {r['change_pct']:+.1f}%\n"
                content += f"- 📍 {r['shrink_reason']}\n"
                content += f"- 买入区: {r['buy_zone'][0]:.2f}-{r['buy_zone'][1]:.2f}\n"
                content += f"- 卖出区: {r['sell_zone'][0]:.2f}-{r['sell_zone'][1]:.2f}\n\n"
        else:
            content += "暂无符合条件的标的\n\n"

        content += """---

#### 📊 全部信号

| 股票 | 现价 | 涨幅 | RSI | 买入位 | 卖出位 | 信号 |
|------|------|------|-----|--------|--------|------|
"""
        for r in results[:10]:
            stars = r.get('stars', '')
            buy = f"{r['buy_zone'][0]:.2f}" if r.get('buy_zone') else '-'
            sell = f"{r['sell_zone'][0]:.2f}" if r.get('sell_zone') else '-'
            rsi = r.get('rsi', 0)
            content += f"| {r['name']} | {r['price']:.2f} | {r['change_pct']:+.1f}% | {rsi:.0f} | {buy} | {sell} | {stars} |\n"

        content += """
---

#### 📝 技术指标说明

- **RSI < 30**: 超卖区，可能反弹
- **RSI > 70**: 超买区，注意风险
- **缩量上涨**: 量价背离，可能蓄势待发
- **信号⭐⭐⭐**: 多指标共振，强烈关注

---

*数据来源: 富途API + 东财*
"""
        return content

    def run_once(self, push: bool = True) -> str:
        """运行一次扫描"""
        print(f"🔍 扫描中... {datetime.now().strftime('%H:%M:%S')}")

        results = self.scan_all()
        alert = self.format_alert(results)

        print(alert)

        if push and results:
            self.notifier.send_markdown("🎯 实时追踪", alert)
            print("✅ 已推送")

        return alert

    def run_loop(self, interval: int = 30):
        """循环监控"""
        print(f"🚀 实时追踪系统启动，间隔 {interval} 秒")
        print("=" * 50)

        # 连接富途
        self.connect_futu()

        try:
            while True:
                try:
                    self.run_once(push=True)
                except Exception as e:
                    print(f"扫描出错: {e}")

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n⏹️ 停止监控")
        finally:
            self.disconnect_futu()


def main():
    import sys
    hunter = RealtimeHunter()

    if 'loop' in sys.argv:
        interval = 30
        for arg in sys.argv:
            if arg.isdigit():
                interval = int(arg)
        hunter.run_loop(interval)
    else:
        hunter.connect_futu()
        try:
            hunter.run_once(push='push' in sys.argv)
        finally:
            hunter.disconnect_futu()


if __name__ == '__main__':
    main()
