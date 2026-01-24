"""
Cryptocurrency data provider using Alpha Vantage
"""

import requests
import json
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from .alphavantage_provider import AlphaVantageProvider


class CryptoProvider(AlphaVantageProvider):
    """加密货币数据提供器 - 基于Alpha Vantage扩展"""
    
    def __init__(self, api_keys: List[str] = None):
        """初始化加密货币提供器"""
        super().__init__(api_keys)
        
        # 支持的加密货币列表
        self.supported_cryptos = {
            'BTC': 'Bitcoin',
            'ETH': 'Ethereum', 
            'SOL': 'Solana',
            'DOT': 'Polkadot',
            'LTC': 'Litecoin',
            'BCH': 'Bitcoin Cash',
            'XRP': 'Ripple',
            'ADA': 'Cardano',
            'LINK': 'Chainlink',
            'UNI': 'Uniswap'
        }
        
        print(f"🪙 Crypto Provider initialized")
        print(f"   Supported: {len(self.supported_cryptos)} cryptocurrencies")
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """判断是否为加密货币代码"""
        # 移除可能的/USD后缀
        base_symbol = symbol.replace('/USD', '').replace('-USD', '').upper()
        return base_symbol in self.supported_cryptos
    
    def get_crypto_quote(self, crypto_symbol: str, fiat_currency: str = 'USD') -> Optional[Dict[str, Any]]:
        """获取加密货币实时报价"""
        try:
            # 清理符号
            crypto_symbol = crypto_symbol.replace('/USD', '').replace('-USD', '').upper()
            
            if not self._is_crypto_symbol(crypto_symbol):
                print(f"⚠️ Unsupported cryptocurrency: {crypto_symbol}")
                return None
            
            data = self._make_api_request(
                'CURRENCY_EXCHANGE_RATE',
                '',  # symbol不需要
                from_currency=crypto_symbol,
                to_currency=fiat_currency
            )
            
            if data and 'Realtime Currency Exchange Rate' in data:
                rate_data = data['Realtime Currency Exchange Rate']
                
                return {
                    'symbol': f"{crypto_symbol}/{fiat_currency}",
                    'from_currency': rate_data.get('1. From_Currency Code', crypto_symbol),
                    'to_currency': rate_data.get('3. To_Currency Code', fiat_currency),
                    'price': float(rate_data.get('5. Exchange Rate', 0)),
                    'bid_price': float(rate_data.get('8. Bid Price', 0)),
                    'ask_price': float(rate_data.get('9. Ask Price', 0)),
                    'last_refreshed': rate_data.get('6. Last Refreshed', ''),
                    'timezone': rate_data.get('7. Time Zone', ''),
                    'timestamp': datetime.now().isoformat(),
                    'type': 'cryptocurrency'
                }
            else:
                print(f"⚠️ No quote data found for {crypto_symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting crypto quote for {crypto_symbol}: {e}")
            return None
    
    def get_crypto_daily_data(self, crypto_symbol: str, market_currency: str = 'USD') -> Optional[Dict[str, List[float]]]:
        """获取加密货币日线数据"""
        try:
            crypto_symbol = crypto_symbol.replace('/USD', '').replace('-USD', '').upper()
            
            if not self._is_crypto_symbol(crypto_symbol):
                return None
            
            data = self._make_api_request(
                'DIGITAL_CURRENCY_DAILY',
                crypto_symbol,
                market=market_currency
            )
            
            if data and 'Time Series (Digital Currency Daily)' in data:
                time_series = data['Time Series (Digital Currency Daily)']
                
                # 按日期排序
                sorted_dates = sorted(time_series.keys())
                
                price_data = {
                    'close': [],
                    'high': [],
                    'low': [],
                    'open': [],
                    'volume': [],
                    'market_cap': [],
                    'dates': []
                }
                
                for date in sorted_dates:
                    day_data = time_series[date]
                    
                    # Alpha Vantage crypto数据格式
                    price_data['open'].append(float(day_data.get(f'1a. open ({market_currency})', 0)))
                    price_data['high'].append(float(day_data.get(f'2a. high ({market_currency})', 0)))
                    price_data['low'].append(float(day_data.get(f'3a. low ({market_currency})', 0)))
                    price_data['close'].append(float(day_data.get(f'4a. close ({market_currency})', 0)))
                    price_data['volume'].append(float(day_data.get('5. volume', 0)))
                    price_data['market_cap'].append(float(day_data.get('6. market cap (USD)', 0)))
                    price_data['dates'].append(date)
                
                print(f"✅ Retrieved {len(price_data['close'])} days of crypto data for {crypto_symbol}")
                return price_data
            
            else:
                print(f"⚠️ No daily crypto data found for {crypto_symbol}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting crypto daily data for {crypto_symbol}: {e}")
            return None
    
    def get_crypto_technical_indicators(self, crypto_symbol: str, indicator: str, **kwargs) -> Optional[Dict]:
        """获取加密货币技术指标"""
        try:
            crypto_symbol = crypto_symbol.replace('/USD', '').replace('-USD', '').upper()
            
            # 对于加密货币，我们需要先获取价格数据，然后本地计算指标
            # Alpha Vantage的技术指标API主要支持传统股票
            
            daily_data = self.get_crypto_daily_data(crypto_symbol)
            if not daily_data or not daily_data['close']:
                return None
            
            # 使用本地计算
            from ..modules.indicators import TechnicalIndicators
            indicators_calc = TechnicalIndicators()
            
            if indicator.upper() == 'ALL':
                return indicators_calc.calculate_all_indicators(daily_data)
            else:
                # 计算特定指标
                all_indicators = indicators_calc.calculate_all_indicators(daily_data)
                indicator_key = indicator.lower() + '14' if indicator.upper() in ['RSI', 'ATR'] else indicator.lower() + '20'
                
                if indicator_key in all_indicators:
                    return {indicator_key: all_indicators[indicator_key]}
                
            return None
            
        except Exception as e:
            print(f"❌ Error getting crypto indicators for {crypto_symbol}: {e}")
            return None
    
    def get_crypto_overview(self, crypto_symbol: str) -> Optional[Dict[str, Any]]:
        """获取加密货币基本信息"""
        try:
            crypto_symbol = crypto_symbol.replace('/USD', '').replace('-USD', '').upper()
            
            if not self._is_crypto_symbol(crypto_symbol):
                return None
            
            # 获取实时价格
            quote = self.get_crypto_quote(crypto_symbol)
            
            # 获取历史数据以计算统计信息
            daily_data = self.get_crypto_daily_data(crypto_symbol)
            
            overview = {
                'symbol': crypto_symbol,
                'name': self.supported_cryptos.get(crypto_symbol, crypto_symbol),
                'type': 'cryptocurrency',
                'base_currency': crypto_symbol,
                'quote_currency': 'USD',
                'exchange': 'Multiple',
                'sector': 'Cryptocurrency',
                'industry': 'Digital Currency'
            }
            
            if quote:
                overview.update({
                    'current_price': quote['price'],
                    'bid_price': quote.get('bid_price', 0),
                    'ask_price': quote.get('ask_price', 0),
                    'last_updated': quote.get('last_refreshed', '')
                })
            
            if daily_data and daily_data['close']:
                closes = daily_data['close']
                highs = daily_data['high']
                lows = daily_data['low']
                volumes = daily_data['volume']
                
                # 计算统计信息
                if len(closes) > 0:
                    overview.update({
                        'previous_close': closes[-2] if len(closes) > 1 else closes[-1],
                        'day_high': highs[-1] if highs else 0,
                        'day_low': lows[-1] if lows else 0,
                        'volume': volumes[-1] if volumes else 0,
                        '52_week_high': max(highs) if len(highs) >= 252 else max(highs[-252:]) if len(highs) > 0 else 0,
                        '52_week_low': min(lows) if len(lows) >= 252 else min(lows[-252:]) if len(lows) > 0 else 0,
                        'avg_volume_30d': np.mean(volumes[-30:]) if len(volumes) >= 30 else np.mean(volumes) if volumes else 0
                    })
            
            overview['timestamp'] = datetime.now().isoformat()
            return overview
            
        except Exception as e:
            print(f"❌ Error getting crypto overview for {crypto_symbol}: {e}")
            return None
    
    def get_crypto_market_status(self) -> Dict[str, Any]:
        """获取加密货币市场状态"""
        try:
            # 加密货币市场24/7运行
            return {
                'market_type': 'cryptocurrency',
                'primary_exchanges': 'Global (24/7)',
                'current_status': 'OPEN',
                'notes': 'Cryptocurrency markets operate 24/7',
                'timezone': 'UTC',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Error getting crypto market status: {e}")
            return {'market_type': 'cryptocurrency', 'current_status': 'UNKNOWN'}
    
    def get_top_cryptocurrencies(self) -> List[Dict[str, Any]]:
        """获取主要加密货币的当前价格"""
        top_cryptos = ['BTC', 'ETH', 'SOL', 'DOT']
        results = []
        
        for crypto in top_cryptos:
            quote = self.get_crypto_quote(crypto)
            if quote:
                results.append({
                    'symbol': crypto,
                    'name': self.supported_cryptos.get(crypto, crypto),
                    'price': quote['price'],
                    'last_updated': quote.get('last_refreshed', '')
                })
        
        return results
    
    def calculate_crypto_volatility(self, crypto_symbol: str, period_days: int = 30) -> Optional[float]:
        """计算加密货币波动率"""
        try:
            daily_data = self.get_crypto_daily_data(crypto_symbol)
            
            if not daily_data or len(daily_data['close']) < period_days:
                return None
            
            closes = daily_data['close'][-period_days:]
            
            # 计算日收益率
            returns = []
            for i in range(1, len(closes)):
                daily_return = (closes[i] - closes[i-1]) / closes[i-1]
                returns.append(daily_return)
            
            if not returns:
                return None
            
            # 计算年化波动率
            daily_volatility = np.std(returns)
            annual_volatility = daily_volatility * np.sqrt(365)  # 365天，因为加密货币24/7交易
            
            return annual_volatility
            
        except Exception as e:
            print(f"❌ Error calculating volatility for {crypto_symbol}: {e}")
            return None
    
    # 兼容性接口（与股票接口保持一致）
    def get_current_price(self, symbol: str) -> float:
        """获取当前价格（兼容接口）"""
        if self._is_crypto_symbol(symbol):
            quote = self.get_crypto_quote(symbol)
            return quote['price'] if quote else 0.0
        else:
            return super().get_current_price(symbol)
    
    def get_price_data(self, symbol: str, days: int = 60) -> Dict[str, List[float]]:
        """获取价格数据（兼容接口）"""
        if self._is_crypto_symbol(symbol):
            daily_data = self.get_crypto_daily_data(symbol)
            if daily_data and days < len(daily_data['close']):
                return {
                    'close': daily_data['close'][-days:],
                    'high': daily_data['high'][-days:],
                    'low': daily_data['low'][-days:],
                    'open': daily_data['open'][-days:]
                }
            return daily_data or {'close': [], 'high': [], 'low': [], 'open': []}
        else:
            return super().get_price_data(symbol, days)
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取资产信息（兼容接口）"""
        if self._is_crypto_symbol(symbol):
            return self.get_crypto_overview(symbol) or {'symbol': symbol}
        else:
            return super().get_stock_info(symbol)