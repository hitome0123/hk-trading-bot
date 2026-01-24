#!/usr/bin/env python3
"""
相似K线 - 找历史上走势相似的情况
"""

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple


class SimilarKlineFinder:
    """相似K线查找器"""

    def __init__(self):
        pass

    def normalize_series(self, series: np.ndarray) -> np.ndarray:
        """归一化序列"""
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return np.zeros_like(series)
        return (series - min_val) / (max_val - min_val)

    def calc_similarity(self, pattern1: np.ndarray, pattern2: np.ndarray) -> float:
        """
        计算两个K线模式的相似度
        返回0-100，越高越相似
        """
        if len(pattern1) != len(pattern2):
            return 0

        # 归一化
        p1 = self.normalize_series(pattern1)
        p2 = self.normalize_series(pattern2)

        # 计算欧氏距离
        distance = np.sqrt(np.sum((p1 - p2) ** 2))
        max_distance = np.sqrt(len(pattern1))  # 最大可能距离

        # 转换为相似度
        similarity = (1 - distance / max_distance) * 100

        return max(0, similarity)

    def find_similar_patterns(self, ticker: str, lookback: int = 10,
                             history_days: int = 365, top_n: int = 5) -> List[Dict]:
        """
        在历史数据中找相似的K线形态

        ticker: 股票代码
        lookback: 当前形态长度（天）
        history_days: 搜索历史范围（天）
        top_n: 返回最相似的N个
        """
        ticker = ticker.upper()
        if not any(ticker.endswith(x) for x in ['.HK', '.SZ', '.SS']):
            ticker += '.HK'

        stock = yf.Ticker(ticker)
        df = stock.history(period='2y')

        if len(df) < history_days:
            return []

        # 当前形态
        current_pattern = df['Close'].values[-lookback:]

        # 在历史中搜索
        results = []
        search_end = len(df) - lookback - 5  # 留出后续走势

        for i in range(lookback, search_end):
            historical_pattern = df['Close'].values[i-lookback:i]
            similarity = self.calc_similarity(current_pattern, historical_pattern)

            if similarity > 60:  # 只保留相似度>60%的
                # 获取该形态之后的走势
                future_start = i
                future_end = min(i + 10, len(df))
                future_prices = df['Close'].values[future_start:future_end]

                if len(future_prices) > 1:
                    future_return = (future_prices[-1] - future_prices[0]) / future_prices[0] * 100
                    max_gain = (future_prices.max() - future_prices[0]) / future_prices[0] * 100
                    max_loss = (future_prices.min() - future_prices[0]) / future_prices[0] * 100

                    results.append({
                        'date': df.index[i].strftime('%Y-%m-%d'),
                        'similarity': similarity,
                        'future_return': future_return,
                        'max_gain': max_gain,
                        'max_loss': max_loss,
                        'start_price': float(df['Close'].values[i]),
                        'end_price': float(future_prices[-1])
                    })

        # 按相似度排序
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results[:top_n]

    def predict_from_similar(self, similar_results: List[Dict]) -> Dict:
        """
        根据相似K线预测未来走势
        """
        if not similar_results:
            return {'error': '无相似形态'}

        returns = [r['future_return'] for r in similar_results]
        max_gains = [r['max_gain'] for r in similar_results]
        max_losses = [r['max_loss'] for r in similar_results]

        avg_return = np.mean(returns)
        win_rate = len([r for r in returns if r > 0]) / len(returns) * 100

        return {
            'sample_count': len(similar_results),
            'avg_return': avg_return,
            'max_avg_gain': np.mean(max_gains),
            'max_avg_loss': np.mean(max_losses),
            'win_rate': win_rate,
            'best_case': max(returns),
            'worst_case': min(returns),
            'prediction': '看涨' if avg_return > 1 else ('看跌' if avg_return < -1 else '震荡')
        }


def analyze_similar(ticker: str, lookback: int = 10):
    """分析相似K线"""
    finder = SimilarKlineFinder()

    print(f"\n{'='*60}")
    print(f"相似K线分析: {ticker.upper()}")
    print(f"形态长度: {lookback}天")
    print(f"{'='*60}")

    results = finder.find_similar_patterns(ticker, lookback)

    if not results:
        print("未找到相似形态")
        return

    print(f"\n找到 {len(results)} 个相似形态:")
    print(f"\n{'日期':<12} {'相似度':>8} {'后10日涨跌':>12} {'最大涨':>8} {'最大跌':>8}")
    print("-" * 55)

    for r in results:
        ret_icon = '🟢' if r['future_return'] > 0 else '🔴'
        print(f"{r['date']:<12} {r['similarity']:>7.1f}% {ret_icon}{r['future_return']:>+10.2f}% {r['max_gain']:>+7.2f}% {r['max_loss']:>+7.2f}%")

    # 预测
    pred = finder.predict_from_similar(results)

    print(f"\n{'='*60}")
    print("📊 基于相似形态的预测:")
    print(f"{'='*60}")
    print(f"  样本数: {pred['sample_count']}")
    print(f"  平均收益: {pred['avg_return']:+.2f}%")
    print(f"  胜率: {pred['win_rate']:.0f}%")
    print(f"  最好情况: {pred['best_case']:+.2f}%")
    print(f"  最差情况: {pred['worst_case']:+.2f}%")
    print(f"  平均最大涨幅: {pred['max_avg_gain']:+.2f}%")
    print(f"  平均最大跌幅: {pred['max_avg_loss']:+.2f}%")

    pred_icon = '🟢' if pred['prediction'] == '看涨' else ('🔴' if pred['prediction'] == '看跌' else '🟡')
    print(f"\n  {pred_icon} 预测方向: {pred['prediction']}")

    # 操作建议
    print(f"\n💡 操作建议:")
    if pred['win_rate'] > 70 and pred['avg_return'] > 2:
        print(f"   历史胜率高，可以考虑做多")
    elif pred['win_rate'] < 30 and pred['avg_return'] < -2:
        print(f"   历史胜率低，建议观望或做空")
    else:
        print(f"   信号不明确，谨慎操作")

    print(f"\n{'='*60}")


def batch_analyze(tickers: List[str]):
    """批量分析"""
    finder = SimilarKlineFinder()

    print(f"\n{'='*70}")
    print(f"相似K线批量分析 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"{'='*70}")
    print(f"\n{'股票':<12} {'相似数':>6} {'平均收益':>10} {'胜率':>8} {'预测':>8}")
    print("-" * 50)

    for ticker in tickers:
        try:
            results = finder.find_similar_patterns(ticker, 10)
            if results:
                pred = finder.predict_from_similar(results)
                pred_icon = '🟢' if pred['prediction'] == '看涨' else ('🔴' if pred['prediction'] == '看跌' else '🟡')
                print(f"{ticker:<12} {pred['sample_count']:>6} {pred['avg_return']:>+9.2f}% {pred['win_rate']:>7.0f}% {pred_icon}{pred['prediction']:>6}")
            else:
                print(f"{ticker:<12} {'无数据':>6}")
        except Exception as e:
            print(f"{ticker:<12} {'错误':>6}")

    print(f"\n{'='*70}")


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python similar_kline.py 0700.HK      - 分析单只股票")
        print("  python similar_kline.py 0700.HK 15   - 指定形态长度(天)")
        print("  python similar_kline.py batch        - 批量分析热门股")
        sys.exit(0)

    if sys.argv[1] == 'batch':
        tickers = ['0700.HK', '9888.HK', '9618.HK', '1929.HK',
                   '0386.HK', '0981.HK', '1024.HK', '1816.HK']
        batch_analyze(tickers)
    else:
        ticker = sys.argv[1]
        lookback = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        analyze_similar(ticker, lookback)
