#!/usr/bin/env python3
"""
港股价格提醒 - 支持Bark推送到iPhone
"""

import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, List
import yfinance as yf

ALERT_FILE = os.path.expanduser('~/.hk_alerts.json')
CONFIG_FILE = os.path.expanduser('~/.hk_alert_config.json')


def load_config() -> Dict:
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'bark_key': '', 'alerts': []}


def save_config(config: Dict):
    """保存配置"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def set_bark_key(key: str):
    """设置Bark Key"""
    config = load_config()
    config['bark_key'] = key
    save_config(config)
    print(f"Bark Key已设置: {key[:10]}...")


def send_bark(title: str, body: str, sound: str = 'alarm'):
    """发送Bark推送"""
    config = load_config()
    bark_key = config.get('bark_key', '')

    if not bark_key:
        print("未设置Bark Key，仅终端提醒")
        print(f"\a{title}: {body}")  # 终端响铃
        return False

    url = f"https://api.day.app/{bark_key}/{title}/{body}"
    params = {
        'sound': sound,
        'level': 'timeSensitive'  # 即时通知
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            print(f"已推送: {title}")
            return True
        else:
            print(f"推送失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"推送错误: {e}")
        return False


def add_alert(ticker: str, price: float, direction: str, name: str = ''):
    """
    添加价格提醒
    direction: 'above' 高于触发, 'below' 低于触发
    """
    config = load_config()

    ticker = ticker.upper()
    if not ticker.endswith('.HK'):
        ticker += '.HK'

    alert = {
        'ticker': ticker,
        'name': name,
        'price': price,
        'direction': direction,
        'triggered': False,
        'created': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

    config['alerts'].append(alert)
    save_config(config)

    dir_text = "高于" if direction == 'above' else "低于"
    print(f"已添加提醒: {name or ticker} {dir_text} {price}")


def remove_alert(ticker: str = None, index: int = None):
    """删除提醒"""
    config = load_config()

    if index is not None and 0 <= index < len(config['alerts']):
        removed = config['alerts'].pop(index)
        save_config(config)
        print(f"已删除: {removed['ticker']} {removed['price']}")
        return

    if ticker:
        ticker = ticker.upper()
        if not ticker.endswith('.HK'):
            ticker += '.HK'
        config['alerts'] = [a for a in config['alerts'] if a['ticker'] != ticker]
        save_config(config)
        print(f"已删除 {ticker} 的所有提醒")


def show_alerts():
    """显示所有提醒"""
    config = load_config()

    if not config['alerts']:
        print("暂无价格提醒")
        return

    print("\n" + "=" * 60)
    print("价格提醒列表")
    print("=" * 60)
    print(f"{'#':<3} {'股票':<12} {'方向':<6} {'目标价':>8} {'状态':<6}")
    print("-" * 60)

    for i, a in enumerate(config['alerts']):
        dir_text = "高于" if a['direction'] == 'above' else "低于"
        status = "已触发" if a.get('triggered') else "等待中"
        print(f"{i:<3} {a['name'] or a['ticker']:<12} {dir_text:<6} {a['price']:>8.2f} {status:<6}")

    print("=" * 60)
    bark_key = config.get('bark_key', '')
    print(f"Bark推送: {'已配置' if bark_key else '未配置'}")


def check_alerts(once: bool = False, interval: int = 30):
    """
    检查价格并触发提醒
    once: 只检查一次
    interval: 检查间隔(秒)
    """
    print("开始监控价格...")
    print(f"检查间隔: {interval}秒")
    print("按 Ctrl+C 停止\n")

    while True:
        config = load_config()
        alerts = [a for a in config['alerts'] if not a.get('triggered')]

        if not alerts:
            print("没有待触发的提醒")
            if once:
                break
            time.sleep(interval)
            continue

        # 获取价格
        tickers = list(set(a['ticker'] for a in alerts))

        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period='1d')
                if len(hist) == 0:
                    continue

                current = hist['Close'].iloc[-1]

                for a in alerts:
                    if a['ticker'] != ticker or a.get('triggered'):
                        continue

                    triggered = False
                    if a['direction'] == 'above' and current >= a['price']:
                        triggered = True
                    elif a['direction'] == 'below' and current <= a['price']:
                        triggered = True

                    if triggered:
                        dir_text = "突破" if a['direction'] == 'above' else "跌破"
                        name = a['name'] or ticker
                        title = f"{name} {dir_text} {a['price']}"
                        body = f"现价 {current:.2f}"

                        send_bark(title, body)
                        print(f"\n{'!'*50}")
                        print(f"触发: {title} - {body}")
                        print(f"{'!'*50}\n")

                        # 标记已触发
                        a['triggered'] = True
                        a['triggered_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                        a['triggered_price'] = current

            except Exception as e:
                print(f"获取{ticker}失败: {e}")

        # 保存状态
        config['alerts'] = [a for a in config['alerts'] if not a.get('triggered')] + \
                          [a for a in config['alerts'] if a.get('triggered')]
        save_config(config)

        if once:
            break

        now = datetime.now().strftime('%H:%M:%S')
        print(f"\r[{now}] 监控中... {len(alerts)}个提醒", end='', flush=True)
        time.sleep(interval)


def quick_setup():
    """快速设置止盈止损提醒"""
    print("\n快速设置止盈止损")
    print("-" * 40)

    ticker = input("股票代码: ").strip().upper()
    if not ticker.endswith('.HK'):
        ticker += '.HK'

    name = input("股票名称(可选): ").strip()
    take_profit = input("止盈价: ").strip()
    stop_loss = input("止损价: ").strip()

    if take_profit:
        add_alert(ticker, float(take_profit), 'above', name)
    if stop_loss:
        add_alert(ticker, float(stop_loss), 'below', name)

    print("\n设置完成! 运行 'python price_alert.py watch' 开始监控")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python price_alert.py bark <your_bark_key>  - 设置Bark Key")
        print("  python price_alert.py add 1929.HK 14.40 above 周大福  - 添加提醒")
        print("  python price_alert.py add 1929.HK 13.70 below 周大福  - 添加止损提醒")
        print("  python price_alert.py list                   - 显示所有提醒")
        print("  python price_alert.py del 0                  - 删除第0个提醒")
        print("  python price_alert.py watch                  - 开始监控")
        print("  python price_alert.py setup                  - 快速设置")
        print("\nBark Key获取: 在iPhone安装Bark App，复制Key")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'bark' and len(sys.argv) >= 3:
        set_bark_key(sys.argv[2])
    elif cmd == 'add' and len(sys.argv) >= 5:
        ticker = sys.argv[2]
        price = float(sys.argv[3])
        direction = sys.argv[4]
        name = sys.argv[5] if len(sys.argv) > 5 else ''
        add_alert(ticker, price, direction, name)
    elif cmd == 'list':
        show_alerts()
    elif cmd == 'del' and len(sys.argv) >= 3:
        if sys.argv[2].isdigit():
            remove_alert(index=int(sys.argv[2]))
        else:
            remove_alert(ticker=sys.argv[2])
    elif cmd == 'watch':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        check_alerts(interval=interval)
    elif cmd == 'setup':
        quick_setup()
    else:
        print("参数错误，运行 python price_alert.py 查看帮助")
