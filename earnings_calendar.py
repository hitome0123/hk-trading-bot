#!/usr/bin/env python3
"""
财报日历 - 追踪港股/A股财报发布日期
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import yfinance as yf


class EarningsCalendar:
    """财报日历"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_hk_earnings(self, days: int = 30) -> List[Dict]:
        """
        获取港股即将发布财报的公司
        """
        earnings = []

        try:
            # 东财港股财报预告
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            params = {
                'sortColumns': 'NOTICE_DATE',
                'sortTypes': '-1',
                'pageSize': 50,
                'pageNumber': 1,
                'reportName': 'RPT_HKF10_FN_MAINNEW',
                'columns': 'SECUCODE,SECURITY_CODE,SECURITY_NAME_ABBR,REPORT_DATE,NOTICE_DATE,BASIC_EPS,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT',
                'source': 'WEB',
                'client': 'WEB',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'result' in data and data['result']:
                for item in data['result'].get('data', []):
                    notice_date = item.get('NOTICE_DATE', '')
                    if notice_date:
                        notice_date = notice_date[:10]
                    earnings.append({
                        'code': item.get('SECURITY_CODE', ''),
                        'name': item.get('SECURITY_NAME_ABBR', ''),
                        'report_date': item.get('REPORT_DATE', '')[:10] if item.get('REPORT_DATE') else '',
                        'notice_date': notice_date,
                        'eps': item.get('BASIC_EPS', 0),
                        'revenue': item.get('TOTAL_OPERATE_INCOME', 0),
                        'profit': item.get('PARENT_NETPROFIT', 0)
                    })

        except Exception as e:
            print(f"获取港股财报失败: {e}")

        return earnings

    def get_a_earnings(self, days: int = 7) -> List[Dict]:
        """
        获取A股即将发布财报/业绩预告的公司
        """
        earnings = []

        try:
            # 业绩预告
            url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
            end_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            start_date = datetime.now().strftime('%Y-%m-%d')

            params = {
                'sortColumns': 'NOTICE_DATE',
                'sortTypes': '-1',
                'pageSize': 50,
                'pageNumber': 1,
                'reportName': 'RPT_PUBLIC_OP_NEWPREDICT',
                'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,NOTICE_DATE,REPORT_DATE,PREDICT_FINANCE_CODE,PREDICT_FINANCE,PREDICT_AMT_LOWER,PREDICT_AMT_UPPER,ADD_AMP_LOWER,ADD_AMP_UPPER,PREDICT_CONTENT',
                'filter': f'(NOTICE_DATE>=\'{start_date}\')(NOTICE_DATE<=\'{end_date}\')',
                'source': 'WEB',
                'client': 'WEB',
                '_': int(time.time() * 1000)
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'result' in data and data['result']:
                for item in data['result'].get('data', []):
                    # 业绩类型
                    predict_type = item.get('PREDICT_FINANCE', '')
                    icon = ''
                    if '预增' in predict_type or '扭亏' in predict_type:
                        icon = '📈'
                    elif '预减' in predict_type or '首亏' in predict_type or '续亏' in predict_type:
                        icon = '📉'

                    earnings.append({
                        'code': item.get('SECURITY_CODE', ''),
                        'name': item.get('SECURITY_NAME_ABBR', ''),
                        'notice_date': item.get('NOTICE_DATE', '')[:10] if item.get('NOTICE_DATE') else '',
                        'report_date': item.get('REPORT_DATE', '')[:10] if item.get('REPORT_DATE') else '',
                        'predict_type': predict_type,
                        'change_lower': item.get('ADD_AMP_LOWER', 0),
                        'change_upper': item.get('ADD_AMP_UPPER', 0),
                        'icon': icon
                    })

        except Exception as e:
            print(f"获取A股业绩预告失败: {e}")

        return earnings

    def get_stock_earnings(self, ticker: str) -> Dict:
        """
        获取单只股票的财报信息
        """
        code = ticker.replace('.HK', '').replace('.SZ', '').replace('.SS', '')

        try:
            if '.HK' in ticker.upper() or (code.isdigit() and len(code) <= 5):
                # 港股 - 使用富途/雪球数据
                code_padded = code.zfill(5)

                # 尝试东财港股接口
                url = f"https://emweb.securities.eastmoney.com/PC_HKF10/FinancialAnalysis/PageAjax"
                params = {
                    'code': f'{code_padded}.HK',
                    'type': 'web'
                }

                resp = requests.get(url, params=params, headers=self.headers, timeout=10)
                data = resp.json()

                if data and 'zycwzb' in data:
                    items = data['zycwzb']
                    if items:
                        latest = items[0]
                        return {
                            'code': ticker,
                            'name': data.get('jbzl', {}).get('gsmc', ticker),
                            'latest_report': latest.get('REPORT_DATE', '')[:10] if latest.get('REPORT_DATE') else latest.get('date', ''),
                            'eps': float(latest.get('BASIC_EPS', 0) or 0),
                            'revenue': float(latest.get('TOTAL_OPERATE_INCOME', 0) or 0),
                            'profit': float(latest.get('PARENT_NETPROFIT', 0) or 0),
                            'history': [
                                {
                                    'report_date': i.get('REPORT_DATE', '')[:10] if i.get('REPORT_DATE') else i.get('date', ''),
                                    'eps': float(i.get('BASIC_EPS', 0) or 0),
                                    'profit': float(i.get('PARENT_NETPROFIT', 0) or 0)
                                } for i in items[:4]
                            ]
                        }

                # 备用：雪球
                url = f"https://stock.xueqiu.com/v5/stock/finance/cn/indicator.json"
                params = {
                    'symbol': f'{code_padded}.HK',
                    'type': 'all',
                    'is_detail': 'true',
                    'count': 4
                }
                headers = {**self.headers, 'Cookie': 'xq_a_token=test'}

                resp = requests.get(url, params=params, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data and 'data' in data and data['data'].get('list'):
                        items = data['data']['list']
                        latest = items[0]
                        return {
                            'code': ticker,
                            'name': ticker,
                            'latest_report': latest.get('report_name', ''),
                            'eps': float(latest.get('basic_eps', {}).get('value', 0) or 0),
                            'revenue': float(latest.get('total_revenue', {}).get('value', 0) or 0),
                            'profit': float(latest.get('net_profit_atsopc', {}).get('value', 0) or 0),
                            'history': []
                        }

        except Exception as e:
            pass  # 静默失败

        # 最后用yfinance
        try:
            yf_ticker = ticker.upper()
            if not yf_ticker.endswith('.HK'):
                yf_ticker += '.HK'

            stock = yf.Ticker(yf_ticker)
            info = stock.info

            # 获取财务数据
            financials = stock.quarterly_financials
            earnings = stock.quarterly_earnings

            result = {
                'code': ticker,
                'name': info.get('shortName', info.get('longName', ticker)),
                'latest_report': '',
                'eps': info.get('trailingEps', 0),
                'revenue': info.get('totalRevenue', 0),
                'profit': info.get('netIncomeToCommon', 0),
                'pe': info.get('trailingPE', 0),
                'history': []
            }

            if earnings is not None and not earnings.empty:
                for date, row in earnings.head(4).iterrows():
                    result['history'].append({
                        'report_date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)[:10],
                        'eps': row.get('Earnings', 0),
                        'revenue': row.get('Revenue', 0)
                    })

            if result['name'] != ticker or result['eps'] or result['profit']:
                return result

        except Exception as e:
            pass

        return {}

    def get_upcoming_earnings(self, watchlist: List[str] = None) -> List[Dict]:
        """
        获取关注列表中即将发布财报的股票
        """
        if not watchlist:
            # 默认关注列表
            watchlist = [
                '0700.HK', '9888.HK', '9618.HK', '3690.HK',  # 互联网
                '1929.HK', '0386.HK', '0981.HK', '1024.HK',  # 用户持仓
                '6160.HK', '2015.HK', '1211.HK',  # 热门
            ]

        results = []
        for ticker in watchlist:
            info = self.get_stock_earnings(ticker)
            if info:
                results.append(info)

        return results

    def get_important_dates(self) -> List[Dict]:
        """获取重要财报日期（大型公司）"""
        important = [
            {'code': '0700.HK', 'name': '腾讯', 'typical_date': '3月中/8月中'},
            {'code': '9988.HK', 'name': '阿里巴巴', 'typical_date': '2月/5月/8月/11月'},
            {'code': '9888.HK', 'name': '百度', 'typical_date': '2月底/5月中'},
            {'code': '9618.HK', 'name': '京东', 'typical_date': '3月初'},
            {'code': '3690.HK', 'name': '美团', 'typical_date': '3月底'},
            {'code': '1211.HK', 'name': '比亚迪', 'typical_date': '3月底'},
            {'code': '0981.HK', 'name': '中芯国际', 'typical_date': '2月中'},
            {'code': '1024.HK', 'name': '快手', 'typical_date': '3月中'},
        ]
        return important


def show_hk_earnings():
    """显示港股财报"""
    cal = EarningsCalendar()

    print("\n" + "=" * 70)
    print(f"港股最新财报 ({datetime.now().strftime('%Y-%m-%d')})")
    print("=" * 70)

    earnings = cal.get_hk_earnings()

    if earnings:
        print(f"\n{'代码':<8} {'名称':<12} {'报告期':>12} {'EPS':>8} {'净利润(亿)':>12}")
        print("-" * 70)

        for e in earnings[:20]:
            profit = e['profit'] / 100000000 if e['profit'] else 0
            eps = e['eps'] if e['eps'] else 0
            print(f"{e['code']:<8} {e['name']:<12} {e['report_date']:>12} {eps:>8.2f} {profit:>12.2f}")
    else:
        print("暂无数据")


def show_a_earnings():
    """显示A股业绩预告"""
    cal = EarningsCalendar()

    print("\n" + "=" * 70)
    print(f"A股业绩预告 ({datetime.now().strftime('%Y-%m-%d')})")
    print("=" * 70)

    earnings = cal.get_a_earnings(30)

    if earnings:
        # 按预告类型分组
        good = [e for e in earnings if '预增' in e['predict_type'] or '扭亏' in e['predict_type']]
        bad = [e for e in earnings if '预减' in e['predict_type'] or '首亏' in e['predict_type'] or '续亏' in e['predict_type']]

        if good:
            print("\n📈 业绩预增/扭亏:")
            print(f"{'代码':<8} {'名称':<12} {'类型':<8} {'变动幅度':>15}")
            print("-" * 50)
            for e in good[:10]:
                change = f"{e['change_lower']:.0f}%~{e['change_upper']:.0f}%" if e['change_lower'] else ''
                print(f"{e['code']:<8} {e['name']:<12} {e['predict_type']:<8} {change:>15}")

        if bad:
            print("\n📉 业绩预减/亏损:")
            print(f"{'代码':<8} {'名称':<12} {'类型':<8} {'变动幅度':>15}")
            print("-" * 50)
            for e in bad[:10]:
                change = f"{e['change_lower']:.0f}%~{e['change_upper']:.0f}%" if e['change_lower'] else ''
                print(f"{e['code']:<8} {e['name']:<12} {e['predict_type']:<8} {change:>15}")
    else:
        print("暂无业绩预告")


def show_stock_earnings(ticker: str):
    """显示单只股票财报"""
    cal = EarningsCalendar()

    ticker = ticker.upper()
    if not any(ticker.endswith(x) for x in ['.HK', '.SZ', '.SS']):
        ticker += '.HK'

    info = cal.get_stock_earnings(ticker)

    if info:
        print(f"\n{'='*50}")
        print(f"{info['name']} ({info['code']}) 财报信息")
        print(f"{'='*50}")
        print(f"最新报告期: {info['latest_report']}")

        if info.get('eps'):
            print(f"每股收益: {info['eps']:.2f}")
        if info.get('profit'):
            profit = info['profit'] / 100000000
            print(f"净利润: {profit:.2f} 亿")

        if info.get('history'):
            print(f"\n历史业绩:")
            print(f"{'报告期':<12} {'EPS':>10} {'净利润(亿)':>12}")
            print("-" * 40)
            for h in info['history']:
                profit = h['profit'] / 100000000 if h['profit'] else 0
                eps = h['eps'] if h['eps'] else 0
                print(f"{h['report_date']:<12} {eps:>10.2f} {profit:>12.2f}")
    else:
        print(f"未找到 {ticker} 的财报信息")


def show_watchlist_earnings():
    """显示关注列表的财报"""
    cal = EarningsCalendar()

    # 用户持仓
    watchlist = [
        '1929.HK',  # 周大福
        '0386.HK',  # 中石化
        '1024.HK',  # 快手
        '9618.HK',  # 京东
        '2357.HK',  # 中航科工
        '6082.HK',  # 壁仞科技
        '0981.HK',  # 中芯国际
    ]

    print("\n" + "=" * 70)
    print(f"持仓股票财报信息")
    print("=" * 70)

    for ticker in watchlist:
        info = cal.get_stock_earnings(ticker)
        if info:
            profit = info.get('profit', 0) / 100000000 if info.get('profit') else 0
            eps = info.get('eps', 0) if info.get('eps') else 0
            print(f"\n{info['name']} ({ticker})")
            print(f"  最新报告期: {info['latest_report']}")
            print(f"  EPS: {eps:.2f} | 净利润: {profit:.2f}亿")
        else:
            print(f"\n{ticker}: 暂无数据")


def show_important_dates():
    """显示重要财报日期"""
    cal = EarningsCalendar()

    print("\n" + "=" * 60)
    print("重要公司财报发布时间（参考）")
    print("=" * 60)
    print(f"{'代码':<10} {'公司':<12} {'通常发布时间':<20}")
    print("-" * 60)

    dates = cal.get_important_dates()
    for d in dates:
        print(f"{d['code']:<10} {d['name']:<12} {d['typical_date']:<20}")

    print("\n注：具体日期以公司公告为准")
    print("=" * 60)


def quick_check():
    """快速检查"""
    print("\n" + "=" * 70)
    print(f"财报快速检查 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 70)

    cal = EarningsCalendar()

    # A股业绩预告
    print("\n📊 近期A股业绩预告:")
    a_earnings = cal.get_a_earnings(7)
    good = [e for e in a_earnings if '预增' in e.get('predict_type', '') or '扭亏' in e.get('predict_type', '')]
    bad = [e for e in a_earnings if '预减' in e.get('predict_type', '') or '亏' in e.get('predict_type', '')]

    if good:
        print(f"  📈 预增/扭亏: {len(good)}家")
        for e in good[:3]:
            print(f"     {e['name']}: {e['predict_type']}")
    if bad:
        print(f"  📉 预减/亏损: {len(bad)}家")
        for e in bad[:3]:
            print(f"     {e['name']}: {e['predict_type']}")

    # 重要日期提醒
    print("\n📅 重要财报时间提醒:")
    now = datetime.now()
    month = now.month

    reminders = []
    if month in [2, 3]:
        reminders.append("腾讯年报(3月中)、百度(2月底)、京东(3月初)")
    if month in [5, 6]:
        reminders.append("一季报密集发布期")
    if month in [8, 9]:
        reminders.append("中报密集发布期，腾讯(8月中)")
    if month in [10, 11]:
        reminders.append("三季报密集发布期")

    if reminders:
        for r in reminders:
            print(f"  {r}")
    else:
        print("  当前无重要财报时间")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python earnings_calendar.py hk      - 港股最新财报")
        print("  python earnings_calendar.py a       - A股业绩预告")
        print("  python earnings_calendar.py stock 0700.HK  - 单只股票财报")
        print("  python earnings_calendar.py watch   - 持仓股票财报")
        print("  python earnings_calendar.py dates   - 重要财报日期")
        print("  python earnings_calendar.py quick   - 快速检查")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'hk':
        show_hk_earnings()
    elif cmd == 'a':
        show_a_earnings()
    elif cmd == 'stock' and len(sys.argv) >= 3:
        show_stock_earnings(sys.argv[2])
    elif cmd == 'watch':
        show_watchlist_earnings()
    elif cmd == 'dates':
        show_important_dates()
    elif cmd == 'quick':
        quick_check()
    else:
        print("未知命令")
