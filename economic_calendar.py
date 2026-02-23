#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
宏观经济日历 - 经济数据发布日程
Economic Calendar - Market Moving Events Tracker

功能:
1. 获取全球重要经济数据发布日程
2. 筛选高影响力事件
3. 与港股/美股开盘时间关联
4. 提供交易提醒

数据来源:
- Investing.com 经济日历 (免费)
- Trading Economics API (需订阅)
- Finnhub 经济日历 (免费tier)

用法:
    python economic_calendar.py today      # 今日日程
    python economic_calendar.py week       # 本周日程
    python economic_calendar.py us         # 美国数据
    python economic_calendar.py cn         # 中国数据
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import urllib.request
import urllib.parse


class Impact(Enum):
    """影响程度"""
    HIGH = "高"
    MEDIUM = "中"
    LOW = "低"


@dataclass
class EconomicEvent:
    """经济事件"""
    time: str                # 发布时间 (HKT)
    country: str             # 国家/地区
    event: str               # 事件名称
    impact: str              # 影响程度
    actual: str              # 实际值
    forecast: str            # 预期值
    previous: str            # 前值
    currency: str            # 影响货币

    def to_dict(self):
        return asdict(self)


class EconomicCalendar:
    """宏观经济日历"""

    # 重要经济指标 (按影响力排序)
    KEY_INDICATORS = {
        'US': [
            # 顶级影响力
            ('Non-Farm Payrolls', '非农就业', Impact.HIGH),
            ('FOMC', '美联储利率决议', Impact.HIGH),
            ('CPI', '消费者物价指数', Impact.HIGH),
            ('Core CPI', '核心CPI', Impact.HIGH),
            ('GDP', '国内生产总值', Impact.HIGH),
            ('Fed Chair Powell', '鲍威尔讲话', Impact.HIGH),
            # 高影响力
            ('Unemployment Rate', '失业率', Impact.HIGH),
            ('PPI', '生产者物价指数', Impact.MEDIUM),
            ('Retail Sales', '零售销售', Impact.MEDIUM),
            ('ISM Manufacturing', 'ISM制造业PMI', Impact.MEDIUM),
            ('PCE', '个人消费支出', Impact.MEDIUM),
            # 中等影响力
            ('Initial Jobless Claims', '初请失业金', Impact.MEDIUM),
            ('Consumer Confidence', '消费者信心', Impact.MEDIUM),
            ('Durable Goods', '耐用品订单', Impact.MEDIUM),
        ],
        'CN': [
            ('GDP', '国内生产总值', Impact.HIGH),
            ('CPI', '消费者物价指数', Impact.HIGH),
            ('PPI', '生产者物价指数', Impact.HIGH),
            ('PMI', '制造业PMI', Impact.HIGH),
            ('Caixin PMI', '财新PMI', Impact.HIGH),
            ('Trade Balance', '贸易数据', Impact.MEDIUM),
            ('Industrial Production', '工业增加值', Impact.MEDIUM),
            ('Retail Sales', '社会零售销售', Impact.MEDIUM),
            ('LPR', '贷款市场报价利率', Impact.MEDIUM),
        ],
        'EU': [
            ('ECB Interest Rate', '欧央行利率决议', Impact.HIGH),
            ('CPI', '通胀数据', Impact.HIGH),
            ('GDP', '国内生产总值', Impact.HIGH),
            ('PMI', '制造业PMI', Impact.MEDIUM),
        ],
        'JP': [
            ('BOJ Interest Rate', '日本央行利率', Impact.HIGH),
            ('CPI', '通胀数据', Impact.MEDIUM),
            ('GDP', '国内生产总值', Impact.MEDIUM),
        ],
    }

    # 市场时间表 (HKT)
    MARKET_HOURS = {
        'HK': {'open': '09:30', 'close': '16:00', 'name': '港股'},
        'CN': {'open': '09:30', 'close': '15:00', 'name': 'A股'},
        'US': {'open': '21:30', 'close': '04:00', 'name': '美股'},  # 夏令时
        'US_WINTER': {'open': '22:30', 'close': '05:00', 'name': '美股'},  # 冬令时
    }

    # 美国数据发布时间 (北京时间/香港时间)
    US_DATA_TIMES = {
        'Non-Farm Payrolls': '20:30',  # 每月第一个周五
        'CPI': '20:30',
        'FOMC': '02:00',  # 凌晨
        'GDP': '20:30',
        'Retail Sales': '20:30',
        'Initial Jobless Claims': '20:30',  # 每周四
    }

    def __init__(self, cache_dir: str = None):
        self.cache_dir = cache_dir or os.path.expanduser('~/.hk-trading-bot/calendar_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        # Finnhub API (免费)
        self.finnhub_token = os.environ.get('FINNHUB_API_KEY', '')

    def get_trading_day_events(self, date: datetime = None) -> List[EconomicEvent]:
        """
        获取指定日期的经济事件

        注意: 此方法返回模拟数据
        真实数据需要通过 WebSearch 或 API 获取
        """
        if date is None:
            date = datetime.now()

        # 返回示例事件结构
        events = []

        # 周四固定事件
        if date.weekday() == 3:  # 周四
            events.append(EconomicEvent(
                time='20:30',
                country='US',
                event='Initial Jobless Claims (初请失业金)',
                impact='中',
                actual='-',
                forecast='220K',
                previous='215K',
                currency='USD'
            ))

        # 周五可能有非农
        if date.weekday() == 4 and date.day <= 7:  # 第一个周五
            events.append(EconomicEvent(
                time='20:30',
                country='US',
                event='Non-Farm Payrolls (非农就业)',
                impact='高',
                actual='-',
                forecast='200K',
                previous='175K',
                currency='USD'
            ))

        return events

    def get_week_events(self, start_date: datetime = None) -> Dict[str, List[EconomicEvent]]:
        """获取一周的经济事件"""
        if start_date is None:
            # 找到本周一
            today = datetime.now()
            start_date = today - timedelta(days=today.weekday())

        week_events = {}
        for i in range(7):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            events = self.get_trading_day_events(date)
            if events:
                week_events[date_str] = events

        return week_events

    def get_upcoming_key_events(self) -> str:
        """
        获取即将到来的重要事件

        返回搜索查询建议，用于 WebSearch
        """
        today = datetime.now()

        output = []
        output.append("=" * 70)
        output.append("📅 宏观经济日历")
        output.append("=" * 70)
        output.append("")
        output.append(f"📆 今日: {today.strftime('%Y年%m月%d日 %A')}")
        output.append("")

        # 本周重要事件预览
        output.append("【本周重要事件】")
        output.append("")

        # 周一至周五的固定事件
        weekday = today.weekday()

        if weekday <= 4:  # 工作日
            output.append("  📊 每日关注:")
            output.append("     - 08:30 中国PMI数据 (月初)")
            output.append("     - 09:30 港股/A股开盘")
            output.append("     - 21:30 美股开盘")
            output.append("")

        if weekday == 3 or (weekday < 3):  # 周四或之前
            output.append("  📋 周四 (美东20:30/香港时间):")
            output.append("     - Initial Jobless Claims 初请失业金")
            output.append("")

        if weekday <= 4:
            output.append("  📋 周五 (如果是月初第一个周五):")
            output.append("     - Non-Farm Payrolls 非农就业数据")
            output.append("     - Unemployment Rate 失业率")
            output.append("")

        # 搜索建议
        output.append("【获取最新日历】")
        output.append("")
        output.append("🔍 推荐搜索查询 (用于 WebSearch):")
        output.append(f"  1. \"economic calendar {today.strftime('%B %Y')} important events\"")
        output.append(f"  2. \"US economic data release {today.strftime('%Y-%m-%d')} to {(today + timedelta(days=7)).strftime('%Y-%m-%d')}\"")
        output.append("  3. \"Fed meeting schedule 2026\"")
        output.append("  4. \"China economic data calendar\"")
        output.append("")

        # 数据来源
        output.append("【推荐数据源】")
        output.append("  🌐 Investing.com: https://www.investing.com/economic-calendar/")
        output.append("  🌐 Trading Economics: https://tradingeconomics.com/calendar")
        output.append("  🌐 Finnhub: https://finnhub.io/docs/api/economic-calendar")
        output.append("")

        # 常见事件影响
        output.append("【事件影响指南】")
        output.append("")
        output.append("  🔴 高影响力 (可能导致市场大幅波动):")
        output.append("     - FOMC 利率决议: 决定美联储利率走向")
        output.append("     - 非农就业: 美国就业健康度晴雨表")
        output.append("     - CPI 通胀: 影响利率预期")
        output.append("     - GDP: 经济增长速度")
        output.append("")
        output.append("  🟡 中影响力:")
        output.append("     - PMI: 制造业景气度")
        output.append("     - 零售销售: 消费者信心")
        output.append("     - 初请失业金: 每周就业数据")
        output.append("")

        # 港股相关性
        output.append("【港股影响】")
        output.append("")
        output.append("  📈 美联储加息 → 港股承压 (资金外流)")
        output.append("  📈 中国PMI强劲 → 中概股/港股上涨")
        output.append("  📈 非农超预期 → 美股波动,隔日影响港股")
        output.append("  📈 中国GDP好 → 恒指上行")
        output.append("")

        output.append("=" * 70)
        output.append(f"更新时间: {today.strftime('%Y-%m-%d %H:%M')}")
        output.append("💡 使用 WebSearch 获取最新经济日历数据")
        output.append("=" * 70)

        return "\n".join(output)

    def format_event(self, event: EconomicEvent) -> str:
        """格式化单个事件"""
        impact_emoji = "🔴" if event.impact == "高" else "🟡" if event.impact == "中" else "🟢"

        return (
            f"  {event.time} {impact_emoji} [{event.country}] {event.event}\n"
            f"         预期: {event.forecast} | 前值: {event.previous}"
        )

    def get_event_impact_on_hk(self, event: EconomicEvent) -> str:
        """分析事件对港股的影响"""
        event_lower = event.event.lower()

        # 美联储政策
        if 'fomc' in event_lower or 'fed' in event_lower:
            return "⚡ 直接影响: 利率变动影响港股估值和资金流向"

        # 美国就业数据
        if 'payroll' in event_lower or 'employment' in event_lower:
            return "📊 间接影响: 影响美联储政策预期，隔日传导至港股"

        # 中国数据
        if event.country == 'CN':
            return "🎯 直接影响: 中国经济数据直接影响港股中资股"

        # 通胀数据
        if 'cpi' in event_lower or 'inflation' in event_lower:
            return "📈 影响: 通胀数据影响利率预期"

        return "📋 关注: 可能影响市场情绪"


def main():
    """CLI入口"""
    calendar = EconomicCalendar()

    if len(sys.argv) < 2:
        # 默认显示今日日程
        print(calendar.get_upcoming_key_events())
        return

    cmd = sys.argv[1].lower()

    if cmd == 'today':
        print(calendar.get_upcoming_key_events())

    elif cmd == 'week':
        print(calendar.get_upcoming_key_events())
        print("\n📅 使用 WebSearch 查询完整周日历")

    elif cmd == 'us':
        print("🇺🇸 美国经济数据日历\n")
        print("使用 WebSearch 搜索:")
        print("  \"US economic calendar this week high impact\"")

    elif cmd == 'cn':
        print("🇨🇳 中国经济数据日历\n")
        print("使用 WebSearch 搜索:")
        print("  \"China economic data release schedule\"")

    elif cmd == 'fed':
        print("🏛️ 美联储会议日程\n")
        print("使用 WebSearch 搜索:")
        print("  \"FOMC meeting schedule 2026\"")

    elif cmd == 'help':
        print("""
宏观经济日历 - 使用指南

用法:
  python economic_calendar.py [命令]

命令:
  today   今日经济日历
  week    本周经济日历
  us      美国数据日历
  cn      中国数据日历
  fed     美联储会议日程
  help    显示帮助

示例:
  python economic_calendar.py today
  python economic_calendar.py week

数据源:
  - Investing.com 经济日历
  - Trading Economics
  - Finnhub API (免费)

💡 提示: 使用 Claude WebSearch 可获取最新日历数据
        """)

    else:
        print(f"未知命令: {cmd}")
        print("使用 'help' 查看帮助")


if __name__ == "__main__":
    main()
