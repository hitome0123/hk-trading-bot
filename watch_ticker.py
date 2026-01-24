#!/usr/bin/env python3
"""
港股盯盘工具 - 实时监控价格并提醒
用法: python watch_ticker.py <股票代码> [刷新间隔秒数]
示例: python watch_ticker.py 6160.HK 30
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers import EnhancedDataProvider


class TickerWatcher:
    """股票盯盘器"""

    def __init__(self, ticker: str, plan: Optional[Dict] = None):
        self.ticker = ticker.upper()
        if not self.ticker.endswith('.HK'):
            self.ticker += '.HK'

        self.data_provider = EnhancedDataProvider()
        self.start_price = None
        self.high_price = None
        self.low_price = None
        self.last_price = None
        self.update_count = 0

        # 交易计划（可自定义）
        self.plan = plan or {}

    def set_plan(self, entry_low: float, entry_high: float, stop_loss: float,
                 take_profit_1: float, take_profit_2: float):
        """设置交易计划"""
        self.plan = {
            'entry_low': entry_low,
            'entry_high': entry_high,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2
        }

    def get_current_price(self) -> Optional[float]:
        """获取当前价格"""
        try:
            price_data = self.data_provider.yahoo_provider.get_price_data(self.ticker, 5)
            if price_data and price_data.get('close'):
                return price_data['close'][-1]
        except Exception as e:
            print(f"   ⚠️ 获取价格失败: {e}")
        return None

    def check_signals(self, price: float) -> list:
        """检查信号"""
        signals = []

        if not self.plan:
            return signals

        # 检查止损
        if price <= self.plan.get('stop_loss', 0):
            signals.append(('🔴 止损触发！', 'STOP_LOSS'))

        # 检查止盈1
        if price >= self.plan.get('take_profit_1', float('inf')):
            signals.append(('🟢 止盈1触发！减半仓', 'TP1'))

        # 检查止盈2
        if price >= self.plan.get('take_profit_2', float('inf')):
            signals.append(('🟢 止盈2触发！清仓', 'TP2'))

        # 检查买入区间
        entry_low = self.plan.get('entry_low', 0)
        entry_high = self.plan.get('entry_high', float('inf'))
        if entry_low <= price <= entry_high:
            signals.append(('🟡 进入买入区间', 'ENTRY'))

        return signals

    def format_change(self, price: float, base_price: float) -> str:
        """格式化涨跌幅"""
        if base_price == 0:
            return "N/A"
        change = (price - base_price) / base_price * 100
        if change >= 0:
            return f"+{change:.2f}%"
        return f"{change:.2f}%"

    def print_status(self, price: float):
        """打印状态"""
        now = datetime.now().strftime('%H:%M:%S')

        # 更新统计
        if self.start_price is None:
            self.start_price = price
        if self.high_price is None or price > self.high_price:
            self.high_price = price
        if self.low_price is None or price < self.low_price:
            self.low_price = price

        # 价格变化
        change_from_start = self.format_change(price, self.start_price)
        change_from_last = ""
        if self.last_price:
            diff = price - self.last_price
            if diff != 0:
                arrow = "↑" if diff > 0 else "↓"
                change_from_last = f" {arrow}{abs(diff):.2f}"

        self.last_price = price
        self.update_count += 1

        # 构建状态行
        print(f"\r[{now}] {self.ticker} 💲{price:.2f}{change_from_last} | 涨跌:{change_from_start} | 高:{self.high_price:.2f} 低:{self.low_price:.2f}", end="", flush=True)

    def print_plan(self):
        """打印交易计划"""
        if not self.plan:
            return

        print(f"\n📋 交易计划:")
        print(f"   买入区间: {self.plan.get('entry_low', 'N/A'):.2f} - {self.plan.get('entry_high', 'N/A'):.2f}")
        print(f"   止损: {self.plan.get('stop_loss', 'N/A'):.2f}")
        print(f"   止盈1: {self.plan.get('take_profit_1', 'N/A'):.2f}")
        print(f"   止盈2: {self.plan.get('take_profit_2', 'N/A'):.2f}")

    def watch(self, interval: int = 30, duration_minutes: int = 240):
        """
        开始盯盘
        interval: 刷新间隔（秒）
        duration_minutes: 持续时间（分钟）
        """
        print(f"\n{'='*60}")
        print(f"👁️ 开始盯盘: {self.ticker}")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔄 刷新间隔: {interval}秒")
        print(f"⏱️ 持续时间: {duration_minutes}分钟")
        self.print_plan()
        print(f"{'='*60}")
        print(f"\n按 Ctrl+C 停止盯盘\n")

        start_time = time.time()
        max_duration = duration_minutes * 60

        try:
            while True:
                # 检查是否超时
                elapsed = time.time() - start_time
                if elapsed > max_duration:
                    print(f"\n\n⏰ 盯盘时间结束（{duration_minutes}分钟）")
                    break

                # 获取价格
                price = self.get_current_price()

                if price:
                    # 打印状态
                    self.print_status(price)

                    # 检查信号
                    signals = self.check_signals(price)
                    if signals:
                        print()  # 换行
                        for msg, signal_type in signals:
                            print(f"\n{'!'*60}")
                            print(f"🚨 {msg}")
                            print(f"   当前价格: {price:.2f}")
                            print(f"{'!'*60}")

                            # 止损或止盈2触发时发出警报
                            if signal_type in ['STOP_LOSS', 'TP2']:
                                # 响铃提醒（终端）
                                print('\a' * 3)

                # 等待下次刷新
                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n👋 停止盯盘")

        # 打印汇总
        self.print_summary()

    def print_summary(self):
        """打印盯盘汇总"""
        print(f"\n{'='*60}")
        print(f"📊 盯盘汇总: {self.ticker}")
        print(f"{'='*60}")
        print(f"   开始价格: {self.start_price:.2f}" if self.start_price else "   开始价格: N/A")
        print(f"   最终价格: {self.last_price:.2f}" if self.last_price else "   最终价格: N/A")
        print(f"   最高价格: {self.high_price:.2f}" if self.high_price else "   最高价格: N/A")
        print(f"   最低价格: {self.low_price:.2f}" if self.low_price else "   最低价格: N/A")
        if self.start_price and self.last_price:
            print(f"   总涨跌幅: {self.format_change(self.last_price, self.start_price)}")
        print(f"   刷新次数: {self.update_count}")
        print(f"{'='*60}\n")


def main():
    if len(sys.argv) < 2:
        print("用法: python watch_ticker.py <股票代码> [刷新间隔秒数]")
        print("示例: python watch_ticker.py 6160.HK 30")
        print("\n预设交易计划会自动加载（如果有）")
        return

    ticker = sys.argv[1].upper()
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # 创建盯盘器
    watcher = TickerWatcher(ticker)

    # 预设一些常用股票的交易计划
    preset_plans = {
        '6160.HK': {  # 百济神州
            'entry_low': 195.60,
            'entry_high': 202.20,
            'stop_loss': 190.65,
            'take_profit_1': 208.00,
            'take_profit_2': 215.00
        },
        '0700.HK': {  # 腾讯
            'entry_low': 579.00,
            'entry_high': 600.00,
            'stop_loss': 577.00,
            'take_profit_1': 610.00,
            'take_profit_2': 623.00
        },
        '0981.HK': {  # 中芯国际
            'entry_low': 73.86,
            'entry_high': 77.08,
            'stop_loss': 72.07,
            'take_profit_1': 79.79,
            'take_profit_2': 82.00
        },
        '2015.HK': {  # 理想汽车 - 追涨回调
            'entry_low': 64.50,
            'entry_high': 65.50,
            'stop_loss': 62.80,
            'take_profit_1': 65.80,
            'take_profit_2': 66.50
        },
        '9888.HK': {  # 百度 - 创新高追涨
            'entry_low': 158.00,
            'entry_high': 161.00,
            'stop_loss': 156.50,
            'take_profit_1': 165.00,
            'take_profit_2': 169.00
        },
        '1072.HK': {  # 东方电气 - 创新高追涨
            'entry_low': 27.00,
            'entry_high': 28.30,
            'stop_loss': 27.20,
            'take_profit_1': 29.00,
            'take_profit_2': 29.50
        }
    }

    # 加载预设计划
    if ticker in preset_plans:
        plan = preset_plans[ticker]
        watcher.set_plan(
            entry_low=plan['entry_low'],
            entry_high=plan['entry_high'],
            stop_loss=plan['stop_loss'],
            take_profit_1=plan['take_profit_1'],
            take_profit_2=plan['take_profit_2']
        )
        print(f"✅ 已加载 {ticker} 预设交易计划")

    # 开始盯盘
    watcher.watch(interval=interval)


if __name__ == "__main__":
    main()

# 追加理想汽车预设
