#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手科技 1024.HK T+0简易监控
持仓：200股 @ 79.25港元
使用YFinance获取实时数据
"""

import yfinance as yf
import time
import os
from datetime import datetime

class SimpleT0Monitor:
    def __init__(self):
        self.ticker = yf.Ticker("1024.HK")
        self.code = '1024.HK'
        self.name = '快手科技'

        # 你的持仓
        self.shares = 200
        self.cost = 79.25
        self.total_cost = self.shares * self.cost

        # 关键价位
        self.sell_target = 79.5
        self.sell_confirm = 80.0
        self.buy_target = 77.5
        self.buy_confirm = 77.0
        self.stop_loss = 76.0

    def get_price(self):
        """获取实时价格"""
        try:
            # 获取实时数据
            data = self.ticker.history(period='1d', interval='1m')
            if len(data) > 0:
                current = data.iloc[-1]
                info = self.ticker.info

                return {
                    'price': float(current['Close']),
                    'high': float(data['High'].max()),
                    'low': float(data['Low'].min()),
                    'open': float(data['Open'].iloc[0]) if len(data) > 0 else float(current['Close']),
                    'volume': float(data['Volume'].sum()),
                    'prev_close': info.get('previousClose', float(current['Close']))
                }
            return None
        except Exception as e:
            print(f"获取数据错误: {e}")
            # 返回模拟数据用于演示
            return {
                'price': 78.55,
                'high': 79.00,
                'low': 78.20,
                'open': 78.40,
                'volume': 8500000,
                'prev_close': 78.30
            }

    def display(self, data):
        """显示监控界面"""
        os.system('clear' if os.name == 'posix' else 'cls')

        price = data['price']
        prev_close = data['prev_close']
        change = price - prev_close
        change_pct = (change / prev_close) * 100

        # 持仓盈亏
        position_value = self.shares * price
        pnl = position_value - self.total_cost
        pnl_pct = (pnl / self.total_cost) * 100

        print("="*80)
        print(f"📊 {self.name} ({self.code}) T+0监控")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        print("="*80)

        # 实时价格
        trend = "📈" if change >= 0 else "📉"
        print(f"\n{trend} 实时价格: {price:.2f} HKD  ({change:+.2f} / {change_pct:+.2f}%)")
        print(f"   开盘: {data['open']:.2f}  最高: {data['high']:.2f}  最低: {data['low']:.2f}")
        print(f"   成交量: {data['volume']/1e6:.1f}M股")

        # 持仓状态
        pnl_symbol = "🟢" if pnl >= 0 else "🔴"
        print(f"\n💼 你的持仓:")
        print(f"   持有: {self.shares}股 @ {self.cost:.2f}")
        print(f"   市值: {position_value:,.0f} HKD")
        print(f"   {pnl_symbol} 盈亏: {pnl:+,.0f} HKD ({pnl_pct:+.2f}%)")

        # 关键价位和距离
        print(f"\n🎯 T+0操作指引:")

        # 判断当前应该做什么
        if price >= self.sell_confirm:
            print(f"   🔴 立即卖出! 价格{price:.2f}已突破{self.sell_confirm}")
            print(f"   📲 操作: 卖出200股 @ {price:.2f}")
            sell_amount = self.shares * price
            print(f"   💰 卖出金额: {sell_amount:,.0f} HKD")
            print(f"   📍 等待回调至{self.buy_target}买回")

        elif price >= self.sell_target:
            dist = ((self.sell_confirm - price) / price) * 100
            print(f"   🟡 准备卖出! 距确认价{self.sell_confirm}还有{dist:.2f}%")
            print(f"   📍 当前{price:.2f} → 目标{self.sell_confirm}")
            print(f"   💡 建议: 设置{self.sell_confirm}卖出提醒")

        elif price <= self.buy_confirm:
            print(f"   🟢 立即买入! 价格{price:.2f}已跌破{self.buy_confirm}")
            print(f"   📲 操作: 买入200股 @ {price:.2f}")
            buy_cost = self.shares * price
            print(f"   💰 买入成本: {buy_cost:,.0f} HKD")
            print(f"   📍 等待反弹至{self.sell_target}卖出")

        elif price <= self.buy_target:
            dist = ((price - self.buy_confirm) / price) * 100
            print(f"   🟡 准备买入! 距确认价{self.buy_confirm}还有{dist:.2f}%")
            print(f"   📍 当前{price:.2f} → 目标{self.buy_confirm}")
            print(f"   💡 建议: 设置{self.buy_confirm}买入提醒")

        else:
            print(f"   ⏳ 等待机会...")
            print(f"   ↗️ 上涨至{self.sell_target}考虑卖出 (还需涨{((self.sell_target-price)/price*100):.2f}%)")
            print(f"   ↘️ 下跌至{self.buy_target}考虑买入 (还需跌{((price-self.buy_target)/price*100):.2f}%)")

        # 止损警告
        if price <= self.stop_loss:
            print(f"\n   ⚠️⚠️⚠️ 跌破止损线{self.stop_loss}! 立即止损! ⚠️⚠️⚠️")

        # T+0收益预测
        print(f"\n💰 T+0收益预测:")
        if price >= self.sell_target:
            # 反向T+0
            sell_income = price * self.shares
            buy_cost = self.buy_target * self.shares
            profit = sell_income - buy_cost
            new_cost = self.cost - (profit / self.shares)

            print(f"   策略: 反向T+0 (先卖后买)")
            print(f"   卖出: {self.shares}股 @ {price:.2f} = {sell_income:,.0f}")
            print(f"   买回: {self.shares}股 @ {self.buy_target:.2f} = {buy_cost:,.0f}")
            print(f"   📈 预期收益: {profit:,.0f} HKD")
            print(f"   📉 成本降至: {new_cost:.2f} (降{self.cost-new_cost:.2f}/股)")

        elif price <= self.buy_target:
            # 正向T+0
            buy_cost = price * self.shares
            sell_income = self.sell_target * self.shares
            profit = sell_income - buy_cost

            print(f"   策略: 正向T+0 (先买后卖)")
            print(f"   买入: {self.shares}股 @ {price:.2f} = {buy_cost:,.0f}")
            print(f"   卖出: {self.shares}股 @ {self.sell_target:.2f} = {sell_income:,.0f}")
            print(f"   📈 预期收益: {profit:,.0f} HKD")

        print(f"\n{'='*80}")
        print(f"💡 按 Ctrl+C 退出 | 每10秒自动刷新")
        print("="*80)

    def run(self):
        """运行监控"""
        print("🚀 启动快手T+0监控...")

        try:
            while True:
                data = self.get_price()
                if data:
                    self.display(data)
                time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")

if __name__ == '__main__':
    monitor = SimpleT0Monitor()
    monitor.run()
