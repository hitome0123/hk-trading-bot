#!/usr/bin/env python3
"""
港股智能选股器 - 综合版
板块异动后，自动筛选最值得买入的股票

策略：
1. 板块龙头筛选（涨幅 + 成交额）
2. 社交热度验证（雪球 + 东财股吧）
3. 资金流向确认（主力净流入）
4. 综合评分推荐
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import requests
import re
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from hk_trading_bot.data_providers.futu_provider import FutuProvider
import futu as ft


class SocialHeatTracker:
    """社交热度追踪器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
            'Accept': 'application/json',
        }

    def get_xueqiu_heat(self, stock_code: str) -> Dict:
        """
        获取雪球股票热度
        返回：关注人数、讨论数、24小时新增讨论
        """
        result = {'followers': 0, 'discussions': 0, 'hot_score': 0}

        try:
            # 转换代码格式: 01045.HK -> 01045
            code = stock_code.replace('.HK', '').replace('HK.', '')

            # 雪球搜索接口
            url = f"https://xueqiu.com/query/v1/symbol/search/status"
            params = {
                'q': code,
                'count': 5,
                'comment': 0,
                'symbol': f'HK{code}',
                'source': 'all',
            }
            headers = {
                **self.headers,
                'Cookie': 'xq_a_token=your_token;',  # 可选
                'Referer': 'https://xueqiu.com/',
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()

            # 统计讨论数
            if 'list' in data:
                result['discussions'] = len(data['list'])
                # 计算热度分（讨论数*10，最高100）
                result['hot_score'] = min(result['discussions'] * 10, 100)

        except Exception as e:
            pass

        return result

    def get_eastmoney_guba_heat(self, stock_code: str) -> Dict:
        """
        获取东方财富股吧热度
        返回：帖子数、阅读量、热度评分
        """
        result = {'posts': 0, 'views': 0, 'hot_score': 0}

        try:
            code = stock_code.replace('.HK', '').replace('HK.', '')

            # 东财港股股吧
            url = f"https://guba.eastmoney.com/list,hk{code}.html"
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                html = response.text
                # 提取帖子数（简单正则）
                posts_match = re.findall(r'阅读.*?(\d+)', html)
                if posts_match:
                    result['posts'] = len(posts_match)
                    # 热度分
                    result['hot_score'] = min(result['posts'] * 5, 100)

        except Exception as e:
            pass

        return result

    def get_eastmoney_rank(self, stock_code: str) -> Dict:
        """获取东财人气榜排名"""
        result = {'rank': 0, 'hot_score': 0}

        try:
            # 港股人气榜
            url = "https://emappdata.eastmoney.com/stockhk/hotrank/data"
            response = requests.get(url, headers=self.headers, timeout=10)
            data = response.json()

            code = stock_code.replace('.HK', '').replace('HK.', '')

            for i, item in enumerate(data.get('data', []), 1):
                if code in str(item.get('code', '')):
                    result['rank'] = i
                    # 排名越前分数越高
                    result['hot_score'] = max(100 - i * 2, 0)
                    break

        except Exception as e:
            pass

        return result

    def get_combined_heat(self, stock_code: str) -> Dict:
        """获取综合社交热度"""
        xueqiu = self.get_xueqiu_heat(stock_code)
        guba = self.get_eastmoney_guba_heat(stock_code)
        rank = self.get_eastmoney_rank(stock_code)

        # 综合热度分 (满分100)
        combined_score = (
            xueqiu['hot_score'] * 0.3 +
            guba['hot_score'] * 0.3 +
            rank['hot_score'] * 0.4
        )

        return {
            'xueqiu': xueqiu,
            'guba': guba,
            'rank': rank,
            'combined_score': round(combined_score, 1),
            'heat_level': self._get_heat_level(combined_score),
        }

    def _get_heat_level(self, score: float) -> str:
        if score >= 70:
            return '🔥爆热'
        elif score >= 50:
            return '🔶较热'
        elif score >= 30:
            return '🔷一般'
        else:
            return '❄️冷门'


class CapitalFlowTracker:
    """资金流向追踪器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
        }

    def get_capital_flow(self, stock_code: str) -> Dict:
        """获取资金流向数据"""
        result = {
            'main_inflow': 0,      # 主力净流入(万)
            'main_ratio': 0,       # 主力占比(%)
            'super_big_inflow': 0, # 超大单净流入
            'big_inflow': 0,       # 大单净流入
            'flow_score': 50,      # 资金评分(50为中性)
        }

        try:
            code = stock_code.replace('.HK', '').replace('HK.', '')

            # 东财港股资金流向接口
            url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
            params = {
                'secid': f'116.{code}',  # 港股前缀116
                'fields1': 'f1,f2,f3,f7',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57',
                'klt': '1',  # 日线
                'lmt': 1,
            }

            response = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = response.json()

            if data.get('data') and data['data'].get('klines'):
                line = data['data']['klines'][-1]
                parts = line.split(',')
                if len(parts) >= 6:
                    # 主力净流入
                    main_inflow = float(parts[1]) / 10000  # 转万元
                    result['main_inflow'] = round(main_inflow, 2)

                    # 计算资金评分
                    if main_inflow > 1000:
                        result['flow_score'] = 90
                    elif main_inflow > 500:
                        result['flow_score'] = 80
                    elif main_inflow > 100:
                        result['flow_score'] = 70
                    elif main_inflow > 0:
                        result['flow_score'] = 60
                    elif main_inflow > -100:
                        result['flow_score'] = 40
                    else:
                        result['flow_score'] = 20

        except Exception as e:
            pass

        return result


class SmartPicker:
    """港股智能选股器"""

    def __init__(self):
        self.provider = None
        self.heat_tracker = SocialHeatTracker()
        self.flow_tracker = CapitalFlowTracker()

    def connect(self):
        self.provider = FutuProvider()
        self.provider.connect()

    def disconnect(self):
        if self.provider:
            self.provider.disconnect()

    def get_sector_stocks(self, sector_name: str) -> List[Dict]:
        """从板块扫描器获取板块成分股"""
        from hk_sector_scanner import HKSectorScanner, HK_SECTORS

        if sector_name not in HK_SECTORS:
            # 模糊匹配
            for name in HK_SECTORS:
                if sector_name in name or name in sector_name:
                    sector_name = name
                    break
            else:
                return []

        stocks = HK_SECTORS[sector_name]
        codes = [s[0] for s in stocks]
        names = {s[0]: s[1] for s in stocks}

        # 获取实时行情
        results = []
        try:
            ret, data = self.provider.quote_ctx.get_stock_quote(codes)
            if ret == ft.RET_OK:
                for _, row in data.iterrows():
                    code = row['code']
                    prev = row.get('prev_close_price', 0)
                    price = row.get('last_price', 0)
                    if prev > 0 and price > 0:
                        results.append({
                            'code': code,
                            'name': names.get(code, row.get('name', '')),
                            'price': price,
                            'change_pct': (price - prev) / prev * 100,
                            'turnover': row.get('turnover', 0),
                            'volume': row.get('volume', 0),
                        })
        except Exception as e:
            print(f"获取行情失败: {e}")

        # 按涨幅排序
        results.sort(key=lambda x: x['change_pct'], reverse=True)
        return results

    def analyze_stock(self, stock: Dict) -> Dict:
        """
        综合分析单只股票
        返回评分和推荐
        """
        code = stock['code']

        # 1. 基础行情分数 (涨幅+成交额)
        change_score = min(stock['change_pct'] * 5, 40)  # 最高40分
        turnover_score = min(stock['turnover'] / 1000000, 20)  # 成交额加分，最高20分
        base_score = change_score + turnover_score

        # 2. 社交热度
        heat = self.heat_tracker.get_combined_heat(code)
        heat_score = heat['combined_score'] * 0.2  # 最高20分

        # 3. 资金流向
        flow = self.flow_tracker.get_capital_flow(code)
        flow_score = (flow['flow_score'] - 50) * 0.4  # -20到+20分

        # 4. 综合评分
        total_score = base_score + heat_score + flow_score
        total_score = max(0, min(100, total_score))  # 限制0-100

        # 5. 风险检查
        risks = []
        if stock['change_pct'] > 15:
            risks.append('涨幅过大追高风险')
            total_score -= 10
        if heat['combined_score'] < 20:
            risks.append('热度较低流动性风险')
        if flow['main_inflow'] < -500:
            risks.append('主力资金流出')
            total_score -= 15

        # 6. 生成推荐
        if total_score >= 75:
            recommendation = '⭐⭐⭐ 强烈推荐'
        elif total_score >= 60:
            recommendation = '⭐⭐ 可以关注'
        elif total_score >= 45:
            recommendation = '⭐ 谨慎参与'
        else:
            recommendation = '❌ 暂不推荐'

        return {
            **stock,
            'base_score': round(base_score, 1),
            'heat': heat,
            'heat_score': round(heat_score, 1),
            'flow': flow,
            'flow_score': round(flow_score, 1),
            'total_score': round(total_score, 1),
            'risks': risks,
            'recommendation': recommendation,
        }

    def pick_from_sector(self, sector_name: str, top_n: int = 3) -> List[Dict]:
        """
        从指定板块选股
        返回推荐的前N只股票
        """
        print(f"\n🔍 分析{sector_name}板块...")

        # 获取板块股票
        stocks = self.get_sector_stocks(sector_name)
        if not stocks:
            print(f"❌ 未找到板块: {sector_name}")
            return []

        print(f"📊 共{len(stocks)}只股票，开始综合分析...")

        # 分析每只股票
        results = []
        for i, stock in enumerate(stocks):
            print(f"   分析 {stock['name']}...", end='\r')
            analysis = self.analyze_stock(stock)
            results.append(analysis)
            time.sleep(0.5)  # 避免请求过快

        # 按综合评分排序
        results.sort(key=lambda x: x['total_score'], reverse=True)

        return results[:top_n]

    def quick_pick(self, sector_name: str) -> Dict:
        """
        快速选股 - 直接返回最推荐的一只
        """
        picks = self.pick_from_sector(sector_name, top_n=1)
        return picks[0] if picks else None


def print_pick_report(sector_name: str):
    """打印选股报告"""
    picker = SmartPicker()
    picker.connect()

    print("=" * 70)
    print(f"🎯 港股智能选股 | {sector_name}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = picker.pick_from_sector(sector_name, top_n=5)

    if not results:
        print("\n❌ 未找到推荐股票")
        picker.disconnect()
        return

    print(f"\n📊 综合评分排名 TOP{len(results)}")
    print("-" * 70)

    for i, r in enumerate(results, 1):
        print(f"\n{'='*60}")
        print(f"🏆 第{i}名: {r['name']} ({r['code']})")
        print(f"{'='*60}")

        # 基础行情
        print(f"📈 现价: {r['price']:.2f} | 涨幅: {r['change_pct']:+.2f}%")
        print(f"💰 成交额: {r['turnover']/10000:.0f}万")

        # 社交热度
        heat = r['heat']
        print(f"🔥 社交热度: {heat['combined_score']:.0f}分 {heat['heat_level']}")
        if heat['rank'].get('rank'):
            print(f"   └─ 东财人气榜: 第{heat['rank']['rank']}名")

        # 资金流向
        flow = r['flow']
        flow_icon = "📈" if flow['main_inflow'] > 0 else "📉"
        print(f"{flow_icon} 主力资金: {flow['main_inflow']:+.0f}万")

        # 综合评分
        print(f"\n📊 评分明细:")
        print(f"   行情分: {r['base_score']:.0f} | 热度分: {r['heat_score']:.0f} | 资金分: {r['flow_score']:+.0f}")
        print(f"   ─────────────────────────")
        print(f"   综合评分: {r['total_score']:.0f}/100")

        # 风险提示
        if r['risks']:
            print(f"\n⚠️ 风险提示: {', '.join(r['risks'])}")

        # 推荐等级
        print(f"\n💡 推荐: {r['recommendation']}")

    # 最终推荐
    top = results[0]
    print(f"\n{'='*70}")
    print(f"🎯 最终推荐: {top['name']} ({top['code']})")
    print(f"   评分: {top['total_score']:.0f}分 | {top['recommendation']}")
    print(f"   买入参考: 现价 {top['price']:.2f}")
    print(f"{'='*70}")

    picker.disconnect()


def auto_pick_from_hot_sector():
    """自动从最热板块选股"""
    from hk_sector_scanner import HKSectorScanner

    print("🔍 扫描热门板块...")

    scanner = HKSectorScanner()
    scanner.connect()
    sectors = scanner.scan_all_sectors()
    scanner.disconnect()

    if not sectors:
        print("❌ 未发现热门板块")
        return

    # 取涨幅最高的板块
    top_sector = sectors[0]
    print(f"\n🔥 最热板块: {top_sector['name']} (+{top_sector['avg_change']:.2f}%)")

    # 从该板块选股
    print_pick_report(top_sector['name'])


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sector = sys.argv[1]
        if sector == "auto":
            auto_pick_from_hot_sector()
        else:
            print_pick_report(sector)
    else:
        print("用法:")
        print("  python smart_picker.py 商业航天    - 从指定板块选股")
        print("  python smart_picker.py auto       - 自动从最热板块选股")
        print("")
        print("可用板块: 商业航天, 卫星通信, AI人工智能, 机器人, 新能源汽车, 光伏太阳能, 半导体芯片, 科技互联网, 医药生物, 消费零售, 黄金贵金属, 金融银行")
