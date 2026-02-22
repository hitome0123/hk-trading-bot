#!/usr/bin/env python3
"""
港股交易监控守护进程 v2.0
基于《港股交易完整策略手册_v2.0.md》
"""
import sys
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

def load_watchlist():
    """加载自选股列表"""
    watchlist_file = Path.home() / 'hk-trading-bot' / 'watchlist.json'
    try:
        if watchlist_file.exists():
            with open(watchlist_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('categories', {})
        return {}
    except Exception as e:
        print(f"⚠️ 读取自选股失败: {e}")
        return {}

def get_current_time_info():
    """获取当前时间信息"""
    now = datetime.now()
    return {
        'now': now,
        'hour': now.hour,
        'minute': now.minute,
        'weekday': now.weekday(),
        'time_str': now.strftime('%H:%M')
    }

def is_trading_day(t):
    """判断是否交易日（港股：周一到周五）"""
    return t['weekday'] < 5

def get_trading_phase(t):
    """
    判断当前交易阶段
    返回: phase_name, scan_interval
    """
    if not is_trading_day(t):
        return "周末休市", 3600

    hour, minute = t['hour'], t['minute']

    # 盘前准备 08:30-09:00
    if hour == 8 and minute >= 30:
        return "盘前准备", 1800  # 30分钟执行一次

    # 观察期 09:30-10:00
    if (hour == 9 and minute >= 30) or (hour == 10 and minute == 0):
        return "观察期", 600  # 10分钟执行一次

    # 狙击窗口1 10:00-12:00
    if 10 <= hour < 12:
        return "狙击窗口1", 300  # 5分钟执行一次

    # 午休 12:00-13:00
    if 12 <= hour < 13:
        return "午休", 1800  # 30分钟执行一次

    # 狙击窗口2 13:00-15:00
    if 13 <= hour < 15:
        return "狙击窗口2", 300  # 5分钟执行一次

    # 收盘准备 15:00-15:30
    if hour == 15 and minute < 30:
        return "收盘准备", 600  # 10分钟执行一次

    # 复盘时段 16:00-17:00
    if 16 <= hour < 17:
        return "复盘时段", 3600  # 1小时执行一次

    # 非交易时间
    return "非交易时间", 3600

def run_pre_market_scan():
    """盘前准备：扫描热门板块 + 稀缺股 + 找补涨机会"""
    try:
        print(f"\n{'='*60}")
        print(f"📊 盘前准备 - 扫描市场信号")
        print(f"{'='*60}")

        # 1. 显示自选股
        watchlist = load_watchlist()
        if watchlist:
            print("\n📋 今日自选股监控列表：")
            for category, stocks in watchlist.items():
                print(f"\n  【{category}】")
                for stock in stocks[:5]:  # 每类显示前5只
                    print(f"    • {stock['code'].replace('HK.', ''):<6} {stock['name']:<10} ({stock['sector']})")

        # 2. 热门板块扫描
        print("\n🔥 正在扫描今日热门板块...")
        print("板块轮动：机器人 → AI大模型 → GPU → 新能源")
        print("关注龙头：09880优必选, 00100MiniMax, 06082壁仞, 09988阿里")

        # 2. 稀缺股扫描
        print("\n🔍 正在扫描稀缺股突破信号...")
        result = subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/my_strategy_helper.py',
            'scan'
        ], timeout=120, capture_output=True, text=True)

        # 输出关键信息
        for line in result.stdout.split('\n'):
            if any(kw in line for kw in ['⭐', '突破', '评分', '最优']):
                print(line)

        # 3. 找补涨机会
        print("\n🔍 正在查找龙头补涨机会...")
        result = subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/my_strategy_helper.py',
            'laggards'
        ], timeout=120, capture_output=True, text=True)

        for line in result.stdout.split('\n'):
            if any(kw in line for kw in ['补涨', '龙头', '掉队']):
                print(line)

        print(f"\n✅ 盘前扫描完成")

    except subprocess.TimeoutExpired:
        print(f"⚠️ 盘前扫描超时")
    except Exception as e:
        print(f"❌ 盘前扫描错误: {e}")

def run_intraday_monitor():
    """盘中监控：监控持仓 + 扫描突破信号"""
    try:
        print(f"\n{'='*60}")
        print(f"🎯 盘中监控 - 狙击突破信号")
        print(f"{'='*60}")

        # 显示监控的自选股数量
        watchlist = load_watchlist()
        if watchlist:
            total_stocks = sum(len(stocks) for stocks in watchlist.values())
            print(f"📊 正在监控 {total_stocks} 只自选股...")

        # 稀缺股扫描（快速版）
        result = subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/my_strategy_helper.py',
            'scan'
        ], timeout=90, capture_output=True, text=True)

        # 只输出有突破信号的股票
        for line in result.stdout.split('\n'):
            if any(kw in line for kw in ['⭐⭐⭐', '突破买入']):
                print(line)

        print(f"✅ 盘中扫描完成")

    except subprocess.TimeoutExpired:
        print(f"⚠️ 盘中监控超时")
    except Exception as e:
        print(f"❌ 盘中监控错误: {e}")

def run_close_reminder():
    """收盘提醒：提醒平仓"""
    print(f"\n{'='*60}")
    print(f"⚠️  收盘提醒：15:30前必须平掉所有仓位！")
    print(f"{'='*60}")
    print(f"铁律：不持仓过夜！")
    print(f"")

def run_daily_review():
    """复盘：生成今日交易总结"""
    print(f"\n{'='*60}")
    print(f"📝 复盘时段 - 准备明天观察名单")
    print(f"{'='*60}")
    print(f"请手动填写交易记录表")
    print(f"")

def main():
    """主循环"""
    print(f"\n{'='*60}")
    print(f"🚀 港股交易监控系统 v2.0 启动")
    print(f"{'='*60}")
    print(f"基于: 港股交易完整策略手册_v2.0.md")
    print(f"策略: 日内T+0狙击 + 稀缺股波段")
    print(f"目标: 日赚300元 → 500元 → 800元 → 1000元")
    print(f"{'='*60}\n")

    last_phase = None

    while True:
        t = get_current_time_info()
        phase, interval = get_trading_phase(t)

        # 显示当前阶段（阶段切换时）
        if phase != last_phase:
            print(f"\n[{t['now']}] 📍 当前阶段: {phase}")
            last_phase = phase

        # 根据阶段执行不同任务
        if phase == "盘前准备":
            run_pre_market_scan()

        elif phase == "观察期":
            print(f"[{t['time_str']}] 👀 观察期 - 禁止交易，等待10:00")

        elif phase == "狙击窗口1" or phase == "狙击窗口2":
            run_intraday_monitor()

        elif phase == "午休":
            print(f"[{t['time_str']}] 💤 午休时段")

        elif phase == "收盘准备":
            run_close_reminder()

        elif phase == "复盘时段":
            run_daily_review()

        elif phase == "周末休市":
            print(f"[{t['time_str']}] 🏖️  周末休市，等待下周一开盘")

        else:
            print(f"[{t['time_str']}] 💤 非交易时间")

        # 等待下次扫描
        time.sleep(interval)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✅ 监控系统已停止")
        sys.exit(0)
