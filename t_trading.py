#!/usr/bin/env python3
"""
港股做T推荐系统
基于富途API实时数据，提供做T建议
包含：推荐股票、买卖位置、预期收益
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime
from typing import Dict, List, Optional
import time

try:
    from hk_trading_bot.data_providers.futu_provider import FutuProvider
    import futu as ft
    HAS_FUTU = True
except:
    HAS_FUTU = False
    print("警告: 富途API未安装，部分功能不可用")


class TTradingAdvisor:
    """做T交易顾问"""

    def __init__(self):
        self.provider = None
        self.connected = False

    def connect(self):
        """连接富途API"""
        if not HAS_FUTU:
            print("❌ 富途API未安装")
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
        """断开连接"""
        if self.provider:
            self.provider.disconnect()
            self.connected = False

    def get_realtime_quote(self, code: str) -> Optional[Dict]:
        """获取实时行情"""
        if not self.connected:
            return None

        try:
            ret, data = self.provider.quote_ctx.get_stock_quote([code])
            if ret == ft.RET_OK and not data.empty:
                row = data.iloc[0]
                return {
                    'code': code,
                    'name': row.get('name', ''),
                    'price': row['last_price'],
                    'open': row['open_price'],
                    'high': row['high_price'],
                    'low': row['low_price'],
                    'prev_close': row['prev_close_price'],
                    'volume': row['volume'],
                    'turnover': row['turnover'],
                    'amplitude': (row['high_price'] - row['low_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                    'change_pct': (row['last_price'] - row['prev_close_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                }
        except Exception as e:
            print(f"获取行情失败: {e}")
        return None

    def get_kline_data(self, code: str, ktype: str = 'K_DAY', count: int = 60) -> Optional[List]:
        """获取K线数据"""
        if not self.connected:
            return None

        try:
            ktype_map = {
                'K_1M': ft.KLType.K_1M,
                'K_5M': ft.KLType.K_5M,
                'K_15M': ft.KLType.K_15M,
                'K_30M': ft.KLType.K_30M,
                'K_60M': ft.KLType.K_60M,
                'K_DAY': ft.KLType.K_DAY,
            }
            ret, data = self.provider.quote_ctx.get_cur_kline(code, count, ktype_map.get(ktype, ft.KLType.K_DAY))
            if ret == ft.RET_OK and not data.empty:
                return data.to_dict('records')
        except Exception as e:
            print(f"获取K线失败: {e}")
        return None

    def calculate_support_resistance(self, code: str) -> Dict:
        """计算支撑位和压力位"""
        result = {
            'support1': 0,    # 第一支撑位
            'support2': 0,    # 第二支撑位
            'resistance1': 0, # 第一压力位
            'resistance2': 0, # 第二压力位
            'pivot': 0,       # 枢轴点
        }

        # 获取日K数据
        klines = self.get_kline_data(code, 'K_DAY', 20)
        if not klines or len(klines) < 2:
            return result

        # 使用前一日数据计算
        prev = klines[-2]
        high = prev['high']
        low = prev['low']
        close = prev['close']

        # 经典枢轴点计算
        pivot = (high + low + close) / 3

        result['pivot'] = round(pivot, 3)
        result['support1'] = round(2 * pivot - high, 3)
        result['support2'] = round(pivot - (high - low), 3)
        result['resistance1'] = round(2 * pivot - low, 3)
        result['resistance2'] = round(pivot + (high - low), 3)

        return result

    def calculate_volatility(self, code: str) -> Dict:
        """计算波动率"""
        result = {
            'atr': 0,           # 平均真实波幅
            'atr_pct': 0,       # ATR百分比
            'daily_range': 0,   # 日均波动
            'volatility_score': 0,  # 波动评分
        }

        klines = self.get_kline_data(code, 'K_DAY', 14)
        if not klines or len(klines) < 14:
            return result

        # 计算ATR
        tr_list = []
        for i in range(1, len(klines)):
            high = klines[i]['high']
            low = klines[i]['low']
            prev_close = klines[i-1]['close']

            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)

        atr = sum(tr_list) / len(tr_list)
        current_price = klines[-1]['close']
        atr_pct = atr / current_price * 100 if current_price > 0 else 0

        # 日均波动
        ranges = [(k['high'] - k['low']) / k['close'] * 100 for k in klines if k['close'] > 0]
        daily_range = sum(ranges) / len(ranges) if ranges else 0

        # 波动评分 (适合做T需要波动大)
        if atr_pct >= 3:
            volatility_score = 90
        elif atr_pct >= 2:
            volatility_score = 75
        elif atr_pct >= 1.5:
            volatility_score = 60
        elif atr_pct >= 1:
            volatility_score = 45
        else:
            volatility_score = 30

        result['atr'] = round(atr, 3)
        result['atr_pct'] = round(atr_pct, 2)
        result['daily_range'] = round(daily_range, 2)
        result['volatility_score'] = volatility_score

        return result

    def analyze_t_opportunity(self, code: str) -> Dict:
        """分析做T机会"""
        result = {
            'code': code,
            'name': '',
            'price': 0,
            'suitable_for_t': False,
            'score': 0,
            'buy_price': 0,
            'sell_price': 0,
            'stop_loss': 0,
            'expected_profit_pct': 0,
            'risk_reward': 0,
            'reason': '',
            'strategy': '',
        }

        # 获取实时行情
        quote = self.get_realtime_quote(code)
        if not quote:
            result['reason'] = '无法获取行情'
            return result

        result['name'] = quote['name']
        result['price'] = quote['price']

        # 获取支撑压力位
        levels = self.calculate_support_resistance(code)

        # 获取波动率
        volatility = self.calculate_volatility(code)

        # 分析做T适合度
        price = quote['price']
        amplitude = quote['amplitude']

        # 评分逻辑
        score = 0
        reasons = []

        # 1. 波动率评分 (40%)
        score += volatility['volatility_score'] * 0.4
        if volatility['atr_pct'] >= 2:
            reasons.append(f"波动率高({volatility['atr_pct']:.1f}%)")

        # 2. 当日振幅 (30%)
        if amplitude >= 3:
            score += 30
            reasons.append(f"今日振幅大({amplitude:.1f}%)")
        elif amplitude >= 2:
            score += 20
        elif amplitude >= 1:
            score += 10

        # 3. 价格位置 (30%)
        if levels['support1'] > 0:
            # 接近支撑位 - 适合做多
            support_distance = (price - levels['support1']) / price * 100
            resistance_distance = (levels['resistance1'] - price) / price * 100

            if support_distance < 1:
                score += 30
                reasons.append("接近支撑位")
            elif resistance_distance < 1:
                score += 25
                reasons.append("接近压力位")
            else:
                score += 15

        # 判断是否适合做T
        result['score'] = round(score)
        result['suitable_for_t'] = score >= 60

        # 计算买卖点位
        if levels['support1'] > 0 and levels['resistance1'] > 0:
            # 做T策略：支撑买入，压力卖出
            result['buy_price'] = round(levels['support1'], 3)
            result['sell_price'] = round(levels['resistance1'], 3)
            result['stop_loss'] = round(levels['support2'], 3)

            # 预期收益
            if result['buy_price'] > 0:
                result['expected_profit_pct'] = round((result['sell_price'] - result['buy_price']) / result['buy_price'] * 100, 2)

                # 风险收益比
                risk = result['buy_price'] - result['stop_loss']
                reward = result['sell_price'] - result['buy_price']
                if risk > 0:
                    result['risk_reward'] = round(reward / risk, 2)

        result['reason'] = '，'.join(reasons) if reasons else '波动一般'

        # 策略建议
        if result['suitable_for_t']:
            if price < levels['pivot']:
                result['strategy'] = f"📈 低吸策略：在{result['buy_price']:.3f}附近买入，目标{result['sell_price']:.3f}，止损{result['stop_loss']:.3f}"
            else:
                result['strategy'] = f"📉 高抛策略：当前价偏高，等回调到{levels['support1']:.3f}再介入"
        else:
            result['strategy'] = "⚠️ 当前不适合做T，波动不足或风险收益比不佳"

        return result

    def scan_t_candidates(self, stock_list: List[tuple]) -> List[Dict]:
        """扫描做T候选股"""
        candidates = []

        for code, name in stock_list:
            try:
                analysis = self.analyze_t_opportunity(code)
                if analysis['score'] >= 50:  # 50分以上才列入候选
                    candidates.append(analysis)
            except Exception as e:
                print(f"分析{name}失败: {e}")
                continue

        # 按分数排序
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates


# 默认做T候选股池
T_TRADING_POOL = [
    ('HK.09988', '阿里巴巴'),
    ('HK.00700', '腾讯'),
    ('HK.03690', '美团'),
    ('HK.01810', '小米'),
    ('HK.09618', '京东'),
    ('HK.01024', '快手'),
    ('HK.09888', '百度'),
    ('HK.01211', '比亚迪'),
    ('HK.02015', '理想汽车'),
    ('HK.09868', '小鹏汽车'),
    ('HK.09866', '蔚来'),
    ('HK.00981', '中芯国际'),
    ('HK.01347', '华虹半导体'),
    ('HK.03800', '协鑫科技'),
    ('HK.00020', '商汤'),
    ('HK.01045', '亚太卫星'),
]


def get_t_recommendations() -> str:
    """获取做T推荐"""
    advisor = TTradingAdvisor()

    if not advisor.connect():
        return "❌ 无法连接富途API，请确保FutuOpenD已启动"

    try:
        print("🔍 扫描做T机会...")
        candidates = advisor.scan_t_candidates(T_TRADING_POOL)

        content = f"""### 📊 做T推荐

**扫描时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**扫描股票:** {len(T_TRADING_POOL)}只

---

#### 🎯 推荐做T标的

"""

        if not candidates:
            content += "暂无合适的做T机会\n"
        else:
            content += "| 股票 | 代码 | 现价 | 评分 | 买入位 | 卖出位 | 止损 | 预期收益 |\n"
            content += "|------|------|------|------|--------|--------|------|----------|\n"

            for c in candidates[:8]:
                suitable = "✅" if c['suitable_for_t'] else "⚠️"
                content += f"| {c['name'][:4]} | {c['code'].replace('HK.', '')} | {c['price']:.2f} | {suitable}{c['score']} | {c['buy_price']:.2f} | {c['sell_price']:.2f} | {c['stop_loss']:.2f} | {c['expected_profit_pct']:+.1f}% |\n"

            content += "\n---\n\n#### 📝 详细策略\n\n"

            for c in candidates[:5]:
                if c['suitable_for_t']:
                    content += f"**{c['name']}** ({c['code'].replace('HK.', '')})\n"
                    content += f"- 现价: {c['price']:.2f}\n"
                    content += f"- {c['strategy']}\n"
                    content += f"- 理由: {c['reason']}\n"
                    content += f"- 风险收益比: 1:{c['risk_reward']}\n\n"

        content += """---

#### ⚠️ 做T注意事项

1. **仓位控制**: 单只股票不超过总仓位30%
2. **止损纪律**: 严格执行止损，亏损2%必须止损
3. **交易时间**: 避开开盘30分钟和收盘30分钟
4. **手续费**: 考虑港股交易成本(约0.1%)

---

*数据来源: 富途API实时行情*
"""
        return content

    finally:
        advisor.disconnect()


def push_t_recommendations():
    """推送做T推荐到钉钉"""
    from dingtalk_notifier import DingTalkNotifier

    content = get_t_recommendations()
    print(content)

    notifier = DingTalkNotifier()
    notifier.send_markdown("📊 做T推荐", content)
    print("\n✅ 已推送到钉钉!")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'push':
            push_t_recommendations()
        elif cmd == 'analyze':
            code = sys.argv[2] if len(sys.argv) > 2 else 'HK.09988'
            advisor = TTradingAdvisor()
            if advisor.connect():
                result = advisor.analyze_t_opportunity(code)
                print(f"\n{result['name']} ({code}) 做T分析:")
                print(f"  现价: {result['price']}")
                print(f"  评分: {result['score']}")
                print(f"  适合做T: {'是' if result['suitable_for_t'] else '否'}")
                print(f"  买入位: {result['buy_price']}")
                print(f"  卖出位: {result['sell_price']}")
                print(f"  止损位: {result['stop_loss']}")
                print(f"  预期收益: {result['expected_profit_pct']}%")
                print(f"  策略: {result['strategy']}")
                advisor.disconnect()
    else:
        print(get_t_recommendations())
