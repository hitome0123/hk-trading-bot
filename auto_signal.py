#!/usr/bin/env python3
"""
自动信号推送 - 监控并推送交易信号到Bark
"""

import yfinance as yf
import numpy as np
import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, List


CONFIG_FILE = os.path.expanduser('~/.hk_alert_config.json')


def load_config() -> Dict:
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'bark_key': '', 'alerts': []}


def send_bark(title: str, body: str, sound: str = 'alarm'):
    """发送Bark推送"""
    config = load_config()
    bark_key = config.get('bark_key', '')

    if not bark_key:
        print(f"[本地提醒] {title}: {body}")
        print('\a')  # 终端响铃
        return False

    url = f"https://api.day.app/{bark_key}/{title}/{body}"
    params = {'sound': sound, 'level': 'timeSensitive'}

    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            print(f"[已推送] {title}")
            return True
    except:
        pass

    print(f"[推送失败] {title}: {body}")
    return False


class SignalMonitor:
    """信号监控器"""

    def __init__(self):
        self.last_signals = {}  # 记录已发送的信号，避免重复

    def analyze_stock(self, ticker: str) -> Dict:
        """分析股票，返回信号"""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1mo')

            if len(hist) < 20:
                return None

            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            change = (current - prev) / prev * 100

            # 均线
            ma5 = hist['Close'].tail(5).mean()
            ma10 = hist['Close'].tail(10).mean()
            ma20 = hist['Close'].tail(20).mean()

            # RSI
            delta = hist['Close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # 量比
            vol_today = hist['Volume'].iloc[-1]
            vol_avg = hist['Volume'].tail(5).mean()
            vol_ratio = vol_today / vol_avg if vol_avg > 0 else 0

            # 突破检测
            high_20d = hist['High'].tail(20).max()
            low_20d = hist['Low'].tail(20).min()

            signals = []

            # 信号检测

            # 1. 放量突破新高
            if current > high_20d and vol_ratio > 1.5:
                signals.append({
                    'type': 'breakout',
                    'level': 'high',
                    'msg': f'放量突破20日新高! 量比{vol_ratio:.1f}x'
                })

            # 2. 跌破新低
            if current < low_20d:
                signals.append({
                    'type': 'breakdown',
                    'level': 'high',
                    'msg': f'跌破20日新低!'
                })

            # 3. 大涨(>5%)
            if change > 5:
                signals.append({
                    'type': 'surge',
                    'level': 'medium',
                    'msg': f'大涨{change:.1f}%!'
                })

            # 4. 大跌(<-5%)
            if change < -5:
                signals.append({
                    'type': 'plunge',
                    'level': 'high',
                    'msg': f'大跌{change:.1f}%!'
                })

            # 5. RSI超买
            if rsi > 80:
                signals.append({
                    'type': 'rsi_overbought',
                    'level': 'medium',
                    'msg': f'RSI超买({rsi:.0f})，注意回调'
                })

            # 6. RSI超卖
            if rsi < 20:
                signals.append({
                    'type': 'rsi_oversold',
                    'level': 'medium',
                    'msg': f'RSI超卖({rsi:.0f})，可能反弹'
                })

            # 7. 金叉
            ma5_prev = hist['Close'].tail(6).head(5).mean()
            ma10_prev = hist['Close'].tail(11).head(10).mean()
            if ma5_prev < ma10_prev and ma5 > ma10:
                signals.append({
                    'type': 'golden_cross',
                    'level': 'medium',
                    'msg': 'MA5金叉MA10'
                })

            # 8. 死叉
            if ma5_prev > ma10_prev and ma5 < ma10:
                signals.append({
                    'type': 'death_cross',
                    'level': 'medium',
                    'msg': 'MA5死叉MA10'
                })

            # 9. 异常放量(>3倍)
            if vol_ratio > 3:
                signals.append({
                    'type': 'volume_spike',
                    'level': 'medium',
                    'msg': f'异常放量! 量比{vol_ratio:.1f}x'
                })

            return {
                'ticker': ticker,
                'price': float(current),
                'change': float(change),
                'signals': signals
            }

        except Exception as e:
            return None

    def check_and_alert(self, watchlist: List[str]):
        """检查并发送提醒"""
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        for ticker in watchlist:
            result = self.analyze_stock(ticker)
            if not result or not result['signals']:
                continue

            for signal in result['signals']:
                # 生成唯一ID，避免重复推送
                signal_id = f"{ticker}_{signal['type']}_{today}"

                if signal_id in self.last_signals:
                    continue

                # 发送推送
                title = f"{ticker} {signal['msg']}"
                body = f"现价: {result['price']:.2f} ({result['change']:+.2f}%)"

                send_bark(title, body)
                self.last_signals[signal_id] = now

                # 同时打印
                level_icon = '🔴' if signal['level'] == 'high' else '🟡'
                print(f"{level_icon} [{now.strftime('%H:%M:%S')}] {title} - {body}")


def run_monitor(watchlist: List[str] = None, interval: int = 60):
    """运行监控"""
    if not watchlist:
        watchlist = [
            '0700.HK', '9888.HK', '9618.HK', '3690.HK',
            '1929.HK', '0386.HK', '0981.HK', '1024.HK',
            '2015.HK', '1211.HK', '6160.HK', '1816.HK'
        ]

    monitor = SignalMonitor()

    print("=" * 60)
    print(f"自动信号监控 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)
    print(f"监控股票: {', '.join(watchlist)}")
    print(f"检查间隔: {interval}秒")

    config = load_config()
    if config.get('bark_key'):
        print(f"Bark推送: 已配置")
    else:
        print(f"Bark推送: 未配置 (仅本地提醒)")

    print("=" * 60)
    print("按 Ctrl+C 停止\n")

    while True:
        try:
            monitor.check_and_alert(watchlist)
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n停止监控")
            break


def quick_scan(watchlist: List[str] = None):
    """快速扫描一次"""
    if not watchlist:
        watchlist = [
            '0700.HK', '9888.HK', '9618.HK', '3690.HK',
            '1929.HK', '0386.HK', '0981.HK', '1024.HK',
            '2015.HK', '1211.HK', '6160.HK', '1816.HK'
        ]

    monitor = SignalMonitor()

    print("\n" + "=" * 60)
    print(f"信号扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 60)

    found_signals = []

    for ticker in watchlist:
        result = monitor.analyze_stock(ticker)
        if result and result['signals']:
            for signal in result['signals']:
                found_signals.append({
                    'ticker': ticker,
                    'price': result['price'],
                    'change': result['change'],
                    **signal
                })

    if found_signals:
        # 按级别排序
        high_signals = [s for s in found_signals if s['level'] == 'high']
        medium_signals = [s for s in found_signals if s['level'] == 'medium']

        if high_signals:
            print("\n🔴 重要信号:")
            for s in high_signals:
                print(f"   {s['ticker']}: {s['msg']} (现价{s['price']:.2f}, {s['change']:+.2f}%)")

        if medium_signals:
            print("\n🟡 一般信号:")
            for s in medium_signals:
                print(f"   {s['ticker']}: {s['msg']} (现价{s['price']:.2f}, {s['change']:+.2f}%)")
    else:
        print("\n暂无信号")

    print("\n" + "=" * 60)


def test_bark():
    """测试Bark推送"""
    send_bark("测试推送", "如果你收到这条消息，Bark配置成功！")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python auto_signal.py scan      - 快速扫描一次")
        print("  python auto_signal.py watch     - 持续监控")
        print("  python auto_signal.py watch 30  - 指定间隔(秒)")
        print("  python auto_signal.py test      - 测试Bark推送")
        print("")
        print("配置Bark: python price_alert.py bark <your_bark_key>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'scan':
        quick_scan()
    elif cmd == 'watch':
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        run_monitor(interval=interval)
    elif cmd == 'test':
        test_bark()
    else:
        print("未知命令")
