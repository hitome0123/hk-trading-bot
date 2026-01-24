"""
Demo script to create favorable conditions and execute a trade
"""

import sys
import os
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from hk_trading_bot.modules.risk_gate import RiskManager
from hk_trading_bot.modules.execution_paper import PaperTrader


class DemoTradingBot:
    """演示用的交易机器人 - 创造有利条件以展示完整交易流程"""
    
    def __init__(self):
        self.risk_manager = RiskManager()
        self.paper_trader = PaperTrader("hk_trading_bot/data")
        print("🤖 Demo Trading Bot initialized")
        print(f"💰 Initial cash: {self.paper_trader.cash:,.2f} HKD")
    
    def create_favorable_conditions(self, ticker: str):
        """创造有利交易条件的数据"""
        # 设置种子以获得一致的结果
        np.random.seed(42)
        
        closes = []
        highs = []
        lows = []
        
        # 创造一个明确的下降趋势（前30天）
        base_price = 100
        for i in range(30):
            # 明显下降趋势
            price = base_price - (i * 1.2) + np.random.normal(0, 0.5)
            price = max(price, 50)
            
            closes.append(price)
            highs.append(price * 1.01)
            lows.append(price * 0.99)
        
        # 继续下跌到超卖区域（接下来20天）
        for i in range(20):
            # 继续下跌，创造RSI < 30的条件
            price = closes[-1] - np.random.uniform(0.3, 0.8)
            price = max(price, 45)
            
            closes.append(price)
            highs.append(price * 1.01)
            lows.append(price * 0.99)
        
        # 最后10天轻微反弹但保持超卖
        for i in range(10):
            # 轻微反弹，但仍在低位
            price = closes[-1] + np.random.uniform(-0.1, 0.3)
            price = max(price, 45)
            
            closes.append(price)
            highs.append(price * 1.01)
            lows.append(price * 0.99)
        
        # 设置当前价格略高于最后的收盘价
        current_price = closes[-1] + 1.0
        
        return {
            'close': closes,
            'high': highs,
            'low': lows
        }, current_price
    
    def demo_full_trading_cycle(self, ticker: str):
        """演示完整的交易周期"""
        print(f"\n🎬 Starting demo for {ticker}")
        print("=" * 60)
        
        # 1. 创造有利条件的数据
        price_data, current_price = self.create_favorable_conditions(ticker)
        print(f"📊 Using crafted market data for demonstration")
        print(f"💲 Current price: {current_price:.2f} HKD")
        
        # 2. 计算技术指标
        indicators = TechnicalIndicators.calculate_all_indicators(price_data)
        print(f"\n📈 Technical Indicators:")
        for name, value in indicators.items():
            if not np.isnan(value):
                print(f"   {name.upper()}: {value:.2f}")
        
        # 3. 计算入场策略
        entry_strategy = EntryStrategy()
        entry_analysis = entry_strategy.calculate_entry_price(current_price, indicators)
        
        print(f"\n🎯 Entry Analysis:")
        print(f"   Signal: {entry_analysis['signal']}")
        print(f"   Reason: {entry_analysis['reason']}")
        if entry_analysis['entry_price']:
            print(f"   Entry Price: {entry_analysis['entry_price']:.2f} HKD")
            discount_pct = ((current_price - entry_analysis['entry_price'])/current_price*100)
            print(f"   Discount from current: {discount_pct:.1f}%")
        
        # 4. 模拟价格下跌到入场点
        if entry_analysis['entry_price'] and entry_analysis['signal'] == 'LONG':
            simulated_buy_price = entry_analysis['entry_price'] - 0.10  # 稍微低一点确保触发
            print(f"\n📉 Market drops to {simulated_buy_price:.2f} HKD (below entry price)")
            
            # 5. 计算交易数量
            target_amount = 5000
            quantity = self.paper_trader.calculate_quantity(simulated_buy_price, target_amount)
            print(f"🔢 Calculated quantity: {quantity} shares (target: {target_amount} HKD)")
            
            # 6. 风险检查
            risk_check = self.risk_manager.validate_trade(ticker, simulated_buy_price, quantity)
            print(f"\n⚖️ Risk Check:")
            print(f"   Approved: {risk_check['approved']}")
            if not risk_check['approved']:
                print(f"   Reasons: {', '.join(risk_check['reasons'])}")
                return
            
            if risk_check.get('warnings'):
                print(f"   Warnings: {', '.join(risk_check['warnings'])}")
            
            # 7. 执行交易
            print(f"\n🔥 Executing BUY order:")
            print(f"   Ticker: {ticker}")
            print(f"   Quantity: {risk_check['adjusted_quantity']} shares")
            print(f"   Price: {simulated_buy_price:.2f} HKD")
            print(f"   Total Amount: {simulated_buy_price * risk_check['adjusted_quantity']:,.2f} HKD")
            
            order_result = self.paper_trader.place_order(
                ticker=ticker,
                side='buy',
                quantity=risk_check['adjusted_quantity'],
                price=simulated_buy_price,
                signal_info=entry_analysis
            )
            
            if order_result['success']:
                self.risk_manager.record_trade(ticker)
                print(f"✅ Trade executed successfully!")
                print(f"   Order ID: {order_result['order_id']}")
                print(f"   New cash balance: {order_result['new_cash_balance']:,.2f} HKD")
                
                # 8. 显示更新后的投资组合
                print(f"\n💼 Updated Portfolio:")
                summary = self.paper_trader.get_portfolio_summary()
                print(f"   Cash: {summary['cash']:,.2f} HKD")
                print(f"   Total Value: {summary['total_value']:,.2f} HKD")
                print(f"   P&L: {summary['pnl']:,.2f} HKD ({summary['pnl_pct']:.1f}%)")
                print(f"   Total Trades: {summary['total_trades']}")
                
                if summary['positions']:
                    print(f"\n📋 Current Positions:")
                    for pos_ticker, pos in summary['positions'].items():
                        print(f"   {pos_ticker}: {pos['quantity']} shares @ {pos['avg_price']:.2f} HKD")
                        print(f"      Value: {pos['current_value']:,.2f} HKD")
                
                # 9. 显示最近交易
                print(f"\n📜 Recent Trades:")
                recent_trades = self.paper_trader.get_recent_trades(3)
                for trade in recent_trades:
                    print(f"   {trade['timestamp'][:19]} - {trade['side'].upper()} {trade['quantity']} {trade['ticker']} @ {trade['price']:.2f}")
                
                print(f"\n🎉 Demo completed successfully!")
            else:
                print(f"❌ Trade failed: {order_result['reason']}")
        else:
            print(f"\n❌ No trade signal or invalid entry price")


def main():
    demo_bot = DemoTradingBot()
    
    # 演示几只不同的股票
    tickers = ['0700.HK', '0005.HK', '0941.HK']
    
    for ticker in tickers:
        demo_bot.demo_full_trading_cycle(ticker)
        print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()