#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手科技 1024.HK T+0实时监控系统
持仓：200股 @ 79.25港元
"""

import sys
import time
from datetime import datetime
from futu import *
import os

class KuaishouT0Monitor:
    def __init__(self):
        self.code = '1024.HK'
        self.name = '快手科技'

        # 你的持仓信息
        self.position_shares = 200  # 持仓数量
        self.position_cost = 79.25   # 成本价
        self.position_value = self.position_shares * self.position_cost

        # T+0目标价位
        self.sell_target = 79.5     # 卖出目标
        self.sell_confirm = 80.0    # 确认卖出
        self.buy_target = 77.5      # 买入目标
        self.buy_confirm = 77.0     # 确认买入
        self.stop_loss = 76.0       # 止损线

        # 富途连接
        self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

        # 状态
        self.last_alert_time = {}
        self.alert_cooldown = 60  # 提醒冷却时间（秒）

        print("=" * 80)
        print(f"🚀 快手T+0实时监控系统启动")
        print(f"⏰ 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def get_realtime_price(self):
        """获取实时价格"""
        try:
            ret_sub = self.quote_ctx.subscribe([self.code], [SubType.QUOTE], subscribe_push=False)
            if ret_sub == RET_OK:
                ret, data = self.quote_ctx.get_stock_quote([self.code])
                if ret == RET_OK and len(data) > 0:
                    return {
                        'price': float(data['last_price'].iloc[0]),
                        'change_rate': float(data['change_rate'].iloc[0]),
                        'volume': float(data['volume'].iloc[0]),
                        'turnover': float(data['turnover'].iloc[0]),
                        'high': float(data['high_price'].iloc[0]),
                        'low': float(data['low_price'].iloc[0]),
                        'open': float(data['open_price'].iloc[0])
                    }
            return None
        except Exception as e:
            print(f"❌ 获取价格失败: {e}")
            return None

    def calculate_position(self, current_price):
        """计算持仓盈亏"""
        current_value = self.position_shares * current_price
        pnl = current_value - self.position_value
        pnl_pct = (pnl / self.position_value) * 100

        return {
            'current_value': current_value,
            'pnl': pnl,
            'pnl_pct': pnl_pct
        }

    def calculate_t0_plan(self, current_price):
        """计算T+0方案"""
        # 反向T+0: 先卖后买
        if current_price >= self.sell_target:
            sell_price = current_price
            buy_price = self.buy_target
            profit = (sell_price - buy_price) * self.position_shares
            new_cost = ((self.position_cost * self.position_shares) - profit) / self.position_shares

            return {
                'strategy': '反向T+0',
                'action': '先卖后买',
                'sell_price': sell_price,
                'buy_price': buy_price,
                'profit': profit,
                'new_cost': new_cost,
                'cost_reduction': self.position_cost - new_cost
            }

        # 正向T+0: 先买后卖
        elif current_price <= self.buy_target:
            buy_price = current_price
            sell_price = self.sell_target
            profit = (sell_price - buy_price) * self.position_shares

            return {
                'strategy': '正向T+0',
                'action': '先买后卖',
                'buy_price': buy_price,
                'sell_price': sell_price,
                'profit': profit,
                'new_cost': self.position_cost,
                'cost_reduction': 0
            }

        return None

    def check_alerts(self, price_data):
        """检查价格提醒"""
        current_price = price_data['price']
        now = time.time()

        alerts = []

        # 卖出信号
        if current_price >= self.sell_confirm:
            if self._should_alert('sell_confirm', now):
                alerts.append({
                    'type': 'SELL',
                    'level': '🔴 确认',
                    'message': f'价格突破{self.sell_confirm}，立即卖出200股！',
                    'action': f'卖出200股@{current_price:.2f}'
                })
        elif current_price >= self.sell_target:
            if self._should_alert('sell_target', now):
                alerts.append({
                    'type': 'SELL',
                    'level': '🟡 准备',
                    'message': f'价格到达{self.sell_target}，准备卖出',
                    'action': f'等待突破{self.sell_confirm}确认'
                })

        # 买入信号
        if current_price <= self.buy_confirm:
            if self._should_alert('buy_confirm', now):
                alerts.append({
                    'type': 'BUY',
                    'level': '🟢 确认',
                    'message': f'价格跌至{self.buy_confirm}，立即买入200股！',
                    'action': f'买入200股@{current_price:.2f}'
                })
        elif current_price <= self.buy_target:
            if self._should_alert('buy_target', now):
                alerts.append({
                    'type': 'BUY',
                    'level': '🟡 准备',
                    'message': f'价格到达{self.buy_target}，准备买入',
                    'action': f'等待跌破{self.buy_confirm}确认'
                })

        # 止损警告
        if current_price <= self.stop_loss:
            if self._should_alert('stop_loss', now):
                alerts.append({
                    'type': 'STOP',
                    'level': '⚠️ 止损',
                    'message': f'价格跌破止损线{self.stop_loss}！',
                    'action': '立即止损出局！'
                })

        return alerts

    def _should_alert(self, alert_key, now):
        """检查是否应该发出提醒（冷却机制）"""
        if alert_key not in self.last_alert_time:
            self.last_alert_time[alert_key] = now
            return True

        if now - self.last_alert_time[alert_key] >= self.alert_cooldown:
            self.last_alert_time[alert_key] = now
            return True

        return False

    def display_status(self, price_data):
        """显示当前状态"""
        os.system('clear' if os.name == 'posix' else 'cls')

        current_price = price_data['price']
        position = self.calculate_position(current_price)
        t0_plan = self.calculate_t0_plan(current_price)

        print("=" * 80)
        print(f"📊 {self.name} ({self.code}) T+0实时监控")
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 实时行情
        print(f"\n💲 实时行情:")
        print(f"   当前价: {current_price:.2f} HKD")
        print(f"   涨跌幅: {price_data['change_rate']:+.2f}%")
        print(f"   今开: {price_data['open']:.2f}  最高: {price_data['high']:.2f}  最低: {price_data['low']:.2f}")
        print(f"   成交量: {price_data['volume']/1e6:.1f}M 股")
        print(f"   成交额: {price_data['turnover']/1e8:.2f}亿 HKD")

        # 持仓情况
        pnl_color = "🟢" if position['pnl'] >= 0 else "🔴"
        print(f"\n💼 持仓情况:")
        print(f"   数量: {self.position_shares} 股")
        print(f"   成本: {self.position_cost:.2f} HKD")
        print(f"   市值: {position['current_value']:.0f} HKD")
        print(f"   {pnl_color} 盈亏: {position['pnl']:+.0f} HKD ({position['pnl_pct']:+.2f}%)")

        # 关键位置
        print(f"\n🎯 关键价位:")
        print(f"   确认卖出: {self.sell_confirm:.2f}")
        print(f"   目标卖出: {self.sell_target:.2f}")
        print(f"   当前价格: {current_price:.2f} {'⬆️' if price_data['change_rate'] > 0 else '⬇️'}")
        print(f"   目标买入: {self.buy_target:.2f}")
        print(f"   确认买入: {self.buy_confirm:.2f}")
        print(f"   止损警戒: {self.stop_loss:.2f}")

        # 距离关键位
        print(f"\n📏 距离关键位:")
        dist_sell = ((self.sell_confirm - current_price) / current_price) * 100
        dist_buy = ((current_price - self.buy_confirm) / current_price) * 100
        print(f"   距卖出位: {abs(dist_sell):.2f}% {'⬆️需上涨' if dist_sell > 0 else '✅已到达'}")
        print(f"   距买入位: {abs(dist_buy):.2f}% {'⬇️需下跌' if dist_buy > 0 else '✅已到达'}")

        # T+0方案
        if t0_plan:
            print(f"\n🔥 T+0方案 ({t0_plan['strategy']}):")
            print(f"   操作: {t0_plan['action']}")
            if t0_plan['strategy'] == '反向T+0':
                print(f"   1️⃣ 卖出200股@{t0_plan['sell_price']:.2f}")
                print(f"   2️⃣ 买回200股@{t0_plan['buy_price']:.2f}")
                print(f"   💰 预期收益: {t0_plan['profit']:.0f} HKD")
                print(f"   📉 成本降至: {t0_plan['new_cost']:.2f} (降{t0_plan['cost_reduction']:.2f})")
            else:
                print(f"   1️⃣ 买入200股@{t0_plan['buy_price']:.2f}")
                print(f"   2️⃣ 卖出200股@{t0_plan['sell_price']:.2f}")
                print(f"   💰 预期收益: {t0_plan['profit']:.0f} HKD")

        # 检查提醒
        alerts = self.check_alerts(price_data)
        if alerts:
            print(f"\n{'='*80}")
            print(f"⚡ 交易提醒:")
            for alert in alerts:
                print(f"\n{alert['level']} {alert['type']}信号")
                print(f"   {alert['message']}")
                print(f"   👉 {alert['action']}")
            print(f"{'='*80}")

        print(f"\n💡 提示: Ctrl+C 停止监控 | 每5秒刷新")
        print("=" * 80)

    def run(self):
        """运行监控"""
        try:
            print("✅ 连接到 FutuOpenD 成功")
            print("🔄 开始监控...\n")

            while True:
                price_data = self.get_realtime_price()

                if price_data:
                    self.display_status(price_data)
                else:
                    print("⚠️ 获取数据失败，5秒后重试...")

                time.sleep(5)  # 每5秒刷新

        except KeyboardInterrupt:
            print("\n\n👋 监控已停止")
        except Exception as e:
            print(f"\n❌ 错误: {e}")
        finally:
            self.quote_ctx.close()
            print("✅ 已断开 FutuOpenD 连接")

if __name__ == '__main__':
    monitor = KuaishouT0Monitor()
    monitor.run()
