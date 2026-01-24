#!/usr/bin/env python3
"""
港股持仓管理工具 - 含手续费计算
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import yfinance as yf

# 富途手续费结构
FUTU_FEES = {
    'platform_fee': 15,  # 平台使用费 HKD/笔
    'commission_rate': 0.0003,  # 佣金 0.03%
    'commission_min': 3,  # 最低佣金 3 HKD
    'stamp_duty': 0.001,  # 印花税 0.1%
    'trading_fee': 0.0000565,  # 交易征费
    'settlement_fee': 0.00002,  # 结算费
}

PORTFOLIO_FILE = os.path.expanduser('~/.hk_portfolio.json')


def calculate_fees(amount: float, is_sell: bool = False) -> float:
    """计算单笔交易手续费"""
    fees = FUTU_FEES['platform_fee']
    commission = max(amount * FUTU_FEES['commission_rate'], FUTU_FEES['commission_min'])
    fees += commission
    fees += amount * FUTU_FEES['stamp_duty']
    fees += amount * FUTU_FEES['trading_fee']
    fees += amount * FUTU_FEES['settlement_fee']
    return round(fees, 2)


def load_portfolio() -> Dict:
    """加载持仓"""
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, 'r') as f:
            return json.load(f)
    return {'positions': [], 'history': []}


def save_portfolio(portfolio: Dict):
    """保存持仓"""
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2, ensure_ascii=False)


def add_position(ticker: str, shares: int, cost: float, name: str = ''):
    """添加持仓"""
    portfolio = load_portfolio()

    ticker = ticker.upper()
    if not ticker.endswith('.HK'):
        ticker += '.HK'

    buy_amount = shares * cost
    fees = calculate_fees(buy_amount)

    position = {
        'ticker': ticker,
        'name': name,
        'shares': shares,
        'cost': cost,
        'buy_fees': fees,
        'buy_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'total_cost': buy_amount + fees
    }

    # 检查是否已有持仓，有则合并
    existing = None
    for i, p in enumerate(portfolio['positions']):
        if p['ticker'] == ticker:
            existing = i
            break

    if existing is not None:
        old = portfolio['positions'][existing]
        total_shares = old['shares'] + shares
        total_cost = old['total_cost'] + position['total_cost']
        avg_cost = (old['cost'] * old['shares'] + cost * shares) / total_shares
        portfolio['positions'][existing] = {
            'ticker': ticker,
            'name': name or old['name'],
            'shares': total_shares,
            'cost': round(avg_cost, 3),
            'buy_fees': old['buy_fees'] + fees,
            'buy_date': old['buy_date'],
            'total_cost': total_cost
        }
        print(f"已合并持仓: {ticker} 总{total_shares}股 均价{avg_cost:.3f}")
    else:
        portfolio['positions'].append(position)
        print(f"已添加: {ticker} {shares}股 @ {cost}")

    print(f"买入手续费: {fees:.2f} HKD")
    save_portfolio(portfolio)


def remove_position(ticker: str, shares: int = None, sell_price: float = None):
    """卖出持仓"""
    portfolio = load_portfolio()

    ticker = ticker.upper()
    if not ticker.endswith('.HK'):
        ticker += '.HK'

    for i, p in enumerate(portfolio['positions']):
        if p['ticker'] == ticker:
            if shares is None or shares >= p['shares']:
                # 全部卖出
                sell_shares = p['shares']
                if sell_price:
                    sell_amount = sell_shares * sell_price
                    sell_fees = calculate_fees(sell_amount, is_sell=True)
                    pnl = sell_amount - p['total_cost'] - sell_fees

                    # 记录历史
                    history = {
                        'ticker': ticker,
                        'name': p['name'],
                        'shares': sell_shares,
                        'buy_cost': p['cost'],
                        'sell_price': sell_price,
                        'buy_fees': p['buy_fees'],
                        'sell_fees': sell_fees,
                        'pnl': round(pnl, 2),
                        'sell_date': datetime.now().strftime('%Y-%m-%d %H:%M')
                    }
                    portfolio['history'].append(history)
                    print(f"卖出: {ticker} {sell_shares}股 @ {sell_price}")
                    print(f"卖出手续费: {sell_fees:.2f} HKD")
                    print(f"盈亏: {pnl:+.2f} HKD")

                portfolio['positions'].pop(i)
            else:
                # 部分卖出
                p['shares'] -= shares
                p['total_cost'] = p['total_cost'] * (p['shares'] / (p['shares'] + shares))
                if sell_price:
                    sell_amount = shares * sell_price
                    sell_fees = calculate_fees(sell_amount, is_sell=True)
                    buy_cost_portion = p['cost'] * shares + p['buy_fees'] * (shares / (p['shares'] + shares))
                    pnl = sell_amount - buy_cost_portion - sell_fees
                    print(f"部分卖出: {ticker} {shares}股 @ {sell_price}")
                    print(f"盈亏: {pnl:+.2f} HKD")

            save_portfolio(portfolio)
            return

    print(f"未找到持仓: {ticker}")


def get_realtime_prices(tickers: List[str]) -> Dict[str, float]:
    """获取实时价格"""
    prices = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            if len(hist) > 0:
                prices[ticker] = hist['Close'].iloc[-1]
        except:
            pass
    return prices


def show_portfolio():
    """显示持仓和盈亏"""
    portfolio = load_portfolio()

    if not portfolio['positions']:
        print("暂无持仓")
        return

    tickers = [p['ticker'] for p in portfolio['positions']]
    prices = get_realtime_prices(tickers)

    print("\n" + "=" * 70)
    print("当前持仓")
    print("=" * 70)
    print(f"{'股票':<12} {'股数':>6} {'成本':>8} {'现价':>8} {'盈亏':>10} {'盈亏%':>8}")
    print("-" * 70)

    total_cost = 0
    total_value = 0
    total_pnl = 0

    for p in portfolio['positions']:
        ticker = p['ticker']
        current = prices.get(ticker, 0)

        if current > 0:
            market_value = p['shares'] * current
            sell_fees = calculate_fees(market_value, is_sell=True)
            # 盈亏 = 市值 - 总成本 - 卖出手续费
            pnl = market_value - p['total_cost'] - sell_fees
            pnl_pct = pnl / p['total_cost'] * 100

            total_cost += p['total_cost']
            total_value += market_value
            total_pnl += pnl

            icon = "+" if pnl > 0 else ""
            print(f"{p['name'] or ticker:<12} {p['shares']:>6} {p['cost']:>8.2f} {current:>8.2f} {icon}{pnl:>9.0f} {icon}{pnl_pct:>7.1f}%")
        else:
            print(f"{p['name'] or ticker:<12} {p['shares']:>6} {p['cost']:>8.2f} {'N/A':>8} {'N/A':>10}")

    print("-" * 70)
    total_fees = sum(p['buy_fees'] for p in portfolio['positions'])
    print(f"总成本(含手续费): {total_cost:.0f} HKD")
    print(f"当前市值: {total_value:.0f} HKD")
    print(f"已付手续费: {total_fees:.0f} HKD")
    print(f"预估卖出手续费: {calculate_fees(total_value):.0f} HKD")
    pnl_icon = "+" if total_pnl > 0 else ""
    print(f"总盈亏(扣除手续费): {pnl_icon}{total_pnl:.0f} HKD")
    print("=" * 70)


def show_history():
    """显示交易历史"""
    portfolio = load_portfolio()

    if not portfolio['history']:
        print("暂无交易历史")
        return

    print("\n" + "=" * 70)
    print("交易历史")
    print("=" * 70)

    total_pnl = 0
    for h in portfolio['history']:
        total_pnl += h['pnl']
        icon = "+" if h['pnl'] > 0 else ""
        print(f"{h['sell_date']} {h['ticker']} {h['shares']}股 买{h['buy_cost']:.2f}卖{h['sell_price']:.2f} {icon}{h['pnl']:.0f}")

    print("-" * 70)
    print(f"历史总盈亏: {total_pnl:+.0f} HKD")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python portfolio.py show          - 显示持仓")
        print("  python portfolio.py add 1929.HK 200 13.97 周大福  - 添加持仓")
        print("  python portfolio.py sell 1929.HK 200 14.40       - 卖出")
        print("  python portfolio.py history       - 交易历史")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'show':
        show_portfolio()
    elif cmd == 'add' and len(sys.argv) >= 5:
        ticker = sys.argv[2]
        shares = int(sys.argv[3])
        cost = float(sys.argv[4])
        name = sys.argv[5] if len(sys.argv) > 5 else ''
        add_position(ticker, shares, cost, name)
    elif cmd == 'sell' and len(sys.argv) >= 4:
        ticker = sys.argv[2]
        shares = int(sys.argv[3]) if len(sys.argv) > 3 else None
        price = float(sys.argv[4]) if len(sys.argv) > 4 else None
        remove_position(ticker, shares, price)
    elif cmd == 'history':
        show_history()
    else:
        print("参数错误")
