#!/usr/bin/env python3
"""
热门板块 + 智能做T推荐系统
策略：
1. 扫描今日热门涨幅榜板块
2. 从热门板块中筛选股票
3. 完整技术分析：RSI、MACD、量比、社交热度
4. 优先推荐：放量上涨的股票
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

from market_scanner import MarketScanner


class HotSectorSmartT:
    """热门板块智能做T系统"""

    def __init__(self):
        self.provider = None
        self.connected = False
        self.scanner = MarketScanner()
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

    def get_hot_sectors(self) -> List[Dict]:
        """获取热门板块"""
        print("🔍 扫描热门板块...")
        hot_sectors = self.scanner.detect_hot_industries(min_stocks=2, min_avg_change=2.0)
        return hot_sectors[:10]  # TOP10热门板块

    def get_sector_stocks(self, sector_name: str) -> List[tuple]:
        """根据板块名称获取股票列表"""
        # 扩展的板块股票池（包含市值适中、基本面好的股票）
        sector_map = {
            '互联网': [
                ('HK.09988', '阿里巴巴'),
                ('HK.00700', '腾讯控股'),
                ('HK.03690', '美团'),
                ('HK.09618', '京东集团'),
                ('HK.01024', '快手'),
                ('HK.09888', '百度'),
            ],
            '电商': [
                ('HK.09988', '阿里巴巴'),
                ('HK.09618', '京东集团'),
                ('HK.01024', '快手'),
            ],
            '新能源汽车': [
                ('HK.01211', '比亚迪'),
                ('HK.02015', '理想汽车'),
                ('HK.09868', '小鹏汽车'),
                ('HK.09866', '蔚来'),
            ],
            '汽车': [
                ('HK.01211', '比亚迪'),
                ('HK.02015', '理想汽车'),
                ('HK.09868', '小鹏汽车'),
                ('HK.09866', '蔚来'),
            ],
            '半导体': [
                ('HK.00981', '中芯国际'),
                ('HK.01347', '华虹半导体'),
            ],
            '芯片': [
                ('HK.00981', '中芯国际'),
                ('HK.01347', '华虹半导体'),
            ],
            'AI': [
                ('HK.09888', '百度'),
                ('HK.00020', '商汤'),
            ],
            '人工智能': [
                ('HK.09888', '百度'),
                ('HK.00020', '商汤'),
            ],
            '医药': [
                ('HK.01801', '信达生物'),
                ('HK.09969', '诺诚健华'),
                ('HK.01177', '中国生物制药'),
            ],
            '生物科技': [
                ('HK.01801', '信达生物'),
                ('HK.09969', '诺诚健华'),
            ],
            '光伏': [
                ('HK.03800', '协鑫科技'),
                ('HK.00968', '信义光能'),
            ],
            '新能源': [
                ('HK.03800', '协鑫科技'),
                ('HK.00968', '信义光能'),
                ('HK.01211', '比亚迪'),
            ],
            '消费': [
                ('HK.01810', '小米集团'),
                ('HK.02020', '安踏体育'),
                ('HK.01458', '周黑鸭'),
            ],
            '手机': [
                ('HK.01810', '小米集团'),
            ],
            '智能硬件': [
                ('HK.01810', '小米集团'),
            ],
            '金融': [
                ('HK.06098', '碧桂园服务'),
            ],
        }

        # 模糊匹配
        stocks = []
        for key, stock_list in sector_map.items():
            if key in sector_name or sector_name in key:
                stocks.extend(stock_list)

        # 去重
        stocks = list(set(stocks))
        return stocks

    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """计算RSI"""
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
        """计算MACD"""
        result = {'macd': 0, 'signal': 0, 'histogram': 0, 'trend': 'neutral'}

        if len(closes) < 26:
            return result

        def ema(data, period):
            multiplier = 2 / (period + 1)
            ema_values = [sum(data[:period]) / period]
            for price in data[period:]:
                ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
            return ema_values[-1]

        ema12 = ema(closes, 12)
        ema26 = ema(closes, 26)
        macd = ema12 - ema26

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

        if histogram > 0 and macd > signal:
            result['trend'] = 'bullish'
        elif histogram < 0 and macd < signal:
            result['trend'] = 'bearish'

        return result

    def get_social_heat(self, code: str, name: str) -> Dict:
        """获取社交热度"""
        result = {
            'xueqiu_score': 0,
            'eastmoney_score': 0,
            'total_score': 0,
            'hot_level': 'cold'
        }

        try:
            stock_code = code.replace('HK.', '')

            # 雪球
            try:
                xq_url = f"https://xueqiu.com/query/v1/symbol/search/status"
                params = {'q': stock_code, 'count': 5}
                resp = requests.get(xq_url, params=params, headers=self.headers, timeout=5)
                data = resp.json()
                if 'list' in data and len(data['list']) > 0:
                    result['xueqiu_score'] = min(len(data['list']) * 20, 50)
            except:
                pass

            # 东财股吧
            try:
                em_url = f"https://guba.eastmoney.com/list,hk{stock_code}.html"
                resp = requests.get(em_url, headers=self.headers, timeout=5)
                if resp.status_code == 200 and '阅读' in resp.text:
                    result['eastmoney_score'] = 30
            except:
                pass

            result['total_score'] = result['xueqiu_score'] + result['eastmoney_score']

            if result['total_score'] >= 60:
                result['hot_level'] = 'hot'
            elif result['total_score'] >= 30:
                result['hot_level'] = 'warm'

        except:
            pass

        return result

    def analyze_stock(self, code: str, name: str, sector: str) -> Optional[Dict]:
        """完整技术分析"""
        result = {
            'code': code.replace('HK.', ''),
            'name': name,
            'sector': sector,
            'price': 0,
            'change_pct': 0,
            'amplitude': 0,
            'volume': 0,
            'volume_ratio': 0,
            'volume_status': 'normal',
            'rsi': 50,
            'rsi_signal': 'neutral',
            'macd': {},
            'social_heat': {},
            'buy_price': 0,
            'sell_price': 0,
            'stop_loss': 0,
            'expected_profit': 0,
            'score': 0,
            'reasons': [],
            'strategy': '',
            'suitable': False
        }

        if not self.connected:
            return None

        try:
            # 订阅
            ret_sub, err = self.provider.quote_ctx.subscribe([code], [ft.SubType.QUOTE, ft.SubType.K_DAY], subscribe_push=False)

            # 获取实时行情
            ret, data = self.provider.quote_ctx.get_stock_quote([code])
            if ret != ft.RET_OK or data.empty:
                return None

            row = data.iloc[0]
            price = row['last_price']
            prev_close = row['prev_close_price']
            high = row['high_price']
            low = row['low_price']
            volume = row['volume']

            if price <= 0 or prev_close <= 0:
                return None

            result['price'] = price
            result['change_pct'] = (price - prev_close) / prev_close * 100
            result['amplitude'] = (high - low) / prev_close * 100
            result['volume'] = volume / 1_000_000

            # 获取K线数据
            ret_k, kdata = self.provider.quote_ctx.get_cur_kline(code, 60, ft.KLType.K_DAY)
            if ret_k != ft.RET_OK or kdata.empty:
                return None

            klines = kdata.to_dict('records')
            closes = [k['close'] for k in klines]
            volumes = [k['volume'] for k in klines]

            # 计算量比
            if len(volumes) >= 6:
                current_vol = volumes[-1]
                avg_vol = sum(volumes[-6:-1]) / 5
                if avg_vol > 0:
                    vol_ratio = current_vol / avg_vol
                    result['volume_ratio'] = round(vol_ratio, 2)

                    if vol_ratio >= 2.0:
                        result['volume_status'] = 'heavy_volume'
                    elif vol_ratio <= 0.5:
                        result['volume_status'] = 'low_volume'

            # 计算RSI
            rsi = self.calculate_rsi(closes)
            result['rsi'] = round(rsi, 1)

            if rsi <= 30:
                result['rsi_signal'] = 'oversold'
            elif rsi >= 70:
                result['rsi_signal'] = 'overbought'
            elif 30 < rsi <= 45:
                result['rsi_signal'] = 'buy_zone'
            elif 55 <= rsi < 70:
                result['rsi_signal'] = 'sell_zone'

            # 计算MACD
            result['macd'] = self.calculate_macd(closes)

            # 社交热度
            result['social_heat'] = self.get_social_heat(code, name)

            # 支撑压力位
            pivot = (high + low + prev_close) / 3
            support1 = 2 * pivot - high
            resistance1 = 2 * pivot - low
            support2 = pivot - (high - low)

            result['buy_price'] = round(support1, 2)
            result['sell_price'] = round(resistance1, 2)
            result['stop_loss'] = round(support2, 2)

            if result['buy_price'] > 0:
                result['expected_profit'] = round((result['sell_price'] - result['buy_price']) / result['buy_price'] * 100, 2)

            # === 综合评分（优先放量上涨）===
            score = 0
            reasons = []

            # 1. 放量上涨（最高权重40分）
            vol_ratio = result['volume_ratio']
            vol_status = result['volume_status']
            change = result['change_pct']

            if vol_status == 'heavy_volume' and change > 0:
                if vol_ratio >= 3:
                    score += 40
                    reasons.append(f"强势放量上涨(量比{vol_ratio:.1f})")
                else:
                    score += 35
                    reasons.append(f"放量上涨(量比{vol_ratio:.1f})")
            elif vol_status == 'heavy_volume' and change < 0:
                score += 10
                reasons.append(f"放量下跌(量比{vol_ratio:.1f})")
            elif vol_status == 'low_volume' and change < 0:
                score += 15
                reasons.append(f"缩量回调(量比{vol_ratio:.1f})")
            elif vol_ratio >= 1.2:
                score += 10
                reasons.append(f"成交活跃(量比{vol_ratio:.1f})")

            # 2. 振幅评分（20分）
            amplitude = result['amplitude']
            if amplitude >= 5:
                score += 20
                reasons.append(f"振幅极大({amplitude:.1f}%)")
            elif amplitude >= 3:
                score += 15
                reasons.append(f"振幅大({amplitude:.1f}%)")
            elif amplitude >= 2:
                score += 10
                reasons.append(f"振幅良好({amplitude:.1f}%)")

            # 3. RSI评分（15分）
            if result['rsi_signal'] == 'oversold':
                score += 15
                reasons.append(f"RSI超卖({rsi:.0f})")
            elif result['rsi_signal'] == 'buy_zone':
                score += 12
                reasons.append(f"RSI买入区({rsi:.0f})")
            elif result['rsi_signal'] == 'neutral':
                score += 8
            elif result['rsi_signal'] == 'overbought':
                score -= 5
                reasons.append(f"RSI超买({rsi:.0f})")

            # 4. MACD评分（15分）
            macd_trend = result['macd'].get('trend', 'neutral')
            if macd_trend == 'bullish':
                score += 15
                reasons.append("MACD金叉")
            elif macd_trend == 'bearish':
                score -= 5
                reasons.append("MACD死叉")

            # 5. 社交热度（10分）
            heat_level = result['social_heat'].get('hot_level', 'cold')
            if heat_level == 'hot':
                score += 10
                reasons.append("社交热度高")
            elif heat_level == 'warm':
                score += 5
                reasons.append("有热度")

            result['score'] = min(score, 100)
            result['reasons'] = reasons
            result['suitable'] = score >= 60

            # 策略建议
            if result['suitable']:
                if vol_status == 'heavy_volume' and change > 0 and macd_trend == 'bullish':
                    result['strategy'] = f"🔥🔥🔥 强烈推荐：放量上涨+MACD金叉，可在{result['buy_price']:.2f}附近追涨或回调时买入，目标{result['sell_price']:.2f}"
                elif result['rsi_signal'] in ['oversold', 'buy_zone'] and macd_trend == 'bullish':
                    result['strategy'] = f"🔥 强烈推荐：RSI低位+MACD金叉，在{result['buy_price']:.2f}附近低吸，目标{result['sell_price']:.2f}"
                elif vol_status == 'low_volume' and change < 0:
                    result['strategy'] = f"📈 建议买入：缩量回调，可在{result['buy_price']:.2f}附近低吸，目标{result['sell_price']:.2f}"
                else:
                    result['strategy'] = f"⚠️ 谨慎参与：在{result['buy_price']:.2f}附近买入，目标{result['sell_price']:.2f}"
            else:
                result['strategy'] = "❌ 不建议：技术指标不佳"

            return result

        except Exception as e:
            print(f"  分析{name}失败: {e}")
            return None


def run_hot_sector_smart_t():
    """运行热门板块智能做T分析"""
    advisor = HotSectorSmartT()

    if not advisor.connect():
        print("❌ 无法连接富途API")
        return

    try:
        print("=" * 100)
        print("🔥 港股智能做T推荐系统（优先放量上涨）")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 100)
        print()

        # 1. 获取热门板块
        hot_sectors = advisor.get_hot_sectors()

        print(f"\n📈 今日热门板块 TOP{len(hot_sectors)}")
        print("-" * 100)
        for i, sector in enumerate(hot_sectors, 1):
            print(f"{i}. {sector['industry']} | 平均涨幅: +{sector['avg_change']:.1f}% | "
                  f"股票数: {sector['stock_count']}只 | 领涨: {sector['leader']['name']} +{sector['leader']['change_pct']:.1f}%")
        print()

        # 2. 分析优质大盘股（市值大、基本面好、流动性强）
        print("\n🔍 正在分析优质大盘股...")
        candidates = []

        quality_stocks = [
            ('HK.09988', '阿里巴巴', '互联网'),
            ('HK.00700', '腾讯控股', '互联网'),
            ('HK.03690', '美团', '互联网'),
            ('HK.01810', '小米集团', '消费电子'),
            ('HK.01211', '比亚迪', '新能源汽车'),
            ('HK.09618', '京东集团', '互联网'),
            ('HK.09888', '百度', 'AI'),
            ('HK.01024', '快手', '互联网'),
            ('HK.02015', '理想汽车', '新能源汽车'),
            ('HK.09868', '小鹏汽车', '新能源汽车'),
            ('HK.09866', '蔚来', '新能源汽车'),
            ('HK.00981', '中芯国际', '半导体'),
            ('HK.01347', '华虹半导体', '半导体'),
            ('HK.01801', '信达生物', '医药'),
            ('HK.09969', '诺诚健华', '医药'),
            ('HK.03800', '协鑫科技', '新能源'),
            ('HK.00968', '信义光能', '新能源'),
            ('HK.02020', '安踏体育', '消费'),
        ]

        for code, name, sector_label in quality_stocks:
            print(f"  分析 {name}...", end='\r')
            result = advisor.analyze_stock(code, name, sector_label)
            if result and result['score'] >= 35:  # 降低门槛到35分
                candidates.append(result)
            time.sleep(0.3)

        print()

        if not candidates:
            print("❌ 暂无合适的做T机会")
            return

        # 按评分排序
        candidates.sort(key=lambda x: x['score'], reverse=True)

        # 输出推荐列表
        print("=" * 100)
        print("🎯 智能做T推荐（优先放量上涨，按评分排序）")
        print("=" * 100)
        print(f"{'排名':<4} {'股票':<10} {'板块':<12} {'现价':<8} {'涨幅':<8} {'振幅':<8} {'量比':<6} {'RSI':<6} {'评分':<6}")
        print("-" * 100)

        for i, c in enumerate(candidates, 1):
            icon = "✅" if c['suitable'] else "⚠️" if c['score'] >= 50 else "❌"
            vol_icon = "🔥" if c['volume_status'] == 'heavy_volume' else "❄️" if c['volume_status'] == 'low_volume' else "📊"

            print(f"{i:<4} {c['name']:<10} {c['sector'][:10]:<12} {c['price']:<8.2f} {c['change_pct']:+7.2f}% "
                  f"{c['amplitude']:<7.2f}% {vol_icon}{c['volume_ratio']:<5.1f} {c['rsi']:<6.0f} {icon}{c['score']:<4}")

        # 详细推荐
        print("\n" + "=" * 100)
        print("🎯 详细做T策略（TOP 10 推荐 - 放量上涨优先）")
        print("=" * 100)

        for i, c in enumerate(candidates[:10], 1):
            if c['score'] < 45:
                continue

            print(f"\n{'='*80}")
            print(f"{i}. **{c['name']}** ({c['code']}) - {c['sector']}板块 - 评分: {c['score']}/100")
            print(f"{'='*80}")
            print(f"💰 现价: {c['price']:.2f} HKD | 涨幅: {c['change_pct']:+.2f}% | 振幅: {c['amplitude']:.2f}%")
            print(f"📊 成交量: {c['volume']:.1f}M股 | 量比: {c['volume_ratio']:.2f} ({c['volume_status']})")

            # 技术指标
            print(f"\n📈 技术指标:")
            print(f"  • RSI: {c['rsi']:.0f} ({c['rsi_signal']})")

            macd = c['macd']
            print(f"  • MACD: {macd.get('macd', 0):.2f} | Signal: {macd.get('signal', 0):.2f} | 趋势: {macd.get('trend', 'neutral')}")

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
            print(f"\n✨ 推荐理由: {', '.join(c['reasons'])}")

            # 策略建议
            print(f"\n💡 {c['strategy']}")

        # 注意事项
        print("\n" + "=" * 100)
        print("⚠️ 做T注意事项")
        print("=" * 100)
        print("1. 🔥 优先选择「放量上涨」的股票（量比≥2且涨幅>0）")
        print("2. 📈 评分≥60分为强推荐，50-60分为谨慎参与")
        print("3. 💡 RSI<30超卖+MACD金叉是最佳买点")
        print("4. 📊 放量上涨+MACD金叉是追涨信号，缩量回调是低吸机会")
        print("5. 🛑 严格止损，跌破止损位立即出局")
        print("6. 💰 单只仓位≤30%，避开开盘/收盘各30分钟")
        print("7. 🎯 优先选择热门板块，跟随市场热点")
        print("=" * 100)

    finally:
        advisor.disconnect()


if __name__ == '__main__':
    run_hot_sector_smart_t()
