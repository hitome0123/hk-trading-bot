#!/usr/bin/env python3
"""
技术形态识别 - 自动识别K线形态
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple


class PatternDetector:
    """K线形态识别"""

    def __init__(self):
        pass

    def get_data(self, ticker: str, period: str = '6mo') -> pd.DataFrame:
        """获取数据"""
        stock = yf.Ticker(ticker)
        return stock.history(period=period)

    def detect_double_bottom(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """
        识别双底形态 (W底)
        条件：两个相近的低点，中间有反弹
        """
        if len(df) < window * 2:
            return None

        lows = df['Low'].values[-window*2:]
        closes = df['Close'].values[-window*2:]

        # 找局部低点
        local_mins = []
        for i in range(2, len(lows) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                local_mins.append((i, lows[i]))

        if len(local_mins) < 2:
            return None

        # 检查最近两个低点
        bottom1 = local_mins[-2]
        bottom2 = local_mins[-1]

        # 两个低点价格接近（差距<5%）
        price_diff = abs(bottom1[1] - bottom2[1]) / bottom1[1]
        if price_diff > 0.05:
            return None

        # 中间有反弹（至少5%）
        mid_start = bottom1[0]
        mid_end = bottom2[0]
        mid_high = max(closes[mid_start:mid_end])
        rebound = (mid_high - bottom1[1]) / bottom1[1]

        if rebound < 0.05:
            return None

        # 当前价格位置
        current = closes[-1]
        neckline = mid_high  # 颈线位置

        # 是否突破颈线
        breakout = current > neckline

        return {
            'pattern': '双底(W底)',
            'bottom1_price': float(bottom1[1]),
            'bottom2_price': float(bottom2[1]),
            'neckline': float(neckline),
            'current': float(current),
            'breakout': breakout,
            'target': float(neckline + (neckline - bottom1[1])),  # 目标=颈线+底到颈线的距离
            'stop_loss': float(min(bottom1[1], bottom2[1]) * 0.98),
            'signal': '买入信号' if breakout else '等待突破颈线'
        }

    def detect_double_top(self, df: pd.DataFrame, window: int = 20) -> Dict:
        """
        识别双顶形态 (M顶)
        """
        if len(df) < window * 2:
            return None

        highs = df['High'].values[-window*2:]
        closes = df['Close'].values[-window*2:]

        # 找局部高点
        local_maxs = []
        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                local_maxs.append((i, highs[i]))

        if len(local_maxs) < 2:
            return None

        top1 = local_maxs[-2]
        top2 = local_maxs[-1]

        # 两个高点价格接近
        price_diff = abs(top1[1] - top2[1]) / top1[1]
        if price_diff > 0.05:
            return None

        # 中间有回调
        mid_start = top1[0]
        mid_end = top2[0]
        mid_low = min(closes[mid_start:mid_end])
        pullback = (top1[1] - mid_low) / top1[1]

        if pullback < 0.05:
            return None

        current = closes[-1]
        neckline = mid_low

        breakdown = current < neckline

        return {
            'pattern': '双顶(M顶)',
            'top1_price': float(top1[1]),
            'top2_price': float(top2[1]),
            'neckline': float(neckline),
            'current': float(current),
            'breakdown': breakdown,
            'target': float(neckline - (top1[1] - neckline)),
            'signal': '卖出信号' if breakdown else '警惕回落'
        }

    def detect_breakout(self, df: pd.DataFrame, period: int = 20) -> Dict:
        """
        识别突破形态
        """
        if len(df) < period + 5:
            return None

        current = df['Close'].iloc[-1]
        high_n = df['High'].tail(period + 1).iloc[:-1].max()
        low_n = df['Low'].tail(period + 1).iloc[:-1].min()

        vol_today = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].tail(5).mean()
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 0

        result = {
            'high_n': float(high_n),
            'low_n': float(low_n),
            'current': float(current),
            'vol_ratio': float(vol_ratio)
        }

        # 向上突破
        if current > high_n:
            result['pattern'] = '向上突破'
            result['breakout_pct'] = (current - high_n) / high_n * 100
            result['signal'] = '强势买入' if vol_ratio > 1.5 else '突破待确认'
            result['target'] = float(current + (high_n - low_n))
            result['stop_loss'] = float(high_n * 0.98)

        # 向下突破
        elif current < low_n:
            result['pattern'] = '向下突破'
            result['breakdown_pct'] = (low_n - current) / low_n * 100
            result['signal'] = '卖出/观望'
            result['target'] = float(current - (high_n - low_n))

        else:
            result['pattern'] = '区间震荡'
            result['position'] = (current - low_n) / (high_n - low_n) * 100
            result['signal'] = '观望'

        return result

    def detect_ma_cross(self, df: pd.DataFrame) -> Dict:
        """
        识别均线交叉
        """
        if len(df) < 30:
            return None

        df = df.copy()
        df['ma5'] = df['Close'].rolling(5).mean()
        df['ma10'] = df['Close'].rolling(10).mean()
        df['ma20'] = df['Close'].rolling(20).mean()

        current = df['Close'].iloc[-1]
        ma5 = df['ma5'].iloc[-1]
        ma10 = df['ma10'].iloc[-1]
        ma20 = df['ma20'].iloc[-1]

        ma5_prev = df['ma5'].iloc[-2]
        ma10_prev = df['ma10'].iloc[-2]

        result = {
            'current': float(current),
            'ma5': float(ma5),
            'ma10': float(ma10),
            'ma20': float(ma20)
        }

        # 金叉
        if ma5_prev < ma10_prev and ma5 > ma10:
            result['pattern'] = 'MA5金叉MA10'
            result['signal'] = '买入信号'
        # 死叉
        elif ma5_prev > ma10_prev and ma5 < ma10:
            result['pattern'] = 'MA5死叉MA10'
            result['signal'] = '卖出信号'
        # 多头排列
        elif ma5 > ma10 > ma20:
            result['pattern'] = '多头排列'
            result['signal'] = '持有'
        # 空头排列
        elif ma5 < ma10 < ma20:
            result['pattern'] = '空头排列'
            result['signal'] = '观望'
        else:
            result['pattern'] = '均线缠绕'
            result['signal'] = '方向不明'

        return result

    def detect_volume_pattern(self, df: pd.DataFrame) -> Dict:
        """
        识别量价形态
        """
        if len(df) < 10:
            return None

        current = df['Close'].iloc[-1]
        prev = df['Close'].iloc[-2]
        change = (current - prev) / prev * 100

        vol_today = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].tail(5).mean()
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 0

        result = {
            'current': float(current),
            'change': float(change),
            'vol_ratio': float(vol_ratio)
        }

        # 放量上涨
        if change > 2 and vol_ratio > 1.5:
            result['pattern'] = '放量上涨'
            result['signal'] = '强势，可追'
        # 放量下跌
        elif change < -2 and vol_ratio > 1.5:
            result['pattern'] = '放量下跌'
            result['signal'] = '弱势，观望'
        # 缩量上涨
        elif change > 1 and vol_ratio < 0.8:
            result['pattern'] = '缩量上涨'
            result['signal'] = '上涨乏力'
        # 缩量下跌
        elif change < -1 and vol_ratio < 0.8:
            result['pattern'] = '缩量下跌'
            result['signal'] = '可能企稳'
        # 放量滞涨
        elif abs(change) < 1 and vol_ratio > 1.5:
            result['pattern'] = '放量滞涨'
            result['signal'] = '注意变盘'
        else:
            result['pattern'] = '正常波动'
            result['signal'] = '观望'

        return result

    def detect_support_resistance_test(self, df: pd.DataFrame) -> Dict:
        """
        识别支撑阻力测试
        """
        if len(df) < 20:
            return None

        current = df['Close'].iloc[-1]
        high_20d = df['High'].tail(20).max()
        low_20d = df['Low'].tail(20).min()

        # 计算位置
        pos = (current - low_20d) / (high_20d - low_20d) * 100

        result = {
            'current': float(current),
            'high_20d': float(high_20d),
            'low_20d': float(low_20d),
            'position': float(pos)
        }

        # 测试阻力
        if pos > 95:
            result['pattern'] = '测试阻力位'
            result['signal'] = '突破则追，否则减仓'
            result['key_price'] = float(high_20d)
        # 测试支撑
        elif pos < 5:
            result['pattern'] = '测试支撑位'
            result['signal'] = '企稳则买，破位则跑'
            result['key_price'] = float(low_20d)
        # 中间位置
        else:
            result['pattern'] = '区间中部'
            result['signal'] = '观望'

        return result

    def full_scan(self, ticker: str) -> Dict:
        """
        完整形态扫描
        """
        ticker = ticker.upper()
        if not any(ticker.endswith(x) for x in ['.HK', '.SZ', '.SS']):
            ticker += '.HK'

        df = self.get_data(ticker)
        if len(df) < 30:
            return {'error': '数据不足'}

        results = {
            'ticker': ticker,
            'current': float(df['Close'].iloc[-1]),
            'patterns': []
        }

        # 检测各种形态
        checks = [
            ('双底', self.detect_double_bottom),
            ('双顶', self.detect_double_top),
            ('突破', self.detect_breakout),
            ('均线', self.detect_ma_cross),
            ('量价', self.detect_volume_pattern),
            ('支撑阻力', self.detect_support_resistance_test)
        ]

        for name, func in checks:
            try:
                result = func(df)
                if result and result.get('pattern'):
                    result['type'] = name
                    results['patterns'].append(result)
            except:
                pass

        return results


def scan_stock(ticker: str):
    """扫描单只股票"""
    detector = PatternDetector()
    results = detector.full_scan(ticker)

    if 'error' in results:
        print(f"错误: {results['error']}")
        return

    print(f"\n{'='*60}")
    print(f"形态识别: {results['ticker']}")
    print(f"当前价格: {results['current']:.2f}")
    print(f"{'='*60}")

    for p in results['patterns']:
        signal_icon = '🟢' if '买' in p.get('signal', '') else ('🔴' if '卖' in p.get('signal', '') or '弱' in p.get('signal', '') else '🟡')
        print(f"\n{signal_icon} [{p['type']}] {p['pattern']}")
        print(f"   信号: {p.get('signal', 'N/A')}")

        if 'target' in p:
            print(f"   目标价: {p['target']:.2f}")
        if 'stop_loss' in p:
            print(f"   止损价: {p['stop_loss']:.2f}")
        if 'neckline' in p:
            print(f"   颈线: {p['neckline']:.2f}")
        if 'vol_ratio' in p:
            print(f"   量比: {p['vol_ratio']:.2f}x")

    print(f"\n{'='*60}")


def scan_watchlist():
    """扫描关注列表"""
    watchlist = [
        '0700.HK', '9888.HK', '9618.HK', '1929.HK',
        '0386.HK', '0981.HK', '1024.HK', '1816.HK'
    ]

    detector = PatternDetector()

    print(f"\n{'='*70}")
    print(f"形态扫描 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"{'='*70}")

    signals = []

    for ticker in watchlist:
        results = detector.full_scan(ticker)
        if 'error' in results:
            continue

        for p in results['patterns']:
            signal = p.get('signal', '')
            if '买' in signal or '强势' in signal:
                signals.append({
                    'ticker': ticker,
                    'pattern': p['pattern'],
                    'signal': signal,
                    'type': 'buy'
                })
            elif '卖' in signal or '弱势' in signal:
                signals.append({
                    'ticker': ticker,
                    'pattern': p['pattern'],
                    'signal': signal,
                    'type': 'sell'
                })

    # 买入信号
    buy_signals = [s for s in signals if s['type'] == 'buy']
    if buy_signals:
        print("\n🟢 买入信号:")
        for s in buy_signals:
            print(f"   {s['ticker']}: {s['pattern']} - {s['signal']}")

    # 卖出信号
    sell_signals = [s for s in signals if s['type'] == 'sell']
    if sell_signals:
        print("\n🔴 卖出/警示信号:")
        for s in sell_signals:
            print(f"   {s['ticker']}: {s['pattern']} - {s['signal']}")

    if not signals:
        print("\n暂无明显信号")

    print(f"\n{'='*70}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python pattern_detector.py scan 0700.HK  - 扫描单只股票")
        print("  python pattern_detector.py watch         - 扫描关注列表")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'scan' and len(sys.argv) >= 3:
        scan_stock(sys.argv[2])
    elif cmd == 'watch':
        scan_watchlist()
    else:
        print("未知命令")
