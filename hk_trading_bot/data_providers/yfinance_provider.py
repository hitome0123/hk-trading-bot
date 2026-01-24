"""
Improved Yahoo Finance data provider using yfinance library
"""

import yfinance as yf
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd


class YFinanceProvider:
    """改进的Yahoo Finance数据提供器 - 使用yfinance库"""
    
    def __init__(self):
        self.session = None
        
    def get_price_data(self, ticker: str, days: int = 60) -> Dict[str, List[float]]:
        """获取股票价格数据"""
        try:
            stock = yf.Ticker(ticker)
            
            # 获取历史数据
            period = f"{days}d" if days <= 60 else f"{days//30}mo"
            hist = stock.history(period=period)
            
            if hist.empty:
                print(f"⚠️ No historical data found for {ticker}")
                return self._generate_mock_data(ticker, days)
            
            # 转换为我们需要的格式
            price_data = {
                'close': hist['Close'].fillna(method='ffill').tolist(),
                'high': hist['High'].fillna(method='ffill').tolist(), 
                'low': hist['Low'].fillna(method='ffill').tolist(),
                'open': hist['Open'].fillna(method='ffill').tolist()
            }
            
            print(f"✅ Retrieved {len(price_data['close'])} days of data for {ticker}")
            return price_data
            
        except Exception as e:
            print(f"❌ Error fetching data for {ticker}: {e}")
            return self._generate_mock_data(ticker, days)
    
    def get_current_price(self, ticker: str) -> float:
        """获取当前股票价格"""
        try:
            stock = yf.Ticker(ticker)
            
            # 尝试获取实时价格
            info = stock.info
            current_price = info.get('currentPrice')
            
            if current_price and current_price > 0:
                return float(current_price)
            
            # 备选：使用最近的历史价格
            hist = stock.history(period="1d")
            if not hist.empty:
                return float(hist['Close'].iloc[-1])
            
            # 备选：使用前一天收盘价
            previous_close = info.get('previousClose')
            if previous_close and previous_close > 0:
                return float(previous_close)
            
            print(f"⚠️ Could not get current price for {ticker}")
            return 50.0
            
        except Exception as e:
            print(f"❌ Error getting current price for {ticker}: {e}")
            return 50.0
    
    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """获取股票基本信息"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            return {
                'symbol': ticker,
                'shortName': info.get('shortName', ticker),
                'longName': info.get('longName', ''),
                'currency': info.get('currency', 'HKD'),
                'exchange': info.get('exchange', ''),
                'market_cap': info.get('marketCap', 0),
                'enterprise_value': info.get('enterpriseValue', 0),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'dividend_yield': info.get('dividendYield', 0),
                'beta': info.get('beta', 1.0),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'market_state': info.get('marketState', 'REGULAR'),
                'previous_close': info.get('previousClose'),
                'current_price': info.get('currentPrice'),
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error getting stock info for {ticker}: {e}")
            return self._default_stock_info(ticker)
    
    def get_detailed_analysis(self, ticker: str) -> Dict[str, Any]:
        """获取详细的股票分析数据"""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="1y")
            
            if hist.empty:
                return {'error': 'No historical data available'}
            
            # 计算技术指标
            current_price = self.get_current_price(ticker)
            latest_high = info.get('fiftyTwoWeekHigh', hist['High'].max())
            latest_low = info.get('fiftyTwoWeekLow', hist['Low'].min())
            
            # 价格位置分析
            price_position = (current_price - latest_low) / (latest_high - latest_low) if latest_high > latest_low else 0.5
            
            # 波动性分析
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)  # 年化波动率
            
            # 成交量分析
            avg_volume = hist['Volume'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else hist['Volume'].mean()
            current_volume = info.get('volume', 0)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            return {
                'ticker': ticker,
                'current_price': current_price,
                'price_analysis': {
                    '52w_high': latest_high,
                    '52w_low': latest_low,
                    'price_position_pct': price_position * 100,
                    'distance_from_high_pct': (latest_high - current_price) / latest_high * 100,
                    'distance_from_low_pct': (current_price - latest_low) / latest_low * 100
                },
                'volatility_analysis': {
                    'annual_volatility': volatility,
                    'risk_level': 'High' if volatility > 0.3 else 'Medium' if volatility > 0.15 else 'Low'
                },
                'volume_analysis': {
                    'current_volume': current_volume,
                    'avg_volume_20d': avg_volume,
                    'volume_ratio': volume_ratio,
                    'volume_signal': 'High' if volume_ratio > 1.5 else 'Normal' if volume_ratio > 0.5 else 'Low'
                },
                'market_info': {
                    'currency': info.get('currency', 'HKD'),
                    'exchange': info.get('exchange', ''),
                    'market_cap': info.get('marketCap', 0),
                    'sector': info.get('sector', 'Unknown')
                },
                'analysis_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error in detailed analysis for {ticker}: {e}")
            return {'error': str(e)}
    
    def is_market_open(self) -> bool:
        """检查香港市场是否开盘"""
        try:
            import pytz
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
            # 简化判断
            now = datetime.now()
            return 9 <= now.hour <= 16 and now.weekday() < 5
    
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
    
    def _default_stock_info(self, ticker: str) -> Dict[str, Any]:
        """默认股票信息"""
        return {
            'symbol': ticker,
            'market_cap': 0,
            'pe_ratio': 15.0,
            'dividend_yield': 0.02,
            'beta': 1.0,
            'sector': 'Technology',
            'currency': 'HKD',
            'last_updated': datetime.now().isoformat()
        }