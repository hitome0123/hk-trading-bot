"""
Risk management module
"""

from typing import Dict, Any, Optional
import datetime


class RiskManager:
    """风险控制模块"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化风险管理器
        
        Args:
            config: 风险控制配置
        """
        self.config = config or {
            'max_position_size': 10000,      # 最大单仓位金额 (HKD)
            'max_daily_trades': 5,           # 每日最大交易次数
            'max_portfolio_risk': 0.02,      # 组合最大风险比例 (2%)
            'min_price_threshold': 1.0,      # 最低价格阈值 (HKD)
            'max_price_threshold': 1000.0,   # 最高价格阈值 (HKD)
            'blacklist_tickers': [],         # 黑名单股票
            'trading_hours': {               # 交易时间
                'start': '09:30',
                'end': '16:00'
            }
        }
        
        # 记录今日交易次数
        self.daily_trades = {}
    
    def check_trading_hours(self) -> bool:
        """检查是否在交易时间内"""
        now = datetime.datetime.now()
        current_time = now.strftime('%H:%M')
        
        start_time = self.config['trading_hours']['start']
        end_time = self.config['trading_hours']['end']
        
        return start_time <= current_time <= end_time
    
    def check_ticker_validity(self, ticker: str) -> Dict[str, Any]:
        """检查股票代码有效性"""
        result = {
            'valid': True,
            'reason': ''
        }
        
        # 检查黑名单
        if ticker in self.config['blacklist_tickers']:
            result['valid'] = False
            result['reason'] = f'Ticker {ticker} is blacklisted'
            return result
        
        # 检查港股格式 (简化版)
        if not ticker.endswith('.HK'):
            result['valid'] = False
            result['reason'] = f'Invalid HK ticker format: {ticker}'
            return result
        
        return result
    
    def check_price_validity(self, price: float) -> Dict[str, Any]:
        """检查价格有效性"""
        result = {
            'valid': True,
            'reason': ''
        }
        
        if price < self.config['min_price_threshold']:
            result['valid'] = False
            result['reason'] = f'Price {price} below minimum threshold {self.config["min_price_threshold"]}'
            return result
        
        if price > self.config['max_price_threshold']:
            result['valid'] = False
            result['reason'] = f'Price {price} above maximum threshold {self.config["max_price_threshold"]}'
            return result
        
        return result
    
    def check_position_size(self, price: float, quantity: int) -> Dict[str, Any]:
        """检查仓位大小"""
        result = {
            'valid': True,
            'reason': '',
            'adjusted_quantity': quantity
        }
        
        position_value = price * quantity
        max_position = self.config['max_position_size']
        
        if position_value > max_position:
            # 自动调整数量
            adjusted_quantity = int(max_position / price)
            result['adjusted_quantity'] = adjusted_quantity
            result['reason'] = f'Position size adjusted from {quantity} to {adjusted_quantity} shares'
        
        return result
    
    def check_daily_trade_limit(self, ticker: str) -> Dict[str, Any]:
        """检查每日交易限制"""
        result = {
            'valid': True,
            'reason': ''
        }
        
        today = datetime.date.today().isoformat()
        
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
        
        if self.daily_trades[today] >= self.config['max_daily_trades']:
            result['valid'] = False
            result['reason'] = f'Daily trade limit ({self.config["max_daily_trades"]}) exceeded'
            return result
        
        return result
    
    def validate_trade(self, ticker: str, price: float, quantity: int) -> Dict[str, Any]:
        """
        综合风险检查
        
        Args:
            ticker: 股票代码
            price: 价格
            quantity: 数量
        
        Returns:
            验证结果字典
        """
        result = {
            'approved': True,
            'reasons': [],
            'adjusted_quantity': quantity,
            'warnings': []
        }
        
        # 1. 检查交易时间
        if not self.check_trading_hours():
            result['approved'] = False
            result['reasons'].append('Outside trading hours')
        
        # 2. 检查股票代码
        ticker_check = self.check_ticker_validity(ticker)
        if not ticker_check['valid']:
            result['approved'] = False
            result['reasons'].append(ticker_check['reason'])
        
        # 3. 检查价格
        price_check = self.check_price_validity(price)
        if not price_check['valid']:
            result['approved'] = False
            result['reasons'].append(price_check['reason'])
        
        # 4. 检查仓位大小
        size_check = self.check_position_size(price, quantity)
        result['adjusted_quantity'] = size_check['adjusted_quantity']
        if size_check['reason']:
            result['warnings'].append(size_check['reason'])
        
        # 5. 检查每日交易限制
        daily_check = self.check_daily_trade_limit(ticker)
        if not daily_check['valid']:
            result['approved'] = False
            result['reasons'].append(daily_check['reason'])
        
        return result
    
    def record_trade(self, ticker: str) -> None:
        """记录交易"""
        today = datetime.date.today().isoformat()
        
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
        
        self.daily_trades[today] += 1