"""
Alpha Vantage MCP provider for real-time financial data
"""

import requests
import json
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio


class AlphaVantageProvider:
    """Alpha Vantage 数据提供器 - 通过MCP获取真实金融数据"""
    
    def __init__(self, api_keys: List[str] = None):
        """
        初始化Alpha Vantage提供器
        
        Args:
            api_keys: Alpha Vantage API密钥列表
        """
        self.api_keys = api_keys or [
            "WU67XB37TICVU5MM",
            "336PN0924QQGVE2H"
        ]
        self.current_key_index = 0
        self.base_url = "https://www.alphavantage.co/query"
        self.mcp_urls = [
            f"https://mcp.alphavantage.co/mcp?apikey={key}" 
            for key in self.api_keys
        ]
        
    def _get_current_api_key(self) -> str:
        """获取当前使用的API密钥"""
        return self.api_keys[self.current_key_index]
    
    def _rotate_api_key(self) -> None:
        """轮换API密钥以避免限流"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        print(f"🔄 Switched to API key #{self.current_key_index + 1}")
    
    def _make_api_request(self, function: str, symbol: str, **kwargs) -> Optional[Dict]:
        """发起Alpha Vantage API请求"""
        params = {
            'function': function,
            'symbol': symbol,
            'apikey': self._get_current_api_key()
        }
        params.update(kwargs)
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查是否有错误信息
                if 'Error Message' in data:
                    print(f"❌ API Error: {data['Error Message']}")
                    return None
                
                if 'Note' in data:
                    print(f"⚠️ API Note: {data['Note']}")
                    if "premium" in data['Note'].lower() or "limit" in data['Note'].lower():
                        # API限流，尝试轮换密钥
                        self._rotate_api_key()
                        return self._make_api_request(function, symbol, **kwargs)
                
                return data
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Request Error: {e}")
            return None
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时报价"""
        try:
            data = self._make_api_request('GLOBAL_QUOTE', symbol)
            
            if data and 'Global Quote' in data:
                quote = data['Global Quote']
                
                return {
                    'symbol': quote.get('01. symbol', symbol),
                    'price': float(quote.get('05. price', 0)),
                    'change': float(quote.get('09. change', 0)),
                    'change_percent': quote.get('10. change percent', '0%'),
                    'volume': int(quote.get('06. volume', 0)),
                    'previous_close': float(quote.get('08. previous close', 0)),
                    'open': float(quote.get('02. open', 0)),
                    'high': float(quote.get('03. high', 0)),
                    'low': float(quote.get('04. low', 0)),
                    'latest_trading_day': quote.get('07. latest trading day', ''),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print(f"⚠️ No quote data found for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting quote for {symbol}: {e}")
            return None
    
    def get_daily_data(self, symbol: str, outputsize: str = 'compact') -> Optional[Dict[str, List[float]]]:
        """获取日线数据"""
        try:
            data = self._make_api_request('TIME_SERIES_DAILY_ADJUSTED', symbol, outputsize=outputsize)
            
            if data and 'Time Series (Daily)' in data:
                time_series = data['Time Series (Daily)']
                
                # 按日期排序
                sorted_dates = sorted(time_series.keys())
                
                price_data = {
                    'close': [],
                    'high': [],
                    'low': [],
                    'open': [],
                    'volume': [],
                    'dates': []
                }
                
                for date in sorted_dates:
                    day_data = time_series[date]
                    price_data['open'].append(float(day_data['1. open']))
                    price_data['high'].append(float(day_data['2. high']))
                    price_data['low'].append(float(day_data['3. low']))
                    price_data['close'].append(float(day_data['5. adjusted close']))
                    price_data['volume'].append(int(day_data['6. volume']))
                    price_data['dates'].append(date)
                
                print(f"✅ Retrieved {len(price_data['close'])} days of data for {symbol}")
                return price_data
            
            else:
                print(f"⚠️ No daily data found for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting daily data for {symbol}: {e}")
            return None
    
    def get_intraday_data(self, symbol: str, interval: str = '5min') -> Optional[Dict[str, List[float]]]:
        """获取分钟级数据"""
        try:
            data = self._make_api_request('TIME_SERIES_INTRADAY', symbol, interval=interval, outputsize='compact')
            
            if data and f'Time Series ({interval})' in data:
                time_series = data[f'Time Series ({interval})']
                
                # 按时间排序
                sorted_times = sorted(time_series.keys())
                
                price_data = {
                    'close': [],
                    'high': [],
                    'low': [],
                    'open': [],
                    'volume': [],
                    'timestamps': []
                }
                
                for timestamp in sorted_times:
                    tick_data = time_series[timestamp]
                    price_data['open'].append(float(tick_data['1. open']))
                    price_data['high'].append(float(tick_data['2. high']))
                    price_data['low'].append(float(tick_data['3. low']))
                    price_data['close'].append(float(tick_data['4. close']))
                    price_data['volume'].append(int(tick_data['5. volume']))
                    price_data['timestamps'].append(timestamp)
                
                print(f"✅ Retrieved {len(price_data['close'])} {interval} bars for {symbol}")
                return price_data
            
            else:
                print(f"⚠️ No intraday data found for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting intraday data for {symbol}: {e}")
            return None
    
    def get_technical_indicators(self, symbol: str, indicator: str, **kwargs) -> Optional[Dict]:
        """获取技术指标数据"""
        try:
            # 常用技术指标映射
            indicator_functions = {
                'SMA': 'SMA',
                'EMA': 'EMA', 
                'RSI': 'RSI',
                'MACD': 'MACD',
                'BBANDS': 'BBANDS',
                'ATR': 'ATR'
            }
            
            if indicator.upper() not in indicator_functions:
                print(f"⚠️ Unsupported indicator: {indicator}")
                return None
            
            func = indicator_functions[indicator.upper()]
            
            # 设置默认参数
            default_params = {
                'interval': 'daily',
                'time_period': 14,
                'series_type': 'close'
            }
            default_params.update(kwargs)
            
            data = self._make_api_request(func, symbol, **default_params)
            
            if data:
                # 寻找技术指标数据
                for key in data.keys():
                    if 'Technical Analysis' in key:
                        return data[key]
            
            return data
            
        except Exception as e:
            print(f"❌ Error getting {indicator} for {symbol}: {e}")
            return None
    
    def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取公司基本面信息"""
        try:
            data = self._make_api_request('OVERVIEW', symbol)
            
            if data and 'Symbol' in data:
                return {
                    'symbol': data.get('Symbol', symbol),
                    'name': data.get('Name', ''),
                    'exchange': data.get('Exchange', ''),
                    'currency': data.get('Currency', ''),
                    'country': data.get('Country', ''),
                    'sector': data.get('Sector', ''),
                    'industry': data.get('Industry', ''),
                    'market_cap': self._safe_float(data.get('MarketCapitalization', 0)),
                    'pe_ratio': self._safe_float(data.get('PERatio', 0)),
                    'dividend_yield': self._safe_float(data.get('DividendYield', 0)),
                    'eps': self._safe_float(data.get('EPS', 0)),
                    'beta': self._safe_float(data.get('Beta', 1.0)),
                    '52_week_high': self._safe_float(data.get('52WeekHigh', 0)),
                    '52_week_low': self._safe_float(data.get('52WeekLow', 0)),
                    'description': data.get('Description', ''),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print(f"⚠️ No company overview found for {symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting company overview for {symbol}: {e}")
            return None
    
    def _safe_float(self, value: str) -> float:
        """安全转换字符串为浮点数"""
        try:
            if value == 'None' or value == '-':
                return 0.0
            return float(str(value).replace(',', ''))
        except (ValueError, TypeError):
            return 0.0
    
    def get_current_price(self, symbol: str) -> float:
        """获取当前价格"""
        quote = self.get_quote(symbol)
        if quote:
            return quote.get('price', 0.0)
        return 0.0
    
    def get_price_data(self, symbol: str, days: int = 60) -> Dict[str, List[float]]:
        """获取历史价格数据（兼容原接口）"""
        outputsize = 'full' if days > 100 else 'compact'
        daily_data = self.get_daily_data(symbol, outputsize)
        
        if daily_data and days < len(daily_data['close']):
            # 截取最近N天的数据
            return {
                'close': daily_data['close'][-days:],
                'high': daily_data['high'][-days:],
                'low': daily_data['low'][-days:],
                'open': daily_data['open'][-days:]
            }
        
        return daily_data or {'close': [], 'high': [], 'low': [], 'open': []}
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票信息（兼容原接口）"""
        overview = self.get_company_overview(symbol)
        quote = self.get_quote(symbol)
        
        if overview and quote:
            overview.update({
                'current_price': quote['price'],
                'previous_close': quote['previous_close'],
                'day_high': quote['high'],
                'day_low': quote['low'],
                'volume': quote['volume']
            })
        
        return overview or {'symbol': symbol}
    
    def test_connection(self) -> bool:
        """测试API连接"""
        print(f"🔍 Testing Alpha Vantage connection...")
        
        # 测试一个简单的请求
        test_symbol = "AAPL"
        quote = self.get_quote(test_symbol)
        
        if quote:
            print(f"✅ Alpha Vantage connection successful!")
            print(f"   Test symbol: {quote['symbol']}")
            print(f"   Current price: ${quote['price']:.2f}")
            print(f"   Available API keys: {len(self.api_keys)}")
            return True
        else:
            print(f"❌ Alpha Vantage connection failed!")
            return False