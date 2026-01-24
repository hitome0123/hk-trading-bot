#!/usr/bin/env python3
"""
港股定时推送服务
自动推送：热点板块、涨幅榜、资金流向等
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import time
import schedule
from datetime import datetime

from dingtalk_notifier import DingTalkNotifier
from market_scanner import MarketScanner
from smart_picker import CapitalFlowTracker

notifier = DingTalkNotifier()
scanner = MarketScanner()
flow_tracker = CapitalFlowTracker()

# 关注的股票
WATCH_STOCKS = [
    ('09988', '阿里巴巴'),
    ('00700', '腾讯控股'),
    ('03690', '美团'),
    ('01810', '小米'),
    ('09618', '京东'),
    ('01211', '比亚迪'),
    ('00981', '中芯国际'),
    ('01045', '亚太卫星'),
]


def push_morning_brief():
    """早盘快报 (9:30)"""
    print(f"[{datetime.now().strftime('%H:%M')}] 推送早盘快报...")

    content = f"""### 📊 港股早盘快报

**日期:** {datetime.now().strftime('%Y-%m-%d')} 周{['一','二','三','四','五','六','日'][datetime.now().weekday()]}

---

#### 🔥 热门板块
"""

    try:
        hot = scanner.detect_hot_industries(min_stocks=2, min_avg_change=1.0)
        for i, ind in enumerate(hot[:5], 1):
            content += f"{i}. **{ind['industry']}** +{ind['avg_change']:.2f}%\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    content += f"\n---\n*祝您投资顺利！*"

    notifier.send_markdown("📊 早盘快报", content)
    print("✅ 早盘快报已推送")


def push_hot_sectors():
    """热门板块推送 (每30分钟)"""
    print(f"[{datetime.now().strftime('%H:%M')}] 推送热门板块...")

    content = f"""### 🔥 港股热门板块

**时间:** {datetime.now().strftime('%H:%M')}

"""

    try:
        hot = scanner.detect_hot_industries(min_stocks=2, min_avg_change=2.0)

        if not hot:
            content += "暂无明显热点板块\n"
        else:
            for i, ind in enumerate(hot[:6], 1):
                leader = ind['leader']
                content += f"**{i}. {ind['industry']}** +{ind['avg_change']:.2f}%\n"
                content += f"> 领涨: {leader['name']} +{leader['change_pct']:.1f}%\n\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    notifier.send_markdown("🔥 热门板块", content)
    print("✅ 热门板块已推送")


def push_top_gainers():
    """涨幅榜推送 (每小时)"""
    print(f"[{datetime.now().strftime('%H:%M')}] 推送涨幅榜...")

    content = f"""### 🏆 港股涨幅榜

**时间:** {datetime.now().strftime('%H:%M')}

| 股票 | 涨幅 | 行业 |
|------|------|------|
"""

    try:
        gainers = scanner._get_eastmoney_hk_rank('asc', top_n=10)
        for s in gainers[:10]:
            content += f"| {s['name'][:6]} | +{s['change_pct']:.1f}% | {s['industry'][:4]} |\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    notifier.send_markdown("🏆 涨幅榜", content)
    print("✅ 涨幅榜已推送")


def push_capital_flow():
    """资金流向推送 (每小时)"""
    print(f"[{datetime.now().strftime('%H:%M')}] 推送资金流向...")

    content = f"""### 💰 关注股资金流向

**时间:** {datetime.now().strftime('%H:%M')}

| 股票 | 主力净流入 | 评分 |
|------|------------|------|
"""

    try:
        for code, name in WATCH_STOCKS[:6]:
            flow = flow_tracker.get_capital_flow(code)
            inflow = flow['main_inflow'] / 10000  # 亿
            icon = "🟢" if inflow > 0 else "🔴"
            content += f"| {name[:4]} | {icon}{inflow:+.1f}亿 | {flow['flow_score']} |\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    notifier.send_markdown("💰 资金流向", content)
    print("✅ 资金流向已推送")


def push_closing_summary():
    """收盘总结 (16:30)"""
    print(f"[{datetime.now().strftime('%H:%M')}] 推送收盘总结...")

    content = f"""### 📈 港股收盘总结

**日期:** {datetime.now().strftime('%Y-%m-%d')}

---

#### 🔥 今日热门板块
"""

    try:
        hot = scanner.detect_hot_industries(min_stocks=2, min_avg_change=2.0)
        for i, ind in enumerate(hot[:5], 1):
            content += f"{i}. **{ind['industry']}** +{ind['avg_change']:.2f}%\n"
    except:
        content += "获取失败\n"

    content += "\n#### 🏆 涨幅榜TOP5\n"
    try:
        gainers = scanner._get_eastmoney_hk_rank('asc', top_n=5)
        for i, s in enumerate(gainers[:5], 1):
            content += f"{i}. {s['name']} +{s['change_pct']:.1f}%\n"
    except:
        content += "获取失败\n"

    content += "\n#### 💰 关注股资金\n"
    try:
        for code, name in WATCH_STOCKS[:4]:
            flow = flow_tracker.get_capital_flow(code)
            inflow = flow['main_inflow'] / 10000
            icon = "🟢" if inflow > 0 else "🔴"
            content += f"- {name}: {icon}{inflow:+.1f}亿\n"
    except:
        content += "获取失败\n"

    content += "\n---\n*明天见！*"

    notifier.send_markdown("📈 收盘总结", content)
    print("✅ 收盘总结已推送")


def is_trading_time():
    """检查是否为交易时间"""
    now = datetime.now()
    # 周一到周五
    if now.weekday() >= 5:
        return False
    # 9:00 - 16:30
    hour = now.hour
    minute = now.minute
    if hour < 9 or (hour == 16 and minute > 30) or hour > 16:
        return False
    return True


def run_scheduler():
    """运行定时任务"""
    print("=" * 60)
    print("📅 港股定时推送服务启动")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\n定时任务:")
    print("  • 09:30 - 早盘快报")
    print("  • 每30分钟 - 热门板块 (交易时间)")
    print("  • 每小时 - 涨幅榜 + 资金流向 (交易时间)")
    print("  • 16:30 - 收盘总结")
    print("\n")

    # 设置定时任务
    schedule.every().day.at("09:30").do(push_morning_brief)
    schedule.every().day.at("16:30").do(push_closing_summary)

    # 交易时间每30分钟推送热门板块
    for t in ["09:30", "10:00", "10:30", "11:00", "11:30",
              "13:30", "14:00", "14:30", "15:00", "15:30", "16:00"]:
        schedule.every().day.at(t).do(push_hot_sectors)

    # 交易时间每小时推送涨幅榜和资金
    for t in ["10:00", "11:00", "14:00", "15:00", "16:00"]:
        schedule.every().day.at(t).do(push_top_gainers)
        schedule.every().day.at(t).do(push_capital_flow)

    print("⏳ 等待下一个推送时间...")
    print("   (按 Ctrl+C 停止)\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


def test_push():
    """测试推送"""
    print("测试推送所有内容...\n")

    print("1. 热门板块")
    push_hot_sectors()
    time.sleep(2)

    print("\n2. 涨幅榜")
    push_top_gainers()
    time.sleep(2)

    print("\n3. 资金流向")
    push_capital_flow()

    print("\n✅ 测试完成，请查看钉钉")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'test':
            test_push()
        elif cmd == 'morning':
            push_morning_brief()
        elif cmd == 'hot':
            push_hot_sectors()
        elif cmd == 'gainers':
            push_top_gainers()
        elif cmd == 'flow':
            push_capital_flow()
        elif cmd == 'close':
            push_closing_summary()
        else:
            print("用法:")
            print("  python auto_push.py         - 启动定时推送")
            print("  python auto_push.py test    - 测试所有推送")
            print("  python auto_push.py hot     - 推送热门板块")
            print("  python auto_push.py gainers - 推送涨幅榜")
            print("  python auto_push.py flow    - 推送资金流向")
    else:
        run_scheduler()
