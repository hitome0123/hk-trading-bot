#!/usr/bin/env python3
"""
进出场信号系统
基于技术指标计算最佳买卖点位
支持富途API获取实时数据和历史K线
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime
from typing import Dict, List, Tuple, Optional
import requests
import numpy as np

try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False

from dingtalk_notifier import DingTalkNotifier


class SignalCalculator:
    """信号计算器"""

    def __init__(self):
        self.quote_ctx = None
        self.connected = False
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def connect(self) -> bool:
        """连接富途"""
        if not HAS_FUTU:
            print("⚠️ 未安装futu-api")
            return False

        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            self.connected = True
            print("✅ 富途连接成功")
            return True
        except Exception as e:
            print(f"⚠️ 富途连接失败: {e}")
            return False

    def disconnect(self):
        """断开连接"""
        if self.quote_ctx:
            self.quote_ctx.close()

    def get_kline(self, code: str, days: int = 60) -> List[Dict]:
        """获取K线数据"""
        klines = []

        if self.connected:
            try:
                ret, data, _ = self.quote_ctx.request_history_kline(
                    code, ktype=KLType.K_DAY, autype=AuType.QFQ, max_count=days
                )
                if ret == RET_OK and not data.empty:
                    for _, row in data.iterrows():
                        klines.append({
                            'date': row['time_key'],
                            'open': row['open'],
                            'high': row['high'],
                            'low': row['low'],
                            'close': row['close'],
                            'volume': row['volume'],
                            'turnover': row['turnover'],
                        })
            except Exception as e:
                print(f"获取K线失败: {e}")

        return klines

    def get_realtime_quote(self, code: str) -> Dict:
        """获取实时行情"""
        if self.connected:
            try:
                ret, data = self.quote_ctx.get_stock_quote([code])
                if ret == RET_OK and not data.empty:
                    row = data.iloc[0]
                    return {
                        'code': code,
                        'name': row.get('name', code),
                        'price': row['last_price'],
                        'prev_close': row['prev_close_price'],
                        'open': row['open_price'],
                        'high': row['high_price'],
                        'low': row['low_price'],
                        'volume': row['volume'],
                        'turnover': row['turnover'],
                        'change_pct': (row['last_price'] - row['prev_close_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                    }
            except Exception as e:
                print(f"获取行情失败: {e}")

        # 备用：东财API
        return self.get_quote_eastmoney(code)

    def get_quote_eastmoney(self, code: str) -> Dict:
        """东财API备用"""
        try:
            stock_code = code.replace('HK.', '')
            url = "https://push2.eastmoney.com/api/qt/stock/get"
            params = {
                'secid': f'116.{stock_code}',
                'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f58,f60,f168,f169,f170,f171'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data.get('data'):
                d = data['data']
                price = d.get('f43', 0) / 1000
                prev = d.get('f60', 0) / 1000

                return {
                    'code': code,
                    'name': d.get('f58', code),
                    'price': price,
                    'prev_close': prev,
                    'open': d.get('f46', 0) / 1000,
                    'high': d.get('f44', 0) / 1000,
                    'low': d.get('f45', 0) / 1000,
                    'volume': d.get('f47', 0),
                    'change_pct': d.get('f170', 0) / 100,
                }
        except:
            pass
        return {}

    # ========== 技术指标计算 ==========

    def calc_ma(self, closes: List[float], period: int) -> List[float]:
        """计算移动平均线"""
        ma = []
        for i in range(len(closes)):
            if i < period - 1:
                ma.append(None)
            else:
                ma.append(sum(closes[i-period+1:i+1]) / period)
        return ma

    def calc_ema(self, closes: List[float], period: int) -> List[float]:
        """计算指数移动平均"""
        ema = [closes[0]]
        multiplier = 2 / (period + 1)
        for i in range(1, len(closes)):
            ema.append(closes[i] * multiplier + ema[-1] * (1 - multiplier))
        return ema

    def calc_rsi(self, closes: List[float], period: int = 14) -> List[float]:
        """计算RSI"""
        rsi = [50] * period

        for i in range(period, len(closes)):
            gains = []
            losses = []
            for j in range(i - period + 1, i + 1):
                diff = closes[j] - closes[j - 1]
                if diff > 0:
                    gains.append(diff)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(diff))

            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period

            if avg_loss == 0:
                rsi.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi.append(100 - (100 / (1 + rs)))

        return rsi

    def calc_macd(self, closes: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """计算MACD"""
        ema12 = self.calc_ema(closes, 12)
        ema26 = self.calc_ema(closes, 26)

        dif = [ema12[i] - ema26[i] for i in range(len(closes))]
        dea = self.calc_ema(dif, 9)
        macd = [(dif[i] - dea[i]) * 2 for i in range(len(closes))]

        return dif, dea, macd

    def calc_bollinger(self, closes: List[float], period: int = 20) -> Tuple[List[float], List[float], List[float]]:
        """计算布林带"""
        upper, mid, lower = [], [], []

        for i in range(len(closes)):
            if i < period - 1:
                upper.append(None)
                mid.append(None)
                lower.append(None)
            else:
                window = closes[i-period+1:i+1]
                ma = sum(window) / period
                std = np.std(window)
                mid.append(ma)
                upper.append(ma + 2 * std)
                lower.append(ma - 2 * std)

        return upper, mid, lower

    def calc_kdj(self, highs: List[float], lows: List[float], closes: List[float], n: int = 9) -> Tuple[List[float], List[float], List[float]]:
        """计算KDJ"""
        k, d, j = [], [], []

        for i in range(len(closes)):
            if i < n - 1:
                k.append(50)
                d.append(50)
                j.append(50)
            else:
                hn = max(highs[i-n+1:i+1])
                ln = min(lows[i-n+1:i+1])
                if hn == ln:
                    rsv = 50
                else:
                    rsv = (closes[i] - ln) / (hn - ln) * 100

                if i == n - 1:
                    k_val = rsv
                    d_val = rsv
                else:
                    k_val = 2/3 * k[-1] + 1/3 * rsv
                    d_val = 2/3 * d[-1] + 1/3 * k_val

                j_val = 3 * k_val - 2 * d_val
                k.append(k_val)
                d.append(d_val)
                j.append(j_val)

        return k, d, j

    def find_support_resistance(self, klines: List[Dict]) -> Dict:
        """寻找支撑位和压力位"""
        if len(klines) < 20:
            return {}

        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]

        current = closes[-1]

        # 最近的高低点
        recent_high = max(highs[-10:])
        recent_low = min(lows[-10:])

        # 枢轴点
        pivot = (klines[-1]['high'] + klines[-1]['low'] + klines[-1]['close']) / 3
        s1 = 2 * pivot - klines[-1]['high']
        s2 = pivot - (klines[-1]['high'] - klines[-1]['low'])
        r1 = 2 * pivot - klines[-1]['low']
        r2 = pivot + (klines[-1]['high'] - klines[-1]['low'])

        # 均线作为动态支撑压力
        ma5 = sum(closes[-5:]) / 5
        ma10 = sum(closes[-10:]) / 10
        ma20 = sum(closes[-20:]) / 20

        # 布林带
        upper, mid, lower = self.calc_bollinger(closes)

        # 综合支撑位（取多个支撑中的较高者）
        supports = [s for s in [s1, s2, recent_low, lower[-1], ma20] if s and s < current]
        resistances = [r for r in [r1, r2, recent_high, upper[-1]] if r and r > current]

        return {
            'pivot': round(pivot, 3),
            's1': round(s1, 3),
            's2': round(s2, 3),
            'r1': round(r1, 3),
            'r2': round(r2, 3),
            'recent_high': round(recent_high, 3),
            'recent_low': round(recent_low, 3),
            'ma5': round(ma5, 3),
            'ma10': round(ma10, 3),
            'ma20': round(ma20, 3),
            'boll_upper': round(upper[-1], 3) if upper[-1] else None,
            'boll_lower': round(lower[-1], 3) if lower[-1] else None,
            'best_support': round(max(supports), 3) if supports else None,
            'best_resistance': round(min(resistances), 3) if resistances else None,
        }

    def detect_shrink_up(self, klines: List[Dict]) -> Tuple[bool, str]:
        """检测缩量上涨"""
        if len(klines) < 6:
            return False, ""

        # 今日数据
        today = klines[-1]
        yesterday = klines[-2]

        # 5日平均成交量
        avg_vol = sum([k['volume'] for k in klines[-6:-1]]) / 5

        # 今日涨幅
        change = (today['close'] - yesterday['close']) / yesterday['close'] * 100

        # 今日成交量相对均量
        vol_ratio = today['volume'] / avg_vol if avg_vol > 0 else 1

        # 缩量上涨条件: 涨幅>0.5% 且 成交量<70%均量
        if change > 0.5 and vol_ratio < 0.7:
            return True, f"涨{change:.1f}% 量缩{(1-vol_ratio)*100:.0f}%"

        return False, ""

    def generate_signal(self, code: str) -> Dict:
        """生成完整的进出场信号"""
        # 获取数据
        quote = self.get_realtime_quote(code)
        if not quote:
            return {'error': '获取行情失败'}

        klines = self.get_kline(code, 60)
        if len(klines) < 20:
            return {'error': 'K线数据不足'}

        closes = [k['close'] for k in klines]
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        volumes = [k['volume'] for k in klines]

        # 计算指标
        rsi = self.calc_rsi(closes)[-1]
        dif, dea, macd = self.calc_macd(closes)
        k, d, j = self.calc_kdj(highs, lows, closes)

        # 支撑压力
        levels = self.find_support_resistance(klines)

        # 缩量上涨检测
        is_shrink_up, shrink_reason = self.detect_shrink_up(klines)

        # 信号评估
        signals = []
        score = 0

        # RSI信号
        if rsi < 30:
            signals.append(('买入', 'RSI超卖', 2))
            score += 2
        elif rsi < 40:
            signals.append(('观望', 'RSI偏低', 1))
            score += 1
        elif rsi > 70:
            signals.append(('卖出', 'RSI超买', -2))
            score -= 2

        # MACD信号
        if dif[-1] > dea[-1] and dif[-2] <= dea[-2]:
            signals.append(('买入', 'MACD金叉', 2))
            score += 2
        elif dif[-1] < dea[-1] and dif[-2] >= dea[-2]:
            signals.append(('卖出', 'MACD死叉', -2))
            score -= 2

        # KDJ信号
        if j[-1] < 20:
            signals.append(('买入', 'KDJ超卖', 1))
            score += 1
        elif j[-1] > 80:
            signals.append(('卖出', 'KDJ超买', -1))
            score -= 1

        # 缩量上涨（高权重）
        if is_shrink_up:
            signals.append(('买入', shrink_reason, 3))
            score += 3

        # 均线排列
        if levels['ma5'] > levels['ma10'] > levels['ma20']:
            signals.append(('持有', '均线多头排列', 1))
            score += 1
        elif levels['ma5'] < levels['ma10'] < levels['ma20']:
            signals.append(('观望', '均线空头排列', -1))
            score -= 1

        # 综合判断
        if score >= 4:
            action = '强烈买入'
            stars = '⭐⭐⭐'
        elif score >= 2:
            action = '建议买入'
            stars = '⭐⭐'
        elif score >= 0:
            action = '观望'
            stars = '⭐'
        elif score >= -2:
            action = '建议卖出'
            stars = '⚠️'
        else:
            action = '强烈卖出'
            stars = '🔴'

        # 买入区间
        buy_low = levels.get('best_support', levels['s1'])
        buy_high = round(buy_low * 1.02, 2) if buy_low else None

        # 卖出区间
        sell_low = levels.get('best_resistance', levels['r1'])
        sell_high = round(sell_low * 1.02, 2) if sell_low else None

        # 止损
        stop_loss = round(levels['s2'] * 0.98, 2) if levels.get('s2') else None

        # 预期收益
        expected_profit = round((sell_low - buy_high) / buy_high * 100, 1) if buy_high and sell_low else 0

        return {
            'code': code.replace('HK.', ''),
            'name': quote.get('name', code),
            'price': quote['price'],
            'change_pct': quote.get('change_pct', 0),

            # 技术指标
            'rsi': round(rsi, 1),
            'macd': round(macd[-1], 4),
            'kdj_j': round(j[-1], 1),

            # 支撑压力
            'levels': levels,

            # 缩量上涨
            'is_shrink_up': is_shrink_up,
            'shrink_reason': shrink_reason,

            # 信号
            'signals': signals,
            'score': score,
            'action': action,
            'stars': stars,

            # 交易建议
            'buy_zone': (buy_low, buy_high),
            'sell_zone': (sell_low, sell_high),
            'stop_loss': stop_loss,
            'expected_profit': expected_profit,
        }

    def format_signal(self, signal: Dict) -> str:
        """格式化信号报告"""
        if signal.get('error'):
            return f"❌ {signal['error']}"

        content = f"""### 📍 进出场信号 - {signal['name']} ({signal['code']})

---

#### 📊 当前状态

- **现价:** {signal['price']:.2f}
- **涨跌:** {signal['change_pct']:+.1f}%
- **综合判断:** {signal['action']} {signal['stars']}

---

#### 📈 技术指标

| 指标 | 数值 | 状态 |
|------|------|------|
| RSI(14) | {signal['rsi']:.1f} | {'超卖' if signal['rsi'] < 30 else '超买' if signal['rsi'] > 70 else '正常'} |
| MACD | {signal['macd']:.4f} | {'多头' if signal['macd'] > 0 else '空头'} |
| KDJ-J | {signal['kdj_j']:.1f} | {'超卖' if signal['kdj_j'] < 20 else '超买' if signal['kdj_j'] > 80 else '正常'} |
| MA5 | {signal['levels']['ma5']:.2f} | - |
| MA10 | {signal['levels']['ma10']:.2f} | - |
| MA20 | {signal['levels']['ma20']:.2f} | - |

"""
        if signal['is_shrink_up']:
            content += f"""
#### 🔥 缩量上涨信号

**{signal['shrink_reason']}** - 量价背离，蓄势待发！

"""

        content += f"""---

#### 🎯 交易建议

| 项目 | 价位 | 说明 |
|------|------|------|
| 📗 买入区 | **{signal['buy_zone'][0]:.2f} - {signal['buy_zone'][1]:.2f}** | 支撑位附近低吸 |
| 📕 卖出区 | **{signal['sell_zone'][0]:.2f} - {signal['sell_zone'][1]:.2f}** | 压力位附近高抛 |
| 🛑 止损位 | **{signal['stop_loss']:.2f}** | 跌破立即出局 |
| 💰 预期收益 | **{signal['expected_profit']:+.1f}%** | - |

---

#### 📋 信号明细

"""
        for action, reason, weight in signal['signals']:
            icon = '🟢' if weight > 0 else '🔴' if weight < 0 else '🟡'
            content += f"- {icon} **{action}**: {reason}\n"

        content += f"""
---

#### 📐 关键价位

- 枢轴点: {signal['levels']['pivot']:.2f}
- 支撑1: {signal['levels']['s1']:.2f} | 支撑2: {signal['levels']['s2']:.2f}
- 压力1: {signal['levels']['r1']:.2f} | 压力2: {signal['levels']['r2']:.2f}
- 近期高点: {signal['levels']['recent_high']:.2f}
- 近期低点: {signal['levels']['recent_low']:.2f}

---

*数据来源: 富途API | 更新时间: {datetime.now().strftime('%H:%M:%S')}*
"""
        return content


def main():
    import sys

    calc = SignalCalculator()
    calc.connect()

    try:
        # 分析指定股票
        if len(sys.argv) > 1:
            code = sys.argv[1]
            if not code.startswith('HK.'):
                code = f'HK.{code}'

            print(f"📊 分析 {code}...")
            signal = calc.generate_signal(code)
            report = calc.format_signal(signal)
            print(report)

            if 'push' in sys.argv:
                notifier = DingTalkNotifier()
                notifier.send_markdown(f"📍 {signal.get('name', code)}", report)
                print("✅ 已推送")
        else:
            # 批量分析热门股
            watchlist = ['HK.09888', 'HK.00700', 'HK.01810', 'HK.01211', 'HK.00981']
            print("📊 批量分析热门股...\n")

            for code in watchlist:
                signal = calc.generate_signal(code)
                if not signal.get('error'):
                    print(f"{signal['name']} ({signal['code']}): {signal['action']} {signal['stars']}")
                    print(f"  买入: {signal['buy_zone'][0]:.2f}-{signal['buy_zone'][1]:.2f}")
                    print(f"  卖出: {signal['sell_zone'][0]:.2f}-{signal['sell_zone'][1]:.2f}")
                    if signal['is_shrink_up']:
                        print(f"  🔥 {signal['shrink_reason']}")
                    print()

    finally:
        calc.disconnect()


if __name__ == '__main__':
    main()
