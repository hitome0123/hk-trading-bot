#!/usr/bin/env python3
"""
港股资金流向监控 - 南向资金/个股资金流向
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class FundFlowMonitor:
    """资金流向监控"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Referer': 'https://finance.sina.com.cn'
        }

    def get_south_flow(self) -> Dict:
        """
        获取南向资金流向（港股通）
        南向 = 大陆资金流入港股
        """
        try:
            # 东方财富API - 港股通资金流向
            url = "https://push2.eastmoney.com/api/qt/kamtbs.rtmin/get"
            params = {
                'fields1': 'f1,f2,f3,f4',
                'fields2': 'f51,f52,f53,f54,f55,f56',
                'ut': 'b2884a393a59ad64002292a3e90d46a5',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                d = data['data']
                # 解析沪港通南向和深港通南向
                s2n = d.get('s2n', [])
                hgt = d.get('hgt', [])  # 沪股通
                sgt = d.get('sgt', [])  # 深股通

                # 获取最新值（最后一个数据点）
                south_hk = 0
                south_sz = 0
                if s2n and isinstance(s2n, list) and len(s2n) > 0:
                    latest = s2n[-1].split(',') if isinstance(s2n[-1], str) else []
                    if len(latest) >= 2:
                        south_hk = float(latest[1]) / 100 if latest[1] != '-' else 0  # 亿

                # 备用：直接从hgt/sgt获取
                if hgt and isinstance(hgt, list) and len(hgt) > 0:
                    latest = hgt[-1].split(',') if isinstance(hgt[-1], str) else []
                    if len(latest) >= 2:
                        try:
                            south_sz = float(latest[1]) / 100 if latest[1] != '-' else 0
                        except:
                            pass

                return {
                    'south_total': south_hk + south_sz,
                    'south_sh': south_hk,
                    'south_sz': south_sz,
                    'north_total': 0,  # 需要另外的API
                    'update_time': datetime.now().strftime('%H:%M:%S')
                }
        except Exception as e:
            print(f"获取南向资金失败: {e}")

        return {}

    def get_stock_fund_flow(self, ticker: str) -> Dict:
        """
        获取个股资金流向
        """
        # 转换代码格式
        code = ticker.replace('.HK', '')

        try:
            # 新浪财经API
            url = f"https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzj_zjlrqs"
            params = {
                'page': 1,
                'num': 20,
                'sort': 'opendate',
                'asc': 0,
                'bankuai': f'hk{code}'
            }

            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200 and resp.text:
                # 解析返回数据
                text = resp.text.strip()
                if text.startswith('['):
                    data = json.loads(text)
                    if data:
                        latest = data[0]
                        return {
                            'date': latest.get('opendate', ''),
                            'main_inflow': float(latest.get('r0_net', 0)) / 10000,  # 主力净流入(万)
                            'main_inflow_pct': float(latest.get('r0_ratio', 0)),
                            'retail_inflow': float(latest.get('r3_net', 0)) / 10000,
                            'super_big': float(latest.get('r0_net', 0)) / 10000,  # 超大单
                            'big': float(latest.get('r1_net', 0)) / 10000,  # 大单
                            'medium': float(latest.get('r2_net', 0)) / 10000,  # 中单
                            'small': float(latest.get('r3_net', 0)) / 10000,  # 小单
                        }
        except Exception as e:
            print(f"获取{ticker}资金流向失败: {e}")

        return {}

    def get_hk_top_flow(self, direction: str = 'in', top_n: int = 10) -> List[Dict]:
        """
        获取港股资金流入/流出排行
        direction: 'in' 流入, 'out' 流出
        """
        try:
            # 东方财富港股资金流向
            url = "https://push2.eastmoney.com/api/qt/clist/get"

            # fid: f62=主力净流入, f184=主力净流入占比
            sort_field = 'f62' if direction == 'in' else 'f62'
            order = 'desc' if direction == 'in' else 'asc'

            params = {
                'pn': 1,
                'pz': top_n,
                'po': 1 if direction == 'in' else 0,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': sort_field,
                'fs': 'b:DLMK0144',  # 港股
                'fields': 'f2,f3,f12,f14,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data and data['data']:
                results = []
                for item in data['data'].get('diff', []):
                    results.append({
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'price': item.get('f2', 0),
                        'change_pct': item.get('f3', 0),
                        'main_net': item.get('f62', 0) / 10000,  # 主力净流入(万)
                        'main_pct': item.get('f184', 0),  # 主力净流入占比
                        'super_big': item.get('f66', 0) / 10000,  # 超大单
                        'big': item.get('f72', 0) / 10000,  # 大单
                        'medium': item.get('f78', 0) / 10000,  # 中单
                        'small': item.get('f84', 0) / 10000,  # 小单
                    })
                return results
        except Exception as e:
            print(f"获取港股资金排行失败: {e}")

        return []

    def get_sector_flow(self) -> List[Dict]:
        """获取港股板块资金流向"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1,
                'pz': 20,
                'po': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'fid': 'f62',
                'fs': 'b:BK0921',  # 港股行业板块
                'fields': 'f2,f3,f12,f14,f62,f184,f66,f72,f78,f84',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data and data['data']:
                results = []
                for item in data['data'].get('diff', []):
                    results.append({
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'change_pct': item.get('f3', 0),
                        'main_net': item.get('f62', 0) / 100000000,  # 主力净流入(亿)
                        'main_pct': item.get('f184', 0),
                    })
                return results
        except Exception as e:
            print(f"获取板块资金流向失败: {e}")

        return []


def show_south_flow():
    """显示南向资金"""
    monitor = FundFlowMonitor()
    flow = monitor.get_south_flow()

    if flow:
        print("\n" + "=" * 50)
        print(f"南向资金流向 ({flow.get('update_time', '')})")
        print("=" * 50)

        south = flow.get('south_total', 0)
        icon = '🟢' if south > 0 else '🔴'
        print(f"\n{icon} 南向资金(港股通): {south:+.2f} 亿")
        print(f"   沪港通南向: {flow.get('south_sh', 0):+.2f} 亿")
        print(f"   深港通南向: {flow.get('south_sz', 0):+.2f} 亿")

        north = flow.get('north_total', 0)
        icon = '🟢' if north > 0 else '🔴'
        print(f"\n{icon} 北向资金(A股): {north:+.2f} 亿")

        print("\n" + "=" * 50)
        if south > 10:
            print("📈 南向资金大幅流入，港股看涨")
        elif south > 0:
            print("📊 南向资金小幅流入")
        elif south > -10:
            print("📊 南向资金小幅流出")
        else:
            print("📉 南向资金大幅流出，港股承压")
    else:
        print("获取南向资金失败")


def show_top_inflow(top_n: int = 10):
    """显示资金流入排行"""
    monitor = FundFlowMonitor()
    stocks = monitor.get_hk_top_flow('in', top_n)

    if stocks:
        print("\n" + "=" * 70)
        print("港股主力资金流入 TOP 10")
        print("=" * 70)
        print(f"{'代码':<8} {'名称':<12} {'涨跌':>8} {'主力净流入':>12} {'占比':>8}")
        print("-" * 70)

        for s in stocks:
            change = s['change_pct']
            icon = '🔴' if change < 0 else '🟢' if change > 0 else '⚪'
            main_net = s['main_net']
            if abs(main_net) >= 10000:
                net_str = f"{main_net/10000:.1f}亿"
            else:
                net_str = f"{main_net:.0f}万"

            print(f"{s['code']:<8} {s['name']:<12} {change:>+7.2f}% {net_str:>12} {s['main_pct']:>+7.1f}% {icon}")
    else:
        print("获取资金排行失败")


def show_top_outflow(top_n: int = 10):
    """显示资金流出排行"""
    monitor = FundFlowMonitor()
    stocks = monitor.get_hk_top_flow('out', top_n)

    if stocks:
        print("\n" + "=" * 70)
        print("港股主力资金流出 TOP 10")
        print("=" * 70)
        print(f"{'代码':<8} {'名称':<12} {'涨跌':>8} {'主力净流出':>12} {'占比':>8}")
        print("-" * 70)

        for s in stocks:
            change = s['change_pct']
            icon = '🔴' if change < 0 else '🟢' if change > 0 else '⚪'
            main_net = abs(s['main_net'])
            if main_net >= 10000:
                net_str = f"{main_net/10000:.1f}亿"
            else:
                net_str = f"{main_net:.0f}万"

            print(f"{s['code']:<8} {s['name']:<12} {change:>+7.2f}% {net_str:>12} {s['main_pct']:>+7.1f}% {icon}")
    else:
        print("获取资金排行失败")


def show_stock_flow(ticker: str):
    """显示个股资金流向"""
    monitor = FundFlowMonitor()
    flow = monitor.get_stock_fund_flow(ticker)

    if flow:
        print(f"\n{ticker} 资金流向:")
        print(f"  主力净流入: {flow.get('main_inflow', 0):.0f}万")
        print(f"  超大单: {flow.get('super_big', 0):.0f}万")
        print(f"  大单: {flow.get('big', 0):.0f}万")
        print(f"  中单: {flow.get('medium', 0):.0f}万")
        print(f"  小单: {flow.get('small', 0):.0f}万")
    else:
        print(f"获取{ticker}资金流向失败")


def quick_analysis():
    """快速分析"""
    print("\n" + "=" * 70)
    print(f"港股资金流向快速分析 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    monitor = FundFlowMonitor()

    # 南向资金
    flow = monitor.get_south_flow()
    if flow:
        south = flow.get('south_total', 0)
        icon = '🟢' if south > 0 else '🔴'
        print(f"\n{icon} 南向资金: {south:+.2f} 亿")

    # 资金流入前5
    print("\n📈 主力流入 TOP 5:")
    stocks = monitor.get_hk_top_flow('in', 5)
    for i, s in enumerate(stocks):
        main_net = s['main_net']
        if abs(main_net) >= 10000:
            net_str = f"{main_net/10000:.1f}亿"
        else:
            net_str = f"{main_net:.0f}万"
        print(f"  {i+1}. {s['name']}: {net_str} ({s['change_pct']:+.1f}%)")

    # 资金流出前5
    print("\n📉 主力流出 TOP 5:")
    stocks = monitor.get_hk_top_flow('out', 5)
    for i, s in enumerate(stocks):
        main_net = abs(s['main_net'])
        if main_net >= 10000:
            net_str = f"{main_net/10000:.1f}亿"
        else:
            net_str = f"{main_net:.0f}万"
        print(f"  {i+1}. {s['name']}: -{net_str} ({s['change_pct']:+.1f}%)")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python fund_flow.py south     - 查看南向资金")
        print("  python fund_flow.py in        - 资金流入排行")
        print("  python fund_flow.py out       - 资金流出排行")
        print("  python fund_flow.py stock 0700.HK  - 个股资金流向")
        print("  python fund_flow.py quick     - 快速分析")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'south':
        show_south_flow()
    elif cmd == 'in':
        show_top_inflow()
    elif cmd == 'out':
        show_top_outflow()
    elif cmd == 'stock' and len(sys.argv) >= 3:
        show_stock_flow(sys.argv[2])
    elif cmd == 'quick':
        quick_analysis()
    else:
        print("未知命令")
