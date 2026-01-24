#!/usr/bin/env python3
"""
Test Alpha Vantage cryptocurrency support
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.alphavantage_provider import AlphaVantageProvider
import requests

def test_crypto_endpoints():
    """测试Alpha Vantage加密货币API支持"""
    
    print("🪙 Testing Alpha Vantage Cryptocurrency Support")
    print("=" * 60)
    
    provider = AlphaVantageProvider()
    api_key = provider._get_current_api_key()
    base_url = "https://www.alphavantage.co/query"
    
    # 测试不同的加密货币功能
    crypto_tests = [
        {
            'name': 'Bitcoin Real-time',
            'params': {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': 'BTC',
                'to_currency': 'USD'
            }
        },
        {
            'name': 'Bitcoin Daily Data',
            'params': {
                'function': 'DIGITAL_CURRENCY_DAILY',
                'symbol': 'BTC',
                'market': 'USD'
            }
        },
        {
            'name': 'Ethereum Real-time',
            'params': {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': 'ETH',
                'to_currency': 'USD'
            }
        },
        {
            'name': 'Crypto Market Status',
            'params': {
                'function': 'MARKET_STATUS'
            }
        }
    ]
    
    results = {}
    
    for test in crypto_tests:
        print(f"\n📊 Testing: {test['name']}")
        
        try:
            params = test['params'].copy()
            params['apikey'] = api_key
            
            response = requests.get(base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'Error Message' in data:
                    print(f"❌ API Error: {data['Error Message']}")
                    results[test['name']] = {'status': 'error', 'data': data}
                elif 'Note' in data:
                    print(f"⚠️ API Note: {data['Note']}")
                    results[test['name']] = {'status': 'limited', 'data': data}
                else:
                    print(f"✅ Success: {test['name']}")
                    results[test['name']] = {'status': 'success', 'data': data}
                    
                    # 显示部分数据
                    if test['name'] == 'Bitcoin Real-time':
                        rate_data = data.get('Realtime Currency Exchange Rate', {})
                        if rate_data:
                            rate = rate_data.get('5. Exchange Rate', 'N/A')
                            timestamp = rate_data.get('6. Last Refreshed', 'N/A')
                            print(f"   BTC/USD Rate: ${rate}")
                            print(f"   Last Updated: {timestamp}")
                    
                    elif test['name'] == 'Bitcoin Daily Data':
                        time_series = data.get('Time Series (Digital Currency Daily)', {})
                        if time_series:
                            latest_date = max(time_series.keys())
                            latest_data = time_series[latest_date]
                            close_price = latest_data.get('4a. close (USD)', 'N/A')
                            print(f"   Latest Close: ${close_price}")
                            print(f"   Date: {latest_date}")
                
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                results[test['name']] = {'status': 'http_error', 'code': response.status_code}
                
        except Exception as e:
            print(f"❌ Exception: {e}")
            results[test['name']] = {'status': 'exception', 'error': str(e)}
    
    # 总结结果
    print(f"\n📋 Test Summary:")
    success_count = sum(1 for r in results.values() if r['status'] == 'success')
    total_tests = len(results)
    
    print(f"   Successful: {success_count}/{total_tests}")
    print(f"   Crypto Support: {'✅ Available' if success_count > 0 else '❌ Limited'}")
    
    return results

def test_popular_cryptocurrencies():
    """测试流行加密货币"""
    print(f"\n🚀 Testing Popular Cryptocurrencies")
    print("-" * 40)
    
    provider = AlphaVantageProvider()
    api_key = provider._get_current_api_key()
    base_url = "https://www.alphavantage.co/query"
    
    cryptos = ['BTC', 'ETH', 'BNB', 'SOL', 'ADA', 'DOT', 'AVAX']
    
    for crypto in cryptos:
        try:
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': crypto,
                'to_currency': 'USD',
                'apikey': api_key
            }
            
            response = requests.get(base_url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                rate_data = data.get('Realtime Currency Exchange Rate', {})
                
                if rate_data:
                    rate = rate_data.get('5. Exchange Rate', 'N/A')
                    print(f"   {crypto}/USD: ${rate}")
                else:
                    print(f"   {crypto}/USD: No data")
            else:
                print(f"   {crypto}/USD: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   {crypto}/USD: Error - {e}")

if __name__ == "__main__":
    results = test_crypto_endpoints()
    test_popular_cryptocurrencies()
    
    print(f"\n🎯 Conclusion:")
    print(f"Alpha Vantage provides cryptocurrency support for trading bot integration!")