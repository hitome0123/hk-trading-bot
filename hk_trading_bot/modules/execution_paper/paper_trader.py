"""
Paper trading execution module
"""

import datetime
import json
import os
from typing import Dict, Any, List, Optional
import uuid


class PaperTrader:
    """模拟交易执行器"""
    
    def __init__(self, data_dir: str = "data"):
        """
        初始化模拟交易器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir
        self.positions_file = os.path.join(data_dir, "positions.json")
        self.trades_file = os.path.join(data_dir, "trades.json")
        
        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)
        
        # 初始化持仓和交易记录
        self.positions = self._load_positions()
        self.trades = self._load_trades()
        
        # 初始资金
        self.initial_cash = 100000  # 10万港币
        self.cash = self._calculate_current_cash()
    
    def _load_positions(self) -> Dict[str, Any]:
        """加载持仓数据"""
        if os.path.exists(self.positions_file):
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading positions: {e}")
                return {}
        return {}
    
    def _load_trades(self) -> List[Dict[str, Any]]:
        """加载交易记录"""
        if os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading trades: {e}")
                return []
        return []
    
    def _save_positions(self) -> None:
        """保存持仓数据"""
        try:
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(self.positions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving positions: {e}")
    
    def _save_trades(self) -> None:
        """保存交易记录"""
        try:
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(self.trades, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving trades: {e}")
    
    def _calculate_current_cash(self) -> float:
        """计算当前现金余额"""
        total_invested = 0
        for trade in self.trades:
            if trade['side'] == 'buy':
                total_invested += trade['amount']
            else:  # sell
                total_invested -= trade['amount']
        
        return self.initial_cash - total_invested
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """获取组合摘要"""
        total_value = self.cash
        
        summary = {
            'cash': self.cash,
            'positions': {},
            'total_value': total_value,
            'total_trades': len(self.trades),
            'positions_count': len(self.positions)
        }
        
        # 计算每个持仓的当前价值（简化版，使用成本价）
        for ticker, position in self.positions.items():
            if position['quantity'] > 0:
                position_value = position['quantity'] * position['avg_price']
                total_value += position_value
                summary['positions'][ticker] = {
                    'quantity': position['quantity'],
                    'avg_price': position['avg_price'],
                    'current_value': position_value
                }
        
        summary['total_value'] = total_value
        summary['pnl'] = total_value - self.initial_cash
        summary['pnl_pct'] = (summary['pnl'] / self.initial_cash) * 100
        
        return summary
    
    def place_order(self, ticker: str, side: str, quantity: int, price: float, 
                   order_type: str = "market", signal_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        下单（模拟）
        
        Args:
            ticker: 股票代码
            side: 买卖方向 ('buy' 或 'sell')
            quantity: 数量
            price: 价格
            order_type: 订单类型
            signal_info: 信号信息
        
        Returns:
            订单执行结果
        """
        # 生成订单ID
        order_id = str(uuid.uuid4())[:8]
        
        # 计算交易金额
        amount = quantity * price
        
        # 检查资金是否足够（买入时）
        if side == 'buy' and amount > self.cash:
            return {
                'success': False,
                'order_id': order_id,
                'reason': f'Insufficient funds. Required: {amount:.2f}, Available: {self.cash:.2f}'
            }
        
        # 检查持仓是否足够（卖出时）
        if side == 'sell':
            current_position = self.positions.get(ticker, {}).get('quantity', 0)
            if quantity > current_position:
                return {
                    'success': False,
                    'order_id': order_id,
                    'reason': f'Insufficient position. Required: {quantity}, Available: {current_position}'
                }
        
        # 执行交易
        trade_record = {
            'order_id': order_id,
            'timestamp': datetime.datetime.now().isoformat(),
            'ticker': ticker,
            'side': side,
            'quantity': quantity,
            'price': price,
            'amount': amount,
            'order_type': order_type,
            'signal_info': signal_info or {}
        }
        
        # 更新持仓
        self._update_position(ticker, side, quantity, price)
        
        # 更新现金
        if side == 'buy':
            self.cash -= amount
        else:  # sell
            self.cash += amount
        
        # 记录交易
        self.trades.append(trade_record)
        
        # 保存数据
        self._save_positions()
        self._save_trades()
        
        return {
            'success': True,
            'order_id': order_id,
            'trade_record': trade_record,
            'new_cash_balance': self.cash
        }
    
    def _update_position(self, ticker: str, side: str, quantity: int, price: float) -> None:
        """更新持仓"""
        if ticker not in self.positions:
            self.positions[ticker] = {
                'quantity': 0,
                'avg_price': 0.0,
                'total_cost': 0.0
            }
        
        position = self.positions[ticker]
        
        if side == 'buy':
            # 买入：更新平均成本
            new_total_cost = position['total_cost'] + (quantity * price)
            new_quantity = position['quantity'] + quantity
            
            if new_quantity > 0:
                position['avg_price'] = new_total_cost / new_quantity
            else:
                position['avg_price'] = price
            
            position['quantity'] = new_quantity
            position['total_cost'] = new_total_cost
            
        else:  # sell
            # 卖出：减少持仓
            position['quantity'] -= quantity
            
            if position['quantity'] <= 0:
                # 清仓
                position['quantity'] = 0
                position['avg_price'] = 0.0
                position['total_cost'] = 0.0
            else:
                # 部分卖出，保持平均成本不变，但总成本按比例减少
                remaining_ratio = position['quantity'] / (position['quantity'] + quantity)
                position['total_cost'] *= remaining_ratio
    
    def get_position(self, ticker: str) -> Dict[str, Any]:
        """获取特定股票的持仓信息"""
        return self.positions.get(ticker, {
            'quantity': 0,
            'avg_price': 0.0,
            'total_cost': 0.0
        })
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的交易记录"""
        return self.trades[-limit:] if len(self.trades) > limit else self.trades
    
    def calculate_quantity(self, price: float, target_amount: float) -> int:
        """根据目标金额计算购买数量（港股最小单位100股）"""
        if price <= 0:
            return 0
        quantity = int(target_amount / price)
        # 港股以100股为一手
        return max((quantity // 100) * 100, 100)  # 至少买100股