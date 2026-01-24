#!/usr/bin/env python3
"""
Test script to get real-time data for 2807.HK from multiple sources
"""

import yfinance as yf
import requests
from datetime import datetime

def test_yfinance_data(ticker):
    """Test yfinance data retrieval"""
    print(f"🔍 Testing yfinance for {ticker}")
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="5d")
        
        print(f"✅ yfinance SUCCESS:")
        print(f"   Current Price: {info.get('currentPrice', 'N/A')}")
        print(f"   Previous Close: {info.get('previousClose', 'N/A')}")
        print(f"   Day High: {info.get('dayHigh', 'N/A')}")
        print(f"   Day Low: {info.get('dayLow', 'N/A')}")
        print(f"   52W High: {info.get('fiftyTwoWeekHigh', 'N/A')}")
        print(f"   52W Low: {info.get('fiftyTwoWeekLow', 'N/A')}")
        print(f"   Volume: {info.get('volume', 'N/A')}")
        print(f"   Market Cap: {info.get('marketCap', 'N/A')}")
        print(f"   Currency: {info.get('currency', 'N/A')}")
        
        if not hist.empty:
            latest = hist.iloc[-1]
            print(f"   Latest Close: {latest['Close']:.3f}")
            print(f"   Latest Volume: {int(latest['Volume'])}")
            
        return True, info.get('currentPrice', hist.iloc[-1]['Close'] if not hist.empty else None)
        
    except Exception as e:
        print(f"❌ yfinance FAILED: {e}")
        return False, None

def test_yahoo_api_direct(ticker):
    """Test direct Yahoo Finance API"""
    print(f"\n🌐 Testing Yahoo Finance API for {ticker}")
    try:
        # Yahoo Finance quote API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        params = {
            'interval': '1d',
            'range': '1d'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data['chart']['result'][0]
            
            meta = result['meta']
            current_price = meta.get('regularMarketPrice', meta.get('previousClose'))
            
            print(f"✅ Yahoo API SUCCESS:")
            print(f"   Current Price: {current_price}")
            print(f"   Previous Close: {meta.get('previousClose')}")
            print(f"   Day High: {meta.get('regularMarketDayHigh')}")
            print(f"   Day Low: {meta.get('regularMarketDayLow')}")
            print(f"   Currency: {meta.get('currency')}")
            print(f"   Exchange: {meta.get('exchangeName')}")
            print(f"   Market State: {meta.get('marketState')}")
            
            return True, current_price
        else:
            print(f"❌ Yahoo API FAILED: Status {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ Yahoo API FAILED: {e}")
        return False, None

def test_futu_comparison():
    """Show comparison with Futu data"""
    print(f"\n📱 Futu Data Comparison:")
    print(f"   You mentioned: 63.440 HKD")
    print(f"   Source: Futu App")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def main():
    ticker = "2807.HK"
    print(f"🚀 Real-time Data Test for {ticker}")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Test different data sources
    yf_success, yf_price = test_yfinance_data(ticker)
    api_success, api_price = test_yahoo_api_direct(ticker)
    
    # Show Futu comparison
    test_futu_comparison()
    
    print(f"\n📊 SUMMARY:")
    print(f"   yfinance: {'✅' if yf_success else '❌'} Price: {yf_price}")
    print(f"   Yahoo API: {'✅' if api_success else '❌'} Price: {api_price}")
    print(f"   Futu App: ✅ Price: 63.440 (user provided)")
    
    # Check for discrepancies
    futu_price = 63.440
    if yf_success and yf_price:
        diff_yf = abs(yf_price - futu_price)
        print(f"\n🔍 Price Differences:")
        print(f"   yfinance vs Futu: {diff_yf:.3f} HKD ({diff_yf/futu_price*100:.1f}%)")
    
    if api_success and api_price:
        diff_api = abs(api_price - futu_price)
        print(f"   Yahoo API vs Futu: {diff_api:.3f} HKD ({diff_api/futu_price*100:.1f}%)")

if __name__ == "__main__":
    main()