"""
Enhanced data provider combining Yahoo Finance and Gemini analysis
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import os

from .yahoo_finance_provider import YahooFinanceProvider
from .gemini_provider import GeminiProvider


class EnhancedDataProvider:
    """增强的数据提供器 - 结合Yahoo Finance价格数据和Gemini基本面分析"""
    
    def __init__(self, gemini_api_key: Optional[str] = None, cache_dir: str = "hk_trading_bot/data/cache"):
        self.yahoo_provider = YahooFinanceProvider()
        self.gemini_provider = GeminiProvider(gemini_api_key)
        self.cache_dir = cache_dir
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_comprehensive_analysis(self, ticker: str) -> Dict[str, Any]:
        """获取综合分析（技术面 + 基本面）"""
        print(f"🔍 Starting comprehensive analysis for {ticker}...")
        
        try:
            # 1. 获取价格数据和技术指标
            print(f"📊 Fetching price data...")
            price_data = self.yahoo_provider.get_price_data(ticker, 60)
            current_price = self.yahoo_provider.get_current_price(ticker)
            stock_info = self.yahoo_provider.get_stock_info(ticker)
            
            # 2. 计算技术指标
            from ..modules.indicators import TechnicalIndicators
            indicators = TechnicalIndicators.calculate_all_indicators(price_data)
            
            # 3. 获取基本面分析（使用缓存）
            print(f"🧠 Analyzing fundamentals with Gemini AI...")
            fundamentals = self._get_cached_or_new_analysis(ticker, stock_info)
            
            # 4. 获取市场情绪
            print(f"📈 Analyzing market sentiment...")
            sentiment = self._get_cached_or_new_sentiment(ticker)
            
            # 5. 组合结果
            comprehensive_data = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'price_data': {
                    'current_price': current_price,
                    'historical_prices': price_data,
                    'stock_info': stock_info
                },
                'technical_analysis': {
                    'indicators': indicators,
                    'market_open': self.yahoo_provider.is_market_open()
                },
                'fundamental_analysis': fundamentals,
                'market_sentiment': sentiment,
                'data_quality': self._assess_data_quality(price_data, fundamentals, sentiment)
            }
            
            print(f"✅ Comprehensive analysis completed for {ticker}")
            return comprehensive_data
            
        except Exception as e:
            print(f"❌ Error in comprehensive analysis: {e}")
            return self._fallback_analysis(ticker)
    
    def _get_cached_or_new_analysis(self, ticker: str, stock_info: Dict) -> Dict[str, Any]:
        """获取缓存的分析或进行新分析"""
        cache_file = os.path.join(self.cache_dir, f"{ticker}_fundamentals.json")
        
        try:
            # 检查缓存（24小时有效）
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 检查缓存时间
                cache_time = datetime.fromisoformat(cached_data.get('analysis_timestamp', '2000-01-01'))
                hours_diff = (datetime.now() - cache_time).total_seconds() / 3600
                
                if hours_diff < 24:
                    print(f"📁 Using cached fundamental analysis (age: {hours_diff:.1f}h)")
                    return cached_data
            
            # 进行新分析
            fundamentals = self.gemini_provider.analyze_company_fundamentals(ticker, stock_info)
            
            # 保存到缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(fundamentals, f, indent=2, ensure_ascii=False)
            
            return fundamentals
            
        except Exception as e:
            print(f"⚠️ Error in fundamental analysis caching: {e}")
            return self.gemini_provider._default_analysis(ticker)
    
    def _get_cached_or_new_sentiment(self, ticker: str) -> Dict[str, Any]:
        """获取缓存的情绪分析或进行新分析"""
        cache_file = os.path.join(self.cache_dir, f"{ticker}_sentiment.json")
        
        try:
            # 检查缓存（4小时有效）
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                
                # 检查缓存时间
                cache_time = datetime.fromisoformat(cached_data.get('timestamp', '2000-01-01'))
                hours_diff = (datetime.now() - cache_time).total_seconds() / 3600
                
                if hours_diff < 4:
                    print(f"📁 Using cached sentiment analysis (age: {hours_diff:.1f}h)")
                    return cached_data
            
            # 进行新分析
            sentiment = self.gemini_provider.get_market_sentiment(ticker)
            
            # 保存到缓存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(sentiment, f, indent=2, ensure_ascii=False)
            
            return sentiment
            
        except Exception as e:
            print(f"⚠️ Error in sentiment analysis caching: {e}")
            return self.gemini_provider._default_sentiment(ticker)
    
    def _assess_data_quality(self, price_data: Dict, fundamentals: Dict, sentiment: Dict) -> Dict[str, Any]:
        """评估数据质量"""
        quality_score = 0
        issues = []
        
        # 检查价格数据质量
        if price_data and price_data.get('close'):
            if len(price_data['close']) >= 50:
                quality_score += 30
            elif len(price_data['close']) >= 20:
                quality_score += 20
            else:
                quality_score += 10
                issues.append("Price data insufficient (< 20 days)")
        else:
            issues.append("No price data available")
        
        # 检查基本面分析质量
        if fundamentals.get('confidence_level', 0) >= 7:
            quality_score += 35
        elif fundamentals.get('confidence_level', 0) >= 5:
            quality_score += 25
        else:
            quality_score += 10
            issues.append("Low confidence in fundamental analysis")
        
        # 检查情绪分析质量
        if sentiment.get('confidence', 0) >= 7:
            quality_score += 35
        elif sentiment.get('confidence', 0) >= 5:
            quality_score += 25
        else:
            quality_score += 10
            issues.append("Low confidence in sentiment analysis")
        
        quality_level = "High" if quality_score >= 80 else "Medium" if quality_score >= 60 else "Low"
        
        return {
            'score': quality_score,
            'level': quality_level,
            'issues': issues,
            'recommendations': self._get_quality_recommendations(quality_score, issues)
        }
    
    def _get_quality_recommendations(self, score: int, issues: List[str]) -> List[str]:
        """获取数据质量改进建议"""
        recommendations = []
        
        if score < 60:
            recommendations.append("Consider using this analysis with caution")
        
        if "Price data insufficient" in str(issues):
            recommendations.append("Wait for more historical data before making decisions")
        
        if "Low confidence" in str(issues):
            recommendations.append("Supplement with additional research sources")
        
        if not recommendations:
            recommendations.append("Data quality is sufficient for analysis")
        
        return recommendations
    
    def _fallback_analysis(self, ticker: str) -> Dict[str, Any]:
        """备用分析结果"""
        return {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat(),
            'price_data': {
                'current_price': 50.0,
                'historical_prices': {'close': [], 'high': [], 'low': [], 'open': []},
                'stock_info': {'symbol': ticker}
            },
            'technical_analysis': {
                'indicators': {'ema20': 50.0, 'ema50': 50.0, 'rsi14': 50.0, 'atr14': 1.0},
                'market_open': False
            },
            'fundamental_analysis': self.gemini_provider._default_analysis(ticker),
            'market_sentiment': self.gemini_provider._default_sentiment(ticker),
            'data_quality': {
                'score': 20,
                'level': 'Low',
                'issues': ['Data provider unavailable'],
                'recommendations': ['Manual research required']
            }
        }
    
    def get_simple_price_data(self, ticker: str, days: int = 60) -> Dict[str, List[float]]:
        """简化接口：仅获取价格数据"""
        return self.yahoo_provider.get_price_data(ticker, days)
    
    def get_current_price(self, ticker: str) -> float:
        """简化接口：获取当前价格"""
        return self.yahoo_provider.get_current_price(ticker)
    
    def clear_cache(self, ticker: Optional[str] = None) -> None:
        """清除缓存"""
        try:
            if ticker:
                # 清除特定股票的缓存
                files = [f"{ticker}_fundamentals.json", f"{ticker}_sentiment.json"]
                for file in files:
                    file_path = os.path.join(self.cache_dir, file)
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"🗑️ Cleared cache for {ticker}: {file}")
            else:
                # 清除所有缓存
                import glob
                cache_files = glob.glob(os.path.join(self.cache_dir, "*.json"))
                for file_path in cache_files:
                    os.remove(file_path)
                print(f"🗑️ Cleared all cache files ({len(cache_files)} files)")
                
        except Exception as e:
            print(f"Error clearing cache: {e}")
    
    def get_cache_status(self) -> Dict[str, Any]:
        """获取缓存状态"""
        try:
            import glob
            cache_files = glob.glob(os.path.join(self.cache_dir, "*.json"))
            
            status = {
                'total_files': len(cache_files),
                'cache_dir': self.cache_dir,
                'files': []
            }
            
            for file_path in cache_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                age_hours = (datetime.now() - mod_time).total_seconds() / 3600
                
                status['files'].append({
                    'name': file_name,
                    'size_bytes': file_size,
                    'modified': mod_time.isoformat(),
                    'age_hours': round(age_hours, 1)
                })
            
            return status
            
        except Exception as e:
            return {'error': str(e), 'cache_dir': self.cache_dir}