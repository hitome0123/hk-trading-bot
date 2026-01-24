#!/usr/bin/env python3
"""
Real-time analysis for 2807.HK using actual data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.yfinance_provider import YFinanceProvider
from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from datetime import datetime
import numpy as np

def analyze_2807():
    """分析2807.HK的真实数据"""
    ticker = "2807.HK"
    provider = YFinanceProvider()
    indicators_calc = TechnicalIndicators()
    entry_strategy = EntryStrategy()
    
    print(f"🔍 Real-time Analysis for {ticker}")
    print(f"⏰ Analysis Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # 1. 获取基本信息
    print(f"📊 Fetching stock information...")
    stock_info = provider.get_stock_info(ticker)
    
    print(f"📈 Stock Information:")
    print(f"   Full Name: {stock_info.get('longName', 'N/A')}")
    print(f"   Short Name: {stock_info.get('shortName', 'N/A')}")
    print(f"   Exchange: {stock_info.get('exchange', 'N/A')}")
    print(f"   Currency: {stock_info.get('currency', 'HKD')}")
    print(f"   Sector: {stock_info.get('sector', 'N/A')}")
    print(f"   Industry: {stock_info.get('industry', 'N/A')}")
    
    # 2. 获取价格数据
    print(f"\n💰 Price Information:")
    current_price = provider.get_current_price(ticker)
    print(f"   Current Price: {current_price:.3f} HKD")
    print(f"   Previous Close: {stock_info.get('previous_close', 'N/A')}")
    print(f"   Day High: {stock_info.get('day_high', 'N/A')}")
    print(f"   Day Low: {stock_info.get('day_low', 'N/A')}")
    print(f"   52W High: {stock_info.get('fifty_two_week_high', 'N/A')}")
    print(f"   52W Low: {stock_info.get('fifty_two_week_low', 'N/A')}")
    
    # 3. 获取历史数据并计算技术指标
    print(f"\n📊 Fetching historical data...")
    price_data = provider.get_price_data(ticker, 60)
    
    if price_data and price_data.get('close'):
        print(f"   Retrieved {len(price_data['close'])} days of historical data")
        
        # 计算技术指标
        indicators = indicators_calc.calculate_all_indicators(price_data)
        
        print(f"\n📈 Technical Indicators:")
        for name, value in indicators.items():
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
            else:
                print(f"   {name.upper()}: N/A")
        
        # 入场分析
        entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)
        
        print(f"\n🎯 Entry Analysis:")
        print(f"   Signal: {entry_analysis['signal']}")
        print(f"   Reason: {entry_analysis['reason']}")
        if entry_analysis['entry_price']:
            discount = ((current_price - entry_analysis['entry_price']) / current_price) * 100
            print(f"   Entry Price: {entry_analysis['entry_price']:.2f} HKD")
            print(f"   Current vs Entry: {discount:+.1f}%")
            if current_price <= entry_analysis['entry_price']:
                print(f"   💡 Entry Signal: TRIGGERED! Current price is at/below entry price")
            else:
                print(f"   ⏳ Entry Signal: WAITING for price to drop to entry level")
        
    # 4. 详细分析
    print(f"\n🔍 Detailed Analysis:")
    detailed = provider.get_detailed_analysis(ticker)
    
    if 'error' not in detailed:
        price_analysis = detailed.get('price_analysis', {})
        vol_analysis = detailed.get('volatility_analysis', {})
        volume_analysis = detailed.get('volume_analysis', {})
        
        print(f"   Price Position: {price_analysis.get('price_position_pct', 0):.1f}% between 52W low/high")
        print(f"   Distance from 52W High: -{price_analysis.get('distance_from_high_pct', 0):.1f}%")
        print(f"   Distance from 52W Low: +{price_analysis.get('distance_from_low_pct', 0):.1f}%")
        print(f"   Volatility Risk: {vol_analysis.get('risk_level', 'Unknown')} ({vol_analysis.get('annual_volatility', 0)*100:.1f}% annual)")
        print(f"   Volume Signal: {volume_analysis.get('volume_signal', 'Unknown')} (ratio: {volume_analysis.get('volume_ratio', 1):.1f}x)")
    
    # 5. 市场状态
    market_open = provider.is_market_open()
    print(f"\n🕒 Market Status: {'OPEN' if market_open else 'CLOSED'}")
    
    # 6. 投资建议总结
    print(f"\n💡 Investment Summary:")
    
    # 基于技术分析的建议
    if price_data and price_data.get('close'):
        signal = entry_analysis.get('signal', 'WAIT')
        if signal == 'LONG':
            print(f"   📈 Technical Signal: BUY opportunity detected")
        elif signal == 'WAIT':
            print(f"   ⏸️ Technical Signal: Hold/Wait for better entry")
        
        # 基于价格位置的建议
        if 'price_analysis' in detailed:
            pos = price_analysis.get('price_position_pct', 50)
            if pos < 30:
                print(f"   🔽 Price Position: Near 52W low - potential value opportunity")
            elif pos > 70:
                print(f"   🔼 Price Position: Near 52W high - exercise caution")
            else:
                print(f"   ➡️ Price Position: Mid-range - normal valuation zone")
    
    # 与富途数据对比
    futu_price = 63.44
    if abs(current_price - futu_price) < 0.5:
        print(f"   ✅ Data Consistency: Price matches Futu data ({futu_price:.3f} HKD)")
    else:
        print(f"   ⚠️ Data Variance: Price differs from Futu data (Futu: {futu_price:.3f}, Our: {current_price:.3f})")

if __name__ == "__main__":
    analyze_2807()