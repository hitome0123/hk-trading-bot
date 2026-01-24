#!/usr/bin/env python3
"""
港股板块异动扫描器
实时监控港股概念板块涨幅，发现商业航天等热点
解决：昨天商业航天暴涨未追踪的问题
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from hk_trading_bot.data_providers.futu_provider import FutuProvider
import futu as ft
from datetime import datetime
from typing import Dict, List
import time

# 港股热门概念板块配置
# 重点关注容易暴涨的新兴概念
HK_SECTORS = {
    '商业航天': [
        ('01045.HK', '亚太卫星'),
        ('02865.HK', '钧达股份'),
        ('00031.HK', '航天控股'),
        ('02357.HK', '中航科工'),
        ('02382.HK', '蓝思科技'),
        ('01725.HK', '中国技术'),
    ],
    '卫星通信': [
        ('01045.HK', '亚太卫星'),
        ('00763.HK', '中兴通讯'),
        ('02342.HK', '京信通信'),
        ('00552.HK', '中国通信服务'),
    ],
    'AI人工智能': [
        ('09888.HK', '百度'),
        ('00020.HK', '商汤'),
        ('01024.HK', '快手'),
        ('09618.HK', '京东'),
        ('03690.HK', '美团'),
    ],
    '机器人': [
        ('02382.HK', '蓝思科技'),
        ('01810.HK', '小米'),
        ('00285.HK', '比亚迪电子'),
        ('02018.HK', '瑞声科技'),
    ],
    '新能源汽车': [
        ('09866.HK', '蔚来'),
        ('02015.HK', '理想'),
        ('01211.HK', '比亚迪'),
        ('00175.HK', '吉利'),
        ('09868.HK', '小鹏'),
        ('02208.HK', '金风科技'),
    ],
    '光伏太阳能': [
        ('02865.HK', '钧达股份'),
        ('03800.HK', '协鑫科技'),
        ('00968.HK', '信义光能'),
        ('06865.HK', '福莱特玻璃'),
    ],
    '半导体芯片': [
        ('00981.HK', '中芯国际'),
        ('01347.HK', '华虹半导体'),
        ('02388.HK', '中银香港'),
    ],
    '科技互联网': [
        ('00700.HK', '腾讯'),
        ('09988.HK', '阿里巴巴'),
        ('09888.HK', '百度'),
        ('09618.HK', '京东'),
        ('03690.HK', '美团'),
        ('09999.HK', '网易'),
    ],
    '医药生物': [
        ('06160.HK', '百济神州'),
        ('02269.HK', '药明生物'),
        ('01177.HK', '中生制药'),
        ('02359.HK', '药明康德'),
    ],
    '消费零售': [
        ('01929.HK', '周大福'),
        ('09633.HK', '农夫山泉'),
        ('02331.HK', '李宁'),
        ('06862.HK', '海底捞'),
        ('09992.HK', '泡泡玛特'),
    ],
    '黄金贵金属': [
        ('02899.HK', '紫金矿业'),
        ('01818.HK', '招金矿业'),
        ('00813.HK', '世界黄金'),
        ('02890.HK', '卫龙美味'),
    ],
    '金融银行': [
        ('00005.HK', '汇丰'),
        ('01398.HK', '工商银行'),
        ('03988.HK', '中国银行'),
        ('02318.HK', '平安'),
        ('00388.HK', '港交所'),
    ],
}

# 重点监控的新兴概念（预警优先级更高）
HOT_CONCEPTS = ['商业航天', '卫星通信', 'AI人工智能', '机器人', '光伏太阳能']


class HKSectorScanner:
    """港股板块异动扫描器"""

    def __init__(self):
        self.provider = None
        self.connected = False

    def connect(self):
        """连接富途API"""
        if not self.connected:
            self.provider = FutuProvider()
            self.provider.connect()
            self.connected = True

    def disconnect(self):
        """断开连接"""
        if self.provider:
            self.provider.disconnect()
            self.connected = False

    def get_stock_quote(self, codes: List[str]) -> Dict:
        """批量获取股票行情"""
        quotes = {}
        try:
            ret, data = self.provider.quote_ctx.get_stock_quote(codes)
            if ret == ft.RET_OK:
                for _, row in data.iterrows():
                    code = row['code']
                    prev = row.get('prev_close_price', 0)
                    price = row.get('last_price', 0)
                    if prev > 0 and price > 0:
                        change_pct = (price - prev) / prev * 100
                        quotes[code] = {
                            'price': price,
                            'prev_close': prev,
                            'change_pct': change_pct,
                            'volume': row.get('volume', 0),
                            'turnover': row.get('turnover', 0),
                            'name': row.get('name', code),
                        }
        except Exception as e:
            print(f"获取行情失败: {e}")
        return quotes

    def scan_sector(self, sector_name: str, stocks: List) -> Dict:
        """扫描单个板块"""
        codes = [s[0] for s in stocks]
        names = {s[0]: s[1] for s in stocks}

        quotes = self.get_stock_quote(codes)
        if not quotes:
            return None

        results = []
        for code, data in quotes.items():
            results.append({
                'code': code,
                'name': names.get(code, data.get('name', '')),
                'price': data['price'],
                'change_pct': data['change_pct'],
                'turnover': data['turnover'],
            })

        if not results:
            return None

        # 计算板块平均涨跌幅
        avg_change = sum(r['change_pct'] for r in results) / len(results)
        up_count = sum(1 for r in results if r['change_pct'] > 0)

        # 按涨幅排序
        results.sort(key=lambda x: x['change_pct'], reverse=True)

        return {
            'name': sector_name,
            'avg_change': avg_change,
            'up_count': up_count,
            'total_count': len(results),
            'stocks': results,
            'leader': results[0] if results else None,
            'is_hot': sector_name in HOT_CONCEPTS,
        }

    def scan_all_sectors(self) -> List[Dict]:
        """扫描所有板块"""
        results = []

        for sector_name, stocks in HK_SECTORS.items():
            result = self.scan_sector(sector_name, stocks)
            if result:
                results.append(result)
            time.sleep(0.3)  # 避免API限流

        # 按涨幅排序
        results.sort(key=lambda x: x['avg_change'], reverse=True)
        return results

    def find_explosive_sectors(self, threshold: float = 3.0) -> List[Dict]:
        """找出暴涨板块"""
        all_sectors = self.scan_all_sectors()
        explosive = [s for s in all_sectors if s['avg_change'] >= threshold]

        for s in explosive:
            if s['avg_change'] >= 5:
                s['alert_level'] = 'HIGH'
            else:
                s['alert_level'] = 'MEDIUM'

        return explosive

    def get_sector_detail(self, sector_name: str) -> Dict:
        """获取指定板块详情"""
        if sector_name not in HK_SECTORS:
            # 尝试模糊匹配
            for name in HK_SECTORS:
                if sector_name in name or name in sector_name:
                    sector_name = name
                    break
            else:
                return None

        return self.scan_sector(sector_name, HK_SECTORS[sector_name])


def print_hk_sector_report():
    """打印港股板块扫描报告"""
    scanner = HKSectorScanner()
    scanner.connect()

    print("=" * 70)
    print(f"📊 港股板块异动扫描 | {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # 1. 暴涨板块预警
    print("\n🔥 【暴涨板块预警】(涨幅>3%)")
    print("-" * 70)
    explosive = scanner.find_explosive_sectors(threshold=3.0)

    if explosive:
        print(f"{'板块':<12} {'涨幅':>8} {'上涨/总数':>10} {'领涨股':>12} {'领涨幅':>8}")
        print("-" * 70)
        for s in explosive[:8]:
            alert = "⚠️" if s['alert_level'] == 'HIGH' else "📈"
            hot = "🌟" if s['is_hot'] else ""
            leader = s['leader']
            print(f"{alert} {s['name']:<10}{hot} {s['avg_change']:>+7.2f}% "
                  f"{s['up_count']}/{s['total_count']:>8} "
                  f"{leader['name'][:6]:>10} {leader['change_pct']:>+7.2f}%")
    else:
        print("  暂无涨幅超过3%的板块")

    # 2. 板块涨幅榜
    print("\n📈 【港股板块涨幅榜】")
    print("-" * 70)

    all_sectors = scanner.scan_all_sectors()
    print(f"{'排名':<4} {'板块':<12} {'涨幅':>8} {'领涨股':>10} {'领涨幅':>8}")
    print("-" * 70)

    for i, s in enumerate(all_sectors, 1):
        hot = "🌟" if s['is_hot'] else ""
        leader = s['leader']
        print(f"{i:<4} {s['name']:<10}{hot} {s['avg_change']:>+7.2f}% "
              f"{leader['name'][:6]:>10} {leader['change_pct']:>+7.2f}%")

    # 3. 最强板块详情
    if all_sectors:
        top = all_sectors[0]
        print(f"\n🏆 【最强板块详情: {top['name']}】")
        print("-" * 70)
        print(f"{'股票':<10} {'代码':<12} {'现价':>8} {'涨幅':>8} {'成交额(万)':>12}")
        print("-" * 70)

        for stock in top['stocks']:
            zt = "🔴" if stock['change_pct'] >= 9.9 else ""
            turnover_w = stock['turnover'] / 10000
            print(f"{stock['name']:<8} {stock['code']:<12} {stock['price']:>8.2f} "
                  f"{stock['change_pct']:>+7.2f}% {turnover_w:>11.0f} {zt}")

    print("\n" + "=" * 70)
    print("💡 提示: 🌟=重点关注概念 🔴=涨幅超10% ⚠️=板块涨幅>5%")
    print("=" * 70)

    scanner.disconnect()


def quick_alert(threshold: float = 4.0) -> List[Dict]:
    """快速预警"""
    scanner = HKSectorScanner()
    scanner.connect()

    alerts = scanner.find_explosive_sectors(threshold=threshold)

    if alerts:
        print(f"\n⚠️ 港股板块异动预警 ({datetime.now().strftime('%H:%M')})")
        for a in alerts[:5]:
            hot = "🌟" if a['is_hot'] else ""
            print(f"  {a['name']}{hot}: +{a['avg_change']:.2f}% | 领涨: {a['leader']['name']}")
    else:
        print(f"✅ 暂无涨幅超过{threshold}%的港股板块")

    scanner.disconnect()
    return alerts


def check_sector(sector_name: str):
    """查看指定板块"""
    scanner = HKSectorScanner()
    scanner.connect()

    result = scanner.get_sector_detail(sector_name)
    if result:
        print(f"\n📊 {result['name']} 成分股:")
        print("-" * 60)
        print(f"{'股票':<10} {'代码':<12} {'现价':>8} {'涨幅':>8}")
        print("-" * 60)
        for s in result['stocks']:
            zt = "🔴" if s['change_pct'] >= 9.9 else ""
            print(f"{s['name']:<8} {s['code']:<12} {s['price']:>8.2f} {s['change_pct']:>+7.2f}% {zt}")
        print(f"\n板块平均涨幅: {result['avg_change']:+.2f}%")
    else:
        print(f"❌ 未找到板块: {sector_name}")
        print(f"可用板块: {', '.join(HK_SECTORS.keys())}")

    scanner.disconnect()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "alert":
            threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
            quick_alert(threshold)
        elif cmd == "sector":
            if len(sys.argv) > 2:
                check_sector(sys.argv[2])
            else:
                print("用法: python hk_sector_scanner.py sector <板块名>")
                print(f"可用板块: {', '.join(HK_SECTORS.keys())}")
        else:
            print("用法:")
            print("  python hk_sector_scanner.py          - 完整扫描报告")
            print("  python hk_sector_scanner.py alert    - 快速预警")
            print("  python hk_sector_scanner.py alert 3  - 预警(阈值3%)")
            print("  python hk_sector_scanner.py sector 商业航天 - 查看板块")
    else:
        print_hk_sector_report()
