"""
Gemini AI provider for fundamental analysis
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import subprocess


class GeminiProvider:
    """Gemini AI 提供器 - 用于公司基本面分析"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com/v1"
        self.model = "gemini-1.5-flash"
        
    def _check_api_key(self) -> bool:
        """检查API密钥是否配置"""
        if not self.api_key:
            print("⚠️ Gemini API key not found. Set GEMINI_API_KEY environment variable")
            return False
        return True
    
    async def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """调用Gemini API"""
        if not self._check_api_key():
            return None
            
        try:
            import aiohttp
            
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 2048,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            params = {
                "key": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['candidates'][0]['content']['parts'][0]['text']
                    else:
                        print(f"Gemini API error: {response.status}")
                        error_text = await response.text()
                        print(f"Error details: {error_text}")
                        return None
                        
        except ImportError:
            print("Installing aiohttp for Gemini API...")
            subprocess.run(['pip', 'install', 'aiohttp'], check=True)
            return await self._call_gemini_api(prompt)
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return None
    
    def _fallback_requests_call(self, prompt: str) -> Optional[str]:
        """备选：使用requests同步调用"""
        if not self._check_api_key():
            return None
            
        try:
            import requests
            
            url = f"{self.base_url}/models/{self.model}:generateContent"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 2048,
                }
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            params = {
                "key": self.api_key
            }
            
            response = requests.post(url, json=payload, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"Gemini API error: {response.status_code}")
                print(f"Error details: {response.text}")
                return None
                
        except ImportError:
            print("Installing requests for Gemini fallback...")
            subprocess.run(['pip', 'install', 'requests'], check=True)
            return self._fallback_requests_call(prompt)
        except Exception as e:
            print(f"Error in fallback Gemini call: {e}")
            return None
    
    def analyze_company_fundamentals(self, ticker: str, stock_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析公司基本面"""
        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(ticker, stock_info)
            
            # 尝试异步调用
            try:
                response = asyncio.run(self._call_gemini_api(prompt))
            except Exception:
                # 备选同步调用
                response = self._fallback_requests_call(prompt)
            
            if response:
                return self._parse_analysis_response(response, ticker)
            else:
                return self._default_analysis(ticker)
                
        except Exception as e:
            print(f"Error in fundamental analysis: {e}")
            return self._default_analysis(ticker)
    
    def _build_analysis_prompt(self, ticker: str, stock_info: Optional[Dict] = None) -> str:
        """构建分析提示"""
        base_prompt = f"""
请分析港股 {ticker} 的投资价值和基本面，提供结构化的分析报告。

股票代码: {ticker}
"""
        
        if stock_info:
            base_prompt += f"""
当前股票信息:
- 市值: {stock_info.get('market_cap', 'N/A')}
- 市盈率: {stock_info.get('pe_ratio', 'N/A')}
- 股息率: {stock_info.get('dividend_yield', 'N/A')}
- Beta值: {stock_info.get('beta', 'N/A')}
- 行业: {stock_info.get('sector', 'N/A')}
"""
        
        base_prompt += """
请从以下维度进行分析，并以JSON格式返回结果:

{
  "company_overview": "公司简介和主营业务",
  "financial_health": "财务健康状况评分(1-10)",
  "growth_prospects": "增长前景评分(1-10)", 
  "competitive_position": "竞争地位评分(1-10)",
  "valuation": "估值水平(便宜/合理/昂贵)",
  "investment_rating": "投资评级(强烈买入/买入/持有/卖出/强烈卖出)",
  "key_risks": ["风险1", "风险2", "风险3"],
  "key_opportunities": ["机会1", "机会2", "机会3"],
  "analyst_summary": "整体分析总结(100字以内)",
  "confidence_level": "分析置信度(1-10)"
}

请确保返回有效的JSON格式，不要包含其他内容。
"""
        
        return base_prompt
    
    def _parse_analysis_response(self, response: str, ticker: str) -> Dict[str, Any]:
        """解析Gemini响应"""
        try:
            # 尝试提取JSON部分
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                analysis = json.loads(json_str)
                
                # 确保必要字段存在
                required_fields = [
                    'financial_health', 'growth_prospects', 'competitive_position',
                    'investment_rating', 'analyst_summary', 'confidence_level'
                ]
                
                for field in required_fields:
                    if field not in analysis:
                        if field in ['financial_health', 'growth_prospects', 'competitive_position', 'confidence_level']:
                            analysis[field] = 5  # 默认中等评分
                        else:
                            analysis[field] = f"Analysis for {ticker}"
                
                analysis['ticker'] = ticker
                analysis['analysis_timestamp'] = datetime.now().isoformat()
                
                return analysis
            else:
                raise ValueError("No valid JSON found in response")
                
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")
            print(f"Raw response: {response[:200]}...")
            return self._default_analysis(ticker)
    
    def _default_analysis(self, ticker: str) -> Dict[str, Any]:
        """默认分析结果"""
        return {
            'ticker': ticker,
            'company_overview': f'{ticker} 基本面分析暂不可用',
            'financial_health': 5,
            'growth_prospects': 5,
            'competitive_position': 5,
            'valuation': '需要更多数据',
            'investment_rating': '持有',
            'key_risks': ['市场风险', '行业风险', '公司特定风险'],
            'key_opportunities': ['行业增长', '市场扩张', '技术创新'],
            'analyst_summary': f'{ticker} 需要更详细的分析数据',
            'confidence_level': 3,
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def get_market_sentiment(self, ticker: str) -> Dict[str, Any]:
        """获取市场情绪分析"""
        try:
            prompt = f"""
分析港股 {ticker} 当前的市场情绪和投资者情绪。

请考虑以下因素:
1. 近期新闻和公告
2. 行业趋势
3. 宏观经济环境
4. 技术面走势

以JSON格式返回:
{{
  "sentiment_score": "市场情绪评分(-10到10，负数为悲观，正数为乐观)",
  "sentiment_trend": "情绪趋势(改善/稳定/恶化)",
  "key_factors": ["影响因素1", "影响因素2", "影响因素3"],
  "recommendation": "基于情绪的建议",
  "confidence": "分析置信度(1-10)"
}}
"""
            
            try:
                response = asyncio.run(self._call_gemini_api(prompt))
            except Exception:
                response = self._fallback_requests_call(prompt)
            
            if response:
                return self._parse_sentiment_response(response, ticker)
            else:
                return self._default_sentiment(ticker)
                
        except Exception as e:
            print(f"Error in sentiment analysis: {e}")
            return self._default_sentiment(ticker)
    
    def _parse_sentiment_response(self, response: str, ticker: str) -> Dict[str, Any]:
        """解析情绪分析响应"""
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                sentiment = json.loads(json_str)
                sentiment['ticker'] = ticker
                sentiment['timestamp'] = datetime.now().isoformat()
                return sentiment
            else:
                raise ValueError("No valid JSON found")
                
        except Exception as e:
            print(f"Error parsing sentiment response: {e}")
            return self._default_sentiment(ticker)
    
    def _default_sentiment(self, ticker: str) -> Dict[str, Any]:
        """默认情绪分析"""
        return {
            'ticker': ticker,
            'sentiment_score': 0,
            'sentiment_trend': '稳定',
            'key_factors': ['市场不确定性', '缺乏具体数据'],
            'recommendation': '需要更多信息进行判断',
            'confidence': 3,
            'timestamp': datetime.now().isoformat()
        }