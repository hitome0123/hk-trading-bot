#!/usr/bin/env python3
"""
模拟持仓追踪器
- 读取模拟持仓
- 获取最新价格
- 计算盈亏
- 检查止盈止损
- 推送到Telegram
"""

import json
import os
from datetime import datetime
from futu import *
import requests

# Telegram配置
TELEGRAM_BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
TELEGRAM_CHAT_ID = "7082819163"

def send_telegram(message):
    """发送Telegram消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        print(f"Telegram发送失败: {e}")

def load_portfolio():
    """加载模拟持仓"""
    portfolio_file = os.path.join(os.path.dirname(__file__), 'simulated_portfolio.json')
    if not os.path.exists(portfolio_file):
        print("❌ 未找到模拟持仓文件")
        return None

    with open(portfolio_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_portfolio(portfolio):
    """保存模拟持仓"""
    portfolio_file = os.path.join(os.path.dirname(__file__), 'simulated_portfolio.json')
    with open(portfolio_file, 'w', encoding='utf-8') as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=2)

def track_portfolio(push_telegram=False):
    """追踪持仓"""
    portfolio = load_portfolio()
    if not portfolio:
        return

    print("=" * 80)
    print("📊 模拟持仓追踪")
    print("=" * 80)
    print(f"追踪时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"创建时间: {portfolio['created_time']}")
    print("-" * 80)

    # 连接富途
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

    total_cost = 0
    total_market_value = 0
    alerts = []

    print(f"\n{'代码':<10} {'名称':<10} {'数量':>6} {'成本':>8} {'现价':>8} {'盈亏':>10} {'盈亏%':>8} {'状态'}")
    print("-" * 80)

    for pos in portfolio['positions']:
        code = pos['code']
        name = pos['name']
        qty = pos['qty']
        buy_price = pos['buy_price']
        tp1 = pos['tp1']
        tp2 = pos['tp2']
        sl = pos['sl']

        try:
            # 获取最新价格
            ret, snap = quote_ctx.get_market_snapshot([code])
            if ret != RET_OK:
                print(f"{code}: 获取价格失败")
                continue

            current_price = snap['last_price'].iloc[0]

            # 计算盈亏
            cost = buy_price * qty
            market_value = current_price * qty
            pnl = market_value - cost
            pnl_pct = (current_price - buy_price) / buy_price * 100

            total_cost += cost
            total_market_value += market_value

            # 更新持仓数据
            pos['current_price'] = current_price
            pos['market_value'] = market_value
            pos['pnl'] = pnl
            pos['pnl_pct'] = pnl_pct
            pos['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 检查止盈止损
            status = "持有"
            if current_price >= tp1:
                status = "🔴 到止盈1"
                alerts.append(f"🎯 {code.replace('HK.', '')} {name} 到止盈1！现价{current_price:.2f}，盈利{pnl_pct:+.1f}%")
            elif current_price >= tp2:
                status = "🔴 到止盈2"
                alerts.append(f"🎯🎯 {code.replace('HK.', '')} {name} 到止盈2！现价{current_price:.2f}，盈利{pnl_pct:+.1f}%")
            elif current_price <= sl:
                status = "⚠️ 触止损"
                alerts.append(f"⚠️ {code.replace('HK.', '')} {name} 触及止损！现价{current_price:.2f}，亏损{pnl_pct:.1f}%")
            elif pnl_pct > 10:
                status = "✅ 盈利中"
            elif pnl_pct < -5:
                status = "📉 亏损中"

            print(f"{code.replace('HK.', ''):<10} {name[:8]:<10} {qty:>5}股 {buy_price:>8.2f} {current_price:>8.2f} {pnl:>+9,.0f} {pnl_pct:>+7.1f}% {status}")

        except Exception as e:
            print(f"{code}: 错误 - {e}")

    quote_ctx.close()

    # 汇总
    total_pnl = total_market_value - total_cost
    total_pnl_pct = (total_market_value - total_cost) / total_cost * 100 if total_cost > 0 else 0

    print("\n" + "=" * 80)
    print("💰 持仓汇总")
    print("=" * 80)
    print(f"总成本:     {total_cost:>15,.0f} 港元")
    print(f"总市值:     {total_market_value:>15,.0f} 港元")
    print(f"总盈亏:     {total_pnl:>+14,.0f} 港元")
    print(f"收益率:     {total_pnl_pct:>+14.2f} %")
    print(f"剩余现金:   {portfolio['available_cash']:>15,.0f} 港元")
    print(f"总资产:     {total_market_value + portfolio['available_cash']:>15,.0f} 港元")

    # 更新portfolio
    portfolio['total_cost'] = total_cost
    portfolio['total_market_value'] = total_market_value
    portfolio['total_pnl'] = total_pnl
    portfolio['total_pnl_pct'] = total_pnl_pct
    portfolio['last_track_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    save_portfolio(portfolio)
    print(f"\n✅ 持仓数据已更新")

    # 打印提醒
    if alerts:
        print("\n" + "=" * 80)
        print("⚡ 交易提醒")
        print("=" * 80)
        for alert in alerts:
            print(f"  {alert}")

    # 推送Telegram
    if push_telegram:
        msg = f"""📊 *模拟持仓追踪*
⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}

💰 *汇总*
总成本: {total_cost:,.0f} 港元
总市值: {total_market_value:,.0f} 港元
总盈亏: {total_pnl:+,.0f} 港元 ({total_pnl_pct:+.2f}%)

📈 *持仓明细*
"""
        for pos in portfolio['positions']:
            if 'current_price' in pos:
                msg += f"• {pos['code'].replace('HK.', '')} {pos['name'][:6]}: {pos['pnl_pct']:+.1f}%\n"

        if alerts:
            msg += "\n⚡ *提醒*\n"
            for alert in alerts:
                msg += f"{alert}\n"

        send_telegram(msg)
        print("\n📱 已推送到Telegram")

    print("\n" + "=" * 80)
    return portfolio

def simulate_sell(code, qty=None, reason="手动卖出"):
    """模拟卖出"""
    portfolio = load_portfolio()
    if not portfolio:
        return

    # 找到持仓
    pos_idx = None
    for i, pos in enumerate(portfolio['positions']):
        if pos['code'] == code or pos['code'].replace('HK.', '') == code:
            pos_idx = i
            break

    if pos_idx is None:
        print(f"❌ 未找到持仓: {code}")
        return

    pos = portfolio['positions'][pos_idx]

    # 获取最新价格
    quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
    ret, snap = quote_ctx.get_market_snapshot([pos['code']])
    quote_ctx.close()

    if ret != RET_OK:
        print(f"❌ 获取价格失败")
        return

    current_price = snap['last_price'].iloc[0]
    sell_qty = qty if qty else pos['qty']
    sell_amount = current_price * sell_qty
    pnl = (current_price - pos['buy_price']) * sell_qty
    pnl_pct = (current_price - pos['buy_price']) / pos['buy_price'] * 100

    print(f"\n🔴 模拟卖出 {pos['code']} {pos['name']}")
    print(f"   数量: {sell_qty}股")
    print(f"   买入价: {pos['buy_price']:.2f}")
    print(f"   卖出价: {current_price:.2f}")
    print(f"   金额: {sell_amount:,.0f} 港元")
    print(f"   盈亏: {pnl:+,.0f} 港元 ({pnl_pct:+.1f}%)")

    # 记录交易历史
    portfolio['history'].append({
        'action': 'SELL',
        'code': pos['code'],
        'name': pos['name'],
        'qty': sell_qty,
        'price': current_price,
        'amount': sell_amount,
        'pnl': pnl,
        'pnl_pct': pnl_pct,
        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'reason': reason
    })

    # 更新持仓
    if sell_qty >= pos['qty']:
        # 全部卖出
        portfolio['positions'].pop(pos_idx)
    else:
        # 部分卖出
        pos['qty'] -= sell_qty
        pos['buy_amount'] = pos['qty'] * pos['buy_price']

    # 更新现金
    portfolio['available_cash'] += sell_amount

    save_portfolio(portfolio)
    print(f"\n✅ 卖出完成，现金余额: {portfolio['available_cash']:,.0f} 港元")

def show_history():
    """显示交易历史"""
    portfolio = load_portfolio()
    if not portfolio:
        return

    print("=" * 80)
    print("📜 交易历史")
    print("=" * 80)

    for trade in portfolio.get('history', []):
        action = "🟢买入" if trade['action'] == 'BUY' else "🔴卖出"
        pnl_str = f" 盈亏:{trade.get('pnl', 0):+,.0f}" if trade['action'] == 'SELL' else ""
        print(f"{trade['time']} {action} {trade['code'].replace('HK.', '')} {trade['name'][:6]} {trade['qty']}股 @{trade['price']:.2f}{pnl_str}")
        print(f"   原因: {trade.get('reason', '-')}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'track':
            push = '--push' in sys.argv
            track_portfolio(push_telegram=push)
        elif cmd == 'sell':
            if len(sys.argv) > 2:
                code = sys.argv[2]
                qty = int(sys.argv[3]) if len(sys.argv) > 3 else None
                reason = sys.argv[4] if len(sys.argv) > 4 else "手动卖出"
                simulate_sell(code, qty, reason)
            else:
                print("用法: python portfolio_tracker.py sell <股票代码> [数量] [原因]")
        elif cmd == 'history':
            show_history()
        else:
            print("用法:")
            print("  python portfolio_tracker.py track [--push]  # 追踪持仓")
            print("  python portfolio_tracker.py sell <代码> [数量]  # 模拟卖出")
            print("  python portfolio_tracker.py history  # 交易历史")
    else:
        track_portfolio()
