#!/usr/bin/env python3
"""
Test Gemini AI integration directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.gemini_provider import GeminiProvider
import asyncio

def test_gemini():
    """测试Gemini AI API"""
    
    # 直接设置API密钥
    api_key = "AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q"
    
    print("🧠 Testing Gemini AI Integration")
    print("=" * 50)
    
    provider = GeminiProvider(api_key=api_key)
    
    print(f"✅ API Key configured: {api_key[:10]}...")
    print(f"✅ API Key check: {provider._check_api_key()}")
    
    # 测试基本面分析
    print(f"\n📊 Testing fundamental analysis for 2807.HK...")
    
    stock_info = {
        'symbol': '2807.HK',
        'shortName': 'GX CN ROBO&AI',
        'longName': 'Global X China Robotics and Artificial Intelligence ETF',
        'currency': 'HKD',
        'sector': 'Technology ETF',
        'market_cap': 5607200000,  # 约56亿港币
        'current_price': 63.5
    }
    
    try:
        analysis = provider.analyze_company_fundamentals('2807.HK', stock_info)
        
        print(f"✅ Fundamental Analysis Results:")
        print(f"   Investment Rating: {analysis.get('investment_rating', 'N/A')}")
        print(f"   Financial Health: {analysis.get('financial_health', 'N/A')}/10")
        print(f"   Growth Prospects: {analysis.get('growth_prospects', 'N/A')}/10")
        print(f"   Competitive Position: {analysis.get('competitive_position', 'N/A')}/10")
        print(f"   Confidence Level: {analysis.get('confidence_level', 'N/A')}/10")
        print(f"   Analyst Summary: {analysis.get('analyst_summary', 'N/A')}")
        
        if analysis.get('key_opportunities'):
            print(f"   Key Opportunities: {', '.join(analysis['key_opportunities'][:2])}")
        
        if analysis.get('key_risks'):
            print(f"   Key Risks: {', '.join(analysis['key_risks'][:2])}")
            
    except Exception as e:
        print(f"❌ Fundamental Analysis Error: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试市场情绪分析
    print(f"\n😊 Testing sentiment analysis for 2807.HK...")
    
    try:
        sentiment = provider.get_market_sentiment('2807.HK')
        
        print(f"✅ Sentiment Analysis Results:")
        print(f"   Sentiment Score: {sentiment.get('sentiment_score', 'N/A')}/10")
        print(f"   Sentiment Trend: {sentiment.get('sentiment_trend', 'N/A')}")
        print(f"   Confidence: {sentiment.get('confidence', 'N/A')}/10")
        print(f"   Recommendation: {sentiment.get('recommendation', 'N/A')}")
        
        if sentiment.get('key_factors'):
            print(f"   Key Factors: {', '.join(sentiment['key_factors'][:2])}")
            
    except Exception as e:
        print(f"❌ Sentiment Analysis Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gemini()