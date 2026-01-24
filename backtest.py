#!/usr/bin/env python3
"""
港股/A股回测系统 - 测试交易策略历史表现
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
import json


class BacktestEngine:
    """回测引擎"""

    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.positions = {}  # {ticker: {'shares': x, 'cost': x}}
        self.trades = []  # 交易记录
        self.equity_curve = []  # 净值曲线
        self.current_date = None

    def reset(self):
        """重置回测状态"""
        self.capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []

    def buy(self, ticker: str, price: float, shares: int, date: str):
        """买入"""
        cost = price * shares
        if cost > self.capital:
            shares = int(self.capital / price)
            cost = price * shares

        if shares <= 0:
            return False

        self.capital -= cost

        if ticker in self.positions:
            old = self.positions[ticker]
            total_shares = old['shares'] + shares
            avg_cost = (old['cost'] * old['shares'] + price * shares) / total_shares
            self.positions[ticker] = {'shares': total_shares, 'cost': avg_cost}
        else:
            self.positions[ticker] = {'shares': shares, 'cost': price}

        self.trades.append({
            'date': date,
            'ticker': ticker,
            'action': 'BUY',
            'price': price,
            'shares': shares,
            'value': cost
        })
        return True

    def sell(self, ticker: str, price: float, shares: int = None, date: str = ''):
        """卖出"""
        if ticker not in self.positions:
            return False

        pos = self.positions[ticker]
        if shares is None:
            shares = pos['shares']
        shares = min(shares, pos['shares'])

        revenue = price * shares
        self.capital += revenue

        pnl = (price - pos['cost']) * shares

        self.trades.append({
            'date': date,
            'ticker': ticker,
            'action': 'SELL',
            'price': price,
            'shares': shares,
            'value': revenue,
            'pnl': pnl
        })

        pos['shares'] -= shares
        if pos['shares'] <= 0:
            del self.positions[ticker]

        return True

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """计算组合总价值"""
        value = self.capital
        for ticker, pos in self.positions.items():
            if ticker in prices:
                value += pos['shares'] * prices[ticker]
        return value

    def record_equity(self, date: str, prices: Dict[str, float]):
        """记录净值"""
        value = self.get_portfolio_value(prices)
        self.equity_curve.append({
            'date': date,
            'value': value,
            'return': (value / self.initial_capital - 1) * 100
        })


class Strategy:
    """策略基类"""

    def __init__(self, name: str):
        self.name = name

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号，子类实现"""
        raise NotImplementedError


class MAStrategy(Strategy):
    """均线策略：短期均线上穿长期均线买入，下穿卖出"""

    def __init__(self, short_period: int = 5, long_period: int = 20):
        super().__init__(f'MA{short_period}_{long_period}')
        self.short_period = short_period
        self.long_period = long_period

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['ma_short'] = df['Close'].rolling(self.short_period).mean()
        df['ma_long'] = df['Close'].rolling(self.long_period).mean()

        df['signal'] = 0
        df.loc[df['ma_short'] > df['ma_long'], 'signal'] = 1  # 买入信号
        df.loc[df['ma_short'] < df['ma_long'], 'signal'] = -1  # 卖出信号

        # 只在交叉点产生信号
        df['signal_change'] = df['signal'].diff()
        df['trade_signal'] = 0
        df.loc[df['signal_change'] == 2, 'trade_signal'] = 1  # 金叉买入
        df.loc[df['signal_change'] == -2, 'trade_signal'] = -1  # 死叉卖出

        return df


class RSIStrategy(Strategy):
    """RSI策略：超卖买入，超买卖出"""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        super().__init__(f'RSI{period}_{oversold}_{overbought}')
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.period).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        df['trade_signal'] = 0
        df.loc[df['rsi'] < self.oversold, 'trade_signal'] = 1  # 超卖买入
        df.loc[df['rsi'] > self.overbought, 'trade_signal'] = -1  # 超买卖出

        return df


class BreakoutStrategy(Strategy):
    """突破策略：突破N日高点买入，跌破N日低点卖出"""

    def __init__(self, period: int = 20):
        super().__init__(f'Breakout{period}')
        self.period = period

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['high_n'] = df['High'].rolling(self.period).max()
        df['low_n'] = df['Low'].rolling(self.period).min()

        df['trade_signal'] = 0
        df.loc[df['Close'] > df['high_n'].shift(1), 'trade_signal'] = 1  # 突破买入
        df.loc[df['Close'] < df['low_n'].shift(1), 'trade_signal'] = -1  # 跌破卖出

        return df


class VolumeBreakoutStrategy(Strategy):
    """放量突破策略：放量+创新高买入"""

    def __init__(self, price_period: int = 20, vol_ratio: float = 1.5):
        super().__init__(f'VolBreakout{price_period}_{vol_ratio}')
        self.price_period = price_period
        self.vol_ratio = vol_ratio

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        df['high_n'] = df['High'].rolling(self.price_period).max()
        df['vol_avg'] = df['Volume'].rolling(5).mean()
        df['vol_ratio'] = df['Volume'] / df['vol_avg']

        df['trade_signal'] = 0
        # 放量突破买入
        buy_cond = (df['Close'] > df['high_n'].shift(1)) & (df['vol_ratio'] > self.vol_ratio)
        df.loc[buy_cond, 'trade_signal'] = 1

        # 跌破5日均线卖出
        df['ma5'] = df['Close'].rolling(5).mean()
        df.loc[df['Close'] < df['ma5'], 'trade_signal'] = -1

        return df


class SmartBreakoutStrategy(Strategy):
    """智能放量突破策略：放量+创新高+低套牢盘+ATR止损+回调买入"""

    def __init__(self, price_period: int = 20, vol_ratio: float = 1.2,
                 trapped_max: float = 30, pullback_pct: float = 0.03,
                 atr_stop: float = 2.0):
        super().__init__(f'SmartBreakout')
        self.price_period = price_period
        self.vol_ratio = vol_ratio
        self.trapped_max = trapped_max  # 最大套牢盘比例
        self.pullback_pct = pullback_pct  # 回调比例
        self.atr_stop = atr_stop  # ATR止损倍数

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        # 基础指标
        df['high_n'] = df['High'].rolling(self.price_period).max()
        df['low_n'] = df['Low'].rolling(self.price_period).min()
        df['vol_avg'] = df['Volume'].rolling(5).mean()
        df['vol_ratio'] = df['Volume'] / df['vol_avg']
        df['ma5'] = df['Close'].rolling(5).mean()
        df['ma20'] = df['Close'].rolling(20).mean()

        # ATR计算
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()

        # 套牢盘计算（过去N日高于当前价的比例）
        def calc_trapped(row_idx, closes, period=60):
            if row_idx < period:
                return 50
            window = closes[max(0, row_idx-period):row_idx]
            current = closes[row_idx]
            return (window > current).sum() / len(window) * 100

        closes = df['Close'].values
        df['trapped'] = [calc_trapped(i, closes) for i in range(len(df))]

        # 趋势判断
        df['uptrend'] = df['ma5'] > df['ma20']

        # 回调判断（从近期高点回调一定比例）
        df['recent_high'] = df['High'].rolling(5).max()
        df['pullback'] = (df['recent_high'] - df['Close']) / df['recent_high']

        df['trade_signal'] = 0
        df['stop_price'] = 0.0

        for i in range(20, len(df)):
            # 买入条件：
            # 1. 上升趋势
            # 2. 套牢盘低
            # 3. 放量
            # 4. 接近新高或回调买入

            uptrend = df['uptrend'].iloc[i]
            low_trapped = df['trapped'].iloc[i] < self.trapped_max
            good_volume = df['vol_ratio'].iloc[i] > self.vol_ratio

            # 两种买入方式
            # A: 放量突破新高
            breakout = df['Close'].iloc[i] > df['high_n'].iloc[i-1]
            # B: 回调到位（从高点回调3%左右）
            pullback_ok = (self.pullback_pct * 0.5 < df['pullback'].iloc[i] < self.pullback_pct * 1.5)

            buy_signal = uptrend and low_trapped and good_volume and (breakout or pullback_ok)

            if buy_signal:
                df.iloc[i, df.columns.get_loc('trade_signal')] = 1
                # 设置ATR止损价
                stop = df['Close'].iloc[i] - self.atr_stop * df['atr'].iloc[i]
                df.iloc[i, df.columns.get_loc('stop_price')] = stop

            # 卖出条件：
            # 1. 跌破ATR止损
            # 2. 或跌破MA5且RSI高

        # 简化卖出逻辑
        df['sell_signal'] = 0
        df.loc[df['Close'] < df['ma5'] * 0.98, 'sell_signal'] = 1  # 跌破MA5的2%
        df.loc[df['trade_signal'] == 0, 'trade_signal'] = -df['sell_signal']

        return df


class MomentumPullbackStrategy(Strategy):
    """追涨回调策略：涨停/大涨后回调买入"""

    def __init__(self, surge_pct: float = 0.05, pullback_pct: float = 0.03):
        super().__init__(f'MomentumPullback')
        self.surge_pct = surge_pct  # 大涨幅度（5%）
        self.pullback_pct = pullback_pct  # 回调幅度（3%）

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        # 计算涨跌幅
        df['change'] = df['Close'].pct_change()

        # 标记大涨日
        df['surge'] = df['change'] > self.surge_pct

        # 大涨后的回调
        df['days_since_surge'] = 0
        surge_idx = None
        surge_high = 0

        for i in range(len(df)):
            if df['surge'].iloc[i]:
                surge_idx = i
                surge_high = df['High'].iloc[i]

            if surge_idx is not None:
                df.iloc[i, df.columns.get_loc('days_since_surge')] = i - surge_idx

        # 量比
        df['vol_avg'] = df['Volume'].rolling(5).mean()
        df['vol_ratio'] = df['Volume'] / df['vol_avg']

        df['trade_signal'] = 0

        # 大涨后3-5天内，回调2-4%，缩量，买入
        for i in range(1, len(df)):
            days = df['days_since_surge'].iloc[i]
            if 2 <= days <= 5:
                # 计算从大涨日高点的回调幅度
                lookback = min(days, 5)
                recent_high = df['High'].iloc[i-lookback:i+1].max()
                pullback = (recent_high - df['Close'].iloc[i]) / recent_high

                # 缩量回调
                vol_shrink = df['vol_ratio'].iloc[i] < 0.8

                if self.pullback_pct * 0.5 < pullback < self.pullback_pct * 2 and vol_shrink:
                    df.iloc[i, df.columns.get_loc('trade_signal')] = 1

        # 卖出：涨5%或跌3%
        df['ma5'] = df['Close'].rolling(5).mean()
        df.loc[df['Close'] < df['ma5'] * 0.97, 'trade_signal'] = -1

        return df


class TrapFreeStrategy(Strategy):
    """无套牢盘策略：只买套牢盘低的股票"""

    def __init__(self, trapped_max: float = 20, vol_ratio_min: float = 1.0):
        super().__init__(f'TrapFree{trapped_max}')
        self.trapped_max = trapped_max
        self.vol_ratio_min = vol_ratio_min

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()

        # 均线
        df['ma5'] = df['Close'].rolling(5).mean()
        df['ma10'] = df['Close'].rolling(10).mean()
        df['ma20'] = df['Close'].rolling(20).mean()

        # 量比
        df['vol_avg'] = df['Volume'].rolling(5).mean()
        df['vol_ratio'] = df['Volume'] / df['vol_avg']

        # 套牢盘
        def calc_trapped(row_idx, closes, period=60):
            if row_idx < period:
                return 50
            window = closes[max(0, row_idx-period):row_idx]
            current = closes[row_idx]
            return (window > current).sum() / len(window) * 100

        closes = df['Close'].values
        df['trapped'] = [calc_trapped(i, closes) for i in range(len(df))]

        # 趋势
        df['uptrend'] = (df['ma5'] > df['ma10']) & (df['ma10'] > df['ma20'])

        df['trade_signal'] = 0

        # 买入：上升趋势 + 低套牢盘 + 放量
        buy_cond = (
            (df['uptrend']) &
            (df['trapped'] < self.trapped_max) &
            (df['vol_ratio'] > self.vol_ratio_min)
        )
        df.loc[buy_cond, 'trade_signal'] = 1

        # 卖出：跌破MA10
        sell_cond = df['Close'] < df['ma10']
        df.loc[sell_cond, 'trade_signal'] = -1

        return df


def run_backtest(ticker: str, strategy: Strategy, start_date: str = None,
                 end_date: str = None, initial_capital: float = 100000,
                 lot_size: int = 100) -> Dict:
    """运行回测"""

    # 获取数据
    stock = yf.Ticker(ticker)
    if start_date and end_date:
        data = stock.history(start=start_date, end=end_date)
    else:
        data = stock.history(period='1y')

    if len(data) < 30:
        return {'error': '数据不足'}

    # 生成信号
    data = strategy.generate_signals(data)

    # 初始化回测引擎
    engine = BacktestEngine(initial_capital)

    # 模拟交易
    holding = False
    for date, row in data.iterrows():
        date_str = date.strftime('%Y-%m-%d')
        price = row['Close']
        signal = row.get('trade_signal', 0)

        if signal == 1 and not holding:
            # 买入
            shares = (engine.capital * 0.95) // (price * lot_size) * lot_size
            if shares >= lot_size:
                engine.buy(ticker, price, int(shares), date_str)
                holding = True

        elif signal == -1 and holding:
            # 卖出
            engine.sell(ticker, price, date=date_str)
            holding = False

        # 记录净值
        engine.record_equity(date_str, {ticker: price})

    # 计算统计指标
    results = calculate_statistics(engine, data)
    results['strategy'] = strategy.name
    results['ticker'] = ticker
    results['trades'] = engine.trades

    return results


def calculate_statistics(engine: BacktestEngine, data: pd.DataFrame) -> Dict:
    """计算回测统计指标"""

    if not engine.equity_curve:
        return {}

    equity = pd.DataFrame(engine.equity_curve)
    equity['value'] = equity['value'].astype(float)

    # 总收益率
    total_return = (equity['value'].iloc[-1] / engine.initial_capital - 1) * 100

    # 年化收益率
    days = len(equity)
    annual_return = (1 + total_return / 100) ** (252 / days) - 1 if days > 0 else 0
    annual_return *= 100

    # 最大回撤
    equity['peak'] = equity['value'].cummax()
    equity['drawdown'] = (equity['value'] - equity['peak']) / equity['peak'] * 100
    max_drawdown = equity['drawdown'].min()

    # 交易统计
    trades = engine.trades
    sell_trades = [t for t in trades if t['action'] == 'SELL']

    win_trades = [t for t in sell_trades if t.get('pnl', 0) > 0]
    lose_trades = [t for t in sell_trades if t.get('pnl', 0) <= 0]

    win_rate = len(win_trades) / len(sell_trades) * 100 if sell_trades else 0

    total_profit = sum(t.get('pnl', 0) for t in win_trades)
    total_loss = sum(t.get('pnl', 0) for t in lose_trades)

    profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float('inf')

    avg_win = total_profit / len(win_trades) if win_trades else 0
    avg_loss = total_loss / len(lose_trades) if lose_trades else 0

    return {
        'initial_capital': engine.initial_capital,
        'final_capital': equity['value'].iloc[-1],
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'total_trades': len(sell_trades),
        'win_trades': len(win_trades),
        'lose_trades': len(lose_trades),
        'win_rate': round(win_rate, 2),
        'profit_factor': round(profit_factor, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'equity_curve': engine.equity_curve
    }


def print_backtest_report(results: Dict):
    """打印回测报告"""

    print("\n" + "=" * 60)
    print(f"回测报告: {results.get('ticker', 'N/A')} - {results.get('strategy', 'N/A')}")
    print("=" * 60)

    if 'error' in results:
        print(f"错误: {results['error']}")
        return

    print(f"\n【资金】")
    print(f"  初始资金: {results['initial_capital']:,.0f}")
    print(f"  最终资金: {results['final_capital']:,.0f}")

    print(f"\n【收益】")
    print(f"  总收益率: {results['total_return']:+.2f}%")
    print(f"  年化收益: {results['annual_return']:+.2f}%")
    print(f"  最大回撤: {results['max_drawdown']:.2f}%")

    print(f"\n【交易】")
    print(f"  总交易次数: {results['total_trades']}")
    print(f"  盈利次数: {results['win_trades']}")
    print(f"  亏损次数: {results['lose_trades']}")
    print(f"  胜率: {results['win_rate']:.1f}%")
    print(f"  盈亏比: {results['profit_factor']:.2f}")
    print(f"  平均盈利: {results['avg_win']:+.0f}")
    print(f"  平均亏损: {results['avg_loss']:.0f}")

    # 打印交易记录
    trades = results.get('trades', [])
    if trades:
        print(f"\n【交易记录】")
        print(f"{'日期':<12} {'操作':<6} {'价格':>8} {'数量':>8} {'盈亏':>10}")
        print("-" * 50)
        for t in trades[-10:]:  # 只显示最近10笔
            pnl = t.get('pnl', 0)
            pnl_str = f"{pnl:+.0f}" if t['action'] == 'SELL' else ""
            print(f"{t['date']:<12} {t['action']:<6} {t['price']:>8.2f} {t['shares']:>8} {pnl_str:>10}")

    print("\n" + "=" * 60)


def compare_strategies(ticker: str, strategies: List[Strategy], **kwargs) -> List[Dict]:
    """比较多个策略"""

    print(f"\n策略对比: {ticker}")
    print("=" * 70)
    print(f"{'策略':<25} {'收益率':>10} {'最大回撤':>10} {'胜率':>8} {'交易次数':>8}")
    print("-" * 70)

    results = []
    for strategy in strategies:
        result = run_backtest(ticker, strategy, **kwargs)
        results.append(result)

        if 'error' not in result:
            print(f"{result['strategy']:<25} {result['total_return']:>+9.2f}% {result['max_drawdown']:>9.2f}% {result['win_rate']:>7.1f}% {result['total_trades']:>8}")

    print("=" * 70)
    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python backtest.py <股票代码> [策略] [天数]")
        print("")
        print("策略选项:")
        print("  ma       - 均线策略 (MA5/MA20)")
        print("  rsi      - RSI策略 (超卖买入)")
        print("  breakout - 突破策略 (N日新高)")
        print("  volume   - 放量突破策略")
        print("  smart    - 智能突破 (ATR止损+低套牢盘+回调)")
        print("  pullback - 追涨回调 (大涨后缩量回调买入)")
        print("  trapfree - 无套牢盘策略 (只买套牢盘低的)")
        print("  all      - 比较所有策略")
        print("")
        print("示例:")
        print("  python backtest.py 0700.HK ma")
        print("  python backtest.py 1929.HK all")
        print("  python backtest.py 300058.SZ rsi")
        sys.exit(0)

    ticker = sys.argv[1].upper()
    if not ticker.endswith('.HK') and not ticker.endswith('.SZ') and not ticker.endswith('.SS'):
        ticker += '.HK'

    strategy_name = sys.argv[2] if len(sys.argv) > 2 else 'ma'

    # 确定手数
    lot_size = 100
    if ticker.endswith('.HK'):
        # 港股手数不固定，简化处理
        lot_size = 100

    strategies = {
        'ma': MAStrategy(5, 20),
        'rsi': RSIStrategy(14, 30, 70),
        'breakout': BreakoutStrategy(20),
        'volume': VolumeBreakoutStrategy(20, 1.5),
        'smart': SmartBreakoutStrategy(20, 1.2, 30, 0.03, 2.0),
        'pullback': MomentumPullbackStrategy(0.05, 0.03),
        'trapfree': TrapFreeStrategy(20, 1.0)
    }

    if strategy_name == 'all':
        compare_strategies(ticker, list(strategies.values()), lot_size=lot_size)
    elif strategy_name in strategies:
        result = run_backtest(ticker, strategies[strategy_name], lot_size=lot_size)
        print_backtest_report(result)
    else:
        print(f"未知策略: {strategy_name}")
        print("可用策略: ma, rsi, breakout, volume, all")
