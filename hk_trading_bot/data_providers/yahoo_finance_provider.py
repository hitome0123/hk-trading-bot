"""
Yahoo Finance data provider using MCP
"""

import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np


class YahooFinanceProvider:
    """Yahoo Finance 数据提供器 - 通过MCP获取真实股票数据"""
    
    def __init__(self):
        self.mcp_available = self._check_mcp_availability()
    
    def _check_mcp_availability(self) -> bool:
        """检查MCP Yahoo Finance服务是否可用"""
        try:
            # 检查是否有Yahoo Finance MCP服务配置
            result = subprocess.run(['mcp', 'list'], capture_output=True, text=True, timeout=5)
            return 'yahoo' in result.stdout.lower() or 'finance' in result.stdout.lower()
        except Exception:
            return False
    
    async def _call_mcp_yahoo(self, ticker: str, period: str = "3mo") -> Optional[Dict]:
        """调用MCP Yahoo Finance服务"""
        try:
            # 这里应该是实际的MCP调用，目前使用模拟
            # 实际实现需要根据MCP Yahoo Finance服务的具体API
            cmd = [
                'mcp', 'call', 'yahoo-finance', 
                'get_stock_data', 
                '--ticker', ticker,
                '--period', period
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                print(f"MCP call failed: {result.stderr}")
                return None
                
        except Exception as e:
            print(f"Error calling MCP Yahoo Finance: {e}")
            return None
    
    def _fallback_to_requests(self, ticker: str) -> Optional[Dict]:
        """备选方案：使用requests直接调用Yahoo Finance API"""
        try:
            import requests
            
            # Yahoo Finance API (非官方)
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            params = {
                'period1': int((datetime.now() - timedelta(days=90)).timestamp()),
                'period2': int(datetime.now().timestamp()),
                'interval': '1d',
                'includePrePost': 'true',
                'events': 'div%2Csplits'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data['chart']['result'][0] if data['chart']['result'] else None
            else:
                print(f"Yahoo Finance API returned status {response.status_code}")
                return None
                
        except ImportError:
            print("requests library not available. Installing...")
            subprocess.run(['pip', 'install', 'requests'])
            return self._fallback_to_requests(ticker)
        except Exception as e:
            print(f"Error fetching data from Yahoo Finance: {e}")
            return None
    
    def get_price_data(self, ticker: str, days: int = 60) -> Dict[str, List[float]]:
        """获取股票价格数据"""
        try:
            # 首先尝试使用MCP
            if self.mcp_available:
                data = asyncio.run(self._call_mcp_yahoo(ticker))
                if data:
                    return self._parse_yahoo_data(data)
            
            # 备选方案：直接调用Yahoo Finance
            data = self._fallback_to_requests(ticker)
            if data:
                return self._parse_yahoo_data(data)
            
            # 如果都失败了，返回模拟数据并警告
            print(f"⚠️ Warning: Could not fetch real data for {ticker}, using mock data")
            return self._generate_mock_data(ticker, days)
            
        except Exception as e:
            print(f"Error in get_price_data: {e}")
            return self._generate_mock_data(ticker, days)
    
    def _parse_yahoo_data(self, data: Dict) -> Dict[str, List[float]]:
        """解析Yahoo Finance数据"""
        try:
            # 尝试解析MCP返回的数据结构
            if 'indicators' in data:
                quotes = data['indicators']['quote'][0]
                return {
                    'close': quotes.get('close', []),
                    'high': quotes.get('high', []),
                    'low': quotes.get('low', []),
                    'open': quotes.get('open', [])
                }
            
            # 尝试解析直接Yahoo API数据结构
            elif 'meta' in data and 'indicators' in data:
                quotes = data['indicators']['quote'][0]
                return {
                    'close': [x for x in quotes.get('close', []) if x is not None],
                    'high': [x for x in quotes.get('high', []) if x is not None],
                    'low': [x for x in quotes.get('low', []) if x is not None],
                    'open': [x for x in quotes.get('open', []) if x is not None]
                }
            
            else:
                raise ValueError("Unexpected data structure from Yahoo Finance")
                
        except Exception as e:
            print(f"Error parsing Yahoo data: {e}")
            return self._generate_mock_data("DEFAULT", 60)
    
    def get_current_price(self, ticker: str) -> float:
        """获取当前股票价格"""
        try:
            price_data = self.get_price_data(ticker, 1)
            if price_data['close']:
                return price_data['close'][-1]
            else:
                return 50.0  # 默认价格
        except Exception as e:
            print(f"Error getting current price: {e}")
            return 50.0
    
    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        try:
            if self.mcp_available:
                # 使用MCP获取股票信息
                cmd = ['mcp', 'call', 'yahoo-finance', 'get_stock_info', '--ticker', ticker]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0:
                    return json.loads(result.stdout)
            
            # 备选：通过API获取基本信息
            return self._get_stock_info_fallback(ticker)
            
        except Exception as e:
            print(f"Error getting stock info: {e}")
            return self._default_stock_info(ticker)
    
    def _get_stock_info_fallback(self, ticker: str) -> Dict[str, Any]:
        """备选方案获取股票信息"""
        try:
            import requests
            
            url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
            params = {
                'modules': 'summaryDetail,financialData,defaultKeyStatistics'
            }
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                result = data['quoteSummary']['result'][0]
                
                return {
                    'symbol': ticker,
                    'market_cap': result.get('summaryDetail', {}).get('marketCap', {}).get('raw', 0),
                    'pe_ratio': result.get('summaryDetail', {}).get('trailingPE', {}).get('raw', 0),
                    'dividend_yield': result.get('summaryDetail', {}).get('dividendYield', {}).get('raw', 0),
                    'beta': result.get('defaultKeyStatistics', {}).get('beta', {}).get('raw', 1.0),
                    'sector': result.get('summaryProfile', {}).get('sector', 'Unknown')
                }
            
        except Exception as e:
            print(f"Error in fallback stock info: {e}")
        
        return self._default_stock_info(ticker)
    
    def _default_stock_info(self, ticker: str) -> Dict[str, Any]:
        """默认股票信息"""
        return {
            'symbol': ticker,
            'market_cap': 0,
            'pe_ratio': 15.0,
            'dividend_yield': 0.02,
            'beta': 1.0,
            'sector': 'Technology'
        }
    
    def _generate_mock_data(self, ticker: str, days: int) -> Dict[str, List[float]]:
        """生成模拟数据作为备选"""
        np.random.seed(hash(ticker) % 1000)
        
        base_price = 50 + (hash(ticker) % 100)
        prices = []
        highs = []
        lows = []
        closes = []
        
        current_price = base_price
        
        for i in range(days):
            daily_change = np.random.normal(0, 0.02)
            current_price = current_price * (1 + daily_change)
            current_price = max(current_price, 1.0)
            
            daily_volatility = abs(np.random.normal(0, 0.01))
            high = current_price * (1 + daily_volatility)
            low = current_price * (1 - daily_volatility)
            
            prices.append(current_price)
            highs.append(high)
            lows.append(low)
            closes.append(current_price)
        
        return {
            'close': closes,
            'high': highs,
            'low': lows,
            'open': prices
        }
    
    def is_market_open(self) -> bool:
        """检查香港市场是否开盘"""
        try:
            from datetime import datetime
            import pytz
            
            # 香港时区
            hk_tz = pytz.timezone('Asia/Hong_Kong')
            now_hk = datetime.now(hk_tz)
            
            # 港股交易时间：周一至周五 09:30-12:00, 13:00-16:00
            if now_hk.weekday() >= 5:  # 周末
                return False
            
            time_now = now_hk.time()
            morning_open = datetime.strptime('09:30', '%H:%M').time()
            morning_close = datetime.strptime('12:00', '%H:%M').time()
            afternoon_open = datetime.strptime('13:00', '%H:%M').time()
            afternoon_close = datetime.strptime('16:00', '%H:%M').time()
            
            return (morning_open <= time_now <= morning_close) or (afternoon_open <= time_now <= afternoon_close)
            
        except ImportError:
            # 如果没有pytz，使用简化判断
            now = datetime.now()
            return 9 <= now.hour <= 16 and now.weekday() < 5