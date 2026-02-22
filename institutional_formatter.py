#!/usr/bin/env python3
"""
机构信号格式化器 - 为Telegram推送生成消息
输入：机构持仓信号数据
输出：格式化的Telegram消息列表
"""
import json
from datetime import datetime
from typing import List, Dict

INPUT_FILE = '/Users/mantou/.n8n-files/institutional_signals.json'
OUTPUT_FILE = '/Users/mantou/.n8n-files/institutional_messages.json'


def format_recommend_message(signal: Dict) -> str:
    """
    格式化推荐信号为Telegram消息（机构买入）
    """
    message = f"""💎 机构买入推荐

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

💰 资金流向:
  • 机构净流入: {signal['net_inflow']} 亿元
  • 资金类型: 超大单 + 大单
  • 信号强度: {'强' if signal['net_inflow'] > 1.0 else '中' if signal['net_inflow'] > 0.5 else '弱'}

✅ 投资建议:
  • 机构在增持，可跟进
  • 建议仓位: {'30-50%' if signal['net_inflow'] > 1.0 else '20-30%' if signal['net_inflow'] > 0.5 else '10-20%'}
  • 止损位: -5%

⏰ {signal['timestamp']}"""

    return message


def format_warning_message(signal: Dict) -> str:
    """
    格式化避雷信号为Telegram消息（散户买入）
    """
    message = f"""⚠️ 散户追高避雷

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

💰 资金流向:
  • 散户净流入: {signal['net_inflow']} 亿元
  • 资金类型: 小单 + 中单
  • 风险等级: {'高' if signal['net_inflow'] > 1.0 else '中'}

🚫 风险提示:
  • 散户在追高，谨慎跟进
  • 可能成为接盘侠
  • 建议观望或轻仓

⏰ {signal['timestamp']}"""

    return message


def format_mixed_signal_message(stock_code: str, recommend_sig: Dict, warning_sig: Dict) -> str:
    """
    格式化混合信号（机构和散户都在买）
    """
    message = f"""⚡️ 博弈信号 - 机构与散户同时买入

📊 股票: {recommend_sig['stock_name']} ({stock_code})
🏷️ 板块: {recommend_sig['sector']}

💰 资金流向:
  • 机构净流入: {recommend_sig['net_inflow']} 亿元（超大单+大单）
  • 散户净流入: {warning_sig['net_inflow']} 亿元（小单+中单）

📈 资金对比:
  • 机构占比: {recommend_sig['net_inflow'] / (recommend_sig['net_inflow'] + warning_sig['net_inflow']) * 100:.1f}%
  • 散户占比: {warning_sig['net_inflow'] / (recommend_sig['net_inflow'] + warning_sig['net_inflow']) * 100:.1f}%

💡 分析:
  {'• 机构资金占优，可考虑跟进' if recommend_sig['net_inflow'] > warning_sig['net_inflow'] else '• 散户资金占优，谨慎追高'}
  • 存在博弈，注意风险
  • 建议轻仓试探

⏰ {recommend_sig['timestamp']}"""

    return message


def main():
    """主函数"""
    print(f"📝 开始格式化机构信号消息... {datetime.now().strftime('%H:%M:%S')}")

    # 读取信号数据
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        signal_data = json.load(f)

    recommend_signals = signal_data.get('recommend_signals', [])
    warning_signals = signal_data.get('warning_signals', [])

    # 找出混合信号（同时有机构买入和散户买入的股票）
    recommend_stocks = {sig['stock_code']: sig for sig in recommend_signals}
    warning_stocks = {sig['stock_code']: sig for sig in warning_signals}

    mixed_stocks = set(recommend_stocks.keys()) & set(warning_stocks.keys())

    messages = []

    # 1. 生成混合信号消息（优先）
    for stock_code in mixed_stocks:
        msg = format_mixed_signal_message(
            stock_code,
            recommend_stocks[stock_code],
            warning_stocks[stock_code]
        )
        messages.append(msg)

    # 2. 生成纯推荐信号消息
    pure_recommends = [sig for sig in recommend_signals if sig['stock_code'] not in mixed_stocks]
    for sig in pure_recommends:
        msg = format_recommend_message(sig)
        messages.append(msg)

    # 3. 生成纯避雷信号消息
    pure_warnings = [sig for sig in warning_signals if sig['stock_code'] not in mixed_stocks]
    for sig in pure_warnings:
        msg = format_warning_message(sig)
        messages.append(msg)

    output = {
        'messages': messages,
        'count': len(messages),
        'mixed_signals': len(mixed_stocks),
        'recommend_only': len(pure_recommends),
        'warning_only': len(pure_warnings),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 格式化完成：")
    print(f"  • 混合信号: {len(mixed_stocks)} 个")
    print(f"  • 纯推荐信号: {len(pure_recommends)} 个")
    print(f"  • 纯避雷信号: {len(pure_warnings)} 个")
    print(f"  • 总消息数: {len(messages)} 条")
    print(f"📁 消息已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
