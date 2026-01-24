"""
Hybrid data provider combining Alpha Vantage and yfinance for optimal coverage
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os

from .alphavantage_provider import AlphaVantageProvider
from .yfinance_provider import YFinanceProvider
from .gemini_provider import GeminiProvider


class HybridDataProvider:
    """混合数据提供器 - 智能选择最佳数据源"""
    
    def __init__(self, gemini_api_key: Optional[str] = None, 
                 alphavantage_keys: List[str] = None,
                 cache_dir: str = "hk_trading_bot/data/cache"):
        
        # 初始化所有数据提供器
        self.alphavantage = AlphaVantageProvider(alphavantage_keys)
        self.yfinance = YFinanceProvider()
        self.gemini = GeminiProvider(gemini_api_key)
        
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        print("🚀 Hybrid Data Provider Initialized")
        print(f"   📊 Alpha Vantage: Ready (US stocks, Technical indicators)")
        print(f"   🌏 yfinance: Ready (Global stocks, HK stocks)")
        print(f"   🧠 Gemini AI: {'Ready' if self.gemini._check_api_key() else 'Limited'}")
    
    def _is_hk_stock(self, symbol: str) -> bool:
        """判断是否为港股"""
        return symbol.endswith('.HK') or symbol.endswith('.hk')
    
    def _is_us_stock(self, symbol: str) -> bool:
        """判断是否为美股"""
        return not ('.' in symbol) or symbol.endswith('.US')
    
    def get_best_quote(self, symbol: str) -> Dict[str, Any]:
        """获取最优质的实时报价"""
        print(f"💰 Getting best quote for {symbol}...")
        
        if self._is_hk_stock(symbol):
            # 港股：优先使用yfinance
            return self._get_yfinance_quote(symbol)
        else:
            # 美股：优先使用Alpha Vantage
            av_quote = self._get_alphavantage_quote(symbol)
            if av_quote:
                return av_quote
            else:
                # 备选yfinance
                return self._get_yfinance_quote(symbol)
    
    def _get_alphavantage_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从Alpha Vantage获取报价"""
        try:
            quote = self.alphavantage.get_quote(symbol)
            if quote and quote.get('price', 0) > 0:
                print(f"✅ Alpha Vantage quote: ${quote['price']:.2f}")
                return quote
            return None
        except Exception as e:
            print(f"⚠️ Alpha Vantage quote failed: {e}")
            return None
    
    def _get_yfinance_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """从yfinance获取报价"""
        try:
            stock_info = self.yfinance.get_stock_info(symbol)
            current_price = self.yfinance.get_current_price(symbol)
            
            if current_price > 0:
                quote = {
                    'symbol': symbol,
                    'price': current_price,
                    'previous_close': stock_info.get('previous_close', current_price),
                    'open': stock_info.get('day_high', current_price),
                    'high': stock_info.get('day_high', current_price),
                    'low': stock_info.get('day_low', current_price),
                    'volume': stock_info.get('volume', 0),
                    'change': current_price - stock_info.get('previous_close', current_price),
                    'source': 'yfinance',
                    'timestamp': datetime.now().isoformat()
                }
                print(f"✅ yfinance quote: {current_price:.2f} {stock_info.get('currency', 'USD')}")
                return quote
            return None
        except Exception as e:
            print(f"⚠️ yfinance quote failed: {e}")
            return None
    
    def get_enhanced_price_data(self, symbol: str, days: int = 60) -> Dict[str, List[float]]:
        """获取增强的价格数据"""
        print(f"📊 Getting enhanced price data for {symbol} ({days} days)...")
        
        if self._is_hk_stock(symbol):
            # 港股：使用yfinance
            data = self.yfinance.get_price_data(symbol, days)
            if data and data.get('close'):
                print(f"✅ yfinance data: {len(data['close'])} days")
                return data
        else:
            # 美股：优先Alpha Vantage
            av_data = self.alphavantage.get_price_data(symbol, days)
            if av_data and av_data.get('close'):
                print(f"✅ Alpha Vantage data: {len(av_data['close'])} days")
                return av_data
            
            # 备选yfinance
            yf_data = self.yfinance.get_price_data(symbol, days)
            if yf_data and yf_data.get('close'):
                print(f"✅ yfinance backup data: {len(yf_data['close'])} days")
                return yf_data
        
        print(f"⚠️ No price data available for {symbol}")
        return {'close': [], 'high': [], 'low': [], 'open': []}
    
    def get_enhanced_stock_info(self, symbol: str) -> Dict[str, Any]:
        """获取增强的股票信息"""
        print(f"🏢 Getting enhanced stock info for {symbol}...")
        
        info = {}
        
        if self._is_us_stock(symbol):
            # 美股：Alpha Vantage公司信息更详细
            av_info = self.alphavantage.get_company_overview(symbol)
            if av_info:
                info.update(av_info)
                print(f"✅ Alpha Vantage info: {av_info.get('name', 'N/A')}")
        
        # 补充yfinance信息
        yf_info = self.yfinance.get_stock_info(symbol)
        if yf_info:
            # 合并信息，yfinance的实时数据可能更准确
            info.update({
                'current_price': yf_info.get('current_price', info.get('current_price', 0)),
                'previous_close': yf_info.get('previous_close', info.get('previous_close', 0)),
                'day_high': yf_info.get('day_high', info.get('day_high', 0)),
                'day_low': yf_info.get('day_low', info.get('day_low', 0)),
                'volume': yf_info.get('volume', info.get('volume', 0))
            })
            print(f"✅ yfinance supplemental info added")
        
        return info
    
    def get_advanced_technical_indicators(self, symbol: str, price_data: Dict[str, List[float]]) -> Dict[str, Any]:
        """获取高级技术指标分析"""
        print(f"📈 Computing advanced technical indicators for {symbol}...")
        
        # 基础技术指标
        from ..modules.indicators import TechnicalIndicators
        basic_indicators = TechnicalIndicators.calculate_all_indicators(price_data)
        
        # Alpha Vantage高级指标（仅美股）
        advanced_indicators = {}
        if self._is_us_stock(symbol):
            try:
                # RSI
                rsi_data = self.alphavantage.get_technical_indicators(symbol, 'RSI', time_period=14)
                if rsi_data:
                    rsi_values = list(rsi_data.values())
                    if rsi_values:
                        latest_rsi = next(iter(rsi_values[0].values())) if rsi_values else None
                        if latest_rsi:
                            advanced_indicators['av_rsi14'] = float(latest_rsi)
                
                # MACD
                macd_data = self.alphavantage.get_technical_indicators(symbol, 'MACD')
                if macd_data:
                    advanced_indicators['av_macd'] = "Available"
                
                print(f"✅ Alpha Vantage indicators added")
            except Exception as e:
                print(f"⚠️ Alpha Vantage indicators failed: {e}")
        
        # 合并所有指标
        all_indicators = {**basic_indicators, **advanced_indicators}
        
        return all_indicators
    
    def get_comprehensive_analysis(self, symbol: str) -> Dict[str, Any]:
        """获取全面的综合分析"""
        print(f"🔍 Starting comprehensive hybrid analysis for {symbol}...")
        
        try:
            # 1. 获取报价和价格数据
            quote = self.get_best_quote(symbol)
            price_data = self.get_enhanced_price_data(symbol, 60)
            stock_info = self.get_enhanced_stock_info(symbol)
            
            current_price = quote.get('price', 0) if quote else stock_info.get('current_price', 0)
            
            # 2. 计算高级技术指标
            indicators = self.get_advanced_technical_indicators(symbol, price_data)
            
            # 3. 获取基本面分析
            print(f"🧠 Analyzing fundamentals with Gemini AI...")
            fundamentals = self._get_cached_or_new_analysis(symbol, stock_info)
            
            # 4. 获取市场情绪
            print(f"😊 Analyzing market sentiment...")
            sentiment = self._get_cached_or_new_sentiment(symbol)
            
            # 5. 数据源信息
            data_sources = {
                'price_data': 'Alpha Vantage' if not self._is_hk_stock(symbol) else 'yfinance',
                'quote': quote.get('source', 'hybrid') if quote else 'unknown',
                'fundamentals': 'Gemini AI' if self.gemini._check_api_key() else 'default',
                'technical_indicators': 'hybrid (local + Alpha Vantage)'
            }
            
            # 6. 组合结果
            comprehensive_data = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'price_data': {
                    'current_price': current_price,
                    'quote': quote,
                    'historical_prices': price_data,
                    'stock_info': stock_info
                },
                'technical_analysis': {
                    'indicators': indicators,
                    'market_open': self._check_market_status(symbol)
                },
                'fundamental_analysis': fundamentals,
                'market_sentiment': sentiment,
                'data_sources': data_sources,
                'data_quality': self._assess_hybrid_data_quality(price_data, quote, fundamentals, sentiment)
            }
            
            print(f"✅ Comprehensive hybrid analysis completed for {symbol}")
            return comprehensive_data
            
        except Exception as e:
            print(f"❌ Error in comprehensive analysis: {e}")
            return self._fallback_analysis(symbol)
    
    def _check_market_status(self, symbol: str) -> bool:
        """检查市场状态"""
        if self._is_hk_stock(symbol):
            return self.yfinance.is_market_open()
        else:
            # 美股市场时间检查（简化）
            import datetime
            now = datetime.datetime.now()
            # 美股：周一至周五 9:30-16:00 EST (简化判断)
            return 9 <= now.hour <= 16 and now.weekday() < 5
    
    def _assess_hybrid_data_quality(self, price_data: Dict, quote: Dict, fundamentals: Dict, sentiment: Dict) -> Dict[str, Any]:
        """评估混合数据质量"""
        quality_score = 0
        issues = []
        
        # 价格数据质量
        if price_data and price_data.get('close'):
            if len(price_data['close']) >= 50:
                quality_score += 35
            elif len(price_data['close']) >= 20:
                quality_score += 25
            else:
                quality_score += 15
                issues.append("Limited price history")
        else:
            issues.append("No price data")
        
        # 实时报价质量
        if quote and quote.get('price', 0) > 0:
            quality_score += 25
        else:
            quality_score += 5
            issues.append("No real-time quote")
        
        # 基本面分析质量
        if fundamentals.get('confidence_level', 0) >= 7:
            quality_score += 25
        elif fundamentals.get('confidence_level', 0) >= 5:
            quality_score += 15
        else:
            quality_score += 5
            issues.append("Low fundamental confidence")
        
        # 情绪分析质量
        if sentiment.get('confidence', 0) >= 7:
            quality_score += 15
        elif sentiment.get('confidence', 0) >= 5:
            quality_score += 10
        else:
            quality_score += 5
            issues.append("Low sentiment confidence")
        
        quality_level = "Excellent" if quality_score >= 90 else "High" if quality_score >= 75 else "Medium" if quality_score >= 60 else "Low"
        
        return {
            'score': quality_score,
            'level': quality_level,
            'issues': issues,
            'data_sources_used': ['Alpha Vantage', 'yfinance', 'Gemini AI'],
            'recommendations': self._get_quality_recommendations(quality_score, issues)
        }
    
    def _get_cached_or_new_analysis(self, symbol: str, stock_info: Dict) -> Dict[str, Any]:
        """获取缓存的分析或进行新分析"""
        cache_file = os.path.join(self.cache_dir, f"{symbol}_fundamentals.json")
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                cache_time = datetime.fromisoformat(cached_data.get('analysis_timestamp', '2000-01-01'))
                hours_diff = (datetime.now() - cache_time).total_seconds() / 3600
                
                if hours_diff < 24:
                    print(f"📁 Using cached fundamental analysis (age: {hours_diff:.1f}h)")
                    return cached_data
            
            fundamentals = self.gemini.analyze_company_fundamentals(symbol, stock_info)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(fundamentals, f, indent=2, ensure_ascii=False)
            
            return fundamentals
            
        except Exception as e:
            print(f"⚠️ Error in fundamental analysis caching: {e}")
            return self.gemini._default_analysis(symbol)
    
    def _get_cached_or_new_sentiment(self, symbol: str) -> Dict[str, Any]:
        """获取缓存的情绪分析或进行新分析"""
        cache_file = os.path.join(self.cache_dir, f"{symbol}_sentiment.json")
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                cache_time = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
                hours_diff = (datetime.now() - cache_time).total_seconds() / 3600
                
                if hours_diff < 4:
                    print(f"📁 Using cached sentiment analysis (age: {hours_diff:.1f}h)")
                    return cached_data
            
            sentiment = self.gemini.get_market_sentiment(symbol)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(sentiment, f, indent=2, ensure_ascii=False)
            
            return sentiment
            
        except Exception as e:
            print(f"⚠️ Error in sentiment analysis caching: {e}")
            return self.gemini._default_sentiment(symbol)
    
    def _get_quality_recommendations(self, score: int, issues: List[str]) -> List[str]:
        """获取质量改进建议"""
        recommendations = []
        
        if score >= 85:
            recommendations.append("Data quality is excellent for trading decisions")
        elif score >= 70:
            recommendations.append("Data quality is good, minor limitations acceptable")
        else:
            recommendations.append("Consider using this analysis with caution")
        
        if "No real-time quote" in str(issues):
            recommendations.append("Real-time pricing may be delayed")
        
        if "Limited price history" in str(issues):
            recommendations.append("Wait for more historical data for better technical analysis")
        
        return recommendations
    
    def _fallback_analysis(self, symbol: str) -> Dict[str, Any]:
        """备用分析结果"""
        return {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'price_data': {
                'current_price': 0.0,
                'historical_prices': {'close': [], 'high': [], 'low': [], 'open': []},
                'stock_info': {'symbol': symbol}
            },
            'technical_analysis': {
                'indicators': {'ema20': 0.0, 'ema50': 0.0, 'rsi14': 50.0, 'atr14': 1.0},
                'market_open': False
            },
            'fundamental_analysis': self.gemini._default_analysis(symbol),
            'market_sentiment': self.gemini._default_sentiment(symbol),
            'data_sources': {'error': 'All data sources failed'},
            'data_quality': {
                'score': 0,
                'level': 'Critical',
                'issues': ['Complete data failure'],
                'recommendations': ['Manual research required']
            }
        }