#!/usr/bin/env python3
"""
港股智能做T推荐系统 - 完整版
包含：RSI、MACD、量比、社交热度等综合指标
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime
from typing import Dict, List, Optional
import requests
import time
import json

try:
    from hk_trading_bot.data_providers.futu_provider import FutuProvider
    import futu as ft
    HAS_FUTU = True
except:
    HAS_FUTU = False
    print("警告: 富途API未安装")


class SmartTTradingAdvisor:
    """智能做T交易顾问 - 完整技术分析"""

    def __init__(self):
        self.provider = None
        self.connected = False
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
        }

    def connect(self):
        """连接富途API"""
        if not HAS_FUTU:
            return False
        try:
            self.provider = FutuProvider()
            self.provider.connect()
            self.connected = True
            print("✅ 富途API已连接")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False

    def disconnect(self):
        if self.provider:
            self.provider.disconnect()

    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        if len(closes) < period + 1:
            return 50.0

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, closes: List[float]) -> Dict:
        """计算MACD指标"""
        result = {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'neutral'}

        if len(closes) < 26:
            return result

        # 计算EMA
        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values[-1]

        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd = ema12 - ema26

        # Signal line (9-day EMA of MACD)
        macd_line = []
        for i in range(26, len(closes)):
            e12 = ema(closes[:i+1], 12)
            e26 = ema(closes[:i+1], 26)
            macd_line.append(e12 - e26)

        signal = ema(macd_line, 9) if len(macd_line) >= 9 else 0
        histogram = macd - signal

        result['macd'] = round(macd, 2)
        result['signal'] = round(signal, 2)
        result['histogram'] = round(histogram, 2)

        # 判断趋势
        if histogram > 0 and macd > signal:
            result['trend'] = 'bullish'
        elif histogram < 0 and macd < signal:
            result['trend'] = 'bearish'
        else:
            result['trend'] = 'neutral'

        return result

    def calculate_volume_ratio(self, volumes: List[float]) -> Dict:
        """计算量比"""
        result = {'volume_ratio': 0, 'status': 'normal'}

        if len(volumes) < 5:
            return result

        current_volume = volumes[-1]
        avg_volume = sum(volumes[-6:-1]) / 5  # 前5日平均

        if avg_volume > 0:
            volume_ratio = current_volume / avg_volume
            result['volume_ratio'] = round(volume_ratio, 2)

            if volume_ratio >= 2.0:
                result['status'] = 'heavy_volume'  # 放量
            elif volume_ratio <= 0.5:
                result['status'] = 'low_volume'  # 缩量
            else:
                result['status'] = 'normal'

        return result

    def get_social_heat(self, code: str, name: str) -> Dict:
        """获取社交媒体热度"""
        result = {
            'xueqiu_score': 0,
            'eastmoney_score': 0,
            'total_score': 0,
            'hot_level': 'cold'
        }

        try:
            # 雪球热度（简化版）
            stock_code = code.replace('HK.', '')
            xq_url = f"https://xueqiu.com/query/v1/symbol/search/status"
            params = {'q': stock_code, 'count': 5}

            try:
                resp = requests.get(xq_url, params=params, headers=self.headers, timeout=5)
                data = resp.json()
                if 'list' in data and len(data['list']) > 0:
                    result['xueqiu_score'] = min(len(data['list']) * 20, 50)
            except:
                pass

            # 东财股吧热度（简化版）
            try:
                em_url = f"https://guba.eastmoney.com/list,hk{stock_code}.html"
                resp = requests.get(em_url, headers=self.headers, timeout=5)
                if resp.status_code == 200 and '阅读' in resp.text:
                    result['eastmoney_score'] = 30  # 有讨论
            except:
                pass

            # 总分
            result['total_score'] = result['xueqiu_score'] + result['eastmoney_score']

            if result['total_score'] >= 60:
                result['hot_level'] = 'hot'
            elif result['total_score'] >= 30:
                result['hot_level'] = 'warm'
            else:
                result['hot_level'] = 'cold'

        except Exception as e:
            pass

        return result

    def get_technical_analysis(self, code: str) -> Dict:
        """获取完整技术分析"""
        result = {
            'rsi': 50,
            'rsi_signal': 'neutral',
            'macd': {},
            'volume': {},
            'klines': []
        }

        if not self.connected:
            return result

        try:
            # 订阅
            ret_sub, err = self.provider.quote_ctx.subscribe([code], [ft.SubType.QUOTE, ft.SubType.K_DAY], subscribe_push=False)

            # 获取K线数据
            ret, data = self.provider.quote_ctx.get_cur_kline(code, 60, ft.KLType.K_DAY)
            if ret != ft.RET_OK or data.empty:
                return result

            klines = data.to_dict('records')
            result['klines'] = klines

            closes = [k['close'] for k in klines]
            volumes = [k['volume'] for k in klines]

            # 计算RSI
            rsi = self.calculate_rsi(closes)
            result['rsi'] = round(rsi, 2)

            if rsi <= 30:
                result['rsi_signal'] = 'oversold'  # 超卖
            elif rsi >= 70:
                result['rsi_signal'] = 'overbought'  # 超买
            elif 30 < rsi <= 45:
                result['rsi_signal'] = 'buy_zone'  # 买入区
            elif 55 <= rsi < 70:
                result['rsi_signal'] = 'sell_zone'  # 卖出区
            else:
                result['rsi_signal'] = 'neutral'

            # 计算MACD
            result['macd'] = self.calculate_macd(closes)

            # 计算量比
            result['volume'] = self.calculate_volume_ratio(volumes)

        except Exception as e:
            print(f"技术分析失败: {e}")

        return result

    def analyze_stock(self, code: str, name: str) -> Dict:
        """综合分析股票做T机会"""
        result = {
            'code': code.replace('HK.', ''),
            'name': name,
            'price': 0,
            'change_pct': 0,
            'amplitude': 0,
            'volume': 0,
            'score': 0,
            'buy_price': 0,
            'sell_price': 0,
            'stop_loss': 0,
            'expected_profit': 0,
            'technical': {},
            'social_heat': {},
            'reasons': [],
            'strategy': '',
            'suitable': False
        }

        if not self.connected:
            return result

        try:
            # 订阅
            ret_sub, err = self.provider.quote_ctx.subscribe([code], [ft.SubType.QUOTE, ft.SubType.K_DAY], subscribe_push=False)

            # 获取实时行情
            ret, data = self.provider.quote_ctx.get_stock_quote([code])
            if ret != ft.RET_OK or data.empty:
                return result

            row = data.iloc[0]
            price = row['last_price']
            prev_close = row['prev_close_price']
            high = row['high_price']
            low = row['low_price']
            volume = row['volume']

            result['price'] = price
            result['change_pct'] = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            result['amplitude'] = (high - low) / prev_close * 100 if prev_close > 0 else 0
            result['volume'] = volume / 1_000_000

            # 初始化technical
            technical = {'rsi': 50, 'rsi_signal': 'neutral', 'macd': {}, 'volume': {}}

            # 技术分析（获取K线数据）
            try:
                ret_k, kdata = self.provider.quote_ctx.get_cur_kline(code, 60, ft.KLType.K_DAY)
                if ret_k == ft.RET_OK and not kdata.empty:
                    klines = kdata.to_dict('records')
                    closes = [k['close'] for k in klines]
                    volumes = [k['volume'] for k in klines]

                    # 计算技术指标
                    technical = {
                        'rsi': self.calculate_rsi(closes),
                        'rsi_signal': 'neutral',
                        'macd': self.calculate_macd(closes),
                        'volume': self.calculate_volume_ratio(volumes)
                    }

                    # RSI信号
                    rsi = technical['rsi']
                    if rsi <= 30:
                        technical['rsi_signal'] = 'oversold'
                    elif rsi >= 70:
                        technical['rsi_signal'] = 'overbought'
                    elif 30 < rsi <= 45:
                        technical['rsi_signal'] = 'buy_zone'
                    elif 55 <= rsi < 70:
                        technical['rsi_signal'] = 'sell_zone'

                    result['technical'] = technical
                else:
                    result['technical'] = {'rsi': 50, 'rsi_signal': 'neutral', 'macd': {}, 'volume': {}}
            except:
                result['technical'] = {'rsi': 50, 'rsi_signal': 'neutral', 'macd': {}, 'volume': {}}

            # 社交热度
            social = self.get_social_heat(code, name)
            result['social_heat'] = social

            # 计算支撑压力位
            pivot = (high + low + prev_close) / 3
            support1 = 2 * pivot - high
            resistance1 = 2 * pivot - low
            support2 = pivot - (high - low)

            result['buy_price'] = round(support1, 2)
            result['sell_price'] = round(resistance1, 2)
            result['stop_loss'] = round(support2, 2)

            if result['buy_price'] > 0:
                result['expected_profit'] = (result['sell_price'] - result['buy_price']) / result['buy_price'] * 100

            # === 综合评分系统 ===
            score = 0
            reasons = []

            # 1. 振幅评分（30分）
            if result['amplitude'] >= 4:
                score += 30
                reasons.append(f"振幅大({result['amplitude']:.1f}%)")
            elif result['amplitude'] >= 3:
                score += 25
                reasons.append(f"振幅良好({result['amplitude']:.1f}%)")
            elif result['amplitude'] >= 2:
                score += 15
            elif result['amplitude'] >= 1.5:
                score += 10

            # 2. RSI评分（20分）
            rsi = technical.get('rsi', 50)
            rsi_signal = technical.get('rsi_signal', 'neutral')
            if rsi_signal == 'oversold':
                score += 20
                reasons.append(f"RSI超卖({rsi:.0f})")
            elif rsi_signal == 'buy_zone':
                score += 15
                reasons.append(f"RSI买入区({rsi:.0f})")
            elif rsi_signal == 'neutral':
                score += 10
            elif rsi_signal == 'overbought':
                score -= 10
                reasons.append(f"RSI超买({rsi:.0f})")

            # 3. MACD评分（15分）
            macd = technical.get('macd', {})
            macd_trend = macd.get('trend', 'neutral')
            if macd_trend == 'bullish':
                score += 15
                reasons.append("MACD金叉")
            elif macd_trend == 'bearish':
                score -= 10
                reasons.append("MACD死叉")

            # 4. 量比评分（15分）
            vol_info = technical.get('volume', {})
            vol_ratio = vol_info.get('volume_ratio', 0)
            vol_status = vol_info.get('status', 'normal')
            if vol_status == 'heavy_volume' and result['change_pct'] > 0:
                score += 15
                reasons.append(f"放量上涨(量比{vol_ratio:.1f})")
            elif vol_status == 'heavy_volume':
                score += 10
                reasons.append(f"放量({vol_ratio:.1f})")
            elif vol_status == 'low_volume' and result['change_pct'] < 0:
                score += 5
                reasons.append(f"缩量回调(量比{vol_ratio:.1f})")

            # 5. 涨幅位置（10分）
            if -3 < result['change_pct'] < 1:
                score += 10
                reasons.append("涨幅适中")
            elif result['change_pct'] > 5:
                score -= 10
                reasons.append("涨幅过大")

            # 6. 社交热度（10分）
            heat_score = social.get('total_score', 0)
            heat_level = social.get('hot_level', 'cold')
            if heat_level == 'hot':
                score += 10
                reasons.append("社交热度高")
            elif heat_level == 'warm':
                score += 5
                reasons.append("有热度")

            result['score'] = min(score, 100)
            result['reasons'] = reasons
            result['suitable'] = score >= 60

            # 生成策略建议
            if result['suitable']:
                if rsi_signal in ['oversold', 'buy_zone'] and macd_trend == 'bullish':
                    result['strategy'] = f"🔥 强烈推荐：RSI在低位且MACD金叉，在{result['buy_price']:.2f}附近低吸，目标{result['sell_price']:.2f}"
                elif price < support1 * 1.02:
                    result['strategy'] = f"📈 建议买入：接近支撑位{result['buy_price']:.2f}，可低吸，目标{result['sell_price']:.2f}"
                else:
                    result['strategy'] = f"⚠️ 等待回调：等价格回到{result['buy_price']:.2f}附近再介入"
            else:
                if rsi_signal == 'overbought':
                    result['strategy'] = "❌ 不建议：RSI超买，避免追高"
                elif result['amplitude'] < 1.5:
                    result['strategy'] = "❌ 不建议：波动太小，不适合做T"
                else:
                    result['strategy'] = "⚠️ 观望：条件不够理想"

        except Exception as e:
            print(f"分析{name}失败: {e}")

        return result


def run_smart_t_analysis():
    """运行智能做T分析"""
    # 优质大盘股池
    quality_stocks = [
        ('HK.09988', '阿里巴巴'),
        ('HK.00700', '腾讯控股'),
        ('HK.03690', '美团'),
        ('HK.01810', '小米集团'),
        ('HK.01211', '比亚迪'),
        ('HK.09618', '京东集团'),
        ('HK.09888', '百度'),
        ('HK.01024', '快手'),
        ('HK.02015', '理想汽车'),
        ('HK.09868', '小鹏汽车'),
        ('HK.09866', '蔚来'),
        ('HK.00981', '中芯国际'),
        ('HK.01347', '华虹半导体'),
    ]

    advisor = SmartTTradingAdvisor()

    if not advisor.connect():
        print("❌ 无法连接富途API")
        return

    try:
        print("=" * 100)
        print("🎯 港股智能做T推荐系统 - 完整技术分析版")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print()

        candidates = []

        print("🔍 正在分析股票...")
        for i, (code, name) in enumerate(quality_stocks, 1):
            print(f"  [{i}/{len(quality_stocks)}] {name}...", end='\r')
            result = advisor.analyze_stock(code, name)
            if result['score'] > 0:
                candidates.append(result)
            time.sleep(0.5)  # 避免请求过快

        print("\n")

        # 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)

        # 输出推荐列表
        print("📊 做T推荐标的（按评分排序）")
        print("-" * 100)
        print(f"{'排名':<4} {'股票':<10} {'代码':<6} {'现价':<8} {'涨幅':<8} {'振幅':<8} {'RSI':<6} {'量比':<6} {'热度':<6} {'评分':<6}")
        print("-" * 100)

        for i, c in enumerate(candidates, 1):
            icon = "✅" if c['suitable'] else "⚠️" if c['score'] >= 40 else "❌"
            rsi = c['technical'].get('rsi', 0)
            vol_ratio = c['technical'].get('volume', {}).get('volume_ratio', 0)
            heat = c['social_heat'].get('hot_level', 'cold')
            heat_icon = "🔥" if heat == 'hot' else "🌡️" if heat == 'warm' else "❄️"

            print(f"{i:<4} {c['name']:<10} {c['code']:<6} {c['price']:<8.2f} {c['change_pct']:+7.2f}% "
                  f"{c['amplitude']:<7.2f}% {rsi:<6.0f} {vol_ratio:<6.1f} {heat_icon:<6} {icon}{c['score']:<4}")

        # 详细推荐
        print("\n" + "=" * 100)
        print("🎯 详细做T策略（TOP 5 推荐）")
        print("=" * 100)

        for i, c in enumerate(candidates[:5], 1):
            if c['score'] < 40:
                continue

            print(f"\n{'='*50}")
            print(f"{i}. **{c['name']}** ({c['code']}) - 评分: {c['score']}/100")
            print(f"{'='*50}")
            print(f"💰 现价: {c['price']:.2f} HKD | 涨幅: {c['change_pct']:+.2f}% | 振幅: {c['amplitude']:.2f}%")
            print(f"📊 成交量: {c['volume']:.1f}M股")

            # 技术指标
            tech = c['technical']
            print(f"\n📈 技术指标:")
            print(f"  • RSI: {tech.get('rsi', 0):.0f} ({tech.get('rsi_signal', 'neutral')})")

            macd = tech.get('macd', {})
            print(f"  • MACD: {macd.get('macd', 0):.2f} | Signal: {macd.get('signal', 0):.2f} | 趋势: {macd.get('trend', 'neutral')}")

            vol = tech.get('volume', {})
            print(f"  • 量比: {vol.get('volume_ratio', 0):.2f} ({vol.get('status', 'normal')})")

            # 社交热度
            heat = c['social_heat']
            print(f"\n🔥 社交热度: {heat.get('hot_level', 'cold')} (得分: {heat.get('total_score', 0)})")

            # 做T位置
            print(f"\n🎯 做T位置:")
            print(f"  📍 买入位: {c['buy_price']:.2f} HKD (支撑位)")
            print(f"  🎯 卖出位: {c['sell_price']:.2f} HKD (压力位)")
            print(f"  🛑 止损位: {c['stop_loss']:.2f} HKD")
            print(f"  💰 预期收益: {c['expected_profit']:+.2f}%")

            # 推荐理由
            print(f"\n✨ 推荐理由: {', '.join(c['reasons']) if c['reasons'] else '基本面稳健'}")

            # 策略建议
            print(f"\n💡 策略建议: {c['strategy']}")

        # 注意事项
        print("\n" + "=" * 100)
        print("⚠️ 做T注意事项")
        print("=" * 100)
        print("1. 优先选择评分≥60分的标的")
        print("2. RSI<30超卖时是最佳买点，RSI>70超买时要谨慎")
        print("3. MACD金叉+放量是强买入信号")
        print("4. 在支撑位买入，压力位卖出，严格止损")
        print("5. 社交热度高的股票短期波动大，适合做T")
        print("6. 单只仓位不超过30%，避开开盘/收盘各30分钟")
        print("=" * 100)

    finally:
        advisor.disconnect()


if __name__ == '__main__':
    run_smart_t_analysis()
