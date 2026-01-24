"""
Cryptocurrency-specific risk management module
"""

import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta


class CryptoRiskManager:
    """加密货币风险管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化风险管理配置"""
        self.config = config or {
            # 仓位管理
            'max_crypto_exposure': 0.20,      # 加密货币总持仓上限 (20%)
            'max_single_crypto': 0.05,       # 单一加密货币仓位上限 (5%)
            'min_diversification': 3,        # 最少持仓币种数
            
            # 波动率控制
            'volatility_threshold': 1.0,     # 年化波动率阈值 (100%)
            'volatility_position_scaling': True,  # 根据波动率调整仓位
            
            # 止损止盈
            'crypto_stop_loss': 0.20,        # 加密货币止损 (20%)
            'crypto_take_profit': 0.50,      # 加密货币止盈 (50%)
            'trailing_stop_pct': 0.15,       # 跟踪止损 (15%)
            
            # 风险等级
            'risk_levels': {
                'conservative': {'max_exposure': 0.05, 'max_single': 0.02},
                'moderate': {'max_exposure': 0.15, 'max_single': 0.04},
                'aggressive': {'max_exposure': 0.30, 'max_single': 0.08}
            },
            
            # 市场条件
            'bear_market_reduction': 0.5,    # 熊市仓位削减 
            'high_volatility_reduction': 0.3, # 高波动期削减
            
            # 资金管理
            'kelly_criterion': True,          # 使用凯利公式优化仓位
            'var_limit': 0.05,              # 日VaR限制 (5%)
            'drawdown_threshold': 0.15       # 最大回撤阈值 (15%)
        }
        
        # 风险状态跟踪
        self.risk_alerts = []
        self.position_history = []
        
        print("💰 Crypto Risk Manager initialized")
        print(f"   Max Crypto Exposure: {self.config['max_crypto_exposure']*100:.0f}%")
        print(f"   Max Single Position: {self.config['max_single_crypto']*100:.0f}%")
    
    def assess_crypto_risk(self, crypto_symbol: str, 
                          current_price: float,
                          price_data: Dict[str, List[float]],
                          volatility: Optional[float] = None) -> Dict[str, Any]:
        """评估加密货币风险"""
        try:
            risk_assessment = {
                'symbol': crypto_symbol,
                'current_price': current_price,
                'risk_level': 'medium',
                'risk_score': 0.5,
                'warnings': [],
                'recommendations': []
            }
            
            # 1. 波动率风险
            if not volatility and price_data.get('close'):
                volatility = self._calculate_volatility(price_data['close'])
            
            if volatility:
                if volatility > self.config['volatility_threshold']:
                    risk_assessment['warnings'].append(f'High volatility: {volatility*100:.1f}%')
                    risk_assessment['risk_score'] += 0.3
                
                risk_assessment['volatility'] = volatility
            
            # 2. 价格风险 - 52周高低点分析
            if price_data.get('close') and price_data.get('high') and price_data.get('low'):
                closes = price_data['close']
                highs = price_data['high'] 
                lows = price_data['low']
                
                if len(closes) >= 252:  # 一年数据
                    year_high = max(highs[-252:])
                    year_low = min(lows[-252:])
                    
                    # 距离高点的风险
                    distance_from_high = (year_high - current_price) / year_high
                    if distance_from_high < 0.1:  # 接近历史高点
                        risk_assessment['warnings'].append('Near 52-week high - bubble risk')
                        risk_assessment['risk_score'] += 0.2
                    
                    # 距离低点的机会
                    distance_from_low = (current_price - year_low) / year_low
                    if distance_from_low < 0.2:  # 接近历史低点
                        risk_assessment['recommendations'].append('Near 52-week low - potential opportunity')
                        risk_assessment['risk_score'] -= 0.1
            
            # 3. 流动性风险 (基于成交量)
            if 'volume' in price_data and price_data['volume']:
                volumes = price_data['volume']
                if len(volumes) >= 20:
                    avg_volume = np.mean(volumes[-20:])
                    current_volume = volumes[-1] if volumes else 0
                    
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
                    if volume_ratio < 0.3:  # 成交量异常低
                        risk_assessment['warnings'].append('Low trading volume - liquidity risk')
                        risk_assessment['risk_score'] += 0.2
            
            # 4. 确定风险等级
            if risk_assessment['risk_score'] >= 0.8:
                risk_assessment['risk_level'] = 'very_high'
            elif risk_assessment['risk_score'] >= 0.6:
                risk_assessment['risk_level'] = 'high'
            elif risk_assessment['risk_score'] <= 0.2:
                risk_assessment['risk_level'] = 'low'
            else:
                risk_assessment['risk_level'] = 'medium'
            
            risk_assessment['timestamp'] = datetime.now().isoformat()
            return risk_assessment
            
        except Exception as e:
            print(f"❌ Error assessing risk for {crypto_symbol}: {e}")
            return {
                'symbol': crypto_symbol,
                'risk_level': 'unknown',
                'risk_score': 1.0,
                'error': str(e)
            }
    
    def calculate_position_size(self, crypto_symbol: str,
                              account_balance: float,
                              signal_strength: str,
                              confidence: float,
                              volatility: Optional[float] = None,
                              risk_level: str = 'medium') -> Dict[str, Any]:
        """计算加密货币仓位大小"""
        try:
            # 基础仓位计算
            base_positions = {
                'STRONG_BUY': 0.08,   # 8%
                'BUY': 0.05,          # 5%
                'HOLD': 0.02,         # 2%
                'SELL': -0.03,        # -3%
                'STRONG_SELL': -0.05  # -5%
            }
            
            base_position = base_positions.get(signal_strength, 0.02)
            
            # 风险等级调整
            risk_multipliers = {
                'conservative': 0.5,
                'moderate': 1.0,
                'aggressive': 1.5
            }
            
            risk_config = self.config['risk_levels'].get(risk_level, 
                                                       self.config['risk_levels']['moderate'])
            risk_multiplier = risk_multipliers.get(risk_level, 1.0)
            
            # 置信度调整
            confidence_adjustment = min(confidence, 1.0)
            
            # 波动率调整
            volatility_adjustment = 1.0
            if volatility and self.config['volatility_position_scaling']:
                # 高波动率降低仓位
                if volatility > 1.0:  # 100%以上年化波动率
                    volatility_adjustment = 0.5
                elif volatility > 0.6:  # 60%以上年化波动率
                    volatility_adjustment = 0.7
                elif volatility > 0.3:  # 30%以上年化波动率
                    volatility_adjustment = 0.85
            
            # 计算最终仓位
            calculated_position = (base_position * 
                                 risk_multiplier * 
                                 confidence_adjustment * 
                                 volatility_adjustment)
            
            # 应用仓位上限
            max_position = min(
                risk_config['max_single'],
                self.config['max_single_crypto']
            )
            
            final_position = max(-max_position, min(max_position, calculated_position))
            position_value = account_balance * abs(final_position)
            
            return {
                'crypto_symbol': crypto_symbol,
                'signal_strength': signal_strength,
                'recommended_position_pct': final_position * 100,
                'position_value_usd': position_value,
                'max_position_pct': max_position * 100,
                'adjustments_applied': {
                    'base_position': base_position,
                    'risk_multiplier': risk_multiplier,
                    'confidence_adjustment': confidence_adjustment,
                    'volatility_adjustment': volatility_adjustment
                },
                'risk_metrics': {
                    'position_risk': abs(final_position) * volatility if volatility else 0,
                    'dollar_at_risk': position_value * (volatility or 0.5),
                    'max_loss_estimate': position_value * self.config['crypto_stop_loss']
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error calculating position size: {e}")
            return {
                'crypto_symbol': crypto_symbol,
                'recommended_position_pct': 0,
                'error': str(e)
            }
    
    def validate_portfolio_risk(self, portfolio_positions: List[Dict[str, Any]], 
                               account_balance: float) -> Dict[str, Any]:
        """验证投资组合风险"""
        try:
            # 计算总加密货币敞口
            total_crypto_exposure = 0
            crypto_positions = []
            
            for position in portfolio_positions:
                if position.get('asset_type') == 'cryptocurrency':
                    exposure = position.get('position_value', 0) / account_balance
                    total_crypto_exposure += abs(exposure)
                    crypto_positions.append(position)
            
            risk_warnings = []
            risk_adjustments = []
            
            # 检查总敞口
            if total_crypto_exposure > self.config['max_crypto_exposure']:
                excess = total_crypto_exposure - self.config['max_crypto_exposure']
                risk_warnings.append(f'Crypto exposure {total_crypto_exposure*100:.1f}% exceeds limit {self.config["max_crypto_exposure"]*100:.1f}%')
                risk_adjustments.append(f'Reduce crypto exposure by {excess*100:.1f}%')
            
            # 检查单一资产集中度
            for position in crypto_positions:
                exposure = abs(position.get('position_value', 0)) / account_balance
                if exposure > self.config['max_single_crypto']:
                    risk_warnings.append(f'{position.get("symbol")} exposure {exposure*100:.1f}% too high')
            
            # 检查多样化
            if len(crypto_positions) > 0 and len(crypto_positions) < self.config['min_diversification']:
                risk_warnings.append(f'Insufficient diversification: {len(crypto_positions)} assets < {self.config["min_diversification"]}')
            
            # 计算组合风险指标
            portfolio_volatility = self._estimate_portfolio_volatility(crypto_positions)
            portfolio_var = self._calculate_portfolio_var(crypto_positions, account_balance)
            
            return {
                'validation_result': 'PASS' if not risk_warnings else 'FAIL',
                'total_crypto_exposure': total_crypto_exposure * 100,
                'crypto_positions_count': len(crypto_positions),
                'warnings': risk_warnings,
                'recommended_adjustments': risk_adjustments,
                'risk_metrics': {
                    'portfolio_volatility': portfolio_volatility,
                    'daily_var_5pct': portfolio_var,
                    'estimated_max_loss': portfolio_var * np.sqrt(20)  # 月度最大损失估计
                },
                'compliance': {
                    'exposure_limit': total_crypto_exposure <= self.config['max_crypto_exposure'],
                    'diversification': len(crypto_positions) >= self.config['min_diversification'] if crypto_positions else True,
                    'position_limits': all(abs(p.get('position_value', 0))/account_balance <= self.config['max_single_crypto'] for p in crypto_positions)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error validating portfolio risk: {e}")
            return {
                'validation_result': 'ERROR',
                'error': str(e)
            }
    
    def _calculate_volatility(self, prices: List[float], window: int = 30) -> float:
        """计算价格波动率"""
        if len(prices) < window:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return 0.0
        
        daily_volatility = np.std(returns[-window:])
        return daily_volatility * np.sqrt(365)  # 年化波动率 (365天交易)
    
    def _estimate_portfolio_volatility(self, positions: List[Dict[str, Any]]) -> float:
        """估计投资组合波动率"""
        if not positions:
            return 0.0
        
        # 简化计算：假设资产间相关系数为0.3
        total_weight = sum(abs(p.get('position_pct', 0)/100) for p in positions)
        if total_weight == 0:
            return 0.0
        
        weighted_variance = 0
        for position in positions:
            weight = abs(position.get('position_pct', 0)/100) / total_weight
            volatility = position.get('volatility', 0.5)  # 默认50%
            weighted_variance += (weight ** 2) * (volatility ** 2)
        
        # 添加相关性影响
        correlation_adjustment = 1.3  # 假设加密货币间有正相关性
        portfolio_volatility = np.sqrt(weighted_variance) * correlation_adjustment
        
        return portfolio_volatility
    
    def _calculate_portfolio_var(self, positions: List[Dict[str, Any]], 
                               account_balance: float, confidence: float = 0.05) -> float:
        """计算投资组合VaR (Value at Risk)"""
        if not positions:
            return 0.0
        
        portfolio_value = sum(abs(p.get('position_value', 0)) for p in positions)
        if portfolio_value == 0:
            return 0.0
        
        portfolio_volatility = self._estimate_portfolio_volatility(positions)
        daily_volatility = portfolio_volatility / np.sqrt(365)
        
        # 计算5%置信水平的VaR
        var_multiplier = 1.645  # 5%置信水平的z-score
        daily_var = portfolio_value * daily_volatility * var_multiplier
        
        return daily_var