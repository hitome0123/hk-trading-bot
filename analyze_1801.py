#!/usr/bin/env python3
"""
信达生物 (01801.HK) 技术指标分析
成本价：90 HKD
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from datetime import datetime
import numpy as np
import yfinance as yf


def analyze_1801():
    """分析01801.HK（信达生物）的技术指标"""
    ticker = "1801.HK"
    cost_price = 90.0  # 用户成本价
    provider = YFinanceProvider()
    indicators_calc = TechnicalIndicators()
    entry_strategy = EntryStrategy()

    print("=" * 80)
    print(f"📊 信达生物 (01801.HK) 技术指标分析报告")
    print(f"⏰ 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💰 您的持仓成本: {cost_price:.2f} HKD")
    print("=" * 80)

    # 1. 获取基本信息
    print(f"\n📈 基本信息:")
    stock_info = provider.get_stock_info(ticker)
    print(f"   公司名称: {stock_info.get('longName', 'N/A')}")
    print(f"   交易所: {stock_info.get('exchange', 'N/A')}")
    print(f"   行业: {stock_info.get('industry', 'N/A')}")
    print(
        f"   市值: {stock_info.get('market_cap', 0):,.0f} {stock_info.get('currency', 'HKD')}"
        if stock_info.get("market_cap")
        else "   市值: N/A"
    )

    # 2. 获取价格数据
    print(f"\n💰 价格信息:")
    current_price = provider.get_current_price(ticker)
    print(f"   当前价格: {current_price:.2f} HKD")
    print(f"   您的成本: {cost_price:.2f} HKD")

    # 计算盈亏
    pnl = current_price - cost_price
    pnl_pct = (pnl / cost_price) * 100
    print(f"   盈亏: {pnl:+.2f} HKD ({pnl_pct:+.2f}%)")

    if pnl > 0:
        print(f"   ✅ 当前盈利")
    elif pnl < 0:
        print(f"   ⚠️ 当前浮亏")
    else:
        print(f"   ➡️ 持平")

    print(f"   前一收盘: {stock_info.get('previous_close', 'N/A')}")
    print(f"   52周最高: {stock_info.get('fifty_two_week_high', 'N/A')}")
    print(f"   52周最低: {stock_info.get('fifty_two_week_low', 'N/A')}")

    # 计算52周位置
    week52_high = stock_info.get("fifty_two_week_high")
    week52_low = stock_info.get("fifty_two_week_low")
    if week52_high and week52_low:
        price_position = (
            (current_price - week52_low) / (week52_high - week52_low)
        ) * 100
        print(f"   52周位置: {price_position:.1f}% (从52周低点)")

    # 3. 获取历史数据并计算技术指标
    print(f"\n📊 技术指标分析:")
    price_data = provider.get_price_data(ticker, 60)

    if price_data and price_data.get("close"):
        print(f"   历史数据: {len(price_data['close'])} 个交易日")

        # 计算技术指标
        indicators = indicators_calc.calculate_all_indicators(price_data)

        ema20 = indicators.get("ema20", np.nan)
        ema50 = indicators.get("ema50", np.nan)
        rsi14 = indicators.get("rsi14", np.nan)
        atr14 = indicators.get("atr14", np.nan)

        print(f"\n   📈 技术指标值:")
        if not np.isnan(ema20):
            print(f"      EMA20: {ema20:.2f} HKD")
            ema20_signal = (
                "📈 价格在EMA20之上" if current_price > ema20 else "📉 价格在EMA20之下"
            )
            print(f"             {ema20_signal}")
        else:
            print(f"      EMA20: N/A")

        if not np.isnan(ema50):
            print(f"      EMA50: {ema50:.2f} HKD")
            ema50_signal = (
                "📈 价格在EMA50之上" if current_price > ema50 else "📉 价格在EMA50之下"
            )
            print(f"             {ema50_signal}")
        else:
            print(f"      EMA50: N/A")

        if not np.isnan(ema20) and not np.isnan(ema50):
            if ema20 > ema50:
                print(f"      📈 EMA趋势: 上升趋势 (EMA20 > EMA50)")
            else:
                print(f"      📉 EMA趋势: 下降趋势 (EMA20 < EMA50)")

        if not np.isnan(rsi14):
            print(f"      RSI14: {rsi14:.2f}")
            if rsi14 < 30:
                print(f"            ⚠️ 超卖区域 (RSI < 30)")
            elif rsi14 > 70:
                print(f"            ⚠️ 超买区域 (RSI > 70)")
            else:
                print(f"            ✅ 正常区域 (30 < RSI < 70)")
        else:
            print(f"      RSI14: N/A")

        if not np.isnan(atr14):
            print(f"      ATR14: {atr14:.2f} HKD")
            atr_pct = (atr14 / current_price) * 100
            print(f"             (波动率: {atr_pct:.2f}%)")
        else:
            print(f"      ATR14: N/A")

        # 入场分析
        entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)

        print(f"\n   🎯 交易信号分析:")
        signal = entry_analysis.get("signal", "NO_SIGNAL")
        if signal == "LONG":
            print(f"      信号: ✅ 买入信号 (LONG)")
        elif signal == "WAIT":
            print(f"      信号: ⏸️ 等待信号 (WAIT)")
        else:
            print(f"      信号: ❌ 无明确信号")

        print(f"      理由: {entry_analysis.get('reason', 'N/A')}")

    # 4. 获取换手率、机构持仓等数据
    print(f"\n📊 换手率与机构持仓分析:")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # 换手率计算
        float_shares = info.get("floatShares", 0)  # 流通股本
        current_volume = info.get("volume", 0)  # 当日成交量
        avg_volume = info.get("averageVolume", 0)  # 平均成交量

        if float_shares and float_shares > 0:
            turnover_rate = (current_volume / float_shares) * 100
            avg_turnover_rate = (avg_volume / float_shares) * 100

            print(f"   流通股本: {float_shares:,.0f} 股")
            print(f"   当日成交量: {current_volume:,.0f} 股")
            print(f"   平均成交量: {avg_volume:,.0f} 股")
            print(f"   当日换手率: {turnover_rate:.2f}%")
            print(f"   平均换手率: {avg_turnover_rate:.2f}%")

            if turnover_rate < avg_turnover_rate * 0.5:
                print(f"             ⚠️ 换手率偏低（低于平均值的50%），流动性较弱")
            elif turnover_rate > avg_turnover_rate * 1.5:
                print(f"             🔥 换手率较高（高于平均值的150%），交易活跃")
            else:
                print(f"             ✅ 换手率正常")

        # 机构持仓
        inst_holding_pct = info.get("heldPercentInstitutions", 0)
        insider_holding_pct = info.get("heldPercentInsiders", 0)
        shares_outstanding = info.get("sharesOutstanding", 0)

        if inst_holding_pct:
            print(f"\n   机构持仓: {inst_holding_pct*100:.2f}%")
            if inst_holding_pct > 0.6:
                print(f"             ✅ 机构持仓比例高（>60%），机构看好")
            elif inst_holding_pct > 0.4:
                print(f"             ➡️ 机构持仓比例中等（40-60%）")
            else:
                print(f"             ⚠️ 机构持仓比例较低（<40%）")

        if insider_holding_pct:
            print(f"   内部人持仓: {insider_holding_pct*100:.2f}%")

        if shares_outstanding:
            print(f"   总股本: {shares_outstanding:,.0f} 股")

        # 机构成本估算（使用过去一年的成交量加权平均价格）
        if price_data and price_data.get("close"):
            hist_data = stock.history(period="1y")
            if not hist_data.empty and "Volume" in hist_data.columns:
                # 计算成交量加权平均价格（VWAP）作为机构成本的参考
                volumes = hist_data["Volume"].values
                closes = hist_data["Close"].values

                # 排除异常值（成交量过小的交易日）
                valid_mask = volumes > np.percentile(volumes, 10)
                if valid_mask.sum() > 0:
                    vwap = np.average(closes[valid_mask], weights=volumes[valid_mask])

                    # 计算不同时期的VWAP
                    if len(volumes) >= 252:  # 一年数据
                        # 最近3个月的VWAP
                        recent_volumes = volumes[-63:]  # 约3个月
                        recent_closes = closes[-63:]
                        recent_valid = recent_volumes > np.percentile(
                            recent_volumes, 10
                        )
                        if recent_valid.sum() > 0:
                            recent_vwap = np.average(
                                recent_closes[recent_valid],
                                weights=recent_volumes[recent_valid],
                            )
                            print(f"\n   机构成本估算（VWAP）:")
                            print(f"   过去1年VWAP: {vwap:.2f} HKD")
                            print(f"   最近3月VWAP: {recent_vwap:.2f} HKD")

                            # 与当前价格比较
                            if current_price > recent_vwap:
                                premium = (
                                    (current_price - recent_vwap) / recent_vwap
                                ) * 100
                                print(
                                    f"   当前价格 vs 近期成本: +{premium:.2f}% (高于近期成本)"
                                )
                            else:
                                discount = (
                                    (recent_vwap - current_price) / recent_vwap
                                ) * 100
                                print(
                                    f"   当前价格 vs 近期成本: -{discount:.2f}% (低于近期成本)"
                                )

                            # 与用户成本比较
                            if recent_vwap < cost_price:
                                print(
                                    f"   💡 机构近期成本（{recent_vwap:.2f}）低于您的成本（{cost_price:.2f}）"
                                )
                            else:
                                print(
                                    f"   💡 机构近期成本（{recent_vwap:.2f}）高于您的成本（{cost_price:.2f}）"
                                )

        # 南向资金说明
        print(f"\n   南向资金:")
        print(f"             ⚠️ 南向资金数据需要专门的API（如Wind、同花顺等）")
        print(f"             💡 建议：通过交易软件或金融数据平台查询")

    except Exception as e:
        print(f"   ⚠️ 获取换手率和机构数据时出错: {e}")

    # 5. 详细分析
    print(f"\n🔍 深度分析:")
    detailed = provider.get_detailed_analysis(ticker)

    if "error" not in detailed:
        price_analysis = detailed.get("price_analysis", {})
        vol_analysis = detailed.get("volatility_analysis", {})
        volume_analysis = detailed.get("volume_analysis", {})

        if price_analysis:
            pos = price_analysis.get("price_position_pct", 50)
            print(f"   价格位置: {pos:.1f}% (52周区间)")
            if pos < 30:
                print(f"             ✅ 接近52周低点 - 潜在价值机会")
            elif pos > 70:
                print(f"             ⚠️ 接近52周高点 - 需谨慎")
            else:
                print(f"             ➡️ 中位区间 - 正常估值")

        if vol_analysis:
            vol = vol_analysis.get("annual_volatility", 0)
            risk_level = vol_analysis.get("risk_level", "Unknown")
            print(f"   波动性: {risk_level} (年化波动率: {vol*100:.1f}%)")

        if volume_analysis:
            vol_ratio = volume_analysis.get("volume_ratio", 1)
            vol_signal = volume_analysis.get("volume_signal", "Unknown")
            print(f"   成交量: {vol_signal} (成交量比率: {vol_ratio:.2f}x)")

    # 6. 基于成本价的投资建议
    print(f"\n💡 基于成本价 {cost_price:.2f} HKD 的投资建议:")
    print("=" * 80)

    if price_data and price_data.get("close"):
        indicators = indicators_calc.calculate_all_indicators(price_data)
        ema20 = indicators.get("ema20", np.nan)
        ema50 = indicators.get("ema50", np.nan)
        rsi14 = indicators.get("rsi14", np.nan)

        # 综合建议
        suggestions = []

        # 1. 盈亏状态
        if pnl < -5:  # 亏损超过5%
            suggestions.append("⚠️ 当前浮亏超过5%，建议：")
            if not np.isnan(rsi14) and rsi14 < 40:
                suggestions.append("   - RSI显示相对低位，可考虑逢低加仓（分批建仓）")
            else:
                suggestions.append(
                    "   - 观察支撑位，如果跌破重要支撑（如EMA50），考虑止损"
                )
        elif pnl > 5:  # 盈利超过5%
            suggestions.append("✅ 当前盈利超过5%，建议：")
            if not np.isnan(rsi14) and rsi14 > 70:
                suggestions.append("   - RSI超买，可考虑部分获利了结")
            else:
                suggestions.append("   - 设置止盈位（如目标价95-100），锁定利润")
        else:
            suggestions.append("➡️ 当前价格接近成本价，建议：")
            suggestions.append("   - 继续持有，观察技术指标变化")

        # 2. 趋势分析
        if not np.isnan(ema20) and not np.isnan(ema50):
            if ema20 > ema50:
                suggestions.append("\n📈 技术趋势：上升趋势")
                suggestions.append("   - EMA20 > EMA50，整体趋势向好")
                if current_price > ema20:
                    suggestions.append("   - 价格在EMA20之上，维持上升动能")
                    suggestions.append("   - 建议：继续持有，止损位可设在EMA50附近")
                else:
                    suggestions.append("   - 价格跌破EMA20，需观察是否能重新站上")
            else:
                suggestions.append("\n📉 技术趋势：下降趋势")
                suggestions.append("   - EMA20 < EMA50，整体趋势偏弱")
                suggestions.append("   - 建议：谨慎持有，设置止损位")

        # 3. RSI建议
        if not np.isnan(rsi14):
            if rsi14 < 30:
                suggestions.append("\n🔽 RSI超卖（<30）")
                suggestions.append("   - 可能接近短期底部")
                suggestions.append("   - 建议：如果基本面良好，可考虑加仓")
            elif rsi14 > 70:
                suggestions.append("\n🔼 RSI超买（>70）")
                suggestions.append("   - 短期可能回调")
                suggestions.append("   - 建议：考虑部分获利了结或设置止盈")
            else:
                suggestions.append(f"\n➡️ RSI正常（{rsi14:.1f}）")
                suggestions.append("   - 市场情绪稳定")

        # 4. 风险控制建议
        suggestions.append("\n🛡️ 风险控制建议：")
        suggestions.append(f"   - 止损位建议：{cost_price * 0.85:.2f} HKD（亏损15%）")
        suggestions.append(f"   - 止盈位建议：{cost_price * 1.10:.2f} HKD（盈利10%）")
        if week52_high:
            suggestions.append(f"   - 长期目标：接近52周高点 {week52_high:.2f} HKD")

        for suggestion in suggestions:
            print(suggestion)

    # 7. 市场状态
    market_open = provider.is_market_open()
    print(f"\n🕒 市场状态: {'🟢 开盘中' if market_open else '🔴 已收盘'}")

    print("\n" + "=" * 80)
    print("⚠️ 风险提示：以上分析仅供参考，不构成投资建议。投资有风险，入市需谨慎。")
    print("=" * 80)


if __name__ == "__main__":
    analyze_1801()
