#!/usr/bin/env python3
"""
港股日内动量扫描器 - 追涨回调策略
找出正在上涨且有回调买点的股票

用法: python momentum_scanner.py
"""

import sys
import os
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import yfinance as yf
except ImportError:
    print("请先安装 yfinance: pip install yfinance")
    sys.exit(1)


@dataclass
class MomentumSignal:
    """动量信号"""
    ticker: str
    name: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float

    # 涨跌幅
    change_pct: float          # 今日涨跌幅
    from_high_pct: float       # 距日内高点回调幅度
    from_low_pct: float        # 距日内低点涨幅

    # 成交量
    volume: int
    avg_volume: int
    volume_ratio: float        # 量比

    # 信号
    signal: str                # 'BUY', 'WAIT', 'AVOID'
    signal_strength: int       # 1-5
    reasons: List[str]


class MomentumScanner:
    """动量扫描器"""

    # 港股热门股票池
    WATCHLIST = [
        # 科技
        ('0700.HK', '腾讯'),
        ('9988.HK', '阿里巴巴'),
        ('9888.HK', '百度'),
        ('1810.HK', '小米'),
        ('9618.HK', '京东'),
        ('3690.HK', '美团'),
        ('9999.HK', '网易'),

        # 半导体/芯片
        ('0981.HK', '中芯国际'),
        ('1347.HK', '华虹半导体'),
        ('2388.HK', '中银香港'),

        # 医药
        ('6160.HK', '百济神州'),
        ('1801.HK', '信达生物'),
        ('2269.HK', '药明生物'),
        ('9995.HK', '荣昌生物'),
        ('1093.HK', '石药集团'),
        ('9969.HK', '诺诚健华'),
        ('1177.HK', '中国生物制药'),

        # 新能源/汽车
        ('9866.HK', '蔚来'),
        ('9868.HK', '小鹏'),
        ('2015.HK', '理想汽车'),
        ('1211.HK', '比亚迪'),
        ('0175.HK', '吉利汽车'),

        # 金融
        ('0005.HK', '汇丰'),
        ('1398.HK', '工商银行'),
        ('3988.HK', '中国银行'),
        ('2318.HK', '平安保险'),
        ('0388.HK', '港交所'),

        # 消费
        ('9633.HK', '农夫山泉'),
        ('2331.HK', '李宁'),
        ('1919.HK', '中远海控'),
        ('0027.HK', '银河娱乐'),
    ]

    def __init__(self):
        self.results: List[MomentumSignal] = []

    def fetch_stock_data(self, ticker: str) -> Optional[Dict]:
        """获取股票数据"""
        try:
            stock = yf.Ticker(ticker)

            # 获取今日数据
            hist = stock.history(period='5d', interval='1d')
            if hist.empty or len(hist) < 2:
                return None

            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]

            # 计算平均成交量（5日）
            avg_volume = int(hist['Volume'].mean())

            return {
                'open': float(today['Open']),
                'high': float(today['High']),
                'low': float(today['Low']),
                'close': float(today['Close']),
                'volume': int(today['Volume']),
                'prev_close': float(yesterday['Close']),
                'avg_volume': avg_volume
            }
        except Exception as e:
            return None

    def analyze_momentum(self, ticker: str, name: str, data: Dict) -> MomentumSignal:
        """分析动量信号"""
        current = data['close']
        open_price = data['open']
        high = data['high']
        low = data['low']
        prev_close = data['prev_close']
        volume = data['volume']
        avg_volume = data['avg_volume']

        # 计算指标
        change_pct = (current - prev_close) / prev_close * 100
        from_high_pct = (high - current) / high * 100 if high > 0 else 0
        from_low_pct = (current - low) / low * 100 if low > 0 else 0
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1

        # 生成信号
        signal, strength, reasons = self._generate_signal(
            change_pct, from_high_pct, from_low_pct,
            volume_ratio, current, open_price, high, low
        )

        return MomentumSignal(
            ticker=ticker,
            name=name,
            current_price=current,
            open_price=open_price,
            high_price=high,
            low_price=low,
            prev_close=prev_close,
            change_pct=change_pct,
            from_high_pct=from_high_pct,
            from_low_pct=from_low_pct,
            volume=volume,
            avg_volume=avg_volume,
            volume_ratio=volume_ratio,
            signal=signal,
            signal_strength=strength,
            reasons=reasons
        )

    def _generate_signal(
        self,
        change_pct: float,
        from_high_pct: float,
        from_low_pct: float,
        volume_ratio: float,
        current: float,
        open_price: float,
        high: float,
        low: float
    ) -> tuple:
        """生成交易信号"""
        reasons = []
        score = 0

        # 1. 涨幅条件：2-5%最佳
        if 2 <= change_pct <= 5:
            score += 2
            reasons.append(f'涨幅{change_pct:.1f}%，动量适中')
        elif 1 <= change_pct < 2:
            score += 1
            reasons.append(f'涨幅{change_pct:.1f}%，动量较弱')
        elif 5 < change_pct <= 8:
            score += 1
            reasons.append(f'涨幅{change_pct:.1f}%，偏高但可追')
        elif change_pct > 8:
            score -= 1
            reasons.append(f'涨幅{change_pct:.1f}%，追高风险大')
        elif change_pct < 0:
            score -= 2
            reasons.append(f'下跌{change_pct:.1f}%，不适合追涨')
        else:
            reasons.append(f'涨幅{change_pct:.1f}%，动量不足')

        # 2. 回调条件：0.3-1%最佳
        if 0.3 <= from_high_pct <= 1.0:
            score += 2
            reasons.append(f'回调{from_high_pct:.1f}%，理想买点')
        elif 0 < from_high_pct < 0.3:
            score += 1
            reasons.append(f'回调{from_high_pct:.1f}%，接近高点')
        elif 1.0 < from_high_pct <= 2.0:
            score += 1
            reasons.append(f'回调{from_high_pct:.1f}%，回调稍深')
        elif from_high_pct > 2.0:
            score -= 1
            reasons.append(f'回调{from_high_pct:.1f}%，动量可能衰竭')
        else:
            reasons.append(f'正在创新高')

        # 3. 量比条件
        if volume_ratio >= 2:
            score += 2
            reasons.append(f'量比{volume_ratio:.1f}，放量明显')
        elif volume_ratio >= 1.5:
            score += 1
            reasons.append(f'量比{volume_ratio:.1f}，温和放量')
        elif volume_ratio >= 1:
            reasons.append(f'量比{volume_ratio:.1f}，成交正常')
        else:
            score -= 1
            reasons.append(f'量比{volume_ratio:.1f}，缩量')

        # 4. 价格位置：高于开盘价
        if current > open_price:
            score += 1
            reasons.append('价格高于开盘，日内趋势向上')
        else:
            score -= 1
            reasons.append('价格低于开盘，日内偏弱')

        # 5. 振幅检查
        amplitude = (high - low) / low * 100 if low > 0 else 0
        if amplitude > 5:
            reasons.append(f'振幅{amplitude:.1f}%，波动大')

        # 生成信号
        if score >= 5:
            signal = 'BUY'
            strength = 5
        elif score >= 4:
            signal = 'BUY'
            strength = 4
        elif score >= 3:
            signal = 'BUY'
            strength = 3
        elif score >= 2:
            signal = 'WAIT'
            strength = 2
        else:
            signal = 'AVOID'
            strength = 1

        return signal, strength, reasons

    def scan(self, watchlist: List[tuple] = None) -> List[MomentumSignal]:
        """扫描股票池"""
        if watchlist is None:
            watchlist = self.WATCHLIST

        self.results = []
        total = len(watchlist)

        print(f"\n🔍 扫描 {total} 只股票...")

        for i, (ticker, name) in enumerate(watchlist, 1):
            print(f"\r   扫描进度: {i}/{total} - {ticker}", end="", flush=True)

            data = self.fetch_stock_data(ticker)
            if data:
                signal = self.analyze_momentum(ticker, name, data)
                self.results.append(signal)

            # 避免请求过快
            time.sleep(0.3)

        print(f"\r   扫描完成: {len(self.results)}/{total} 只股票有数据")

        # 按信号强度和涨幅排序
        self.results.sort(key=lambda x: (-x.signal_strength, -x.change_pct))

        return self.results

    def print_results(self):
        """打印扫描结果"""
        if not self.results:
            print("\n❌ 没有扫描结果")
            return

        print(f"\n{'='*80}")
        print(f"📊 日内动量扫描结果 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}")

        # 分类显示
        buy_signals = [r for r in self.results if r.signal == 'BUY']
        wait_signals = [r for r in self.results if r.signal == 'WAIT']

        if buy_signals:
            print(f"\n🟢 买入信号 ({len(buy_signals)}只)")
            print("-" * 80)
            print(f"{'股票':<12} {'名称':<8} {'现价':>8} {'涨幅':>8} {'回调':>8} {'量比':>6} {'强度':>4}")
            print("-" * 80)

            for s in buy_signals:
                stars = '★' * s.signal_strength + '☆' * (5 - s.signal_strength)
                print(f"{s.ticker:<12} {s.name:<8} {s.current_price:>8.2f} {s.change_pct:>+7.1f}% {s.from_high_pct:>7.1f}% {s.volume_ratio:>6.1f} {stars}")

        if wait_signals:
            print(f"\n🟡 观望信号 ({len(wait_signals)}只)")
            print("-" * 80)
            for s in wait_signals[:10]:  # 只显示前10个
                print(f"{s.ticker:<12} {s.name:<8} {s.current_price:>8.2f} {s.change_pct:>+7.1f}% {s.from_high_pct:>7.1f}% {s.volume_ratio:>6.1f}")

        # 打印最佳机会详情
        if buy_signals:
            print(f"\n{'='*80}")
            print("⭐ 最佳追涨回调机会")
            print(f"{'='*80}")

            for i, s in enumerate(buy_signals[:3], 1):
                print(f"\n#{i} {s.ticker} {s.name}")
                print(f"   现价: {s.current_price:.2f} | 涨幅: {s.change_pct:+.1f}% | 回调: {s.from_high_pct:.1f}%")
                print(f"   日内: 开{s.open_price:.2f} 高{s.high_price:.2f} 低{s.low_price:.2f}")
                print(f"   量比: {s.volume_ratio:.1f}x | 成交: {s.volume:,}")
                print(f"   信号强度: {'★' * s.signal_strength}{'☆' * (5-s.signal_strength)}")
                print(f"   分析:")
                for reason in s.reasons:
                    print(f"      • {reason}")

                # 计算建议点位
                entry = s.current_price
                stop_loss = s.low_price * 0.995  # 跌破日内低点止损
                take_profit = s.high_price * 1.002  # 突破日内高点止盈

                print(f"\n   📍 建议点位:")
                print(f"      买入: {entry:.2f} (现价)")
                print(f"      止损: {stop_loss:.2f} (跌破日低)")
                print(f"      止盈: {take_profit:.2f} (破日高)")
                risk = (entry - stop_loss) / entry * 100
                reward = (take_profit - entry) / entry * 100
                print(f"      风险: {risk:.1f}% | 收益: {reward:.1f}%")

        # 操作建议
        print(f"\n{'='*80}")
        print("📝 操作建议")
        print("-" * 80)
        print("1. 选择涨幅2-5%、回调0.3-1%、量比>1.5的股票")
        print("2. 等价格企稳（1-2分钟不再创新低）再买入")
        print("3. 止损设在日内低点下方，止盈设在日内高点上方")
        print("4. 快进快出，目标0.5-1%，不贪心")
        print("5. 单笔仓位控制在总资金5%以内")
        print(f"{'='*80}\n")


def main():
    print(f"🚀 港股日内动量扫描器")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📈 策略: 追涨回调")

    scanner = MomentumScanner()
    scanner.scan()
    scanner.print_results()


if __name__ == "__main__":
    main()
