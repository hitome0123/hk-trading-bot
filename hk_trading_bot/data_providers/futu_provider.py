"""
Futu OpenAPI data provider for Hong Kong stocks
富途 OpenAPI 数据提供器 - 专业港股行情数据
"""

import futu as ft
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd


class FutuProvider:
    """富途 OpenAPI 数据提供器 - 获取港股实时行情"""

    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        """
        初始化富途数据提供器

        Args:
            host: FutuOpenD 服务器地址（默认本地）
            port: FutuOpenD 端口（默认11111）

        注意：使用前需要先启动 FutuOpenD 客户端
        """
        self.host = host
        self.port = port
        self.quote_ctx = None
        self._is_connected = False

    def connect(self) -> bool:
        """连接到 FutuOpenD 服务"""
        try:
            if self.quote_ctx is None:
                self.quote_ctx = ft.OpenQuoteContext(host=self.host, port=self.port)
                print(f"✅ 成功连接到 FutuOpenD ({self.host}:{self.port})")
                self._is_connected = True
                return True
            return True
        except Exception as e:
            print(f"❌ 连接 FutuOpenD 失败: {e}")
            print(f"💡 提示: 请确保 FutuOpenD 客户端已启动")
            self._is_connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.quote_ctx:
            try:
                self.quote_ctx.close()
                print("✅ 已断开 FutuOpenD 连接")
            except Exception as e:
                print(f"⚠️ 断开连接时出错: {e}")
            finally:
                self.quote_ctx = None
                self._is_connected = False

    def _convert_ticker(self, ticker: str) -> str:
        """
        转换股票代码格式
        从 '1801.HK' 或 '01801.HK' 转换为 'HK.01801'
        """
        # 移除 .HK 后缀
        code = ticker.replace('.HK', '').replace('.hk', '')

        # 补齐到5位（港股代码标准格式）
        code = code.zfill(5)

        # 返回富途格式
        return f'HK.{code}'

    def _convert_ticker_back(self, futu_code: str) -> str:
        """
        转换回标准格式
        从 'HK.01801' 转换为 '1801.HK'
        """
        if futu_code.startswith('HK.'):
            code = futu_code.replace('HK.', '')
            # 移除前导零
            code = code.lstrip('0') or '0'
            return f'{code}.HK'
        return futu_code

    def get_price_data(self, ticker: str, days: int = 60) -> Dict[str, List[float]]:
        """
        获取股票历史价格数据

        Args:
            ticker: 股票代码（如 '1801.HK'）
            days: 获取天数（默认60天）

        Returns:
            包含 close, high, low, open 的字典
        """
        if not self._is_connected:
            if not self.connect():
                print(f"❌ 无法连接到 FutuOpenD，返回模拟数据")
                return self._generate_mock_data(ticker, days)

        try:
            futu_code = self._convert_ticker(ticker)

            # 计算开始和结束日期
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days+30)  # 多取一些以确保有足够数据

            # 获取K线数据（日K）
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                futu_code,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                ktype=ft.KLType.K_DAY,
                autype=ft.AuType.QFQ,  # 前复权
                max_count=days
            )

            if ret != ft.RET_OK:
                print(f"❌ 获取K线数据失败: {data}")
                return self._generate_mock_data(ticker, days)

            if data.empty:
                print(f"⚠️ {ticker} 没有历史数据")
                return self._generate_mock_data(ticker, days)

            # 转换为我们需要的格式
            price_data = {
                'close': data['close'].tolist(),
                'high': data['high'].tolist(),
                'low': data['low'].tolist(),
                'open': data['open'].tolist()
            }

            print(f"✅ 获取 {ticker} 的 {len(price_data['close'])} 天历史数据")
            return price_data

        except Exception as e:
            print(f"❌ 获取 {ticker} 数据时出错: {e}")
            return self._generate_mock_data(ticker, days)

    def get_current_price(self, ticker: str) -> float:
        """
        获取当前股票价格

        Args:
            ticker: 股票代码（如 '1801.HK'）

        Returns:
            当前价格
        """
        if not self._is_connected:
            if not self.connect():
                print(f"❌ 无法连接到 FutuOpenD")
                return 50.0

        try:
            futu_code = self._convert_ticker(ticker)

            # 订阅报价
            ret_sub, err_msg = self.quote_ctx.subscribe([futu_code], [ft.SubType.QUOTE], subscribe_push=False)
            if ret_sub != ft.RET_OK:
                print(f"⚠️ 订阅失败: {err_msg}")

            # 获取实时报价
            ret, data = self.quote_ctx.get_stock_quote([futu_code])

            if ret != ft.RET_OK:
                print(f"❌ 获取报价失败: {data}")
                return 50.0

            if data.empty:
                print(f"⚠️ {ticker} 没有报价数据")
                return 50.0

            # 获取最新价
            current_price = data['last_price'].iloc[0]
            print(f"✅ {ticker} 当前价格: {current_price:.2f} HKD")

            return float(current_price)

        except Exception as e:
            print(f"❌ 获取 {ticker} 当前价格时出错: {e}")
            return 50.0

    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        获取股票基本信息

        Args:
            ticker: 股票代码（如 '1801.HK'）

        Returns:
            股票基本信息字典
        """
        if not self._is_connected:
            if not self.connect():
                return self._default_stock_info(ticker)

        try:
            futu_code = self._convert_ticker(ticker)

            # 获取股票基本信息
            ret, data = self.quote_ctx.get_stock_basicinfo(ft.Market.HK, ft.SecurityType.STOCK, [futu_code])

            if ret != ft.RET_OK or data.empty:
                print(f"⚠️ 获取 {ticker} 基本信息失败")
                return self._default_stock_info(ticker)

            stock_info = data.iloc[0]

            # 获取实时报价以补充信息
            ret_quote, quote_data = self.quote_ctx.get_stock_quote([futu_code])

            result = {
                'symbol': ticker,
                'shortName': stock_info.get('name', ticker),
                'longName': stock_info.get('name', ''),
                'currency': 'HKD',
                'exchange': 'HKEX',
                'sector': stock_info.get('main_contract', 'Unknown'),
                'industry': 'Unknown',
                'last_updated': datetime.now().isoformat()
            }

            # 添加报价信息
            if ret_quote == ft.RET_OK and not quote_data.empty:
                quote = quote_data.iloc[0]
                result.update({
                    'current_price': quote.get('last_price'),
                    'previous_close': quote.get('prev_close_price'),
                    'day_high': quote.get('high_price'),
                    'day_low': quote.get('low_price'),
                    'volume': quote.get('volume'),
                    'market_cap': quote.get('market_val', 0),
                    'fifty_two_week_high': quote.get('high_price'),
                    'fifty_two_week_low': quote.get('low_price'),
                })

            print(f"✅ 获取 {ticker} 基本信息成功")
            return result

        except Exception as e:
            print(f"❌ 获取 {ticker} 股票信息时出错: {e}")
            return self._default_stock_info(ticker)

    def get_detailed_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        获取详细的股票分析数据

        Args:
            ticker: 股票代码（如 '1801.HK'）

        Returns:
            详细分析数据字典
        """
        try:
            # 获取历史数据
            price_data = self.get_price_data(ticker, days=252)  # 一年数据

            if not price_data or not price_data.get('close'):
                return {'error': 'No historical data available'}

            closes = np.array(price_data['close'])
            highs = np.array(price_data['high'])
            lows = np.array(price_data['low'])

            # 当前价格
            current_price = self.get_current_price(ticker)

            # 52周高低点
            week52_high = np.max(highs[-252:]) if len(highs) >= 252 else np.max(highs)
            week52_low = np.min(lows[-252:]) if len(lows) >= 252 else np.min(lows)

            # 价格位置
            price_position = (current_price - week52_low) / (week52_high - week52_low) if week52_high > week52_low else 0.5

            # 波动性分析
            returns = np.diff(closes) / closes[:-1]
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率

            return {
                'ticker': ticker,
                'current_price': current_price,
                'price_analysis': {
                    '52w_high': float(week52_high),
                    '52w_low': float(week52_low),
                    'price_position_pct': price_position * 100,
                    'distance_from_high_pct': (week52_high - current_price) / week52_high * 100,
                    'distance_from_low_pct': (current_price - week52_low) / week52_low * 100
                },
                'volatility_analysis': {
                    'annual_volatility': float(volatility),
                    'risk_level': 'High' if volatility > 0.3 else 'Medium' if volatility > 0.15 else 'Low'
                },
                'market_info': {
                    'currency': 'HKD',
                    'exchange': 'HKEX',
                    'data_source': 'Futu OpenAPI'
                },
                'analysis_timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ 详细分析时出错: {e}")
            return {'error': str(e)}

    def is_market_open(self) -> bool:
        """
        检查香港市场是否开盘

        Returns:
            True: 开盘中, False: 已收盘
        """
        try:
            import pytz
            hk_tz = pytz.timezone('Asia/Hong_Kong')
            now_hk = datetime.now(hk_tz)

            # 港股交易时间：周一至周五 09:30-12:00, 13:00-16:00
            if now_hk.weekday() >= 5:  # 周末
                return False

            time_now = now_hk.time()
            morning_open = datetime.strptime('09:30', '%H:%M').time()
            morning_close = datetime.strptime('12:00', '%H:%M').time()
            afternoon_open = datetime.strptime('13:00', '%H:%M').time()
            afternoon_close = datetime.strptime('16:00', '%H:%M').time()

            return (morning_open <= time_now <= morning_close) or (afternoon_open <= time_now <= afternoon_close)

        except ImportError:
            # 简化判断
            now = datetime.now()
            return 9 <= now.hour <= 16 and now.weekday() < 5

    def _generate_mock_data(self, ticker: str, days: int) -> Dict[str, List[float]]:
        """生成模拟数据作为备选"""
        np.random.seed(hash(ticker) % 1000)

        base_price = 50 + (hash(ticker) % 100)
        prices = []
        highs = []
        lows = []
        closes = []

        current_price = base_price

        for i in range(days):
            daily_change = np.random.normal(0, 0.02)
            current_price = current_price * (1 + daily_change)
            current_price = max(current_price, 1.0)

            daily_volatility = abs(np.random.normal(0, 0.01))
            high = current_price * (1 + daily_volatility)
            low = current_price * (1 - daily_volatility)

            prices.append(current_price)
            highs.append(high)
            lows.append(low)
            closes.append(current_price)

        print(f"⚠️ 使用模拟数据（{days}天）")
        return {
            'close': closes,
            'high': highs,
            'low': lows,
            'open': prices
        }

    def _default_stock_info(self, ticker: str) -> Dict[str, Any]:
        """默认股票信息"""
        return {
            'symbol': ticker,
            'shortName': ticker,
            'longName': '',
            'currency': 'HKD',
            'exchange': 'HKEX',
            'sector': 'Unknown',
            'industry': 'Unknown',
            'last_updated': datetime.now().isoformat()
        }

    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()
