#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Research Analyzer with WebSearch Integration
适用于Claude Code环境，自动搜索券商研究报告

用法:
  在Claude Code中调用:
  - "帮我分析 02382 的基本面和研究报告"
  - "查看 舜宇光学 的券商研究报告"
"""

import sys
import os
from research_analyzer import ResearchAnalyzer


def analyze_with_websearch(stock_code: str, stock_name: str = None) -> dict:
    """
    使用WebSearch自动获取研究报告 (需要在Claude Code环境中调用)

    Args:
        stock_code: 股票代码 (如 '02382' 或 'HK.02382')
        stock_name: 股票名称 (如 '舜宇光学'，可选)

    Returns:
        分析结果字典，包含:
        - fundamental: 基本面数据
        - search_query: WebSearch查询字符串
        - report_hint: 报告搜索提示
    """
    # 创建分析器
    analyzer = ResearchAnalyzer()

    # 统一代码格式
    if not stock_code.startswith('HK.'):
        stock_code = f'HK.{stock_code}'

    # 获取基本面数据
    fundamental = analyzer.get_fundamental_data(stock_code)

    if 'error' in fundamental:
        return {
            'error': fundamental['error'],
            'fundamental': None,
            'search_query': None
        }

    # 使用实际的股票名称
    if not stock_name:
        stock_name = fundamental['name']

    # 生成搜索查询
    search_query = analyzer.search_research_reports(stock_code, stock_name)

    return {
        'fundamental': fundamental,
        'stock_name': stock_name,
        'search_query': search_query,
        'report_hint': f"""
📌 WebSearch 查询建议:

1. 券商研究报告:
   "{search_query}"

2. 目标价汇总:
   "{stock_name} 目标价 2026 大和 华兴 浦银 国盛"

3. 最新评级:
   "{stock_name} 投资评级 买入 增持 2026年2月"

💡 提示: 在Claude Code中使用WebSearch工具可自动获取这些信息
"""
    }


def format_complete_report(result: dict, websearch_results: str = None) -> str:
    """
    格式化完整报告

    Args:
        result: analyze_with_websearch的返回结果
        websearch_results: WebSearch工具的搜索结果 (可选)

    Returns:
        格式化的完整报告
    """
    if 'error' in result:
        return f"❌ 错误: {result['error']}"

    fundamental = result['fundamental']
    analyzer = ResearchAnalyzer()

    # 基础报告
    if websearch_results:
        report = analyzer.format_research_summary(fundamental, websearch_results)
    else:
        report = analyzer.format_research_summary(fundamental)
        report += "\n\n" + result['report_hint']

    return report


def main():
    """CLI测试入口"""
    if len(sys.argv) < 2:
        print("""
用法: python research_with_websearch.py <股票代码> [股票名称]

示例:
  python research_with_websearch.py 02382
  python research_with_websearch.py 02382 舜宇光学
  python research_with_websearch.py HK.09880 优必选

注意:
  此脚本设计用于Claude Code环境中配合WebSearch工具使用
  在命令行中运行只会显示搜索建议
""")
        return

    code = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else None

    # 执行分析
    result = analyze_with_websearch(code, name)

    # 格式化报告
    report = format_complete_report(result)
    print(report)


if __name__ == "__main__":
    main()
