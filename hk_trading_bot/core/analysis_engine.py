"""
四层过滤通用分析框架 - Universal Analysis Engine
"""

import numpy as np
import requests
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import re
from dataclasses import dataclass


@dataclass
class PatternSignal:
    """形态信号"""
    pattern_type: str
    signal_strength: float  # 0-1
    description: str
    metadata: Dict[str, Any]


@dataclass
class CapitalFlowSignal:
    """资金流向信号"""
    flow_type: str  # 'inflow', 'outflow', 'neutral'
    flow_strength: float  # 0-1
    signal_interpretation: str
    metadata: Dict[str, Any]


@dataclass
class RelativeStrengthSignal:
    """相对强弱信号"""
    rs_ratio: float
    benchmark_symbol: str
    strength_category: str  # 'leader', 'follower', 'laggard'
    outperformance_pct: float
    metadata: Dict[str, Any]


@dataclass
class NarrativeSignal:
    """AI叙事信号"""
    narrative_score: int  # 0-100
    narrative_category: str  # 'rerating', 'cyclical', 'speculative'
    key_themes: List[str]
    news_summary: str
    confidence: float


class UniversalAnalysisEngine:
    """四层过滤通用分析框架"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化分析引擎"""
        
        self.config = config or {
            # 形态识别参数
            'gap_threshold': 0.02,           # 2% 跳空阈值
            'volume_spike_ratio': 2.0,       # 成交量激增倍数
            'institutional_volume_threshold': 2.0,  # 机构介入成交量阈值
            'institutional_price_threshold': 0.03,  # 机构介入涨幅阈值
            'volatility_contraction_days': 5,       # 波动收缩观察天数
            'volatility_contraction_threshold': 0.5, # 波动收缩阈值
            
            # 资金流向参数
            'large_order_threshold': 100000,  # 大单门槛 (USD)
            'flow_signal_weight': 0.3,        # 资金流权重
            
            # 相对强弱参数
            'rs_leader_threshold': 1.2,       # 领涨龙头阈值
            'rs_laggard_threshold': 0.8,      # 落后阈值
            'rs_period_days': 20,             # 相对强弱计算周期
            
            # AI叙事参数
            'narrative_weight': 0.25,         # 叙事权重
            'max_news_items': 3,              # 最大新闻条数
            'news_relevance_days': 30,        # 新闻相关性天数
        }
        
        # 基准映射
        self.benchmark_mapping = {
            # 港股基准
            'HK': '^HSI',           # 恒生指数
            'HK_TECH': '2800.HK',   # 恒生科技指数ETF
            
            # 美股基准  
            'US': 'SPY',            # S&P 500 ETF
            'US_TECH': 'QQQ',       # 纳斯达克100 ETF
            'US_GROWTH': 'VUG',     # 成长股ETF
            
            # 加密货币基准
            'CRYPTO': 'BTC',        # 比特币作为加密货币基准
        }
        
        # Gemini API配置 (如果可用)
        self.gemini_api_key = "AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q"
        
        print("🧠 Universal Analysis Engine initialized")
        print("   📊 Pattern Recognition Layer")
        print("   💰 Capital Flow Detection Layer") 
        print("   📈 Relative Strength Analysis Layer")
        print("   🤖 AI Narrative Scoring Layer")
    
    def analyze_ticker(self, ticker: str, 
                      data_provider: Any,
                      price_data: Optional[Dict] = None,
                      current_price: Optional[float] = None) -> Dict[str, Any]:
        """
        对任意标的进行四层过滤分析
        
        Args:
            ticker: 股票/加密货币代码
            data_provider: 数据提供器
            price_data: 价格数据 (可选)
            current_price: 当前价格 (可选)
        """
        
        print(f"\n🔍 四层过滤分析: {ticker}")
        print("=" * 50)
        
        # 获取基础数据
        if not price_data:
            price_data = self._get_price_data(ticker, data_provider)
        
        if not current_price:
            current_price = self._get_current_price(ticker, data_provider)
        
        if not price_data or not current_price:
            return {'error': f'无法获取 {ticker} 的基础数据'}
        
        try:
            # 第一层：动态形态扫描
            pattern_signals = self._pattern_recognition_layer(
                ticker, price_data, current_price
            )
            
            # 第二层：资金流向探测
            capital_flow_signals = self._capital_flow_layer(
                ticker, price_data, data_provider
            )
            
            # 第三层：相对强弱分析
            relative_strength_signals = self._relative_strength_layer(
                ticker, price_data, data_provider
            )
            
            # 第四层：AI叙事评分
            narrative_signals = self._ai_narrative_layer(
                ticker, current_price
            )
            
            # 综合评分
            composite_analysis = self._calculate_composite_score(
                pattern_signals, capital_flow_signals, 
                relative_strength_signals, narrative_signals
            )
            
            return {
                'ticker': ticker,
                'analysis_timestamp': datetime.now().isoformat(),
                'current_price': current_price,
                'layer_1_patterns': pattern_signals,
                'layer_2_capital_flow': capital_flow_signals,
                'layer_3_relative_strength': relative_strength_signals,
                'layer_4_narrative': narrative_signals,
                'composite_analysis': composite_analysis
            }
            
        except Exception as e:
            print(f"❌ 分析过程中出现错误: {e}")
            return {'error': str(e)}
    
    def _pattern_recognition_layer(self, ticker: str, 
                                  price_data: Dict, 
                                  current_price: float) -> List[PatternSignal]:
        """第一层：动态形态扫描"""
        
        print("🎯 Layer 1: Pattern Recognition")
        
        patterns = []
        closes = price_data.get('close', [])
        highs = price_data.get('high', [])
        lows = price_data.get('low', [])
        volumes = price_data.get('volume', [])
        
        if len(closes) < 20:
            return patterns
        
        # 1. Gap Up/Down 检测
        gap_signal = self._detect_gaps(closes, highs, lows)
        if gap_signal:
            patterns.append(gap_signal)
        
        # 2. Volume Spike 检测
        volume_signal = self._detect_volume_spike(volumes, closes)
        if volume_signal:
            patterns.append(volume_signal)
        
        # 3. Volatility Contraction 检测
        volatility_signal = self._detect_volatility_contraction(closes, highs, lows)
        if volatility_signal:
            patterns.append(volatility_signal)
        
        # 4. 机构介入信号检测
        institutional_signal = self._detect_institutional_intervention(
            volumes, closes, current_price
        )
        if institutional_signal:
            patterns.append(institutional_signal)
        
        for pattern in patterns:
            print(f"   📊 {pattern.pattern_type}: {pattern.description}")
        
        return patterns
    
    def _capital_flow_layer(self, ticker: str, 
                           price_data: Dict,
                           data_provider: Any) -> List[CapitalFlowSignal]:
        """第二层：资金流向/筹码探测"""
        
        print("💰 Layer 2: Capital Flow Analysis")
        
        flows = []
        
        # 判断市场类型
        market_type = self._detect_market_type(ticker)
        
        if market_type == 'HK':
            # 港股：南向资金流向
            flow_signal = self._analyze_southbound_flow(ticker)
        elif market_type == 'US':
            # 美股：大单分析
            flow_signal = self._analyze_large_orders(ticker, price_data)
        elif market_type == 'CRYPTO':
            # 加密货币：鲸鱼动向
            flow_signal = self._analyze_whale_movements(ticker, price_data)
        else:
            flow_signal = None
        
        if flow_signal:
            flows.append(flow_signal)
            print(f"   💎 {flow_signal.flow_type}: {flow_signal.signal_interpretation}")
        
        # 价格与资金流向背离分析
        divergence_signal = self._analyze_price_flow_divergence(
            price_data, flows
        )
        if divergence_signal:
            flows.append(divergence_signal)
            print(f"   ⚠️ Divergence: {divergence_signal.signal_interpretation}")
        
        return flows
    
    def _relative_strength_layer(self, ticker: str,
                                price_data: Dict,
                                data_provider: Any) -> List[RelativeStrengthSignal]:
        """第三层：相对强弱/龙头探测"""
        
        print("📈 Layer 3: Relative Strength Analysis")
        
        rs_signals = []
        
        # 获取基准标的
        benchmark = self._get_benchmark_ticker(ticker)
        
        if not benchmark:
            print("   ⚠️ 无法确定基准标的")
            return rs_signals
        
        # 获取基准数据
        benchmark_data = self._get_price_data(benchmark, data_provider)
        
        if not benchmark_data:
            print(f"   ⚠️ 无法获取基准 {benchmark} 数据")
            return rs_signals
        
        # 计算相对强弱
        rs_signal = self._calculate_relative_strength(
            ticker, price_data, benchmark, benchmark_data
        )
        
        if rs_signal:
            rs_signals.append(rs_signal)
            print(f"   🏆 RS vs {benchmark}: {rs_signal.rs_ratio:.2f} ({rs_signal.strength_category})")
            print(f"   📊 Outperformance: {rs_signal.outperformance_pct:+.1f}%")
        
        return rs_signals
    
    def _ai_narrative_layer(self, ticker: str, 
                           current_price: float) -> Optional[NarrativeSignal]:
        """第四层：AI叙事/逻辑定性"""
        
        print("🤖 Layer 4: AI Narrative Analysis")
        
        try:
            # 获取相关新闻
            news_data = self._fetch_ticker_news(ticker)
            
            if not news_data:
                print("   ⚠️ 无法获取新闻数据")
                return None
            
            # 调用Gemini进行分析
            narrative_analysis = self._analyze_with_gemini(ticker, news_data, current_price)
            
            if narrative_analysis:
                print(f"   🎯 Narrative Score: {narrative_analysis.narrative_score}/100")
                print(f"   📰 Category: {narrative_analysis.narrative_category}")
                print(f"   💡 Key Themes: {', '.join(narrative_analysis.key_themes[:2])}")
                
                return narrative_analysis
            
        except Exception as e:
            print(f"   ⚠️ AI分析跳过: {e}")
            
            # 返回简化的默认分析
            return NarrativeSignal(
                narrative_score=60,
                narrative_category='cyclical',
                key_themes=['technical_analysis', 'market_movement'],
                news_summary='AI分析暂时不可用，使用技术分析结果',
                confidence=0.4
            )
    
    def _detect_gaps(self, closes: List[float], 
                    highs: List[float], 
                    lows: List[float]) -> Optional[PatternSignal]:
        """检测跳空形态"""
        
        if len(closes) < 2:
            return None
        
        # 检测今日跳空
        prev_close = closes[-2]
        today_high = highs[-1] 
        today_low = lows[-1]
        current_close = closes[-1]
        
        # Gap Up
        gap_up = (today_low - prev_close) / prev_close
        if gap_up > self.config['gap_threshold']:
            return PatternSignal(
                pattern_type="Gap_Up",
                signal_strength=min(1.0, gap_up / 0.05),  # 5%为满分
                description=f"向上跳空 {gap_up*100:.1f}%",
                metadata={'gap_percentage': gap_up*100, 'direction': 'up'}
            )
        
        # Gap Down  
        gap_down = (prev_close - today_high) / prev_close
        if gap_down > self.config['gap_threshold']:
            return PatternSignal(
                pattern_type="Gap_Down", 
                signal_strength=min(1.0, gap_down / 0.05),
                description=f"向下跳空 {gap_down*100:.1f}%",
                metadata={'gap_percentage': gap_down*100, 'direction': 'down'}
            )
        
        return None
    
    def _detect_volume_spike(self, volumes: List[float], 
                            closes: List[float]) -> Optional[PatternSignal]:
        """检测成交量激增"""
        
        if len(volumes) < 20:
            return None
        
        current_volume = volumes[-1]
        avg_volume_20 = np.mean(volumes[-21:-1])  # 前20天平均
        
        if avg_volume_20 == 0:
            return None
        
        volume_ratio = current_volume / avg_volume_20
        
        if volume_ratio > self.config['volume_spike_ratio']:
            # 判断是否伴随价格上涨
            if len(closes) >= 2:
                price_change = (closes[-1] - closes[-2]) / closes[-2]
                direction = "bullish" if price_change > 0 else "bearish"
            else:
                direction = "neutral"
            
            return PatternSignal(
                pattern_type="Volume_Spike",
                signal_strength=min(1.0, (volume_ratio - 1) / 2),  # 3倍为满分
                description=f"成交量激增 {volume_ratio:.1f}x ({direction})",
                metadata={
                    'volume_ratio': volume_ratio,
                    'direction': direction,
                    'current_volume': current_volume
                }
            )
        
        return None
    
    def _detect_volatility_contraction(self, closes: List[float],
                                     highs: List[float],
                                     lows: List[float]) -> Optional[PatternSignal]:
        """检测波动率收缩"""
        
        contraction_days = self.config['volatility_contraction_days']
        if len(closes) < contraction_days * 2:
            return None
        
        # 计算最近N天的波动率
        recent_volatility = self._calculate_period_volatility(
            closes[-contraction_days:], highs[-contraction_days:], lows[-contraction_days:]
        )
        
        # 计算之前N天的波动率
        previous_volatility = self._calculate_period_volatility(
            closes[-contraction_days*2:-contraction_days],
            highs[-contraction_days*2:-contraction_days], 
            lows[-contraction_days*2:-contraction_days]
        )
        
        if previous_volatility == 0:
            return None
        
        volatility_ratio = recent_volatility / previous_volatility
        
        if volatility_ratio < self.config['volatility_contraction_threshold']:
            return PatternSignal(
                pattern_type="Volatility_Contraction",
                signal_strength=1.0 - volatility_ratio,  # 收缩越多信号越强
                description=f"波动率收缩 {(1-volatility_ratio)*100:.0f}%",
                metadata={
                    'recent_volatility': recent_volatility,
                    'previous_volatility': previous_volatility,
                    'contraction_ratio': volatility_ratio
                }
            )
        
        return None
    
    def _detect_institutional_intervention(self, volumes: List[float],
                                         closes: List[float],
                                         current_price: float) -> Optional[PatternSignal]:
        """检测机构介入信号"""
        
        if len(volumes) < 20 or len(closes) < 2:
            return None
        
        # 机构介入条件：成交量 > 2倍均值 AND 涨幅 > 3%
        current_volume = volumes[-1]
        avg_volume_20 = np.mean(volumes[-21:-1])
        
        price_change = (closes[-1] - closes[-2]) / closes[-2]
        
        volume_condition = current_volume > (self.config['institutional_volume_threshold'] * avg_volume_20)
        price_condition = price_change > self.config['institutional_price_threshold']
        
        if volume_condition and price_condition:
            signal_strength = min(1.0, 
                (current_volume / avg_volume_20 - 1) * price_change * 10
            )
            
            return PatternSignal(
                pattern_type="Institutional_Intervention",
                signal_strength=signal_strength,
                description=f"机构介入信号 (量:{current_volume/avg_volume_20:.1f}x, 涨:{price_change*100:.1f}%)",
                metadata={
                    'volume_ratio': current_volume / avg_volume_20,
                    'price_change_pct': price_change * 100,
                    'intervention_score': signal_strength
                }
            )
        
        return None
    
    def _analyze_southbound_flow(self, ticker: str) -> Optional[CapitalFlowSignal]:
        """分析南向资金流向 (港股)"""
        
        # 这里应该接入真实的南向资金API
        # 目前使用模拟逻辑
        
        # 模拟南向资金数据
        import random
        flow_amount = random.uniform(-100, 300) * 1000000  # 百万港币
        
        if flow_amount > 50000000:  # 5000万以上净流入
            flow_type = "strong_inflow"
            strength = min(1.0, flow_amount / 200000000)
            interpretation = f"南向资金大幅净流入 {flow_amount/1000000:.0f}M HKD"
        elif flow_amount > 0:
            flow_type = "inflow"  
            strength = flow_amount / 100000000
            interpretation = f"南向资金净流入 {flow_amount/1000000:.0f}M HKD"
        elif flow_amount > -50000000:
            flow_type = "outflow"
            strength = abs(flow_amount) / 100000000  
            interpretation = f"南向资金净流出 {abs(flow_amount)/1000000:.0f}M HKD"
        else:
            flow_type = "strong_outflow"
            strength = min(1.0, abs(flow_amount) / 200000000)
            interpretation = f"南向资金大幅净流出 {abs(flow_amount)/1000000:.0f}M HKD"
        
        return CapitalFlowSignal(
            flow_type=flow_type,
            flow_strength=strength,
            signal_interpretation=interpretation,
            metadata={'flow_amount_hkd': flow_amount, 'data_source': 'simulated'}
        )
    
    def _analyze_large_orders(self, ticker: str, 
                            price_data: Dict) -> Optional[CapitalFlowSignal]:
        """分析大单比率 (美股)"""
        
        # 模拟大单分析
        volumes = price_data.get('volume', [])
        if not volumes:
            return None
        
        current_volume = volumes[-1]
        avg_volume = np.mean(volumes[-20:]) if len(volumes) >= 20 else current_volume
        
        # 假设大单比率与成交量比率相关
        large_order_ratio = min(0.8, (current_volume / avg_volume - 1) * 0.2 + 0.3)
        
        if large_order_ratio > 0.6:
            flow_type = "institutional_buying"
            interpretation = f"检测到机构大单买入 (大单比率: {large_order_ratio*100:.0f}%)"
        elif large_order_ratio > 0.4:
            flow_type = "moderate_buying"
            interpretation = f"检测到适度机构买入 (大单比率: {large_order_ratio*100:.0f}%)"
        else:
            flow_type = "retail_dominated"
            interpretation = f"散户主导交易 (大单比率: {large_order_ratio*100:.0f}%)"
        
        return CapitalFlowSignal(
            flow_type=flow_type,
            flow_strength=large_order_ratio,
            signal_interpretation=interpretation,
            metadata={'large_order_ratio': large_order_ratio, 'data_source': 'estimated'}
        )
    
    def _analyze_whale_movements(self, ticker: str,
                               price_data: Dict) -> Optional[CapitalFlowSignal]:
        """分析鲸鱼动向 (加密货币)"""
        
        # 模拟鲸鱼动向分析
        volumes = price_data.get('volume', [])
        closes = price_data.get('close', [])
        
        if len(volumes) < 5 or len(closes) < 2:
            return None
        
        # 检测异常大额交易
        current_volume = volumes[-1]
        avg_volume_5 = np.mean(volumes[-6:-1])
        price_change = (closes[-1] - closes[-2]) / closes[-2]
        
        if current_volume > avg_volume_5 * 3 and abs(price_change) > 0.05:
            if price_change > 0:
                flow_type = "whale_accumulation"
                interpretation = f"检测到鲸鱼买入 (价格+{price_change*100:.1f}%, 量+{current_volume/avg_volume_5:.1f}x)"
            else:
                flow_type = "whale_distribution"  
                interpretation = f"检测到鲸鱼卖出 (价格{price_change*100:.1f}%, 量+{current_volume/avg_volume_5:.1f}x)"
            
            strength = min(1.0, (current_volume / avg_volume_5) / 5 + abs(price_change) * 2)
        else:
            flow_type = "normal_trading"
            interpretation = "正常交易量，无明显鲸鱼动向"
            strength = 0.3
        
        return CapitalFlowSignal(
            flow_type=flow_type,
            flow_strength=strength,
            signal_interpretation=interpretation,
            metadata={
                'volume_ratio': current_volume / avg_volume_5,
                'price_change_pct': price_change * 100,
                'data_source': 'estimated'
            }
        )
    
    def _analyze_price_flow_divergence(self, price_data: Dict,
                                     flow_signals: List[CapitalFlowSignal]) -> Optional[CapitalFlowSignal]:
        """分析价格与资金流向背离"""
        
        if not flow_signals:
            return None
        
        closes = price_data.get('close', [])
        if len(closes) < 2:
            return None
        
        price_change = (closes[-1] - closes[-2]) / closes[-2]
        
        # 分析主要资金流向
        main_flow = flow_signals[0]
        is_inflow = main_flow.flow_type in ['inflow', 'strong_inflow', 'institutional_buying', 'whale_accumulation']
        
        # 检测背离
        if price_change > 0.02 and not is_inflow:
            # 价格上涨但资金流出 - 可能的诱多
            return CapitalFlowSignal(
                flow_type="bearish_divergence",
                flow_strength=0.7,
                signal_interpretation="价格上涨但资金流出，警惕诱多风险",
                metadata={'price_change': price_change*100, 'flow_direction': 'outflow'}
            )
        elif price_change < -0.02 and is_inflow:
            # 价格下跌但资金流入 - 可能的抄底
            return CapitalFlowSignal(
                flow_type="bullish_divergence",
                flow_strength=0.8,
                signal_interpretation="价格下跌但资金流入，可能出现反弹",
                metadata={'price_change': price_change*100, 'flow_direction': 'inflow'}
            )
        
        return None
    
    def _calculate_relative_strength(self, ticker: str, price_data: Dict,
                                   benchmark: str, benchmark_data: Dict) -> Optional[RelativeStrengthSignal]:
        """计算相对强弱"""
        
        closes = price_data.get('close', [])
        benchmark_closes = benchmark_data.get('close', [])
        
        period = self.config['rs_period_days']
        
        if len(closes) < period or len(benchmark_closes) < period:
            return None
        
        # 计算期间收益率
        ticker_return = (closes[-1] - closes[-period]) / closes[-period]
        benchmark_return = (benchmark_closes[-1] - benchmark_closes[-period]) / benchmark_closes[-period]
        
        if benchmark_return == 0:
            return None
        
        # 相对强弱比率
        rs_ratio = (1 + ticker_return) / (1 + benchmark_return)
        outperformance = (ticker_return - benchmark_return) * 100
        
        # 分类
        if rs_ratio >= self.config['rs_leader_threshold']:
            strength_category = "leader"
        elif rs_ratio <= self.config['rs_laggard_threshold']:
            strength_category = "laggard"
        else:
            strength_category = "follower"
        
        return RelativeStrengthSignal(
            rs_ratio=rs_ratio,
            benchmark_symbol=benchmark,
            strength_category=strength_category,
            outperformance_pct=outperformance,
            metadata={
                'ticker_return': ticker_return * 100,
                'benchmark_return': benchmark_return * 100,
                'period_days': period
            }
        )
    
    def _analyze_with_gemini(self, ticker: str, news_data: List[Dict],
                           current_price: float) -> Optional[NarrativeSignal]:
        """使用Gemini进行叙事分析"""
        
        try:
            # 构建提示词
            news_text = "\n".join([f"- {item.get('title', '')} ({item.get('date', '')})" 
                                 for item in news_data[:self.config['max_news_items']]])
            
            prompt = f"""
请分析 {ticker} 的投资叙事，基于以下最近新闻：

{news_text}

当前价格: ${current_price}

请按照以下格式分析：

1. 核心新闻总结 (3条关键信息)
2. 叙事分类 (选择一个):
   - rerating: 估值重构 (技术突破、商业模式转型)
   - cyclical: 周期反弹 (超跌回补、财报修复)  
   - speculative: 情绪炒作 (无基本面支撑的短期拉升)

3. 叙事得分 (0-100):
   - 0-30: 负面叙事或无支撑
   - 31-60: 中性或混合信号
   - 61-100: 强正面叙事

4. 关键主题标签 (最多5个)

请以JSON格式回复：
{{
    "summary": "新闻核心要点",
    "category": "rerating/cyclical/speculative",
    "score": 85,
    "themes": ["主题1", "主题2"],
    "confidence": 0.8
}}
"""
            
            # 调用Gemini API (简化版，避免超时)
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt, 
                    generation_config={'max_output_tokens': 500, 'temperature': 0.3}
                )
            except:
                # API调用失败，返回默认分析
                raise Exception("Gemini API unavailable")
            
            # 解析响应
            response_text = response.text.strip()
            
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                return NarrativeSignal(
                    narrative_score=int(result.get('score', 50)),
                    narrative_category=result.get('category', 'cyclical'),
                    key_themes=result.get('themes', []),
                    news_summary=result.get('summary', 'No summary available'),
                    confidence=float(result.get('confidence', 0.5))
                )
            
        except Exception as e:
            print(f"   ❌ Gemini API错误: {e}")
        
        # 返回默认分析
        return NarrativeSignal(
            narrative_score=50,
            narrative_category='cyclical',
            key_themes=['market_movement'],
            news_summary='Unable to fetch narrative analysis',
            confidence=0.3
        )
    
    def _calculate_composite_score(self, pattern_signals: List[PatternSignal],
                                 capital_flows: List[CapitalFlowSignal],
                                 relative_strength: List[RelativeStrengthSignal],
                                 narrative: Optional[NarrativeSignal]) -> Dict[str, Any]:
        """计算综合评分"""
        
        composite_score = 0.0
        max_score = 100.0
        
        # 权重配置
        weights = {
            'patterns': 0.25,
            'capital_flow': 0.30, 
            'relative_strength': 0.20,
            'narrative': 0.25
        }
        
        # 形态评分 (0-25)
        pattern_score = 0
        if pattern_signals:
            pattern_strengths = [p.signal_strength for p in pattern_signals]
            pattern_score = np.mean(pattern_strengths) * 25
        
        # 资金流评分 (0-30)
        flow_score = 0
        if capital_flows:
            # 正面流向得分，负面流向减分
            for flow in capital_flows:
                if flow.flow_type in ['inflow', 'strong_inflow', 'institutional_buying', 'whale_accumulation']:
                    flow_score += flow.flow_strength * 15
                elif flow.flow_type in ['bullish_divergence']:
                    flow_score += flow.flow_strength * 10
                elif flow.flow_type in ['bearish_divergence']:
                    flow_score -= flow.flow_strength * 10
            flow_score = max(0, min(30, flow_score))
        
        # 相对强弱评分 (0-20)
        rs_score = 0
        if relative_strength:
            rs = relative_strength[0]
            if rs.strength_category == 'leader':
                rs_score = 20
            elif rs.strength_category == 'follower':
                rs_score = 10
            else:  # laggard
                rs_score = 0
        
        # 叙事评分 (0-25)
        narrative_score = 0
        if narrative:
            narrative_score = narrative.narrative_score * 0.25
        
        # 计算最终评分
        composite_score = pattern_score + flow_score + rs_score + narrative_score
        
        # 确定整体信号
        if composite_score >= 80:
            overall_signal = "STRONG_BUY"
        elif composite_score >= 60:
            overall_signal = "BUY"
        elif composite_score >= 40:
            overall_signal = "HOLD"
        elif composite_score >= 20:
            overall_signal = "SELL"
        else:
            overall_signal = "STRONG_SELL"
        
        return {
            'composite_score': round(composite_score, 1),
            'max_score': max_score,
            'overall_signal': overall_signal,
            'component_scores': {
                'pattern_score': round(pattern_score, 1),
                'capital_flow_score': round(flow_score, 1),
                'relative_strength_score': round(rs_score, 1),  
                'narrative_score': round(narrative_score, 1)
            },
            'weights_used': weights,
            'confidence': self._calculate_confidence(pattern_signals, capital_flows, relative_strength, narrative)
        }
    
    def _calculate_confidence(self, patterns, flows, rs, narrative) -> float:
        """计算分析置信度"""
        confidence_factors = []
        
        # 数据可用性
        if patterns:
            confidence_factors.append(0.8)
        if flows:
            confidence_factors.append(0.9)
        if rs:
            confidence_factors.append(0.7)
        if narrative:
            confidence_factors.append(narrative.confidence)
        
        return np.mean(confidence_factors) if confidence_factors else 0.5
    
    # 辅助方法
    def _get_price_data(self, ticker: str, data_provider: Any) -> Optional[Dict]:
        """获取价格数据"""
        try:
            if hasattr(data_provider, 'get_price_data'):
                return data_provider.get_price_data(ticker, 60)
            elif hasattr(data_provider, 'get_crypto_daily_data'):
                return data_provider.get_crypto_daily_data(ticker)
            return None
        except:
            return None
    
    def _get_current_price(self, ticker: str, data_provider: Any) -> Optional[float]:
        """获取当前价格"""
        try:
            if hasattr(data_provider, 'get_current_price'):
                return data_provider.get_current_price(ticker)
            elif hasattr(data_provider, 'get_crypto_quote'):
                quote = data_provider.get_crypto_quote(ticker)
                return quote['price'] if quote else None
            return None
        except:
            return None
    
    def _detect_market_type(self, ticker: str) -> str:
        """检测市场类型"""
        ticker = ticker.upper()
        
        if ticker.endswith('.HK') or ticker.endswith('.HKG'):
            return 'HK'
        elif ticker in ['BTC', 'ETH', 'SOL', 'DOT', 'ADA', 'LINK', 'UNI']:
            return 'CRYPTO'
        else:
            return 'US'
    
    def _get_benchmark_ticker(self, ticker: str) -> Optional[str]:
        """获取基准标的"""
        market_type = self._detect_market_type(ticker)
        
        if market_type == 'HK':
            return self.benchmark_mapping['HK']
        elif market_type == 'US':
            # 可以根据行业进一步细分
            return self.benchmark_mapping['US']
        elif market_type == 'CRYPTO':
            return self.benchmark_mapping['CRYPTO'] if ticker != 'BTC' else None
        
        return None
    
    def _calculate_period_volatility(self, closes: List[float],
                                   highs: List[float], 
                                   lows: List[float]) -> float:
        """计算期间波动率"""
        if len(closes) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(closes)):
            if closes[i-1] > 0:
                returns.append((closes[i] - closes[i-1]) / closes[i-1])
        
        return np.std(returns) if returns else 0.0
    
    def _fetch_ticker_news(self, ticker: str) -> List[Dict]:
        """获取标的相关新闻 (模拟)"""
        # 这里应该接入真实新闻API
        return [
            {
                'title': f'{ticker} 技术突破获得市场关注',
                'date': '2026-01-10',
                'summary': '公司在核心技术领域取得重大进展'
            },
            {
                'title': f'{ticker} 财报季业绩预期积极',
                'date': '2026-01-08', 
                'summary': '分析师上调业绩预期'
            },
            {
                'title': f'{ticker} 获得机构大幅增持',
                'date': '2026-01-05',
                'summary': '多家机构投资者增加持仓'
            }
        ]