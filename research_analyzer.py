#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research Report Analyzer
研究报告分析器

功能:
1. 获取券商研究报告 (WebSearch)
2. 基本面数据分析 (Futu API + OpenBB)
3. 目标价汇总
4. 投资评级汇总
5. 主力成本分析 (VWAP)
6. 技术指标分析 (OpenBB)
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import re

# Futu API
try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False

# OpenBB Client
try:
    from openbb_client import OpenBBClient
    HAS_OPENBB = True
except ImportError:
    HAS_OPENBB = False


class ResearchAnalyzer:
    """研究报告分析器"""

    def __init__(self, futu_host='127.0.0.1', futu_port=11111):
        """初始化"""
        self.futu_host = futu_host
        self.futu_port = futu_port
        self.quote_ctx = None
        self.openbb = None

        # 连接Futu (如果可用)
        if HAS_FUTU:
            try:
                self.quote_ctx = OpenQuoteContext(host=futu_host, port=futu_port)
                print(f"✅ 已连接Futu OpenD ({futu_host}:{futu_port})")
            except Exception as e:
                print(f"⚠️ 无法连接Futu OpenD: {e}")
                self.quote_ctx = None

        # 初始化OpenBB客户端
        if HAS_OPENBB:
            try:
                self.openbb = OpenBBClient()
                if self.openbb.health_check():
                    print("✅ 已连接OpenBB API")
                else:
                    self.openbb = None
            except Exception as e:
                self.openbb = None

    def __del__(self):
        """清理资源"""
        if self.quote_ctx:
            self.quote_ctx.close()

    def get_fundamental_data(self, code: str) -> Dict:
        """
        获取基本面数据 (Futu API)

        Args:
            code: 股票代码 (如 'HK.02382')

        Returns:
            基本面数据字典
        """
        if not self.quote_ctx:
            return {'error': 'Futu未连接'}

        try:
            # 获取实时行情快照
            ret, data = self.quote_ctx.get_market_snapshot([code])
            if ret != RET_OK:
                return {'error': f'获取行情失败: {data}'}

            if data.empty:
                return {'error': '无数据'}

            row = data.iloc[0]

            # 计算涨跌
            change_val = row['last_price'] - row['prev_close_price']
            change_rate = (change_val / row['prev_close_price']) * 100 if row['prev_close_price'] > 0 else 0

            # 获取20日K线计算VWAP
            vwap_20 = self._calculate_vwap(code, days=20)

            result = {
                'code': code,
                'name': row['name'],
                'last_price': round(row['last_price'], 2),
                'prev_close': round(row['prev_close_price'], 2),
                'change_val': round(change_val, 2),
                'change_rate': round(change_rate, 2),
                'volume': int(row['volume']),
                'turnover': round(row['turnover'], 2),
                'turnover_rate': round(row['turnover_rate'], 2),
                'pe_ttm': round(row['pe_ttm_ratio'], 2) if row['pe_ttm_ratio'] else None,
                'pb_ratio': round(row['pb_ratio'], 2) if row['pb_ratio'] else None,
                'vwap_20': round(vwap_20, 2) if vwap_20 else None,
                'vs_vwap': round(((row['last_price'] - vwap_20) / vwap_20 * 100), 2) if vwap_20 else None,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            return result

        except Exception as e:
            return {'error': f'获取基本面数据失败: {str(e)}'}

    def _calculate_vwap(self, code: str, days: int = 20) -> Optional[float]:
        """
        计算成交量加权平均价 (VWAP)

        Args:
            code: 股票代码
            days: 天数

        Returns:
            VWAP值
        """
        if not self.quote_ctx:
            return None

        try:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days+10)).strftime('%Y-%m-%d')

            # 获取K线数据 (注意: 返回3个值)
            ret_code, kline_data, page_req_key = self.quote_ctx.request_history_kline(
                code,
                start=start_date,
                end=end_date,
                ktype=KLType.K_DAY,
                autype=AuType.QFQ,
                max_count=days + 10
            )

            if ret_code != RET_OK or kline_data.empty:
                return None

            # 取最近N天
            recent = kline_data.tail(days)

            # VWAP = Σ(价格 × 成交量) / Σ成交量
            vwap = (recent['close'] * recent['volume']).sum() / recent['volume'].sum()

            return float(vwap)

        except Exception as e:
            print(f"⚠️ VWAP计算失败: {e}")
            return None

    def get_openbb_data(self, code: str) -> Dict:
        """
        从OpenBB获取补充数据

        Args:
            code: 股票代码 (如 'HK.02382')

        Returns:
            OpenBB数据字典
        """
        if not self.openbb:
            return {}

        try:
            # 获取技术指标
            technical = self.openbb.get_technical_summary(code)

            # 获取VWAP (如果Futu没有的话)
            vwap = self.openbb.calculate_vwap(code, days=20)

            # 获取报价 (用于补充数据)
            quote = self.openbb.get_quote(code)

            return {
                'technical': technical if 'error' not in technical else {},
                'vwap': vwap if 'error' not in vwap else {},
                'quote': quote if 'error' not in quote else {},
            }
        except Exception as e:
            return {'error': str(e)}

    def search_research_reports(self, stock_code: str, stock_name: str) -> str:
        """
        搜索券商研究报告

        注意: 此函数需要在Claude Code环境中使用WebSearch工具
        这里提供搜索查询模板

        Args:
            stock_code: 股票代码 (如 '02382')
            stock_name: 股票名称 (如 '舜宇光学')

        Returns:
            搜索查询字符串
        """
        # 提取纯数字代码
        code_num = stock_code.replace('HK.', '').replace('.HK', '')

        # 构建搜索查询
        queries = [
            f"{code_num}.HK {stock_name} 研究报告 券商",
            f"{stock_name} 投资评级 目标价 2026",
            f"{stock_name} 研究报告 PDF 大和 华兴 浦银",
        ]

        return " OR ".join(queries)

    def format_research_summary(self, fundamental: Dict, openbb_data: Dict = None, reports_info: str = "") -> str:
        """
        格式化研究报告摘要

        Args:
            fundamental: 基本面数据 (Futu)
            openbb_data: OpenBB补充数据
            reports_info: 研究报告信息 (WebSearch结果)

        Returns:
            格式化的报告
        """
        if 'error' in fundamental:
            return f"❌ 错误: {fundamental['error']}"

        openbb_data = openbb_data or {}
        output = []
        output.append("=" * 60)
        output.append(f"📊 研究报告分析 - {fundamental['name']} ({fundamental['code']})")
        output.append("=" * 60)
        output.append("")

        # 1. 实时行情
        output.append("【实时行情】")
        output.append(f"最新价: {fundamental['last_price']:.2f} HKD")
        change_emoji = "📈" if fundamental['change_val'] > 0 else "📉" if fundamental['change_val'] < 0 else "➡️"
        output.append(f"涨跌: {change_emoji} {fundamental['change_val']:+.2f} ({fundamental['change_rate']:+.2f}%)")
        output.append(f"成交量: {fundamental['volume']:,} 股")
        output.append(f"成交额: {fundamental['turnover']:,.2f} 万港元")
        output.append(f"换手率: {fundamental['turnover_rate']:.2f}%")

        # OpenBB 52周数据
        quote = openbb_data.get('quote', {})
        if quote.get('year_high') and quote.get('year_low'):
            output.append(f"52周范围: {quote['year_low']:.2f} - {quote['year_high']:.2f}")
        output.append("")

        # 2. 估值指标
        output.append("【估值指标】")
        if fundamental['pe_ttm']:
            output.append(f"PE(TTM): {fundamental['pe_ttm']:.2f}")
        if fundamental['pb_ratio']:
            output.append(f"PB: {fundamental['pb_ratio']:.2f}")
        output.append("")

        # 3. 主力成本分析
        vwap_20 = fundamental.get('vwap_20')
        vs_vwap = fundamental.get('vs_vwap')

        # 如果Futu没有VWAP，使用OpenBB的
        if not vwap_20 and openbb_data.get('vwap', {}).get('vwap'):
            vwap_20 = openbb_data['vwap']['vwap']
            vs_vwap = openbb_data['vwap'].get('vs_vwap_pct', 0)

        if vwap_20:
            output.append("【主力成本分析】(20日VWAP)")
            output.append(f"主力成本: {vwap_20:.2f} HKD")
            output.append(f"当前位置: {vs_vwap:+.2f}% vs 成本线")

            if vs_vwap < -3:
                output.append("💡 策略建议: 价格低于成本线3%+，可能是主力洗盘或散户恐慌")
            elif vs_vwap > 15:
                output.append("⚠️ 策略建议: 价格高于成本线15%+，警惕主力获利出货")
            elif vs_vwap > 5:
                output.append("📊 策略建议: 高于成本线5%+，观察主力动向")
            else:
                output.append("✅ 策略建议: 接近成本线，可考虑建仓")
            output.append("")

        # 4. 技术指标 (OpenBB)
        technical = openbb_data.get('technical', {})
        if technical and 'error' not in technical:
            output.append("【技术指标】(OpenBB)")

            # 均线
            ma_info = []
            if technical.get('ma_20'):
                ma_info.append(f"MA20: {technical['ma_20']:.2f}")
            if technical.get('ma_50'):
                ma_info.append(f"MA50: {technical['ma_50']:.2f}")
            if technical.get('ma_200'):
                ma_info.append(f"MA200: {technical['ma_200']:.2f}")
            if ma_info:
                output.append(" | ".join(ma_info))

            # RSI
            if technical.get('rsi_14'):
                rsi = technical['rsi_14']
                if rsi > 70:
                    rsi_status = "⚠️ 超买"
                elif rsi < 30:
                    rsi_status = "💡 超卖"
                else:
                    rsi_status = "正常"
                output.append(f"RSI(14): {rsi:.1f} {rsi_status}")

            # 趋势
            if technical.get('trend'):
                trend_map = {'bullish': '🟢 看涨', 'bearish': '🔴 看跌', 'neutral': '⚪ 震荡'}
                output.append(f"趋势判断: {trend_map.get(technical['trend'], technical['trend'])}")

            # 支撑阻力
            if technical.get('support') and technical.get('resistance'):
                output.append(f"支撑位: {technical['support']:.2f} | 阻力位: {technical['resistance']:.2f}")

            output.append("")

        # 5. 研究报告 (需要WebSearch结果)
        if reports_info:
            output.append("【券商研究报告】")
            output.append(reports_info)
            output.append("")
        else:
            output.append("【券商研究报告】")
            output.append("⚠️ 需要使用WebSearch工具搜索以下关键词:")
            search_query = self.search_research_reports(fundamental['code'], fundamental['name'])
            output.append(f"   {search_query}")
            output.append("")

        # 6. 数据来源
        sources = ["Futu OpenD"]
        if openbb_data:
            sources.append("OpenBB")
        output.append(f"📅 数据时间: {fundamental['update_time']} | 来源: {', '.join(sources)}")
        output.append("=" * 60)

        return "\n".join(output)

    def analyze(self, code: str, include_search_hint: bool = True) -> str:
        """
        完整分析流程

        Args:
            code: 股票代码 (如 'HK.02382' 或 '02382')
            include_search_hint: 是否包含搜索提示

        Returns:
            分析报告
        """
        # 统一代码格式
        if not code.startswith('HK.'):
            code = f'HK.{code}'

        # 获取基本面数据 (Futu)
        fundamental = self.get_fundamental_data(code)

        if 'error' in fundamental:
            return f"❌ 分析失败: {fundamental['error']}"

        # 获取OpenBB补充数据
        openbb_data = self.get_openbb_data(code)

        # 生成报告
        report = self.format_research_summary(fundamental, openbb_data)

        if include_search_hint:
            report += "\n\n💡 提示: 在Claude Code中使用WebSearch工具可自动获取券商研究报告"

        return report


def main():
    """CLI入口"""
    if len(sys.argv) < 2:
        print("用法: python research_analyzer.py <股票代码>")
        print("示例: python research_analyzer.py 02382")
        print("      python research_analyzer.py HK.02382")
        return

    code = sys.argv[1]

    # 创建分析器
    analyzer = ResearchAnalyzer()

    # 执行分析
    report = analyzer.analyze(code)
    print(report)


if __name__ == "__main__":
    main()
