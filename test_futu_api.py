#!/usr/bin/env python3
"""
测试富途 OpenAPI 连接和数据获取
Test Futu OpenAPI connection and data retrieval
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.futu_provider import FutuProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from datetime import datetime


def test_futu_connection():
    """测试富途 API 连接"""
    print("=" * 80)
    print("🚀 富途 OpenAPI 连接测试")
    print("=" * 80)

    # 创建富途数据提供器
    provider = FutuProvider(host="127.0.0.1", port=11111)

    # 测试连接
    print("\n1️⃣ 测试连接到 FutuOpenD...")
    if not provider.connect():
        print("\n❌ 连接失败！")
        print("\n💡 请确保：")
        print("   1. 已下载并安装 FutuOpenD 客户端")
        print("   2. FutuOpenD 正在运行")
        print("   3. FutuOpenD 端口设置为 11111（默认）")
        print("\n📥 下载地址: https://www.futuhk.com/download/openAPI")
        return False

    print("✅ 连接成功！\n")
    return True


def test_stock_data(ticker: str = "1801.HK"):
    """
    测试获取股票数据

    Args:
        ticker: 股票代码（默认：信达生物 1801.HK）
    """
    print("=" * 80)
    print(f"📊 测试获取股票数据: {ticker}")
    print("=" * 80)

    # 使用上下文管理器自动连接和断开
    with FutuProvider() as provider:

        # 1. 获取当前价格
        print(f"\n1️⃣ 获取当前价格...")
        current_price = provider.get_current_price(ticker)
        print(f"   当前价格: {current_price:.2f} HKD\n")

        # 2. 获取股票基本信息
        print(f"2️⃣ 获取股票基本信息...")
        stock_info = provider.get_stock_info(ticker)
        print(f"   公司名称: {stock_info.get('longName', 'N/A')}")
        print(f"   交易所: {stock_info.get('exchange', 'N/A')}")
        print(f"   货币: {stock_info.get('currency', 'N/A')}\n")

        # 3. 获取历史数据
        print(f"3️⃣ 获取历史价格数据（60天）...")
        price_data = provider.get_price_data(ticker, days=60)

        if price_data and price_data.get('close'):
            print(f"   数据点数: {len(price_data['close'])} 天")
            print(f"   最高价: {max(price_data['high']):.2f} HKD")
            print(f"   最低价: {min(price_data['low']):.2f} HKD")
            print(f"   平均价: {sum(price_data['close'])/len(price_data['close']):.2f} HKD\n")

            # 4. 计算技术指标
            print(f"4️⃣ 计算技术指标...")
            indicators_calc = TechnicalIndicators()
            indicators = indicators_calc.calculate_all_indicators(price_data)

            ema20 = indicators.get('ema20')
            ema50 = indicators.get('ema50')
            rsi14 = indicators.get('rsi14')
            atr14 = indicators.get('atr14')

            print(f"   EMA20: {ema20:.2f} HKD")
            print(f"   EMA50: {ema50:.2f} HKD")
            print(f"   RSI14: {rsi14:.2f}")
            print(f"   ATR14: {atr14:.2f} HKD\n")

            # 5. 入场策略分析
            print(f"5️⃣ 入场策略分析...")
            entry_strategy = EntryStrategy()
            entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)

            print(f"   信号: {entry_analysis.get('signal')}")
            print(f"   理由: {entry_analysis.get('reason')}")
            print(f"   建议入场价: {entry_analysis.get('entry_price', 0):.2f} HKD\n")

        # 6. 详细分析
        print(f"6️⃣ 获取详细分析...")
        detailed = provider.get_detailed_analysis(ticker)

        if 'error' not in detailed:
            price_analysis = detailed.get('price_analysis', {})
            print(f"   52周高点: {price_analysis.get('52w_high', 0):.2f} HKD")
            print(f"   52周低点: {price_analysis.get('52w_low', 0):.2f} HKD")
            print(f"   价格位置: {price_analysis.get('price_position_pct', 0):.1f}%")

            vol_analysis = detailed.get('volatility_analysis', {})
            print(f"   年化波动率: {vol_analysis.get('annual_volatility', 0)*100:.1f}%")
            print(f"   风险等级: {vol_analysis.get('risk_level', 'Unknown')}\n")

        # 7. 市场状态
        print(f"7️⃣ 检查市场状态...")
        market_open = provider.is_market_open()
        print(f"   市场状态: {'🟢 开盘中' if market_open else '🔴 已收盘'}\n")

    print("=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)


def analyze_innovent():
    """专门分析信达生物（1801.HK）"""
    ticker = "1801.HK"
    cost_price = 90.0  # 您的成本价

    print("=" * 80)
    print(f"📊 信达生物 ({ticker}) 分析报告")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 您的持仓成本: {cost_price:.2f} HKD")
    print("=" * 80)

    with FutuProvider() as provider:
        # 获取当前价格
        current_price = provider.get_current_price(ticker)
        print(f"\n💰 当前价格: {current_price:.2f} HKD")
        print(f"💰 您的成本: {cost_price:.2f} HKD")

        # 计算盈亏
        pnl = current_price - cost_price
        pnl_pct = (pnl / cost_price) * 100
        print(f"📊 盈亏: {pnl:+.2f} HKD ({pnl_pct:+.2f}%)")

        if pnl > 0:
            print(f"✅ 当前盈利")
        elif pnl < 0:
            print(f"⚠️ 当前浮亏")
        else:
            print(f"➡️ 持平")

        # 获取历史数据
        price_data = provider.get_price_data(ticker, days=60)

        if price_data and price_data.get('close'):
            # 计算技术指标
            indicators_calc = TechnicalIndicators()
            indicators = indicators_calc.calculate_all_indicators(price_data)

            print(f"\n📈 技术指标:")
            print(f"   EMA20: {indicators.get('ema20', 0):.2f} HKD")
            print(f"   EMA50: {indicators.get('ema50', 0):.2f} HKD")
            print(f"   RSI14: {indicators.get('rsi14', 0):.2f}")
            print(f"   ATR14: {indicators.get('atr14', 0):.2f} HKD")

            # 入场分析
            entry_strategy = EntryStrategy()
            entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)

            print(f"\n🎯 交易信号:")
            print(f"   信号: {entry_analysis.get('signal')}")
            print(f"   理由: {entry_analysis.get('reason')}")

        # 详细分析
        detailed = provider.get_detailed_analysis(ticker)

        if 'error' not in detailed:
            price_analysis = detailed.get('price_analysis', {})
            print(f"\n📊 价格分析:")
            print(f"   52周高点: {price_analysis.get('52w_high', 0):.2f} HKD")
            print(f"   52周低点: {price_analysis.get('52w_low', 0):.2f} HKD")
            print(f"   价格位置: {price_analysis.get('price_position_pct', 0):.1f}% (从52周低点)")

        # 投资建议
        print(f"\n💡 基于成本价 {cost_price:.2f} HKD 的建议:")
        print(f"   止损位: {cost_price * 0.85:.2f} HKD（-15%）")
        print(f"   止盈位: {cost_price * 1.10:.2f} HKD（+10%）")

        print("\n" + "=" * 80)
        print("⚠️ 风险提示：以上分析仅供参考，不构成投资建议。")
        print("=" * 80)


if __name__ == "__main__":
    # 显示菜单
    print("\n" + "=" * 80)
    print("🚀 富途 OpenAPI 测试程序")
    print("=" * 80)
    print("\n请选择测试项目：")
    print("1. 测试连接")
    print("2. 测试股票数据获取（1801.HK）")
    print("3. 分析信达生物（1801.HK）")
    print("4. 全部测试")
    print("\n")

    choice = input("请输入选项 (1-4，默认4): ").strip() or "4"

    if choice == "1":
        test_futu_connection()
    elif choice == "2":
        if test_futu_connection():
            test_stock_data("1801.HK")
    elif choice == "3":
        if test_futu_connection():
            analyze_innovent()
    elif choice == "4":
        if test_futu_connection():
            print("\n")
            test_stock_data("1801.HK")
            print("\n")
            analyze_innovent()
    else:
        print("无效选项！")
