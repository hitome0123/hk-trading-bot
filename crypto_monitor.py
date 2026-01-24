#!/usr/bin/env python3
"""
加密货币监控 - BTC/ETH分析工具
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class CryptoMonitor:
    """加密货币监控"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_price(self, symbol: str = 'bitcoin') -> Dict:
        """获取实时价格"""
        try:
            # CoinGecko API
            url = f"https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': symbol,
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_24hr_vol': 'true',
                'include_market_cap': 'true'
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if symbol in data:
                return {
                    'price': data[symbol].get('usd', 0),
                    'change_24h': data[symbol].get('usd_24h_change', 0),
                    'volume_24h': data[symbol].get('usd_24h_vol', 0),
                    'market_cap': data[symbol].get('usd_market_cap', 0)
                }
        except Exception as e:
            pass

        # 备用：Binance
        try:
            ticker_map = {'bitcoin': 'BTCUSDT', 'ethereum': 'ETHUSDT'}
            binance_symbol = ticker_map.get(symbol, f'{symbol.upper()}USDT')

            url = f"https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': binance_symbol}

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            return {
                'price': float(data.get('lastPrice', 0)),
                'change_24h': float(data.get('priceChangePercent', 0)),
                'volume_24h': float(data.get('quoteVolume', 0)),
                'high_24h': float(data.get('highPrice', 0)),
                'low_24h': float(data.get('lowPrice', 0))
            }
        except:
            pass

        return {}

    def get_fear_greed_index(self) -> Dict:
        """获取恐惧贪婪指数"""
        try:
            url = "https://api.alternative.me/fng/"
            params = {'limit': 7}

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                latest = data['data'][0]
                history = data['data']

                return {
                    'value': int(latest.get('value', 50)),
                    'classification': latest.get('value_classification', ''),
                    'timestamp': latest.get('timestamp', ''),
                    'history': [
                        {
                            'value': int(h.get('value', 50)),
                            'date': datetime.fromtimestamp(int(h.get('timestamp', 0))).strftime('%m-%d')
                        } for h in history
                    ]
                }
        except Exception as e:
            pass

        return {}

    def get_funding_rate(self, symbol: str = 'BTCUSDT') -> Dict:
        """获取资金费率（合约市场情绪）"""
        try:
            # Binance 合约资金费率
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {'symbol': symbol, 'limit': 10}

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data:
                latest = data[0]
                rates = [float(r.get('fundingRate', 0)) * 100 for r in data]

                return {
                    'current_rate': float(latest.get('fundingRate', 0)) * 100,
                    'avg_rate': sum(rates) / len(rates),
                    'timestamp': datetime.fromtimestamp(latest.get('fundingTime', 0) / 1000).strftime('%H:%M'),
                    'interpretation': self._interpret_funding(float(latest.get('fundingRate', 0)) * 100)
                }
        except Exception as e:
            pass

        return {}

    def _interpret_funding(self, rate: float) -> str:
        """解读资金费率"""
        if rate > 0.1:
            return "多头过热，注意回调风险"
        elif rate > 0.05:
            return "多头情绪偏强"
        elif rate > 0:
            return "市场中性偏多"
        elif rate > -0.05:
            return "市场中性偏空"
        elif rate > -0.1:
            return "空头情绪偏强"
        else:
            return "空头过热，可能有反弹"

    def get_technical_analysis(self, symbol: str = 'bitcoin', days: int = 30) -> Dict:
        """获取技术分析"""
        try:
            # CoinGecko历史数据
            url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
            params = {
                'vs_currency': 'usd',
                'days': days
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'prices' in data:
                prices = [p[1] for p in data['prices']]

                # 计算指标
                current = prices[-1]

                # MA
                ma7 = sum(prices[-7:]) / 7 if len(prices) >= 7 else current
                ma20 = sum(prices[-20:]) / 20 if len(prices) >= 20 else current
                ma30 = sum(prices[-30:]) / 30 if len(prices) >= 30 else current

                # RSI
                rsi = self._calc_rsi(prices, 14)

                # 布林带
                ma20_for_bb = sum(prices[-20:]) / 20
                std20 = (sum((p - ma20_for_bb) ** 2 for p in prices[-20:]) / 20) ** 0.5
                bb_upper = ma20_for_bb + 2 * std20
                bb_lower = ma20_for_bb - 2 * std20

                # 趋势判断
                trend = "上涨" if ma7 > ma20 > ma30 else ("下跌" if ma7 < ma20 < ma30 else "震荡")

                return {
                    'current': current,
                    'ma7': ma7,
                    'ma20': ma20,
                    'ma30': ma30,
                    'rsi': rsi,
                    'bb_upper': bb_upper,
                    'bb_lower': bb_lower,
                    'trend': trend,
                    'above_ma20': current > ma20,
                    'rsi_signal': "超买" if rsi > 70 else ("超卖" if rsi < 30 else "中性")
                }
        except Exception as e:
            pass

        return {}

    def _calc_rsi(self, prices: List[float], period: int = 14) -> float:
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

    def calc_liquidation_risk(self, entry_price: float, current_price: float,
                               ltv: float = 0.5, liquidation_ltv: float = 0.83) -> Dict:
        """
        计算清算风险
        entry_price: 买入价格
        current_price: 当前价格
        ltv: 当前质押率 (借款/抵押物)
        liquidation_ltv: 清算质押率
        """
        # 清算价 = 当前价格 * (当前LTV / 清算LTV)
        liquidation_price = current_price * (ltv / liquidation_ltv)

        # 距离清算的跌幅
        drop_to_liquidation = (current_price - liquidation_price) / current_price * 100

        # 盈亏
        pnl_pct = (current_price - entry_price) / entry_price * 100

        # 风险等级
        if drop_to_liquidation < 20:
            risk_level = "高风险"
            advice = "建议补充抵押物或部分还款"
        elif drop_to_liquidation < 40:
            risk_level = "中等风险"
            advice = "密切关注，设置价格提醒"
        else:
            risk_level = "低风险"
            advice = "安全范围内"

        return {
            'entry_price': entry_price,
            'current_price': current_price,
            'liquidation_price': liquidation_price,
            'drop_to_liquidation': drop_to_liquidation,
            'pnl_pct': pnl_pct,
            'risk_level': risk_level,
            'advice': advice
        }

    def get_support_resistance(self, symbol: str = 'bitcoin', days: int = 90) -> Dict:
        """计算支撑位和阻力位"""
        prices = []

        # 尝试Binance K线数据
        try:
            ticker_map = {'bitcoin': 'BTCUSDT', 'ethereum': 'ETHUSDT'}
            binance_symbol = ticker_map.get(symbol, f'{symbol.upper()}USDT')

            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': binance_symbol,
                'interval': '1h',
                'limit': min(days * 24, 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and isinstance(data, list):
                prices = [float(k[4]) for k in data]  # 收盘价

        except:
            pass

        # 备用CoinGecko
        if not prices:
            try:
                url = f"https://api.coingecko.com/api/v3/coins/{symbol}/market_chart"
                params = {'vs_currency': 'usd', 'days': days}

                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                data = resp.json()

                if data and 'prices' in data:
                    prices = [p[1] for p in data['prices']]
            except:
                pass

        if prices:
            current = prices[-1]

            # 近期高低点
            high_30d = max(prices[-30*24:]) if len(prices) > 30*24 else max(prices)
            low_30d = min(prices[-30*24:]) if len(prices) > 30*24 else min(prices)
            high_7d = max(prices[-7*24:]) if len(prices) > 7*24 else max(prices[-168:])
            low_7d = min(prices[-7*24:]) if len(prices) > 7*24 else min(prices[-168:])

            # 斐波那契回撤位 (从30日高点到低点)
            diff = high_30d - low_30d
            fib_levels = {
                '0% (高点)': high_30d,
                '23.6%': high_30d - diff * 0.236,
                '38.2%': high_30d - diff * 0.382,
                '50%': high_30d - diff * 0.5,
                '61.8%': high_30d - diff * 0.618,
                '100% (低点)': low_30d
            }

            # 枢轴点 (基于昨日数据)
            yesterday_prices = prices[-48:-24] if len(prices) > 48 else prices[-24:]
            pivot_high = max(yesterday_prices)
            pivot_low = min(yesterday_prices)
            pivot_close = yesterday_prices[-1]

            pivot = (pivot_high + pivot_low + pivot_close) / 3
            r1 = 2 * pivot - pivot_low
            r2 = pivot + (pivot_high - pivot_low)
            s1 = 2 * pivot - pivot_high
            s2 = pivot - (pivot_high - pivot_low)

            # 找关键支撑阻力
            all_levels = sorted([
                ('R2', r2), ('R1', r1), ('Pivot', pivot),
                ('S1', s1), ('S2', s2),
                ('30日高', high_30d), ('30日低', low_30d),
                ('7日高', high_7d), ('7日低', low_7d)
            ], key=lambda x: x[1], reverse=True)

            # 找最近的支撑和阻力
            supports = [(n, p) for n, p in all_levels if p < current]
            resistances = [(n, p) for n, p in all_levels if p > current]

            nearest_support = supports[0] if supports else None
            nearest_resistance = resistances[-1] if resistances else None

            return {
                'current': current,
                'high_30d': high_30d,
                'low_30d': low_30d,
                'high_7d': high_7d,
                'low_7d': low_7d,
                'fibonacci': fib_levels,
                'pivot': pivot,
                'r1': r1, 'r2': r2,
                's1': s1, 's2': s2,
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'all_levels': all_levels
            }

        return {}

    def predict_direction(self, symbol: str = 'bitcoin') -> Dict:
        """预测涨跌方向"""
        ta = self.get_technical_analysis(symbol)
        sr = self.get_support_resistance(symbol)
        fng = self.get_fear_greed_index()
        funding = self.get_funding_rate('BTCUSDT' if symbol == 'bitcoin' else 'ETHUSDT')

        if not ta:
            return {}

        current = ta['current']
        signals = []
        bull_score = 0  # 看涨分数
        bear_score = 0  # 看跌分数

        # 1. 趋势分析 (权重: 25%)
        if ta['trend'] == '上涨':
            bull_score += 25
            signals.append(('趋势向上', 'bull'))
        elif ta['trend'] == '下跌':
            bear_score += 25
            signals.append(('趋势向下', 'bear'))
        else:
            bull_score += 12
            bear_score += 12
            signals.append(('趋势震荡', 'neutral'))

        # 2. RSI分析 (权重: 20%)
        rsi = ta['rsi']
        if rsi < 30:
            bull_score += 20
            signals.append(('RSI超卖反弹', 'bull'))
        elif rsi > 70:
            bear_score += 15
            signals.append(('RSI超买回调', 'bear'))
        elif rsi > 50:
            bull_score += 10
            signals.append(('RSI偏强', 'bull'))
        else:
            bear_score += 10
            signals.append(('RSI偏弱', 'bear'))

        # 3. MA位置 (权重: 15%)
        if ta['above_ma20']:
            bull_score += 15
            signals.append(('站上MA20', 'bull'))
        else:
            bear_score += 15
            signals.append(('跌破MA20', 'bear'))

        # 4. 布林带位置 (权重: 15%)
        bb_pos = (current - ta['bb_lower']) / (ta['bb_upper'] - ta['bb_lower'])
        if bb_pos > 0.8:
            bear_score += 10
            signals.append(('接近布林上轨', 'bear'))
        elif bb_pos < 0.2:
            bull_score += 15
            signals.append(('接近布林下轨', 'bull'))

        # 5. 恐惧贪婪 (权重: 15%)
        if fng:
            fng_val = fng['value']
            if fng_val < 25:
                bull_score += 15  # 极度恐惧是买入机会
                signals.append(('极度恐惧(反向)', 'bull'))
            elif fng_val > 75:
                bear_score += 15  # 极度贪婪要小心
                signals.append(('极度贪婪(反向)', 'bear'))
            elif fng_val > 50:
                bull_score += 5
            else:
                bear_score += 5

        # 6. 资金费率 (权重: 10%)
        if funding:
            rate = funding['current_rate']
            if rate > 0.1:
                bear_score += 10
                signals.append(('费率过高', 'bear'))
            elif rate < -0.05:
                bull_score += 10
                signals.append(('费率为负', 'bull'))

        # 计算总分和预测
        total = bull_score + bear_score
        bull_pct = bull_score / total * 100 if total > 0 else 50

        if bull_pct > 65:
            direction = '看涨'
            confidence = '高' if bull_pct > 75 else '中'
        elif bull_pct < 35:
            direction = '看跌'
            confidence = '高' if bull_pct < 25 else '中'
        else:
            direction = '震荡'
            confidence = '低'

        # 目标价位
        targets = {}
        if sr:
            if direction == '看涨':
                targets['目标1'] = sr.get('nearest_resistance', (None, current * 1.05))[1]
                targets['目标2'] = sr.get('high_30d', current * 1.1)
                targets['止损'] = sr.get('nearest_support', (None, current * 0.95))[1]
            elif direction == '看跌':
                targets['目标1'] = sr.get('nearest_support', (None, current * 0.95))[1]
                targets['目标2'] = sr.get('low_30d', current * 0.9)
                targets['止损'] = sr.get('nearest_resistance', (None, current * 1.05))[1]
            else:
                targets['上方阻力'] = sr.get('nearest_resistance', (None, current * 1.03))[1]
                targets['下方支撑'] = sr.get('nearest_support', (None, current * 0.97))[1]

        return {
            'direction': direction,
            'confidence': confidence,
            'bull_score': bull_score,
            'bear_score': bear_score,
            'bull_pct': bull_pct,
            'signals': signals,
            'targets': targets,
            'current': current
        }

    def get_market_overview(self) -> Dict:
        """获取市场概览"""
        try:
            url = "https://api.coingecko.com/api/v3/global"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                d = data['data']
                return {
                    'total_market_cap': d.get('total_market_cap', {}).get('usd', 0),
                    'total_volume': d.get('total_volume', {}).get('usd', 0),
                    'btc_dominance': d.get('market_cap_percentage', {}).get('btc', 0),
                    'eth_dominance': d.get('market_cap_percentage', {}).get('eth', 0),
                    'market_cap_change_24h': d.get('market_cap_change_percentage_24h_usd', 0)
                }
        except:
            pass

        return {}


def show_btc_analysis():
    """显示BTC分析"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print(f"BTC 分析报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)

    # 价格
    price_data = monitor.get_price('bitcoin')
    if price_data:
        price = price_data['price']
        change = price_data['change_24h']
        icon = '🟢' if change > 0 else '🔴'
        print(f"\n{icon} 当前价格: ${price:,.0f}")
        print(f"   24h涨跌: {change:+.2f}%")
        if price_data.get('volume_24h'):
            vol = price_data['volume_24h'] / 1e9
            print(f"   24h成交量: ${vol:.1f}B")

    # 技术指标
    ta = monitor.get_technical_analysis('bitcoin')
    if ta:
        print(f"\n📊 技术指标:")
        print(f"   MA7: ${ta['ma7']:,.0f}")
        print(f"   MA20: ${ta['ma20']:,.0f}")
        print(f"   MA30: ${ta['ma30']:,.0f}")
        print(f"   RSI(14): {ta['rsi']:.1f} ({ta['rsi_signal']})")
        print(f"   布林上轨: ${ta['bb_upper']:,.0f}")
        print(f"   布林下轨: ${ta['bb_lower']:,.0f}")
        print(f"   趋势: {ta['trend']}")

    # 恐惧贪婪
    fng = monitor.get_fear_greed_index()
    if fng:
        value = fng['value']
        if value <= 25:
            emoji = '😱'
        elif value <= 45:
            emoji = '😰'
        elif value <= 55:
            emoji = '😐'
        elif value <= 75:
            emoji = '😊'
        else:
            emoji = '🤑'

        print(f"\n{emoji} 恐惧贪婪指数: {value} ({fng['classification']})")
        if fng.get('history'):
            hist = ' -> '.join([str(h['value']) for h in fng['history'][:5]])
            print(f"   近5天: {hist}")

    # 资金费率
    funding = monitor.get_funding_rate('BTCUSDT')
    if funding:
        rate = funding['current_rate']
        icon = '📈' if rate > 0 else '📉'
        print(f"\n{icon} 资金费率: {rate:.4f}%")
        print(f"   {funding['interpretation']}")

    print("\n" + "=" * 60)


def show_liquidation_check(entry: float = 110000, ltv: float = 0.5):
    """检查清算风险"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print("质押清算风险检查")
    print("=" * 60)

    price_data = monitor.get_price('bitcoin')
    if not price_data:
        print("获取价格失败")
        return

    current = price_data['price']
    risk = monitor.calc_liquidation_risk(entry, current, ltv)

    pnl_icon = '🟢' if risk['pnl_pct'] > 0 else '🔴'
    risk_icon = '🟢' if risk['risk_level'] == '低风险' else ('🟡' if risk['risk_level'] == '中等风险' else '🔴')

    print(f"\n买入价格: ${risk['entry_price']:,.0f}")
    print(f"当前价格: ${risk['current_price']:,.0f}")
    print(f"{pnl_icon} 盈亏: {risk['pnl_pct']:+.1f}%")

    print(f"\n质押率: {ltv*100:.0f}%")
    print(f"清算价格: ${risk['liquidation_price']:,.0f}")
    print(f"距离清算: {risk['drop_to_liquidation']:.1f}% 跌幅")

    print(f"\n{risk_icon} 风险等级: {risk['risk_level']}")
    print(f"   建议: {risk['advice']}")

    # 模拟不同价格的清算风险
    print(f"\n价格敏感性分析:")
    test_prices = [80000, 70000, 60000, 55000, 50000]
    liq_price = risk['liquidation_price']
    for tp in test_prices:
        drop_pct = (tp - liq_price) / tp * 100
        if tp <= liq_price:
            status = "⚠️ 已清算!"
        else:
            status = f"距清算{drop_pct:.0f}%"
        print(f"   ${tp:,}: {status}")

    print("\n" + "=" * 60)


def show_market_overview():
    """市场概览"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print(f"加密货币市场概览 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)

    # BTC
    btc = monitor.get_price('bitcoin')
    if btc:
        icon = '🟢' if btc['change_24h'] > 0 else '🔴'
        print(f"\n{icon} BTC: ${btc['price']:,.0f} ({btc['change_24h']:+.2f}%)")

    # ETH
    eth = monitor.get_price('ethereum')
    if eth:
        icon = '🟢' if eth['change_24h'] > 0 else '🔴'
        print(f"{icon} ETH: ${eth['price']:,.0f} ({eth['change_24h']:+.2f}%)")

    # 市场数据
    overview = monitor.get_market_overview()
    if overview:
        cap = overview['total_market_cap'] / 1e12
        vol = overview['total_volume'] / 1e9
        print(f"\n总市值: ${cap:.2f}T")
        print(f"24h成交量: ${vol:.0f}B")
        print(f"BTC占比: {overview['btc_dominance']:.1f}%")
        print(f"ETH占比: {overview['eth_dominance']:.1f}%")

    # 恐惧贪婪
    fng = monitor.get_fear_greed_index()
    if fng:
        print(f"\n恐惧贪婪: {fng['value']} ({fng['classification']})")

    print("\n" + "=" * 60)


def quick_check():
    """快速检查"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print(f"加密货币快速检查 ({datetime.now().strftime('%H:%M')})")
    print("=" * 60)

    # BTC价格和趋势
    btc = monitor.get_price('bitcoin')
    ta = monitor.get_technical_analysis('bitcoin')
    fng = monitor.get_fear_greed_index()
    funding = monitor.get_funding_rate('BTCUSDT')

    if btc:
        icon = '🟢' if btc['change_24h'] > 0 else '🔴'
        print(f"\n{icon} BTC: ${btc['price']:,.0f} ({btc['change_24h']:+.2f}%)")

    if ta:
        print(f"   趋势: {ta['trend']} | RSI: {ta['rsi']:.0f} ({ta['rsi_signal']})")
        pos = "MA20上方" if ta['above_ma20'] else "MA20下方"
        print(f"   位置: {pos}")

    if fng:
        print(f"   情绪: {fng['value']} ({fng['classification']})")

    if funding:
        print(f"   费率: {funding['current_rate']:.4f}% - {funding['interpretation']}")

    # 操作建议
    print(f"\n💡 操作建议:")
    signals = []

    if ta:
        if ta['rsi'] < 30:
            signals.append("RSI超卖，可能反弹")
        elif ta['rsi'] > 70:
            signals.append("RSI超买，注意回调")

        if ta['trend'] == '上涨':
            signals.append("趋势向上，顺势操作")
        elif ta['trend'] == '下跌':
            signals.append("趋势向下，谨慎操作")

    if fng:
        if fng['value'] < 25:
            signals.append("极度恐惧，可能是买入机会")
        elif fng['value'] > 75:
            signals.append("极度贪婪，注意风险")

    if funding:
        if funding['current_rate'] > 0.1:
            signals.append("费率过高，多头拥挤")
        elif funding['current_rate'] < -0.05:
            signals.append("费率为负，空头过度")

    if signals:
        for s in signals:
            print(f"   - {s}")
    else:
        print("   - 市场中性，观望为主")

    print("\n" + "=" * 60)


def show_support_resistance():
    """显示支撑阻力位"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print(f"BTC 支撑阻力位 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)

    sr = monitor.get_support_resistance('bitcoin')

    if not sr:
        print("获取数据失败")
        return

    current = sr['current']
    print(f"\n当前价格: ${current:,.0f}")

    # 阻力位
    print(f"\n📈 阻力位 (上方):")
    print(f"   R2 (强阻力): ${sr['r2']:,.0f} ({(sr['r2']/current-1)*100:+.1f}%)")
    print(f"   R1 (阻力):   ${sr['r1']:,.0f} ({(sr['r1']/current-1)*100:+.1f}%)")
    print(f"   30日高点:    ${sr['high_30d']:,.0f} ({(sr['high_30d']/current-1)*100:+.1f}%)")
    print(f"   7日高点:     ${sr['high_7d']:,.0f} ({(sr['high_7d']/current-1)*100:+.1f}%)")

    # 枢轴点
    print(f"\n⚖️ 枢轴点: ${sr['pivot']:,.0f}")

    # 支撑位
    print(f"\n📉 支撑位 (下方):")
    print(f"   S1 (支撑):   ${sr['s1']:,.0f} ({(sr['s1']/current-1)*100:+.1f}%)")
    print(f"   S2 (强支撑): ${sr['s2']:,.0f} ({(sr['s2']/current-1)*100:+.1f}%)")
    print(f"   7日低点:     ${sr['low_7d']:,.0f} ({(sr['low_7d']/current-1)*100:+.1f}%)")
    print(f"   30日低点:    ${sr['low_30d']:,.0f} ({(sr['low_30d']/current-1)*100:+.1f}%)")

    # 斐波那契
    print(f"\n📐 斐波那契回撤位:")
    for name, price in sr['fibonacci'].items():
        dist = (price / current - 1) * 100
        marker = " ◀ 当前" if abs(dist) < 1 else ""
        print(f"   {name}: ${price:,.0f} ({dist:+.1f}%){marker}")

    # 最近支撑阻力
    print(f"\n🎯 关键位置:")
    if sr['nearest_resistance']:
        name, price = sr['nearest_resistance']
        print(f"   最近阻力: ${price:,.0f} ({name}, {(price/current-1)*100:+.1f}%)")
    if sr['nearest_support']:
        name, price = sr['nearest_support']
        print(f"   最近支撑: ${price:,.0f} ({name}, {(price/current-1)*100:+.1f}%)")

    print("\n" + "=" * 60)


def show_prediction():
    """显示涨跌预测"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 60)
    print(f"BTC 涨跌预测 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)

    pred = monitor.predict_direction('bitcoin')

    if not pred:
        print("获取数据失败")
        return

    current = pred['current']
    print(f"\n当前价格: ${current:,.0f}")

    # 预测结果
    if pred['direction'] == '看涨':
        icon = '🟢'
    elif pred['direction'] == '看跌':
        icon = '🔴'
    else:
        icon = '🟡'

    print(f"\n{icon} 预测方向: {pred['direction']}")
    print(f"   置信度: {pred['confidence']}")
    print(f"   看涨指数: {pred['bull_pct']:.0f}%")

    # 信号详情
    print(f"\n📊 分析信号:")
    for signal, signal_type in pred['signals']:
        if signal_type == 'bull':
            print(f"   🟢 {signal}")
        elif signal_type == 'bear':
            print(f"   🔴 {signal}")
        else:
            print(f"   🟡 {signal}")

    # 目标价位
    print(f"\n🎯 价位建议:")
    for name, price in pred['targets'].items():
        if price:
            dist = (price / current - 1) * 100
            print(f"   {name}: ${price:,.0f} ({dist:+.1f}%)")

    # 操作建议
    print(f"\n💡 操作建议:")
    if pred['direction'] == '看涨' and pred['confidence'] == '高':
        print("   可以考虑做多，但注意止损")
    elif pred['direction'] == '看跌' and pred['confidence'] == '高':
        print("   建议观望或减仓，等待企稳")
    elif pred['direction'] == '震荡':
        print("   区间震荡，高抛低吸或观望")
    else:
        print("   信号不明确，建议观望")

    print("\n" + "=" * 60)


def show_full_analysis():
    """完整分析"""
    monitor = CryptoMonitor()

    print("\n" + "=" * 70)
    print(f"BTC 完整分析报告 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    # 价格
    price_data = monitor.get_price('bitcoin')
    if price_data:
        icon = '🟢' if price_data['change_24h'] > 0 else '🔴'
        print(f"\n{icon} 当前: ${price_data['price']:,.0f} ({price_data['change_24h']:+.2f}%)")

    # 预测
    pred = monitor.predict_direction('bitcoin')
    if pred:
        dir_icon = '🟢' if pred['direction'] == '看涨' else ('🔴' if pred['direction'] == '看跌' else '🟡')
        print(f"\n{dir_icon} 预测: {pred['direction']} (置信度:{pred['confidence']}, 看涨指数:{pred['bull_pct']:.0f}%)")

    # 关键位置
    sr = monitor.get_support_resistance('bitcoin')
    if sr:
        print(f"\n📍 关键位置:")
        if sr['nearest_resistance']:
            print(f"   阻力: ${sr['nearest_resistance'][1]:,.0f}")
        if sr['nearest_support']:
            print(f"   支撑: ${sr['nearest_support'][1]:,.0f}")

    # 技术指标
    ta = monitor.get_technical_analysis('bitcoin')
    if ta:
        print(f"\n📊 技术指标:")
        print(f"   RSI: {ta['rsi']:.0f} ({ta['rsi_signal']}) | 趋势: {ta['trend']}")

    # 情绪
    fng = monitor.get_fear_greed_index()
    funding = monitor.get_funding_rate('BTCUSDT')
    if fng or funding:
        print(f"\n😀 市场情绪:")
        if fng:
            print(f"   恐惧贪婪: {fng['value']} ({fng['classification']})")
        if funding:
            print(f"   资金费率: {funding['current_rate']:.4f}%")

    # 目标价
    if pred and pred['targets']:
        print(f"\n🎯 目标价位:")
        for name, price in pred['targets'].items():
            if price:
                print(f"   {name}: ${price:,.0f}")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python crypto_monitor.py full      - 完整分析(推荐)")
        print("  python crypto_monitor.py predict   - 涨跌预测")
        print("  python crypto_monitor.py sr        - 支撑阻力位")
        print("  python crypto_monitor.py btc       - BTC技术分析")
        print("  python crypto_monitor.py quick     - 快速检查")
        print("  python crypto_monitor.py market    - 市场概览")
        print("  python crypto_monitor.py risk 110000 0.5  - 清算风险")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'full':
        show_full_analysis()
    elif cmd == 'predict':
        show_prediction()
    elif cmd == 'sr':
        show_support_resistance()
    elif cmd == 'btc':
        show_btc_analysis()
    elif cmd == 'market':
        show_market_overview()
    elif cmd == 'quick':
        quick_check()
    elif cmd == 'risk':
        entry = float(sys.argv[2]) if len(sys.argv) > 2 else 110000
        ltv = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
        show_liquidation_check(entry, ltv)
    else:
        print("未知命令")
