#!/usr/bin/env python3
"""
港股波段交易分析工具
用法: python swing_trade.py <股票代码> [股票代码2] ...
示例: python swing_trade.py 0700.HK 0981.HK 9888.HK
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from typing import List, Dict
from hk_trading_bot.data_providers import EnhancedDataProvider
from hk_trading_bot.modules.indicators import SwingAnalyzer, TechnicalIndicators


class SwingTradeScanner:
    """波段交易扫描器"""

    def __init__(self):
        self.data_provider = EnhancedDataProvider()
        self.analyzer = SwingAnalyzer()
        self.indicators_calc = TechnicalIndicators()

    def scan_ticker(self, ticker: str) -> Dict:
        """扫描单个股票的波段机会"""
        print(f"\n🔍 扫描 {ticker}...")

        try:
            # 获取价格数据
            price_data = self.data_provider.yahoo_provider.get_price_data(ticker, 60)
            current_price = price_data['close'][-1] if price_data['close'] else 0

            if current_price == 0:
                print(f"   ❌ 无法获取 {ticker} 的价格数据")
                return None

            # 计算技术指标
            indicators = self.indicators_calc.calculate_all_indicators(price_data)

            # 生成波段计划
            plan = self.analyzer.calculate_swing_plan(
                ticker, current_price, indicators, price_data
            )

            return {
                'ticker': ticker,
                'plan': plan,
                'indicators': indicators,
                'price_data': price_data
            }

        except Exception as e:
            print(f"   ❌ 分析 {ticker} 时出错: {e}")
            return None

    def scan_multiple(self, tickers: List[str]) -> List[Dict]:
        """扫描多个股票"""
        results = []
        for ticker in tickers:
            result = self.scan_ticker(ticker)
            if result:
                results.append(result)
        return results

    def print_summary(self, results: List[Dict]):
        """打印汇总结果"""
        if not results:
            print("\n❌ 没有可用的分析结果")
            return

        print(f"\n{'='*70}")
        print(f"📊 波段扫描汇总 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*70}")

        # 按信号排序: BUY > WAIT > AVOID
        signal_order = {'BUY': 0, 'WAIT': 1, 'AVOID': 2}
        results.sort(key=lambda x: (signal_order.get(x['plan'].signal, 3), -x['plan'].risk_reward_ratio))

        # 打印表格头
        print(f"\n{'股票':<10} {'现价':>8} {'信号':<6} {'置信度':<8} {'趋势':<10} {'RSI':>6} {'风险收益比':>10}")
        print("-" * 70)

        for r in results:
            plan = r['plan']
            indicators = r['indicators']

            signal_emoji = {'BUY': '🟢', 'WAIT': '🟡', 'AVOID': '🔴'}.get(plan.signal, '⚪')
            trend_cn = {'up': '上涨', 'down': '下跌', 'sideways': '震荡'}.get(plan.trend, '未知')

            print(f"{plan.ticker:<10} {plan.current_price:>8.2f} {signal_emoji}{plan.signal:<5} {plan.confidence:<8} {trend_cn:<10} {indicators['rsi14']:>6.1f} {plan.risk_reward_ratio:>10.2f}")

        # 打印详细计划
        print(f"\n{'='*70}")
        print("📋 详细交易计划")
        print(f"{'='*70}")

        for r in results:
            plan = r['plan']
            print(self.analyzer.format_plan(plan))

        # 打印推荐
        buy_signals = [r for r in results if r['plan'].signal == 'BUY']
        if buy_signals:
            print(f"\n{'='*70}")
            print("⭐ 推荐关注")
            print(f"{'='*70}")

            # 按置信度和风险收益比排序
            buy_signals.sort(key=lambda x: (
                0 if x['plan'].confidence == 'high' else 1,
                -x['plan'].risk_reward_ratio
            ))

            for i, r in enumerate(buy_signals[:3], 1):
                plan = r['plan']
                print(f"\n#{i} {plan.ticker}")
                print(f"   现价: {plan.current_price:.2f} | 买入: {plan.entry_low:.2f}-{plan.entry_high:.2f}")
                print(f"   止损: {plan.stop_loss:.2f} (-{plan.risk_pct:.1f}%)")
                print(f"   止盈: {plan.take_profit_1:.2f} / {plan.take_profit_2:.2f}")
                print(f"   风险收益比: 1:{plan.risk_reward_ratio:.1f}")

        # 风险提示
        print(f"\n{'='*70}")
        print("⚠️ 风险提示")
        print("─" * 70)
        print("• 以上分析仅供参考，不构成投资建议")
        print("• 波段交易有风险，请严格执行止损")
        print("• 建议单笔仓位不超过总资金的10%")
        print("• 港股下午收盘16:00，注意时间")
        print(f"{'='*70}\n")


def main():
    if len(sys.argv) < 2:
        print("用法: python swing_trade.py <股票代码> [股票代码2] ...")
        print("示例: python swing_trade.py 0700.HK")
        print("      python swing_trade.py 0700.HK 0981.HK 9888.HK 1347.HK")
        print("\n常用港股代码:")
        print("  0700.HK  腾讯控股")
        print("  9988.HK  阿里巴巴")
        print("  0981.HK  中芯国际")
        print("  1347.HK  华虹半导体")
        print("  9888.HK  百度集团")
        print("  1810.HK  小米集团")
        print("  9618.HK  京东集团")
        print("  3690.HK  美团")
        return

    tickers = [t.upper() for t in sys.argv[1:]]

    # 确保以.HK结尾
    tickers = [t if t.endswith('.HK') else t + '.HK' for t in tickers]

    print(f"🚀 港股波段分析工具")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 分析标的: {', '.join(tickers)}")

    scanner = SwingTradeScanner()
    results = scanner.scan_multiple(tickers)
    scanner.print_summary(results)


if __name__ == "__main__":
    main()
