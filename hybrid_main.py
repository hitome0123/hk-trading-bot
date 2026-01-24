"""
Hybrid Trading Bot - Main Entry Point with Alpha Vantage + yfinance + Gemini AI
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
from typing import Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers import HybridDataProvider
from hk_trading_bot.modules.entry_pricing import EnhancedEntryStrategy
from hk_trading_bot.modules.risk_gate import RiskManager
from hk_trading_bot.modules.execution_paper import PaperTrader


class HybridTradingBot:
    """混合数据源交易机器人 - Alpha Vantage + yfinance + Gemini AI"""
    
    def __init__(self, data_dir: str = "hk_trading_bot/data", 
                 gemini_api_key: str = None,
                 alphavantage_keys: list = None):
        """初始化混合交易机器人"""
        
        # 设置默认API密钥
        if alphavantage_keys is None:
            alphavantage_keys = ["WU67XB37TICVU5MM", "336PN0924QQGVE2H"]
        
        if gemini_api_key is None:
            gemini_api_key = "AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q"
        
        self.data_provider = HybridDataProvider(
            gemini_api_key=gemini_api_key,
            alphavantage_keys=alphavantage_keys
        )
        self.entry_strategy = EnhancedEntryStrategy()
        self.risk_manager = RiskManager()
        self.paper_trader = PaperTrader(data_dir)
        
        print(f"🚀 Hybrid Trading Bot initialized")
        print(f"📁 Data directory: {data_dir}")
        print(f"💰 Initial cash: {self.paper_trader.cash:,.2f} HKD")
        print(f"📊 Data sources: Alpha Vantage + yfinance + Gemini AI")
    
    def comprehensive_analysis(self, symbol: str) -> Dict:
        """进行全面的混合数据源分析"""
        print(f"\n🔬 Starting hybrid comprehensive analysis for {symbol}")
        print("=" * 80)
        
        # 1. 获取混合综合数据
        comprehensive_data = self.data_provider.get_comprehensive_analysis(symbol)
        
        # 显示数据源信息
        data_sources = comprehensive_data.get('data_sources', {})
        print(f"📡 Data Sources Used:")
        for source_type, source_name in data_sources.items():
            print(f"   {source_type}: {source_name}")
        
        # 显示价格信息
        price_data = comprehensive_data.get('price_data', {})
        quote = price_data.get('quote', {})
        current_price = price_data.get('current_price', 0)
        
        print(f"\n💰 Price Information:")
        print(f"   Current Price: {current_price:.2f}")
        if quote:
            currency = 'HKD' if symbol.endswith('.HK') else 'USD'
            change = quote.get('change', 0)
            print(f"   Change: {change:+.2f} {currency}")
            print(f"   Volume: {quote.get('volume', 0):,}")
            if quote.get('high') and quote.get('low'):
                print(f"   Day Range: {quote['low']:.2f} - {quote['high']:.2f}")
        
        # 显示股票信息
        stock_info = price_data.get('stock_info', {})
        if stock_info.get('name'):
            print(f"   Company: {stock_info['name']}")
        if stock_info.get('sector'):
            print(f"   Sector: {stock_info['sector']}")
        if stock_info.get('market_cap'):
            print(f"   Market Cap: ${stock_info['market_cap']:,.0f}")
        
        # 显示技术指标
        technical = comprehensive_data.get('technical_analysis', {})
        indicators = technical.get('indicators', {})
        
        print(f"\n📈 Technical Indicators:")
        basic_indicators = ['ema20', 'ema50', 'rsi14', 'atr14']
        for name in basic_indicators:
            value = indicators.get(name, np.nan)
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
        
        # Alpha Vantage高级指标
        advanced = {k: v for k, v in indicators.items() if k.startswith('av_')}
        if advanced:
            print(f"   Alpha Vantage Indicators:")
            for name, value in advanced.items():
                print(f"   {name.upper()}: {value}")
        
        # 显示基本面分析
        fundamentals = comprehensive_data.get('fundamental_analysis', {})
        print(f"\n🏢 Fundamental Analysis (Confidence: {fundamentals.get('confidence_level', 0)}/10):")
        print(f"   Investment Rating: {fundamentals.get('investment_rating', 'N/A')}")
        print(f"   Financial Health: {fundamentals.get('financial_health', 0)}/10")
        print(f"   Growth Prospects: {fundamentals.get('growth_prospects', 0)}/10")
        print(f"   Competitive Position: {fundamentals.get('competitive_position', 0)}/10")
        
        if fundamentals.get('analyst_summary'):
            print(f"   Summary: {fundamentals['analyst_summary']}")
        
        # 显示市场情绪
        sentiment = comprehensive_data.get('market_sentiment', {})
        print(f"\n😊 Market Sentiment (Confidence: {sentiment.get('confidence', 0)}/10):")
        print(f"   Sentiment Score: {sentiment.get('sentiment_score', 0)}/10")
        print(f"   Trend: {sentiment.get('sentiment_trend', 'N/A')}")
        
        # 显示数据质量
        data_quality = comprehensive_data.get('data_quality', {})
        print(f"\n📊 Data Quality Assessment:")
        print(f"   Score: {data_quality.get('score', 0)}/100")
        print(f"   Level: {data_quality.get('level', 'Unknown')}")
        
        if data_quality.get('issues'):
            print(f"   Issues: {', '.join(data_quality['issues'])}")
        
        # 增强入场分析
        enhanced_analysis = self.entry_strategy.calculate_enhanced_entry(
            current_price, comprehensive_data
        )
        
        print(f"\n🎯 Enhanced Entry Analysis:")
        print(f"   Overall Signal: {enhanced_analysis['signal']}")
        print(f"   Confidence: {enhanced_analysis['confidence']}")
        
        entry_info = enhanced_analysis.get('entry_analysis', {})
        if entry_info.get('adjusted_entry_price'):
            print(f"   Entry Price: {entry_info['adjusted_entry_price']:.2f}")
            print(f"   Discount: {entry_info.get('discount_pct', 0):.1f}%")
        
        print(f"   Recommendation: {enhanced_analysis.get('recommendation', 'N/A')}")
        
        # 显示警告
        if enhanced_analysis.get('warnings'):
            print(f"\n⚠️ Warnings:")
            for warning in enhanced_analysis['warnings']:
                print(f"   • {warning}")
        
        return {
            'comprehensive_data': comprehensive_data,
            'enhanced_analysis': enhanced_analysis
        }
    
    def execute_hybrid_trade(self, analysis_result: Dict, symbol: str) -> Dict:
        """执行混合分析驱动的交易"""
        enhanced_analysis = analysis_result['enhanced_analysis']
        comprehensive_data = analysis_result['comprehensive_data']
        
        current_price = comprehensive_data['price_data']['current_price']
        overall_signal = enhanced_analysis['signal']
        
        print(f"\n💼 Hybrid Trade Execution Analysis:")
        
        # 检查交易信号
        if overall_signal not in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
            return {
                'executed': False,
                'reason': f'No buy signal (Signal: {overall_signal})'
            }
        
        # 获取数据质量评估
        data_quality = comprehensive_data.get('data_quality', {})
        if data_quality.get('score', 0) < 40:
            return {
                'executed': False,
                'reason': f'Data quality too low ({data_quality.get("score", 0)}/100)'
            }
        
        # 检查入场价格
        entry_info = enhanced_analysis.get('entry_analysis', {})
        entry_price = entry_info.get('adjusted_entry_price')
        
        if not entry_price:
            return {
                'executed': False,
                'reason': 'No valid entry price calculated'
            }
        
        # 检查价格是否达到入场条件
        if current_price > entry_price * 1.01:  # 1%滑点容忍
            return {
                'executed': False,
                'reason': f'Current price {current_price:.2f} above entry price {entry_price:.2f}'
            }
        
        # 根据信号强度和数据质量确定仓位
        signal_multipliers = {
            'STRONG_BUY': 1.0,
            'BUY': 0.8,
            'WEAK_BUY': 0.6
        }
        
        quality_multiplier = min(1.0, data_quality.get('score', 50) / 75)
        
        base_amount = 5000
        target_amount = base_amount * signal_multipliers.get(overall_signal, 0.5) * quality_multiplier
        
        # 计算交易数量
        quantity = self.paper_trader.calculate_quantity(current_price, target_amount)
        
        if quantity == 0:
            return {
                'executed': False,
                'reason': 'Calculated quantity is 0'
            }
        
        # 风险检查
        risk_check = self.risk_manager.validate_trade(symbol, current_price, quantity)
        
        if not risk_check['approved']:
            return {
                'executed': False,
                'reason': f"Risk check failed: {', '.join(risk_check['reasons'])}"
            }
        
        adjusted_quantity = risk_check['adjusted_quantity']
        
        print(f"🔥 Executing HYBRID {overall_signal} order for {symbol}:")
        print(f"   Signal Strength: {overall_signal}")
        print(f"   Data Quality: {data_quality.get('level', 'Unknown')} ({data_quality.get('score', 0)}/100)")
        print(f"   Quantity: {adjusted_quantity} shares")
        print(f"   Price: {current_price:.2f}")
        print(f"   Amount: {current_price * adjusted_quantity:.2f}")
        
        # 执行交易
        order_result = self.paper_trader.place_order(
            ticker=symbol,
            side='buy',
            quantity=adjusted_quantity,
            price=current_price,
            signal_info={
                'strategy_type': 'hybrid',
                'enhanced_analysis': enhanced_analysis,
                'data_sources': comprehensive_data.get('data_sources', {}),
                'data_quality_score': data_quality.get('score', 0)
            }
        )
        
        if order_result['success']:
            self.risk_manager.record_trade(symbol)
            
            print(f"✅ Hybrid trade executed successfully!")
            print(f"   Order ID: {order_result['order_id']}")
            print(f"   New cash balance: {order_result['new_cash_balance']:,.2f}")
            
            return {
                'executed': True,
                'order_result': order_result,
                'signal_strength': overall_signal,
                'data_quality': data_quality.get('level', 'Unknown'),
                'data_sources_used': comprehensive_data.get('data_sources', {}),
                'risk_warnings': risk_check.get('warnings', [])
            }
        else:
            return {
                'executed': False,
                'reason': order_result['reason']
            }
    
    def show_hybrid_portfolio(self):
        """显示混合交易系统的投资组合"""
        summary = self.paper_trader.get_portfolio_summary()
        
        print(f"\n💼 Hybrid Trading Portfolio Summary:")
        print(f"   Cash: {summary['cash']:,.2f} HKD")
        print(f"   Total Value: {summary['total_value']:,.2f} HKD")
        print(f"   P&L: {summary['pnl']:,.2f} HKD ({summary['pnl_pct']:.1f}%)")
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Active Positions: {summary['positions_count']}")
        
        if summary['positions']:
            print(f"\n📋 Current Positions:")
            for ticker, pos in summary['positions'].items():
                print(f"   {ticker}: {pos['quantity']} shares @ {pos['avg_price']:.2f}")
                print(f"      Value: {pos['current_value']:,.2f}")
        
        # 显示最近交易的数据源
        recent_trades = self.paper_trader.get_recent_trades(3)
        if recent_trades:
            print(f"\n📜 Recent Trades (with data sources):")
            for trade in recent_trades:
                signal_info = trade.get('signal_info', {})
                strategy = signal_info.get('strategy_type', 'unknown')
                data_quality = signal_info.get('data_quality_score', 0)
                print(f"   {trade['timestamp'][:19]} - {trade['side'].upper()} {trade['quantity']} {trade['ticker']}")
                print(f"      Strategy: {strategy}, Quality: {data_quality}/100")
    
    def run_hybrid_analysis(self, symbol: str):
        """运行完整的混合分析和交易流程"""
        print(f"🚀 Starting HYBRID analysis for {symbol}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 混合综合分析
            analysis_result = self.comprehensive_analysis(symbol)
            
            # 尝试执行交易
            trade_result = self.execute_hybrid_trade(analysis_result, symbol)
            
            print(f"\n📋 Hybrid Trade Decision:")
            if trade_result['executed']:
                print(f"   ✅ Trade executed successfully")
                print(f"   Signal: {trade_result.get('signal_strength', 'N/A')}")
                print(f"   Data Quality: {trade_result.get('data_quality', 'Unknown')}")
                
                sources_used = trade_result.get('data_sources_used', {})
                print(f"   Sources Used: {', '.join(sources_used.values())}")
                
                if trade_result.get('risk_warnings'):
                    print(f"   ⚠️ Warnings: {', '.join(trade_result['risk_warnings'])}")
            else:
                print(f"   ❌ No trade executed")
                print(f"   Reason: {trade_result['reason']}")
            
            # 显示投资组合
            self.show_hybrid_portfolio()
            
            return {
                'analysis': analysis_result,
                'trade_result': trade_result
            }
            
        except Exception as e:
            print(f"❌ Error in hybrid analysis: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python hybrid_main.py <symbol>")
        print("Examples:")
        print("  python hybrid_main.py AAPL        # US stock (Alpha Vantage primary)")
        print("  python hybrid_main.py 2513.HK     # HK stock (yfinance primary)")
        print("  python hybrid_main.py 0700.HK     # HK stock (yfinance primary)")
        return
    
    symbol = sys.argv[1].upper()
    
    # 创建混合交易机器人
    bot = HybridTradingBot()
    
    # 运行混合分析
    result = bot.run_hybrid_analysis(symbol)
    
    print(f"\n🏁 Hybrid analysis completed for {symbol}")
    
    # 显示数据源总结
    if 'analysis' in result:
        data_sources = result['analysis']['comprehensive_data'].get('data_sources', {})
        print(f"\n📡 Data Sources Summary:")
        for source_type, source_name in data_sources.items():
            print(f"   {source_type.title()}: {source_name}")


if __name__ == "__main__":
    main()