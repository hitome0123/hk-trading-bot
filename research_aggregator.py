#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
研报聚合器 - 多券商目标价抓取
Research Aggregator - Multi-broker Target Price Fetcher

功能:
1. 从多个来源聚合券商研究报告
2. 汇总目标价和投资评级
3. 计算共识目标价和上涨空间
4. 支持港股、A股、美股

数据来源:
- 阿斯达克 (aastocks.com) - 港股研报
- 东方财富 (eastmoney.com) - A股/港股研报
- TipRanks (tipranks.com) - 美股评级
- 雪球 (xueqiu.com) - 研报讨论

用法:
    python research_aggregator.py 09988      # 阿里巴巴
    python research_aggregator.py AAPL       # 苹果
    python research_aggregator.py 600519     # 贵州茅台
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# 添加项目路径
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False


class Rating(Enum):
    """投资评级"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    HOLD = "持有"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"
    UNKNOWN = "未知"


@dataclass
class BrokerReport:
    """券商研报"""
    broker: str              # 券商名称
    analyst: str             # 分析师
    rating: str              # 评级
    target_price: float      # 目标价
    currency: str            # 货币
    date: str                # 发布日期
    title: str               # 报告标题
    source: str              # 来源
    url: str = ""            # 链接


@dataclass
class ConsensusData:
    """共识数据"""
    stock_code: str
    stock_name: str
    current_price: float
    currency: str

    # 共识目标价
    consensus_target: float
    target_high: float
    target_low: float
    upside_pct: float

    # 评级分布
    buy_count: int
    hold_count: int
    sell_count: int
    total_reports: int

    # 明细
    reports: List[BrokerReport]

    # 元数据
    update_time: str


class ResearchAggregator:
    """研报聚合器"""

    # 主要券商列表
    TOP_BROKERS = {
        'HK': [
            '高盛', '摩根士丹利', '瑞银', '花旗', '汇丰',
            '美银美林', '摩根大通', '德银', '大和', '野村',
            '中金', '中信', '华兴', '招银国际', '浦银国际',
            '国泰君安', '申万宏源', '建银国际', '光大', '海通国际',
        ],
        'US': [
            'Goldman Sachs', 'Morgan Stanley', 'UBS', 'Citigroup',
            'JP Morgan', 'Bank of America', 'Deutsche Bank',
            'Barclays', 'Credit Suisse', 'Wells Fargo',
        ],
        'CN': [
            '中金公司', '中信证券', '国泰君安', '华泰证券', '海通证券',
            '招商证券', '申万宏源', '广发证券', '国信证券', '长江证券',
        ]
    }

    # 评级映射
    RATING_MAP = {
        # 买入类
        '强烈买入': Rating.STRONG_BUY, '强买': Rating.STRONG_BUY,
        'strong buy': Rating.STRONG_BUY, 'conviction buy': Rating.STRONG_BUY,
        '买入': Rating.BUY, 'buy': Rating.BUY, '推荐': Rating.BUY,
        'outperform': Rating.BUY, '跑赢大市': Rating.BUY,
        'overweight': Rating.BUY, '增持': Rating.BUY,
        # 持有类
        '持有': Rating.HOLD, 'hold': Rating.HOLD, 'neutral': Rating.HOLD,
        '中性': Rating.HOLD, 'equal-weight': Rating.HOLD,
        'market perform': Rating.HOLD, '与大市同步': Rating.HOLD,
        # 卖出类
        '卖出': Rating.SELL, 'sell': Rating.SELL, '减持': Rating.SELL,
        'underperform': Rating.SELL, '跑输大市': Rating.SELL,
        'underweight': Rating.SELL,
        '强烈卖出': Rating.STRONG_SELL, 'strong sell': Rating.STRONG_SELL,
    }

    def __init__(self, futu_host='127.0.0.1', futu_port=11111):
        self.futu_host = futu_host
        self.futu_port = futu_port
        self.quote_ctx = None
        self.cache_dir = os.path.expanduser('~/.hk-trading-bot/research_cache')
        os.makedirs(self.cache_dir, exist_ok=True)

        # 连接Futu
        if HAS_FUTU:
            try:
                self.quote_ctx = OpenQuoteContext(host=futu_host, port=futu_port)
            except:
                pass

    def __del__(self):
        if self.quote_ctx:
            self.quote_ctx.close()

    def get_market_type(self, code: str) -> str:
        """判断市场类型"""
        if code.isdigit():
            if len(code) == 5:  # 港股
                return 'HK'
            elif len(code) == 6:  # A股
                return 'CN'
        else:
            return 'US'  # 美股
        return 'HK'

    def normalize_code(self, code: str, market: str = None) -> str:
        """标准化代码"""
        code = code.upper().strip()
        code = code.replace('HK.', '').replace('.HK', '')
        code = code.replace('SH.', '').replace('.SH', '')
        code = code.replace('SZ.', '').replace('.SZ', '')

        if not market:
            market = self.get_market_type(code)

        if market == 'HK':
            return f"HK.{code.zfill(5)}"
        elif market == 'CN':
            prefix = 'SH' if code.startswith('6') else 'SZ'
            return f"{prefix}.{code}"
        else:
            return code  # 美股直接返回

    def parse_rating(self, rating_text: str) -> Rating:
        """解析评级文本"""
        rating_text = rating_text.lower().strip()
        for key, value in self.RATING_MAP.items():
            if key.lower() in rating_text:
                return value
        return Rating.UNKNOWN

    def get_current_price(self, code: str) -> Tuple[float, str]:
        """获取当前价格"""
        if not self.quote_ctx:
            return 0.0, 'HKD'

        try:
            ret, data = self.quote_ctx.get_market_snapshot([code])
            if ret == RET_OK and len(data) > 0:
                row = data.iloc[0]
                # 判断货币
                if code.startswith('HK.'):
                    currency = 'HKD'
                elif code.startswith('SH.') or code.startswith('SZ.'):
                    currency = 'CNY'
                else:
                    currency = 'USD'
                return float(row['last_price']), currency
        except:
            pass
        return 0.0, 'HKD'

    def get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        if not self.quote_ctx:
            return code

        try:
            ret, data = self.quote_ctx.get_market_snapshot([code])
            if ret == RET_OK and len(data) > 0:
                return data.iloc[0]['name']
        except:
            pass
        return code

    def build_search_queries(self, code: str, name: str, market: str) -> List[str]:
        """构建搜索查询"""
        code_num = code.split('.')[-1]

        queries = []

        if market == 'HK':
            queries.extend([
                f"{code_num}.HK {name} 研究报告 目标价 2026",
                f"{name} 券商评级 目标价位 买入",
                f"{code_num} 港股 分析师 投资评级",
                f"site:aastocks.com {code_num} 研究报告",
            ])
        elif market == 'CN':
            queries.extend([
                f"{name} 研究报告 目标价 券商",
                f"{code_num} 个股研报 投资评级",
                f"site:eastmoney.com {code_num} 研报",
            ])
        else:  # US
            queries.extend([
                f"{code} stock analyst rating target price 2026",
                f"{code} Wall Street consensus price target",
                f"site:tipranks.com {code}",
            ])

        return queries

    def calculate_consensus(self, reports: List[BrokerReport],
                           current_price: float) -> Dict:
        """计算共识数据"""
        if not reports:
            return {
                'consensus_target': 0,
                'target_high': 0,
                'target_low': 0,
                'upside_pct': 0,
                'buy_count': 0,
                'hold_count': 0,
                'sell_count': 0,
            }

        # 筛选有效目标价
        valid_targets = [r.target_price for r in reports if r.target_price > 0]

        # 统计评级
        buy_count = sum(1 for r in reports if self.parse_rating(r.rating) in
                       [Rating.STRONG_BUY, Rating.BUY])
        hold_count = sum(1 for r in reports if self.parse_rating(r.rating) == Rating.HOLD)
        sell_count = sum(1 for r in reports if self.parse_rating(r.rating) in
                        [Rating.SELL, Rating.STRONG_SELL])

        if valid_targets:
            consensus = sum(valid_targets) / len(valid_targets)
            upside = ((consensus - current_price) / current_price * 100) if current_price > 0 else 0
        else:
            consensus = 0
            upside = 0

        return {
            'consensus_target': round(consensus, 2),
            'target_high': max(valid_targets) if valid_targets else 0,
            'target_low': min(valid_targets) if valid_targets else 0,
            'upside_pct': round(upside, 2),
            'buy_count': buy_count,
            'hold_count': hold_count,
            'sell_count': sell_count,
        }

    def format_report(self, data: ConsensusData) -> str:
        """格式化报告输出"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"📊 研报聚合 - {data.stock_name} ({data.stock_code})")
        lines.append("=" * 70)
        lines.append("")

        # 当前价格
        lines.append(f"💰 当前价格: {data.current_price:.2f} {data.currency}")
        lines.append("")

        # 共识目标价
        lines.append("【共识目标价】")
        if data.consensus_target > 0:
            upside_emoji = "📈" if data.upside_pct > 0 else "📉"
            lines.append(f"  平均目标价: {data.consensus_target:.2f} {data.currency}")
            lines.append(f"  目标区间: {data.target_low:.2f} - {data.target_high:.2f}")
            lines.append(f"  潜在空间: {upside_emoji} {data.upside_pct:+.1f}%")
        else:
            lines.append("  暂无目标价数据")
        lines.append("")

        # 评级分布
        lines.append("【评级分布】")
        total = data.buy_count + data.hold_count + data.sell_count
        if total > 0:
            buy_pct = data.buy_count / total * 100
            hold_pct = data.hold_count / total * 100
            sell_pct = data.sell_count / total * 100

            lines.append(f"  🟢 买入: {data.buy_count} ({buy_pct:.0f}%)")
            lines.append(f"  🟡 持有: {data.hold_count} ({hold_pct:.0f}%)")
            lines.append(f"  🔴 卖出: {data.sell_count} ({sell_pct:.0f}%)")
            lines.append(f"  📊 共识: {'看多' if buy_pct > 50 else '看空' if sell_pct > 50 else '中性'}")
        else:
            lines.append("  暂无评级数据")
        lines.append("")

        # 研报明细
        if data.reports:
            lines.append("【近期研报】")
            for i, report in enumerate(data.reports[:10], 1):
                rating_emoji = "🟢" if "买" in report.rating or "buy" in report.rating.lower() else "🟡"
                target_str = f"目标价 {report.target_price:.2f}" if report.target_price > 0 else ""
                lines.append(f"  {i}. [{report.broker}] {rating_emoji}{report.rating} {target_str}")
                if report.title:
                    lines.append(f"     {report.title[:40]}...")
                lines.append(f"     📅 {report.date} | 来源: {report.source}")
            lines.append("")

        # 投资建议
        lines.append("【投资建议】")
        if data.upside_pct > 20:
            lines.append("  🚀 共识看涨超过20%，关注买入机会")
        elif data.upside_pct > 10:
            lines.append("  📈 共识看涨10-20%，可考虑逢低买入")
        elif data.upside_pct > 0:
            lines.append("  ➡️ 共识温和看涨，持有观察")
        elif data.upside_pct > -10:
            lines.append("  ⚠️ 共识目标价接近现价，谨慎操作")
        else:
            lines.append("  🔻 共识看跌，建议回避或减仓")

        lines.append("")
        lines.append(f"📅 更新时间: {data.update_time}")
        lines.append("")
        lines.append("💡 提示: 使用 Claude WebSearch 可获取更多券商研报")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_search_hint(self, code: str, name: str) -> str:
        """获取搜索提示"""
        market = self.get_market_type(code.split('.')[-1])
        queries = self.build_search_queries(code, name, market)

        return f"""
🔍 推荐搜索查询 (用于 WebSearch 工具):

1. {queries[0]}
2. {queries[1]}
3. {queries[2]}

或者直接问 Claude:
"帮我搜索 {name} 的最新券商研究报告和目标价"
"""

    def analyze(self, code: str) -> str:
        """分析股票研报"""
        # 标准化代码
        normalized_code = self.normalize_code(code)
        market = self.get_market_type(code)

        # 获取当前价格和名称
        current_price, currency = self.get_current_price(normalized_code)
        stock_name = self.get_stock_name(normalized_code)

        # 由于没有直接API,返回搜索提示
        # 真实数据需要通过 WebSearch 获取

        output = []
        output.append("=" * 70)
        output.append(f"📊 研报聚合 - {stock_name} ({normalized_code})")
        output.append("=" * 70)
        output.append("")

        if current_price > 0:
            output.append(f"💰 当前价格: {current_price:.2f} {currency}")
        else:
            output.append("⚠️ 无法获取实时价格 (请确保 Futu OpenD 运行中)")

        output.append("")
        output.append("【数据获取】")
        output.append("  由于券商研报数据需要爬取,请使用以下方式获取:")
        output.append("")
        output.append(self.get_search_hint(normalized_code, stock_name))

        return "\n".join(output)


def main():
    """CLI入口"""
    if len(sys.argv) < 2:
        print("""
研报聚合器 - 多券商目标价抓取

用法:
  python research_aggregator.py <股票代码>

示例:
  python research_aggregator.py 09988      # 阿里巴巴 (港股)
  python research_aggregator.py 600519     # 贵州茅台 (A股)
  python research_aggregator.py AAPL       # 苹果 (美股)

功能:
  - 聚合多家券商目标价
  - 计算共识目标价
  - 评级分布统计
  - 投资建议生成
        """)
        return

    code = sys.argv[1]

    aggregator = ResearchAggregator()
    report = aggregator.analyze(code)
    print(report)


if __name__ == "__main__":
    main()
