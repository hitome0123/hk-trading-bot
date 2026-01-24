"""
Enhanced entry strategy with fundamental and sentiment analysis
"""

from typing import Dict, Any, Optional
import numpy as np
from .entry_strategy import EntryStrategy


class EnhancedEntryStrategy(EntryStrategy):
    """增强的入场策略 - 结合技术面、基本面和情绪分析"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        
        # 增强配置参数
        self.config = config or {
            # 原有技术分析参数
            'atr_multiplier': 0.5,
            'max_discount': 0.02,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            
            # 基本面分析权重
            'fundamental_weight': 0.4,
            'technical_weight': 0.4,
            'sentiment_weight': 0.2,
            
            # 基本面阈值
            'min_financial_health': 6,
            'min_growth_prospects': 5,
            'min_competitive_position': 5,
            
            # 情绪分析阈值
            'min_sentiment_score': -3,
            'max_sentiment_score': 8,
            
            # 投资评级映射
            'rating_scores': {
                '强烈买入': 10,
                '买入': 8,
                '持有': 5,
                '卖出': 2,
                '强烈卖出': 0
            }
        }
    
    def calculate_enhanced_entry(self, current_price: float, 
                               comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算增强的入场分析
        
        Args:
            current_price: 当前价格
            comprehensive_data: 综合分析数据（技术+基本面+情绪）
        
        Returns:
            增强的入场分析结果
        """
        try:
            # 1. 提取各类数据
            indicators = comprehensive_data.get('technical_analysis', {}).get('indicators', {})
            fundamentals = comprehensive_data.get('fundamental_analysis', {})
            sentiment = comprehensive_data.get('market_sentiment', {})
            data_quality = comprehensive_data.get('data_quality', {})
            
            # 2. 基础技术分析
            technical_analysis = super().calculate_entry_price(current_price, indicators, 
                                                             self.config)
            
            # 3. 基本面评分
            fundamental_score = self._calculate_fundamental_score(fundamentals)
            
            # 4. 情绪分析评分
            sentiment_score = self._calculate_sentiment_score(sentiment)
            
            # 5. 综合评分
            composite_score = self._calculate_composite_score(
                technical_analysis, fundamental_score, sentiment_score
            )
            
            # 6. 生成增强的入场建议
            enhanced_analysis = self._generate_enhanced_recommendation(
                technical_analysis, fundamental_score, sentiment_score, 
                composite_score, current_price, data_quality
            )
            
            return enhanced_analysis
            
        except Exception as e:
            print(f"Error in enhanced entry calculation: {e}")
            # 回退到基础技术分析
            return super().calculate_entry_price(current_price, indicators or {}, self.config)
    
    def _calculate_fundamental_score(self, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        """计算基本面评分"""
        try:
            # 提取基本面指标
            financial_health = fundamentals.get('financial_health', 5)
            growth_prospects = fundamentals.get('growth_prospects', 5)
            competitive_position = fundamentals.get('competitive_position', 5)
            investment_rating = fundamentals.get('investment_rating', '持有')
            confidence = fundamentals.get('confidence_level', 5)
            
            # 计算评级分数
            rating_score = self.config['rating_scores'].get(investment_rating, 5)
            
            # 综合基本面分数 (0-10)
            raw_score = (financial_health * 0.3 + 
                        growth_prospects * 0.3 + 
                        competitive_position * 0.2 + 
                        rating_score * 0.2)
            
            # 根据置信度调整
            adjusted_score = raw_score * (confidence / 10)
            
            # 生成建议
            if adjusted_score >= 8:
                recommendation = "STRONG_BUY"
                reason = "优秀的基本面表现"
            elif adjusted_score >= 6.5:
                recommendation = "BUY"
                reason = "良好的基本面支撑"
            elif adjusted_score >= 4:
                recommendation = "HOLD"
                reason = "基本面中性"
            else:
                recommendation = "AVOID"
                reason = "基本面较弱"
            
            return {
                'score': adjusted_score,
                'raw_score': raw_score,
                'recommendation': recommendation,
                'reason': reason,
                'components': {
                    'financial_health': financial_health,
                    'growth_prospects': growth_prospects,
                    'competitive_position': competitive_position,
                    'rating_score': rating_score,
                    'confidence': confidence
                },
                'meets_criteria': (
                    financial_health >= self.config['min_financial_health'] and
                    growth_prospects >= self.config['min_growth_prospects'] and
                    competitive_position >= self.config['min_competitive_position']
                )
            }
            
        except Exception as e:
            print(f"Error calculating fundamental score: {e}")
            return {
                'score': 5.0,
                'recommendation': 'HOLD',
                'reason': '基本面数据不足',
                'meets_criteria': False
            }
    
    def _calculate_sentiment_score(self, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """计算情绪分析评分"""
        try:
            sentiment_raw = sentiment.get('sentiment_score', 0)
            sentiment_trend = sentiment.get('sentiment_trend', '稳定')
            confidence = sentiment.get('confidence', 5)
            
            # 标准化情绪分数到0-10范围
            normalized_score = max(0, min(10, (sentiment_raw + 10) / 2))
            
            # 根据趋势调整
            trend_adjustment = {
                '改善': 0.5,
                '稳定': 0.0,
                '恶化': -0.5
            }.get(sentiment_trend, 0.0)
            
            adjusted_score = normalized_score + trend_adjustment
            adjusted_score = max(0, min(10, adjusted_score))
            
            # 根据置信度调整
            final_score = adjusted_score * (confidence / 10)
            
            # 生成建议
            if final_score >= 7.5:
                recommendation = "POSITIVE"
                reason = "市场情绪积极"
            elif final_score >= 6:
                recommendation = "NEUTRAL_POSITIVE"
                reason = "市场情绪偏乐观"
            elif final_score >= 4:
                recommendation = "NEUTRAL"
                reason = "市场情绪中性"
            elif final_score >= 2.5:
                recommendation = "NEUTRAL_NEGATIVE"
                reason = "市场情绪偏悲观"
            else:
                recommendation = "NEGATIVE"
                reason = "市场情绪消极"
            
            return {
                'score': final_score,
                'raw_sentiment': sentiment_raw,
                'normalized_score': normalized_score,
                'recommendation': recommendation,
                'reason': reason,
                'trend': sentiment_trend,
                'confidence': confidence,
                'in_range': (
                    self.config['min_sentiment_score'] <= sentiment_raw <= 
                    self.config['max_sentiment_score']
                )
            }
            
        except Exception as e:
            print(f"Error calculating sentiment score: {e}")
            return {
                'score': 5.0,
                'recommendation': 'NEUTRAL',
                'reason': '情绪数据不足',
                'in_range': True
            }
    
    def _calculate_composite_score(self, technical: Dict, fundamental: Dict, 
                                 sentiment: Dict) -> Dict[str, Any]:
        """计算综合评分"""
        try:
            # 提取各维度分数
            tech_score = 5.0  # 技术分析转换为0-10分数
            if technical.get('signal') == 'LONG':
                tech_score = 7.0
            elif technical.get('signal') == 'WAIT':
                tech_score = 4.0
            
            fund_score = fundamental.get('score', 5.0)
            sent_score = sentiment.get('score', 5.0)
            
            # 加权计算综合分数
            composite = (
                tech_score * self.config['technical_weight'] +
                fund_score * self.config['fundamental_weight'] +
                sent_score * self.config['sentiment_weight']
            )
            
            # 生成综合建议
            if composite >= 8:
                overall_signal = "STRONG_BUY"
                confidence_level = "高"
            elif composite >= 6.5:
                overall_signal = "BUY" 
                confidence_level = "中高"
            elif composite >= 5.5:
                overall_signal = "WEAK_BUY"
                confidence_level = "中等"
            elif composite >= 4:
                overall_signal = "HOLD"
                confidence_level = "中等"
            else:
                overall_signal = "AVOID"
                confidence_level = "低"
            
            return {
                'composite_score': composite,
                'overall_signal': overall_signal,
                'confidence_level': confidence_level,
                'component_scores': {
                    'technical': tech_score,
                    'fundamental': fund_score,
                    'sentiment': sent_score
                },
                'weights': {
                    'technical': self.config['technical_weight'],
                    'fundamental': self.config['fundamental_weight'],
                    'sentiment': self.config['sentiment_weight']
                }
            }
            
        except Exception as e:
            print(f"Error calculating composite score: {e}")
            return {
                'composite_score': 5.0,
                'overall_signal': 'HOLD',
                'confidence_level': '低'
            }
    
    def _generate_enhanced_recommendation(self, technical: Dict, fundamental: Dict,
                                        sentiment: Dict, composite: Dict,
                                        current_price: float,
                                        data_quality: Dict) -> Dict[str, Any]:
        """生成增强的投资建议"""
        try:
            # 基础入场价格（来自技术分析）
            base_entry_price = technical.get('entry_price')
            
            # 根据基本面和情绪调整入场价格
            adjustment_factor = 1.0
            
            if fundamental.get('score', 5) >= 7:
                adjustment_factor += 0.01  # 基本面好，可以适当提高入场价
            
            if sentiment.get('score', 5) >= 7:
                adjustment_factor += 0.005  # 情绪好，也可以适当提高入场价
            
            if sentiment.get('score', 5) <= 3:
                adjustment_factor -= 0.01  # 情绪差，降低入场价等待更好机会
            
            # 调整后的入场价格
            adjusted_entry_price = base_entry_price * adjustment_factor if base_entry_price else None
            
            # 生成详细分析
            analysis_summary = []
            
            # 技术面总结
            tech_signal = technical.get('signal', 'WAIT')
            analysis_summary.append(f"技术面: {tech_signal} - {technical.get('reason', '')}")
            
            # 基本面总结
            fund_rec = fundamental.get('recommendation', 'HOLD')
            analysis_summary.append(f"基本面: {fund_rec} - {fundamental.get('reason', '')}")
            
            # 情绪面总结
            sent_rec = sentiment.get('recommendation', 'NEUTRAL')
            analysis_summary.append(f"情绪面: {sent_rec} - {sentiment.get('reason', '')}")
            
            # 综合建议
            overall_signal = composite.get('overall_signal', 'HOLD')
            
            # 风险警告
            warnings = []
            if data_quality.get('level') == 'Low':
                warnings.append("数据质量较低，建议谨慎决策")
            
            if not fundamental.get('meets_criteria', True):
                warnings.append("基本面不符合最低标准")
            
            if not sentiment.get('in_range', True):
                warnings.append("市场情绪极端，注意风险")
            
            return {
                'ticker': technical.get('current_price', current_price),
                'current_price': current_price,
                'signal': overall_signal,
                'confidence': composite.get('confidence_level', '中等'),
                
                'entry_analysis': {
                    'original_entry_price': base_entry_price,
                    'adjusted_entry_price': adjusted_entry_price,
                    'adjustment_factor': adjustment_factor,
                    'discount_pct': ((current_price - adjusted_entry_price) / current_price * 100) 
                                   if adjusted_entry_price else 0
                },
                
                'component_analysis': {
                    'technical': technical,
                    'fundamental': fundamental,
                    'sentiment': sentiment,
                    'composite': composite
                },
                
                'analysis_summary': analysis_summary,
                'warnings': warnings,
                'data_quality': data_quality,
                
                'recommendation': self._format_final_recommendation(
                    overall_signal, adjusted_entry_price, current_price, warnings
                )
            }
            
        except Exception as e:
            print(f"Error generating enhanced recommendation: {e}")
            return technical  # 回退到基础技术分析
    
    def _format_final_recommendation(self, signal: str, entry_price: Optional[float],
                                   current_price: float, warnings: list) -> str:
        """格式化最终建议"""
        try:
            if signal == "STRONG_BUY":
                base_rec = "强烈建议买入"
            elif signal == "BUY":
                base_rec = "建议买入"
            elif signal == "WEAK_BUY":
                base_rec = "可以考虑买入"
            elif signal == "HOLD":
                base_rec = "建议观望"
            else:
                base_rec = "建议回避"
            
            if entry_price and entry_price < current_price:
                price_rec = f"，等待价格回落至 {entry_price:.2f} HKD 附近"
            elif entry_price:
                price_rec = f"，可在当前价格 {current_price:.2f} HKD 建仓"
            else:
                price_rec = ""
            
            warning_text = f"。注意：{'; '.join(warnings)}" if warnings else "。"
            
            return base_rec + price_rec + warning_text
            
        except Exception:
            return "建议进一步研究后决策"