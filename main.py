"""
HK Trading Bot - Main Entry Point
"""

import sys
import os
import json
import numpy as np
from datetime import datetime
from typing import Dict

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from hk_trading_bot.modules.risk_gate import RiskManager
from hk_trading_bot.modules.execution_paper import PaperTrader
from hk_trading_bot.data_provider import MockDataProvider


class TradingBot:
    """港股交易机器人"""
    
    def __init__(self, data_dir: str = "hk_trading_bot/data"):
        """初始化交易机器人"""
        self.data_provider = MockDataProvider()
        self.indicators_calc = TechnicalIndicators()
        self.entry_strategy = EntryStrategy()
        self.risk_manager = RiskManager()
        self.paper_trader = PaperTrader(data_dir)
        
        print(f"🤖 HK Trading Bot initialized")
        print(f"📁 Data directory: {data_dir}")
        print(f"💰 Initial cash: {self.paper_trader.cash:,.2f} HKD")
    
    def analyze_ticker(self, ticker: str) -> Dict:
        """分析单个股票"""
        print(f"\n📊 Analyzing {ticker}...")
        
        # 1. 获取价格数据
        price_data = self.data_provider.get_price_data(ticker, 60)
        current_price = self.data_provider.get_current_price(ticker)
        
        print(f"💲 Current price: {current_price:.2f} HKD")
        
        # 2. 计算技术指标
        indicators = self.indicators_calc.calculate_all_indicators(price_data)
        
        print(f"📈 Technical Indicators:")
        for name, value in indicators.items():
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
            else:
                print(f"   {name.upper()}: N/A")
        
        # 3. 计算建仓价格
        entry_analysis = self.entry_strategy.calculate_entry_price(
            current_price, indicators
        )
        
        print(f"\n🎯 Entry Analysis:")
        print(f"   Signal: {entry_analysis['signal']}")
        print(f"   Reason: {entry_analysis['reason']}")
        if entry_analysis['entry_price']:
            print(f"   Entry Price: {entry_analysis['entry_price']:.2f} HKD")
            print(f"   Discount: {((current_price - entry_analysis['entry_price'])/current_price*100):.1f}%")
        
        return {
            'ticker': ticker,
            'current_price': current_price,
            'indicators': indicators,
            'entry_analysis': entry_analysis
        }
    
    def execute_trade_if_triggered(self, analysis: Dict) -> Dict:
        """如果满足条件则执行交易"""
        ticker = analysis['ticker']
        current_price = analysis['current_price']
        entry_analysis = analysis['entry_analysis']
        
        # 检查是否有交易信号
        if entry_analysis['signal'] != 'LONG' or not entry_analysis['entry_price']:
            return {
                'executed': False,
                'reason': 'No buy signal generated'
            }
        
        entry_price = entry_analysis['entry_price']
        
        # 检查当前价格是否达到建仓价
        if current_price > entry_price:
            return {
                'executed': False,
                'reason': f'Current price {current_price:.2f} above entry price {entry_price:.2f}'
            }
        
        # 计算交易数量（目标仓位5000港币）
        target_amount = 5000
        quantity = self.paper_trader.calculate_quantity(current_price, target_amount)
        
        if quantity == 0:
            return {
                'executed': False,
                'reason': f'Calculated quantity is 0 (price too high for minimum lot)'
            }
        
        # 风险检查
        risk_check = self.risk_manager.validate_trade(ticker, current_price, quantity)
        
        if not risk_check['approved']:
            return {
                'executed': False,
                'reason': f"Risk check failed: {', '.join(risk_check['reasons'])}"
            }
        
        # 使用风险管理器调整后的数量
        adjusted_quantity = risk_check['adjusted_quantity']
        
        print(f"\n🔥 Executing BUY order for {ticker}:")
        print(f"   Quantity: {adjusted_quantity} shares")
        print(f"   Price: {current_price:.2f} HKD")
        print(f"   Amount: {current_price * adjusted_quantity:.2f} HKD")
        
        # 执行交易
        order_result = self.paper_trader.place_order(
            ticker=ticker,
            side='buy',
            quantity=adjusted_quantity,
            price=current_price,
            signal_info=entry_analysis
        )
        
        if order_result['success']:
            # 记录到风险管理器
            self.risk_manager.record_trade(ticker)
            
            print(f"✅ Order executed successfully!")
            print(f"   Order ID: {order_result['order_id']}")
            print(f"   New cash balance: {order_result['new_cash_balance']:,.2f} HKD")
            
            return {
                'executed': True,
                'order_result': order_result,
                'risk_warnings': risk_check.get('warnings', [])
            }
        else:
            return {
                'executed': False,
                'reason': order_result['reason']
            }
    
    def show_portfolio(self):
        """显示投资组合状态"""
        summary = self.paper_trader.get_portfolio_summary()
        
        print(f"\n💼 Portfolio Summary:")
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
    
    def run_analysis(self, ticker: str):
        """运行完整的分析和交易流程"""
        print(f"🚀 Starting analysis for {ticker}")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 分析股票
        analysis = self.analyze_ticker(ticker)
        
        # 尝试执行交易
        trade_result = self.execute_trade_if_triggered(analysis)
        
        print(f"\n📋 Trade Decision:")
        if trade_result['executed']:
            print(f"   ✅ Trade executed successfully")
            if trade_result.get('risk_warnings'):
                print(f"   ⚠️  Warnings: {', '.join(trade_result['risk_warnings'])}")
        else:
            print(f"   ❌ No trade executed")
            print(f"   Reason: {trade_result['reason']}")
        
        # 显示投资组合状态
        self.show_portfolio()
        
        return {
            'analysis': analysis,
            'trade_result': trade_result
        }


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <ticker>")
        print("Example: python main.py 0700.HK")
        return
    
    ticker = sys.argv[1].upper()
    
    # 创建交易机器人实例
    bot = TradingBot()
    
    # 运行分析
    result = bot.run_analysis(ticker)
    
    print(f"\n🏁 Analysis completed for {ticker}")


if __name__ == "__main__":
    main()