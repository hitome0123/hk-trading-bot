#!/usr/bin/env python3
"""
热门板块 + 做T推荐 一体化
检测热门板块 → 分析板块内股票 → 推荐做T机会
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime
from typing import Dict, List
import requests

try:
    from hk_trading_bot.data_providers.futu_provider import FutuProvider
    import futu as ft
    HAS_FUTU = True
except:
    HAS_FUTU = False

from market_scanner import MarketScanner
from dingtalk_notifier import DingTalkNotifier


# 板块 -> 股票池映射
SECTOR_STOCKS = {
    '商业航天': [
        ('HK.01045', '亚太卫星'),
        ('HK.02357', '中航科工'),
        ('HK.00031', '航天控股'),
        ('HK.02865', '钧达股份'),
    ],
    '卫星': [
        ('HK.01045', '亚太卫星'),
        ('HK.00471', '中播数据'),
    ],
    '新能源汽车': [
        ('HK.01211', '比亚迪'),
        ('HK.02015', '理想汽车'),
        ('HK.09868', '小鹏汽车'),
        ('HK.09866', '蔚来'),
    ],
    'AI': [
        ('HK.09888', '百度'),
        ('HK.00020', '商汤'),
        ('HK.06082', '壁仞科技'),
    ],
    '人工智能': [
        ('HK.09888', '百度'),
        ('HK.00020', '商汤'),
    ],
    '机器人': [
        ('HK.01810', '小米'),
        ('HK.02382', '蓝思科技'),
    ],
    '光伏': [
        ('HK.03800', '协鑫科技'),
        ('HK.00968', '信义光能'),
    ],
    '芯片': [
        ('HK.00981', '中芯国际'),
        ('HK.01347', '华虹半导体'),
    ],
    '半导体': [
        ('HK.00981', '中芯国际'),
        ('HK.01347', '华虹半导体'),
    ],
    '互联网': [
        ('HK.09988', '阿里巴巴'),
        ('HK.00700', '腾讯'),
        ('HK.03690', '美团'),
        ('HK.09618', '京东'),
        ('HK.01024', '快手'),
    ],
    '地产': [
        ('HK.03688', '莱蒙国际'),
        ('HK.00607', '丰盛控股'),
    ],
    '软件': [
        ('HK.01679', '瑞斯康集团'),
    ],
    '电讯': [
        ('HK.00471', '中播数据'),
    ],
    '金融': [
        ('HK.00851', '盛源控股'),
    ],
    '医药': [
        ('HK.08247', '中生北控'),
    ],
    '原材料': [
        ('HK.01580', '大森控股'),
    ],
}


class HotSectorTTrading:
    """热门板块 + 做T推荐"""

    def __init__(self):
        self.scanner = MarketScanner()
        self.provider = None
        self.connected = False
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def connect_futu(self):
        """连接富途"""
        if not HAS_FUTU:
            return False
        try:
            self.provider = FutuProvider()
            self.provider.connect()
            self.connected = True
            return True
        except:
            return False

    def disconnect_futu(self):
        if self.provider:
            self.provider.disconnect()

    def get_stock_quote_futu(self, code: str) -> Dict:
        """从富途获取行情"""
        if not self.connected:
            return {}
        try:
            ret, data = self.provider.quote_ctx.get_stock_quote([code])
            if ret == ft.RET_OK and not data.empty:
                row = data.iloc[0]
                return {
                    'price': row['last_price'],
                    'high': row['high_price'],
                    'low': row['low_price'],
                    'prev_close': row['prev_close_price'],
                    'change_pct': (row['last_price'] - row['prev_close_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                    'amplitude': (row['high_price'] - row['low_price']) / row['prev_close_price'] * 100 if row['prev_close_price'] > 0 else 0,
                }
        except:
            pass
        return {}

    def get_stock_quote_eastmoney(self, code: str) -> Dict:
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
                high = d.get('f44', 0) / 1000
                low = d.get('f45', 0) / 1000

                return {
                    'price': price,
                    'high': high,
                    'low': low,
                    'prev_close': prev,
                    'change_pct': d.get('f170', 0) / 100,
                    'amplitude': d.get('f171', 0) / 100,
                    'vol_ratio': d.get('f50', 0) / 100,
                    'turnover': d.get('f168', 0) / 100,
                }
        except:
            pass
        return {}

    def get_stock_quote(self, code: str) -> Dict:
        """获取行情（优先富途，备用东财）"""
        if self.connected:
            quote = self.get_stock_quote_futu(code)
            if quote:
                return quote
        return self.get_stock_quote_eastmoney(code)

    def calculate_t_levels(self, code: str, quote: Dict) -> Dict:
        """计算做T点位"""
        result = {
            'buy_price': 0,
            'sell_price': 0,
            'stop_loss': 0,
            'expected_profit': 0,
        }

        price = quote.get('price', 0)
        high = quote.get('high', 0)
        low = quote.get('low', 0)
        prev_close = quote.get('prev_close', 0)

        if not all([price, high, low, prev_close]):
            return result

        # 经典枢轴点计算
        pivot = (high + low + prev_close) / 3
        support1 = 2 * pivot - high
        support2 = pivot - (high - low)
        resistance1 = 2 * pivot - low
        resistance2 = pivot + (high - low)

        # 做T点位
        result['buy_price'] = round(support1, 3)
        result['sell_price'] = round(resistance1, 3)
        result['stop_loss'] = round(support2, 3)

        if result['buy_price'] > 0:
            result['expected_profit'] = round((result['sell_price'] - result['buy_price']) / result['buy_price'] * 100, 2)

        return result

    def analyze_sector_stocks(self, sector_name: str, stocks: List[tuple]) -> List[Dict]:
        """分析板块内股票的做T机会"""
        results = []

        for code, name in stocks:
            quote = self.get_stock_quote(code)
            if not quote or quote.get('price', 0) <= 0:
                continue

            levels = self.calculate_t_levels(code, quote)

            # 计算做T评分
            score = 50  # 基础分
            reasons = []

            # 振幅加分
            amplitude = quote.get('amplitude', 0)
            if amplitude >= 5:
                score += 25
                reasons.append(f"振幅大({amplitude:.1f}%)")
            elif amplitude >= 3:
                score += 15
                reasons.append(f"振幅良好({amplitude:.1f}%)")
            elif amplitude >= 2:
                score += 10

            # 涨幅适中加分（不追高）
            change = quote.get('change_pct', 0)
            if 0 < change < 5:
                score += 15
                reasons.append("涨幅适中")
            elif change > 8:
                score -= 10
                reasons.append("涨幅过大")

            # 量比加分
            vol_ratio = quote.get('vol_ratio', 1)
            if vol_ratio >= 2:
                score += 10
                reasons.append("放量")

            # 预期收益加分
            if levels['expected_profit'] >= 3:
                score += 10

            results.append({
                'code': code.replace('HK.', ''),
                'name': name,
                'price': quote['price'],
                'change_pct': change,
                'amplitude': amplitude,
                'buy_price': levels['buy_price'],
                'sell_price': levels['sell_price'],
                'stop_loss': levels['stop_loss'],
                'expected_profit': levels['expected_profit'],
                'score': min(score, 100),
                'reason': '，'.join(reasons) if reasons else '波动一般',
            })

        # 按评分排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results

    def get_hot_sectors_with_t(self) -> Dict:
        """获取热门板块 + 做T推荐"""
        result = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'hot_sectors': [],
            't_recommendations': [],
        }

        # 1. 扫描热门板块
        print("🔍 扫描热门板块...")
        hot_industries = self.scanner.detect_hot_industries(min_stocks=2, min_avg_change=2.0)

        for ind in hot_industries[:6]:
            sector_info = {
                'name': ind['industry'],
                'change': ind['avg_change'],
                'count': ind['stock_count'],
                'leader': ind['leader']['name'],
                'leader_change': ind['leader']['change_pct'],
            }
            result['hot_sectors'].append(sector_info)

            # 2. 查找该板块的做T机会
            sector_name = ind['industry']
            stocks = []

            # 匹配板块股票池
            for key, stock_list in SECTOR_STOCKS.items():
                if key in sector_name or sector_name in key:
                    stocks.extend(stock_list)

            # 去重
            stocks = list(set(stocks))

            if stocks:
                print(f"📊 分析 {sector_name} 板块做T机会...")
                t_stocks = self.analyze_sector_stocks(sector_name, stocks)

                for t in t_stocks:
                    t['sector'] = sector_name
                    result['t_recommendations'].append(t)

        # 3. 按评分排序所有推荐
        result['t_recommendations'].sort(key=lambda x: x['score'], reverse=True)

        return result

    def format_report(self, result: Dict) -> str:
        """格式化报告"""
        content = f"""### 🔥 热门板块 + 做T推荐

**扫描时间:** {result['time']}

---

#### 📈 今日热门板块

"""
        for i, s in enumerate(result['hot_sectors'][:5], 1):
            content += f"**{i}. {s['name']}** +{s['change']:.1f}% ({s['count']}只)\n"
            content += f"> 领涨: {s['leader']} +{s['leader_change']:.1f}%\n\n"

        content += """---

#### 🎯 做T推荐标的

| 股票 | 代码 | 现价 | 涨幅 | 评分 | 买入位 | 卖出位 | 止损 | 预期 |
|------|------|------|------|------|--------|--------|------|------|
"""
        for t in result['t_recommendations'][:10]:
            icon = "✅" if t['score'] >= 70 else "⚠️" if t['score'] >= 55 else "❌"
            content += f"| {t['name'][:4]} | {t['code']} | {t['price']:.2f} | {t['change_pct']:+.1f}% | {icon}{t['score']} | {t['buy_price']:.2f} | {t['sell_price']:.2f} | {t['stop_loss']:.2f} | {t['expected_profit']:+.1f}% |\n"

        content += "\n---\n\n#### 📝 重点推荐\n\n"

        for t in result['t_recommendations'][:3]:
            if t['score'] >= 60:
                content += f"**{t['name']}** ({t['code']}) - {t['sector']}\n"
                content += f"- 现价: {t['price']:.2f} | 涨幅: {t['change_pct']:+.1f}%\n"
                content += f"- 📍 买入位: **{t['buy_price']:.2f}** (支撑位低吸)\n"
                content += f"- 🎯 目标位: **{t['sell_price']:.2f}** (压力位高抛)\n"
                content += f"- 🛑 止损位: **{t['stop_loss']:.2f}**\n"
                content += f"- 💰 预期收益: **{t['expected_profit']:+.1f}%**\n"
                content += f"- 理由: {t['reason']}\n\n"

        content += """---

#### ⚠️ 做T注意事项

1. **跟随热点**: 只做热门板块内的股票
2. **低吸高抛**: 在支撑位买，压力位卖
3. **严格止损**: 跌破止损位立即出局
4. **仓位控制**: 单只不超过30%仓位
5. **避开首尾**: 避开开盘/收盘30分钟

---

*数据来源: 东财+富途API*
"""
        return content


def scan_and_push():
    """扫描热门板块并推送做T推荐"""
    advisor = HotSectorTTrading()

    # 尝试连接富途（可选）
    if HAS_FUTU:
        advisor.connect_futu()

    try:
        result = advisor.get_hot_sectors_with_t()
        content = advisor.format_report(result)

        print(content)

        notifier = DingTalkNotifier()
        notifier.send_markdown("🔥 热门板块+做T", content)
        print("\n✅ 已推送到钉钉!")

        return content

    finally:
        advisor.disconnect_futu()


if __name__ == '__main__':
    scan_and_push()
