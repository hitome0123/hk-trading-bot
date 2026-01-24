"""
Enhanced HK Trading Bot - Main Entry Point with Real Data Integration
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
from typing import Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.data_providers import EnhancedDataProvider
from hk_trading_bot.modules.entry_pricing import EnhancedEntryStrategy
from hk_trading_bot.modules.risk_gate import RiskManager
from hk_trading_bot.modules.execution_paper import PaperTrader


class EnhancedTradingBot:
    """增强版港股交易机器人 - 集成真实数据和AI分析"""
    
    def __init__(self, data_dir: str = "hk_trading_bot/data", gemini_api_key: str = None):
        """初始化增强版交易机器人"""
        self.data_provider = EnhancedDataProvider(gemini_api_key)
        self.entry_strategy = EnhancedEntryStrategy()
        self.risk_manager = RiskManager()
        self.paper_trader = PaperTrader(data_dir)
        
        print(f"🚀 Enhanced HK Trading Bot initialized")
        print(f"📁 Data directory: {data_dir}")
        print(f"💰 Initial cash: {self.paper_trader.cash:,.2f} HKD")
        print(f"🧠 AI Analysis: {'Enabled' if gemini_api_key else 'Limited (no API key)'}")
        print(f"📊 Real Data: Yahoo Finance {'+ MCP' if self._check_mcp() else 'fallback'}")
    
    def _check_mcp(self) -> bool:
        """检查MCP是否可用"""
        return self.data_provider.yahoo_provider.mcp_available
    
    def comprehensive_analysis(self, ticker: str) -> Dict:
        """进行综合分析"""
        print(f"\n🔬 Starting comprehensive analysis for {ticker}")
        print("=" * 60)
        
        # 1. 获取综合数据
        comprehensive_data = self.data_provider.get_comprehensive_analysis(ticker)
        current_price = comprehensive_data['price_data']['current_price']
        
        print(f"💲 Current price: {current_price:.2f} HKD")
        print(f"📊 Market open: {'Yes' if comprehensive_data['technical_analysis']['market_open'] else 'No'}")
        print(f"📈 Data quality: {comprehensive_data['data_quality']['level']} ({comprehensive_data['data_quality']['score']}/100)")
        
        # 2. 显示技术指标
        indicators = comprehensive_data['technical_analysis']['indicators']
        print(f"\n📈 Technical Indicators:")
        for name, value in indicators.items():
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
            else:
                print(f"   {name.upper()}: N/A")
        
        # 3. 显示基本面分析
        fundamentals = comprehensive_data['fundamental_analysis']
        print(f"\n🏢 Fundamental Analysis (Confidence: {fundamentals.get('confidence_level', 0)}/10):")
        print(f"   Investment Rating: {fundamentals.get('investment_rating', 'N/A')}")
        print(f"   Financial Health: {fundamentals.get('financial_health', 0)}/10")
        print(f"   Growth Prospects: {fundamentals.get('growth_prospects', 0)}/10")
        print(f"   Competitive Position: {fundamentals.get('competitive_position', 0)}/10")
        print(f"   Valuation: {fundamentals.get('valuation', 'N/A')}")
        
        if fundamentals.get('analyst_summary'):
            print(f"   Summary: {fundamentals['analyst_summary']}")
        
        # 4. 显示市场情绪
        sentiment = comprehensive_data['market_sentiment']
        print(f"\n😊 Market Sentiment (Confidence: {sentiment.get('confidence', 0)}/10):")
        print(f"   Sentiment Score: {sentiment.get('sentiment_score', 0)}/10")
        print(f"   Trend: {sentiment.get('sentiment_trend', 'N/A')}")
        if sentiment.get('key_factors'):
            print(f"   Key Factors: {', '.join(sentiment['key_factors'][:3])}")
        
        # 5. 增强入场分析
        enhanced_analysis = self.entry_strategy.calculate_enhanced_entry(
            current_price, comprehensive_data
        )
        
        print(f"\n🎯 Enhanced Entry Analysis:")
        print(f"   Overall Signal: {enhanced_analysis['signal']}")
        print(f"   Confidence: {enhanced_analysis['confidence']}")
        
        entry_info = enhanced_analysis.get('entry_analysis', {})
        if entry_info.get('adjusted_entry_price'):
            print(f"   Entry Price: {entry_info['adjusted_entry_price']:.2f} HKD")
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
    
    def execute_enhanced_trade(self, analysis_result: Dict, ticker: str) -> Dict:
        """执行增强交易逻辑"""
        enhanced_analysis = analysis_result['enhanced_analysis']
        comprehensive_data = analysis_result['comprehensive_data']
        
        current_price = comprehensive_data['price_data']['current_price']
        overall_signal = enhanced_analysis['signal']
        entry_info = enhanced_analysis.get('entry_analysis', {})
        
        print(f"\n💼 Trade Execution Analysis:")
        
        # 检查是否有交易信号
        if overall_signal not in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
            return {
                'executed': False,
                'reason': f'No buy signal (Signal: {overall_signal})'
            }
        
        # 检查入场价格
        entry_price = entry_info.get('adjusted_entry_price')
        if not entry_price:
            return {
                'executed': False,
                'reason': 'No valid entry price calculated'
            }
        
        # 检查当前价格是否达到入场价
        if current_price > entry_price * 1.005:  # 允许0.5%的滑点
            return {
                'executed': False,
                'reason': f'Current price {current_price:.2f} above entry price {entry_price:.2f}'
            }
        
        # 根据信号强度确定仓位大小
        signal_multipliers = {
            'STRONG_BUY': 1.0,
            'BUY': 0.8,
            'WEAK_BUY': 0.6
        }
        
        base_amount = 5000  # 基础目标金额
        target_amount = base_amount * signal_multipliers.get(overall_signal, 0.6)
        
        # 计算交易数量
        quantity = self.paper_trader.calculate_quantity(current_price, target_amount)
        
        if quantity == 0:
            return {
                'executed': False,
                'reason': 'Calculated quantity is 0 (price too high for minimum lot)'
            }
        
        # 风险检查
        risk_check = self.risk_manager.validate_trade(ticker, current_price, quantity)
        
        if not risk_check['approved']:
            return {
                'executed': False,
                'reason': f"Risk check failed: {', '.join(risk_check['reasons'])}"
            }
        
        adjusted_quantity = risk_check['adjusted_quantity']
        
        print(f"🔥 Executing {overall_signal} order for {ticker}:")
        print(f"   Signal Strength: {overall_signal}")
        print(f"   Quantity: {adjusted_quantity} shares")
        print(f"   Price: {current_price:.2f} HKD")
        print(f"   Amount: {current_price * adjusted_quantity:.2f} HKD")
        print(f"   Entry Strategy: Enhanced (Technical + Fundamental + Sentiment)")
        
        # 执行交易
        order_result = self.paper_trader.place_order(
            ticker=ticker,
            side='buy',
            quantity=adjusted_quantity,
            price=current_price,
            signal_info={
                'enhanced_analysis': enhanced_analysis,
                'signal_strength': overall_signal,
                'entry_price': entry_price,
                'data_quality': comprehensive_data['data_quality']['level']
            }
        )
        
        if order_result['success']:
            self.risk_manager.record_trade(ticker)
            
            print(f"✅ Enhanced trade executed successfully!")
            print(f"   Order ID: {order_result['order_id']}")
            print(f"   New cash balance: {order_result['new_cash_balance']:,.2f} HKD")
            
            return {
                'executed': True,
                'order_result': order_result,
                'signal_strength': overall_signal,
                'risk_warnings': risk_check.get('warnings', []),
                'enhanced_features_used': True
            }
        else:
            return {
                'executed': False,
                'reason': order_result['reason']
            }
    
    def show_enhanced_portfolio(self):
        """显示增强的投资组合状态"""
        summary = self.paper_trader.get_portfolio_summary()
        
        print(f"\n💼 Enhanced Portfolio Summary:")
        print(f"   Cash: {summary['cash']:,.2f} HKD")
        print(f"   Total Value: {summary['total_value']:,.2f} HKD")
        print(f"   P&L: {summary['pnl']:,.2f} HKD ({summary['pnl_pct']:.1f}%)")
        print(f"   Total Trades: {summary['total_trades']}")
        print(f"   Active Positions: {summary['positions_count']}")
        
        if summary['positions']:
            print(f"\n📋 Current Positions:")
            for ticker, pos in summary['positions'].items():
                print(f"   {ticker}: {pos['quantity']} shares @ {pos['avg_price']:.2f} HKD")
                print(f"      Value: {pos['current_value']:,.2f} HKD")
        
        # 显示缓存状态
        cache_status = self.data_provider.get_cache_status()
        if cache_status.get('total_files', 0) > 0:
            print(f"\n🗂️ AI Analysis Cache: {cache_status['total_files']} files")
    
    def run_enhanced_analysis(self, ticker: str):
        """运行完整的增强分析和交易流程"""
        print(f"🚀 Starting enhanced analysis for {ticker}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 综合分析
            analysis_result = self.comprehensive_analysis(ticker)
            
            # 尝试执行交易
            trade_result = self.execute_enhanced_trade(analysis_result, ticker)
            
            print(f"\n📋 Enhanced Trade Decision:")
            if trade_result['executed']:
                print(f"   ✅ Trade executed successfully")
                print(f"   Signal Strength: {trade_result.get('signal_strength', 'N/A')}")
                if trade_result.get('risk_warnings'):
                    print(f"   ⚠️  Warnings: {', '.join(trade_result['risk_warnings'])}")
            else:
                print(f"   ❌ No trade executed")
                print(f"   Reason: {trade_result['reason']}")
            
            # 显示投资组合状态
            self.show_enhanced_portfolio()
            
            return {
                'analysis': analysis_result,
                'trade_result': trade_result
            }
            
        except Exception as e:
            print(f"❌ Error in enhanced analysis: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_main.py <ticker> [gemini_api_key]")
        print("Example: python enhanced_main.py 0700.HK")
        print("Example: python enhanced_main.py 0700.HK your_gemini_api_key")
        print("\nTo use Gemini AI analysis, set GEMINI_API_KEY environment variable or provide as argument")
        return
    
    ticker = sys.argv[1].upper()
    gemini_key = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 创建增强版交易机器人
    bot = EnhancedTradingBot(gemini_api_key=gemini_key)
    
    # 运行增强分析
    result = bot.run_enhanced_analysis(ticker)
    
    print(f"\n🏁 Enhanced analysis completed for {ticker}")
    
    # 显示数据源信息
    print(f"\n📡 Data Sources:")
    print(f"   Price Data: Yahoo Finance {'(via MCP)' if bot._check_mcp() else '(direct API)'}")
    print(f"   AI Analysis: {'Gemini AI' if bot.data_provider.gemini_provider._check_api_key() else 'Mock data'}")


if __name__ == "__main__":
    main()