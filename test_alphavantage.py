#!/usr/bin/env python3
"""
Test Alpha Vantage API integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.alphavantage_provider import AlphaVantageProvider
from datetime import datetime

def test_alphavantage_comprehensive():
    """全面测试Alpha Vantage API功能"""
    
    print("🔍 Alpha Vantage API 综合测试")
    print("=" * 60)
    
    # 初始化提供器
    provider = AlphaVantageProvider()
    
    # 1. 测试连接
    print("📡 Testing API Connection...")
    connection_ok = provider.test_connection()
    
    if not connection_ok:
        print("❌ API连接失败，请检查API密钥")
        return
    
    # 2. 测试美股数据
    print(f"\n📊 Testing US Stock Data (AAPL)...")
    test_us_stock(provider, "AAPL")
    
    # 3. 测试港股数据
    print(f"\n🇭🇰 Testing HK Stock Data (0700.HK)...")
    test_hk_stock(provider, "0700.HK")
    
    # 4. 测试智谱AI数据
    print(f"\n🧠 Testing ZhipuAI Data (2513.HK)...")
    test_hk_stock(provider, "2513.HK")
    
    # 5. 测试技术指标
    print(f"\n📈 Testing Technical Indicators...")
    test_technical_indicators(provider, "AAPL")

def test_us_stock(provider: AlphaVantageProvider, symbol: str):
    """测试美股数据"""
    try:
        # 实时报价
        quote = provider.get_quote(symbol)
        if quote:
            print(f"✅ Real-time Quote for {symbol}:")
            print(f"   Price: ${quote['price']:.2f}")
            print(f"   Change: {quote['change']:+.2f} ({quote['change_percent']})")
            print(f"   Volume: {quote['volume']:,}")
            print(f"   Day Range: ${quote['low']:.2f} - ${quote['high']:.2f}")
        else:
            print(f"❌ Failed to get quote for {symbol}")
        
        # 历史数据
        daily_data = provider.get_daily_data(symbol, 'compact')
        if daily_data:
            print(f"✅ Historical Data: {len(daily_data['close'])} days")
            print(f"   Latest Close: ${daily_data['close'][-1]:.2f}")
            print(f"   Date Range: {daily_data['dates'][0]} to {daily_data['dates'][-1]}")
        
        # 公司信息
        overview = provider.get_company_overview(symbol)
        if overview:
            print(f"✅ Company Overview:")
            print(f"   Name: {overview['name']}")
            print(f"   Sector: {overview['sector']}")
            print(f"   Market Cap: ${overview['market_cap']:,.0f}")
            print(f"   P/E Ratio: {overview['pe_ratio']}")
        
    except Exception as e:
        print(f"❌ Error testing {symbol}: {e}")

def test_hk_stock(provider: AlphaVantageProvider, symbol: str):
    """测试港股数据"""
    try:
        # 注意：Alpha Vantage对港股的支持可能有限
        quote = provider.get_quote(symbol)
        if quote:
            print(f"✅ HK Stock Quote for {symbol}:")
            print(f"   Price: {quote['price']:.2f} HKD")
            print(f"   Change: {quote['change']:+.2f}")
            print(f"   Volume: {quote['volume']:,}")
        else:
            print(f"⚠️ No quote data for {symbol} (may not be supported)")
        
        # 历史数据
        daily_data = provider.get_daily_data(symbol)
        if daily_data and daily_data['close']:
            print(f"✅ Historical Data: {len(daily_data['close'])} days")
            print(f"   Latest Close: {daily_data['close'][-1]:.2f}")
        else:
            print(f"⚠️ No historical data for {symbol}")
        
    except Exception as e:
        print(f"❌ Error testing HK stock {symbol}: {e}")

def test_technical_indicators(provider: AlphaVantageProvider, symbol: str):
    """测试技术指标"""
    try:
        indicators = ['RSI', 'EMA', 'SMA', 'MACD']
        
        for indicator in indicators:
            try:
                if indicator == 'EMA':
                    data = provider.get_technical_indicators(symbol, indicator, time_period=20)
                elif indicator == 'SMA':
                    data = provider.get_technical_indicators(symbol, indicator, time_period=50)
                else:
                    data = provider.get_technical_indicators(symbol, indicator)
                
                if data:
                    print(f"✅ {indicator} indicator data retrieved")
                else:
                    print(f"⚠️ No {indicator} data available")
                    
            except Exception as e:
                print(f"❌ Error getting {indicator}: {e}")
        
    except Exception as e:
        print(f"❌ Error testing technical indicators: {e}")

def test_integration_with_existing_system():
    """测试与现有系统的集成"""
    print(f"\n🔧 Testing Integration with Trading Bot...")
    
    provider = AlphaVantageProvider()
    
    # 测试兼容性接口
    symbol = "AAPL"
    
    try:
        # 测试 get_current_price 接口
        current_price = provider.get_current_price(symbol)
        print(f"✅ Current Price Interface: ${current_price:.2f}")
        
        # 测试 get_price_data 接口
        price_data = provider.get_price_data(symbol, 30)
        if price_data and price_data['close']:
            print(f"✅ Price Data Interface: {len(price_data['close'])} days")
            
            # 计算简单技术指标
            closes = price_data['close']
            if len(closes) >= 20:
                sma_20 = sum(closes[-20:]) / 20
                print(f"   SMA20: ${sma_20:.2f}")
        
        # 测试 get_stock_info 接口
        stock_info = provider.get_stock_info(symbol)
        if stock_info:
            print(f"✅ Stock Info Interface: {stock_info.get('name', 'N/A')}")
    
    except Exception as e:
        print(f"❌ Integration test error: {e}")

if __name__ == "__main__":
    test_alphavantage_comprehensive()
    test_integration_with_existing_system()
    
    print(f"\n🎉 Alpha Vantage API测试完成!")
    print(f"ℹ️ 注意: Alpha Vantage对港股支持有限，主要优势在美股数据")