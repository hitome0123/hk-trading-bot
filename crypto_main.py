#!/usr/bin/env python3
"""
加密货币交易分析系统
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers.crypto_provider import CryptoProvider
from hk_trading_bot.modules.crypto_strategy import CryptoTradingStrategy
from hk_trading_bot.modules.crypto_risk_manager import CryptoRiskManager
from hk_trading_bot.modules.indicators import TechnicalIndicators
import time

def analyze_cryptocurrency(crypto_symbol: str):
    """分析加密货币"""
    
    print(f"🪙 加密货币分析系统")
    print(f"📊 分析目标: {crypto_symbol}")
    print("=" * 60)
    
    # 初始化组件
    crypto_provider = CryptoProvider()
    strategy = CryptoTradingStrategy()
    risk_manager = CryptoRiskManager()
    indicators_calc = TechnicalIndicators()
    
    try:
        # 1. 获取实时报价
        print(f"\n📈 获取 {crypto_symbol} 实时数据...")
        quote = crypto_provider.get_crypto_quote(crypto_symbol)
        
        if not quote:
            print(f"❌ 无法获取 {crypto_symbol} 报价")
            return
        
        current_price = quote['price']
        print(f"💰 当前价格: ${current_price:,.2f}")
        print(f"🔄 更新时间: {quote.get('last_refreshed', 'Unknown')}")
        
        # 2. 获取历史数据
        print(f"\n📊 获取历史价格数据...")
        price_data = crypto_provider.get_crypto_daily_data(crypto_symbol)
        
        if not price_data or not price_data['close']:
            print(f"❌ 无法获取 {crypto_symbol} 历史数据")
            return
        
        print(f"✅ 历史数据: {len(price_data['close'])} 天")
        
        # 3. 计算技术指标
        print(f"\n🔬 计算技术指标...")
        indicators = indicators_calc.calculate_all_indicators(price_data)
        
        if indicators:
            print(f"✅ RSI14: {indicators.get('rsi14', 0):.1f}")
            print(f"✅ EMA20: ${indicators.get('ema20', 0):,.2f}")
            print(f"✅ EMA50: ${indicators.get('ema50', 0):,.2f}")
            print(f"✅ ATR14: ${indicators.get('atr14', 0):.2f}")
        
        # 4. 加密货币策略分析
        print(f"\n🚀 加密货币策略分析...")
        signal_analysis = strategy.calculate_crypto_entry_signal(
            crypto_symbol, current_price, price_data, indicators, price_data.get('volume', [])
        )
        
        if 'error' not in signal_analysis:
            print(f"📊 综合信号: {signal_analysis['overall_signal']}")
            print(f"🎯 置信度: {signal_analysis['confidence']*100:.1f}%")
            print(f"💎 建议入场价: ${signal_analysis['entry_price']:,.2f}")
            print(f"🛡️ 止损价: ${signal_analysis['stop_loss']:,.2f}")
            print(f"🎉 止盈价: ${signal_analysis['take_profit']:,.2f}")
            
            # 详细策略分析
            components = signal_analysis.get('analysis_components', {})
            
            print(f"\n📈 动量分析:")
            momentum = components.get('momentum', {})
            print(f"   趋势: {momentum.get('trend', 'Unknown')}")
            print(f"   动量分数: {momentum.get('momentum_score', 0):.3f}")
            
            print(f"\n💥 波动率突破:")
            breakout = components.get('breakout', {})
            print(f"   突破类型: {breakout.get('breakout_type', 'Unknown')}")
            print(f"   ATR扩展: {breakout.get('atr_expansion', 1):.2f}x")
            
            print(f"\n🔄 均值回归:")
            reversion = components.get('reversion', {})
            print(f"   回归信号: {reversion.get('reversion_signal', 'Unknown')}")
            print(f"   价格偏离EMA20: {reversion.get('price_deviation_20', 0)*100:.1f}%")
        
        # 5. 风险评估
        print(f"\n⚠️ 风险评估...")
        volatility = crypto_provider.calculate_crypto_volatility(crypto_symbol)
        risk_assessment = risk_manager.assess_crypto_risk(
            crypto_symbol, current_price, price_data, volatility
        )
        
        print(f"🎲 风险等级: {risk_assessment.get('risk_level', 'Unknown').upper()}")
        print(f"📊 风险分数: {risk_assessment.get('risk_score', 0):.2f}/1.0")
        if volatility:
            print(f"📈 年化波动率: {volatility*100:.1f}%")
        
        # 显示风险警告
        warnings = risk_assessment.get('warnings', [])
        if warnings:
            print(f"\n🚨 风险警告:")
            for warning in warnings:
                print(f"   ⚠️ {warning}")
        
        # 6. 仓位建议
        print(f"\n💰 仓位建议...")
        if 'error' not in signal_analysis:
            position_advice = risk_manager.calculate_position_size(
                crypto_symbol,
                account_balance=10000,  # 假设$10K账户
                signal_strength=signal_analysis['overall_signal'],
                confidence=signal_analysis['confidence'],
                volatility=volatility,
                risk_level='moderate'
            )
            
            if 'error' not in position_advice:
                print(f"📊 建议仓位: {position_advice['recommended_position_pct']:.1f}%")
                print(f"💵 建议金额: ${position_advice['position_value_usd']:,.0f}")
                print(f"🛡️ 预估最大损失: ${position_advice['risk_metrics']['max_loss_estimate']:,.0f}")
                
                risk_metrics = position_advice.get('risk_metrics', {})
                print(f"📊 风险价值: ${risk_metrics.get('dollar_at_risk', 0):,.0f}")
        
        # 7. 市场概况
        print(f"\n🌐 {crypto_symbol} 市场概况...")
        overview = crypto_provider.get_crypto_overview(crypto_symbol)
        
        if overview:
            print(f"💎 加密货币: {overview.get('name', crypto_symbol)}")
            print(f"💱 交易对: {crypto_symbol}/USD")
            print(f"🏢 类型: {overview.get('type', 'cryptocurrency').title()}")
            
            # 显示价格统计
            if 'day_high' in overview and overview['day_high']:
                print(f"📊 日高: ${overview['day_high']:,.2f}")
            if 'day_low' in overview and overview['day_low']:
                print(f"📊 日低: ${overview['day_low']:,.2f}")
            if 'volume' in overview and overview['volume']:
                print(f"📊 成交量: {overview['volume']:,.0f}")
        
        # 8. 交易建议总结
        print(f"\n🎯 交易建议总结")
        print("-" * 40)
        
        if 'error' not in signal_analysis:
            signal = signal_analysis['overall_signal']
            confidence = signal_analysis['confidence']
            
            if signal in ['STRONG_BUY', 'BUY']:
                print(f"✅ 建议: {signal} (置信度: {confidence*100:.1f}%)")
                print(f"💡 策略: 考虑逢低买入，严格止损")
            elif signal in ['STRONG_SELL', 'SELL']:
                print(f"❌ 建议: {signal} (置信度: {confidence*100:.1f}%)")  
                print(f"💡 策略: 考虑获利了结或避免买入")
            else:
                print(f"⏸️ 建议: {signal}")
                print(f"💡 策略: 观望等待更好时机")
            
            # 时间框架建议
            timeframe = signal_analysis.get('risk_management', {}).get('recommended_timeframe', '')
            if timeframe:
                print(f"⏰ 建议持仓期: {timeframe}")
        
        print(f"\n🔔 分析完成于: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")

def main():
    """主程序"""
    if len(sys.argv) < 2:
        print(f"🪙 加密货币交易分析系统")
        print(f"Usage: python crypto_main.py <CRYPTO_SYMBOL>")
        print(f"\n支持的加密货币:")
        print(f"  BTC  - Bitcoin")
        print(f"  ETH  - Ethereum") 
        print(f"  SOL  - Solana")
        print(f"  DOT  - Polkadot")
        print(f"  ADA  - Cardano")
        print(f"  LINK - Chainlink")
        print(f"\n示例:")
        print(f"  python crypto_main.py BTC")
        print(f"  python crypto_main.py ETH")
        return
    
    crypto_symbol = sys.argv[1].upper()
    analyze_cryptocurrency(crypto_symbol)

if __name__ == "__main__":
    main()