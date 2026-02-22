#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速查看快手当前状态"""

import yfinance as yf
from datetime import datetime

# 你的持仓
SHARES = 200
COST = 79.25

# 关键价位
SELL_CONFIRM = 80.0
SELL_TARGET = 79.5
BUY_TARGET = 77.5
BUY_CONFIRM = 77.0
STOP_LOSS = 76.0

print("正在获取快手实时数据...")

try:
    ticker = yf.Ticker("1024.HK")

    # 获取最新价格
    hist = ticker.history(period='1d', interval='1m')
    info = ticker.info

    if len(hist) > 0:
        current = hist.iloc[-1]
        price = float(current['Close'])
        prev_close = info.get('previousClose', price)
    else:
        # 备用：从info获取
        price = info.get('currentPrice', info.get('previousClose', 78.55))
        prev_close = info.get('previousClose', 78.30)

    high = float(hist['High'].max()) if len(hist) > 0 else price
    low = float(hist['Low'].min()) if len(hist) > 0 else price
    open_price = float(hist['Open'].iloc[0]) if len(hist) > 0 else price

except Exception as e:
    print(f"获取数据失败: {e}")
    print("使用模拟数据...")
    price = 78.55
    prev_close = 78.30
    high = 79.00
    low = 78.20
    open_price = 78.40

# 计算涨跌
change = price - prev_close
change_pct = (change / prev_close) * 100

# 持仓盈亏
position_value = SHARES * price
total_cost = SHARES * COST
pnl = position_value - total_cost
pnl_pct = (pnl / total_cost) * 100

print("\n" + "="*80)
print(f"📊 快手科技 (1024.HK) T+0实时状态")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# 实时价格
trend = "📈" if change >= 0 else "📉"
print(f"\n{trend} 当前价格: {price:.2f} HKD")
print(f"   涨跌: {change:+.2f} ({change_pct:+.2f}%)")
print(f"   今开: {open_price:.2f}  最高: {high:.2f}  最低: {low:.2f}")

# 持仓
pnl_symbol = "🟢" if pnl >= 0 else "🔴"
print(f"\n💼 你的持仓:")
print(f"   {SHARES}股 @ {COST:.2f} = {total_cost:,.0f} HKD")
print(f"   {pnl_symbol} 当前盈亏: {pnl:+.0f} HKD ({pnl_pct:+.2f}%)")

# 关键价位
print(f"\n🎯 关键价位:")
print(f"   确认卖出: {SELL_CONFIRM:.2f} (距离{((SELL_CONFIRM-price)/price*100):+.2f}%)")
print(f"   目标卖出: {SELL_TARGET:.2f} (距离{((SELL_TARGET-price)/price*100):+.2f}%)")
print(f"   >>> 当前: {price:.2f} HKD <<<")
print(f"   目标买入: {BUY_TARGET:.2f} (距离{((BUY_TARGET-price)/price*100):+.2f}%)")
print(f"   确认买入: {BUY_CONFIRM:.2f} (距离{((BUY_CONFIRM-price)/price*100):+.2f}%)")
print(f"   止损线: {STOP_LOSS:.2f} (距离{((STOP_LOSS-price)/price*100):+.2f}%)")

# 操作建议
print(f"\n🔥 T+0操作建议:")

if price >= SELL_CONFIRM:
    print(f"   ✅ 立即卖出! 已突破{SELL_CONFIRM}")
    print(f"   📲 操作: 卖出200股 @ {price:.2f}")
    print(f"   💰 回笼: {SHARES * price:,.0f} HKD")
    print(f"   📍 等待回调至{BUY_TARGET}买回")

elif price >= SELL_TARGET:
    dist_to_sell = ((SELL_CONFIRM - price) / price) * 100
    print(f"   🟡 准备卖出! 距{SELL_CONFIRM}还有{dist_to_sell:.2f}%")
    print(f"   💡 建议: 设置{SELL_CONFIRM}卖出提醒")

elif price <= BUY_CONFIRM:
    print(f"   ✅ 立即买入! 已跌破{BUY_CONFIRM}")
    print(f"   📲 操作: 买入200股 @ {price:.2f}")
    print(f"   💰 成本: {SHARES * price:,.0f} HKD")
    print(f"   📍 等待反弹至{SELL_TARGET}卖出")

elif price <= BUY_TARGET:
    dist_to_buy = ((price - BUY_CONFIRM) / price) * 100
    print(f"   🟡 准备买入! 距{BUY_CONFIRM}还有{dist_to_buy:.2f}%")
    print(f"   💡 建议: 设置{BUY_CONFIRM}买入提醒")

else:
    print(f"   ⏳ 继续观望...")
    print(f"   上涨至{SELL_TARGET}考虑卖 (还需{((SELL_TARGET-price)/price*100):.2f}%)")
    print(f"   下跌至{BUY_TARGET}考虑买 (还需{((price-BUY_TARGET)/price*100):.2f}%)")

# 止损警告
if price <= STOP_LOSS:
    print(f"\n   ⚠️⚠️⚠️ 已跌破止损线! 立即止损! ⚠️⚠️⚠️")

# T+0收益预测
print(f"\n💰 T+0收益预测:")
if price >= SELL_TARGET:
    sell_income = price * SHARES
    buy_cost = BUY_TARGET * SHARES
    profit = sell_income - buy_cost
    new_cost = COST - (profit / SHARES)

    print(f"   反向T+0: 卖{price:.2f}买{BUY_TARGET:.2f}")
    print(f"   预期收益: {profit:,.0f} HKD")
    print(f"   成本降至: {new_cost:.2f} (降{COST-new_cost:.2f}/股)")
    print(f"   新盈亏: {((price-new_cost)*SHARES):+.0f} HKD")

elif price <= BUY_TARGET:
    buy_cost = price * SHARES
    sell_income = SELL_TARGET * SHARES
    profit = sell_income - buy_cost

    print(f"   正向T+0: 买{price:.2f}卖{SELL_TARGET:.2f}")
    print(f"   预期收益: {profit:,.0f} HKD")
    print(f"   可覆盖底仓亏损: {abs(pnl):.0f} HKD")

print(f"\n{'='*80}")
print(f"💡 运行 'python kuaishou_t0_simple.py' 开启实时监控（每10秒刷新）")
print("="*80)
