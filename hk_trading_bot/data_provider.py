"""
Mock data provider for testing - Modified to create more trading opportunities
"""

import random
import numpy as np
from typing import Dict, List


class MockDataProvider:
    """模拟数据提供器 - 优化以创造更多交易机会"""
    
    @staticmethod
    def get_price_data(ticker: str, days: int = 60) -> Dict[str, List[float]]:
        """
        获取模拟价格数据
        
        Args:
            ticker: 股票代码
            days: 历史天数
        
        Returns:
            包含价格数据的字典
        """
        # 设置随机种子，使数据可重现
        random.seed(hash(ticker) % 1000)
        np.random.seed(hash(ticker) % 1000)
        
        # 生成基础价格（根据ticker生成不同的起始价格）
        base_price = 50 + (hash(ticker) % 100)
        
        prices = []
        highs = []
        lows = []
        closes = []
        
        current_price = base_price
        
        for i in range(days):
            # 生成每日价格变动 (-3% 到 +3%)
            daily_change = np.random.normal(0, 0.015)
            current_price = current_price * (1 + daily_change)
            
            # 确保价格不会太低
            current_price = max(current_price, 1.0)
            
            # 生成高低价
            daily_volatility = abs(np.random.normal(0, 0.01))
            high = current_price * (1 + daily_volatility)
            low = current_price * (1 - daily_volatility)
            
            prices.append(current_price)
            highs.append(high)
            lows.append(low)
            closes.append(current_price)
        
        return {
            'close': closes,
            'high': highs,
            'low': lows,
            'open': prices  # 简化处理
        }
    
    @staticmethod
    def get_current_price(ticker: str) -> float:
        """获取当前价格 - 稍微降低以触发买入信号"""
        # 获取最近的价格数据
        price_data = MockDataProvider.get_price_data(ticker, 1)
        base_price = price_data['close'][-1]
        
        # 为某些股票人为降低当前价格以创造交易机会
        if ticker in ['0700.HK', '0005.HK', '0941.HK']:
            # 降低2-5%以触发买入信号
            discount = 0.02 + (hash(ticker) % 30) / 1000  # 2% - 5%
            return base_price * (1 - discount)
        
        return base_price