#!/usr/bin/env python3
"""
综合信号格式化器 - 为Telegram推送生成消息
输入：整合后的综合信号
输出：格式化的Telegram消息列表
"""
import json
from datetime import datetime
from typing import List, Dict

INPUT_FILE = '/Users/mantou/.n8n-files/integrated_signals.json'
OUTPUT_FILE = '/Users/mantou/.n8n-files/final_messages.json'


def format_diamond_signal(signal: Dict) -> str:
    """
    💎💎 钻石信号：热点上升 + 机构买入
    """
    message = f"""💎💎 钻石信号 - 强烈推荐

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

🔥 热点趋势:
  • 关键词: {signal['keyword']}
  • K值: {signal['k_value']} ({signal['trend']})
  • 热度: 加速上涨中

💰 机构资金:
  • 机构净流入: {signal['institutional_inflow']} 亿元
  • 资金类型: 超大单 + 大单

✅ 综合评价:
  • 信号强度: ⭐️⭐️⭐️⭐️⭐️
  • {signal['recommendation']}
  • 热点话题正在发酵，机构同步增持

💡 操作建议:
  • 建议仓位: {'30-50%' if signal['institutional_inflow'] > 1.0 else '20-30%'}
  • 入场策略: 分批建仓
  • 止损位: -5%

⏰ {signal['timestamp']}"""

    return message


def format_super_signal(signal: Dict) -> str:
    """
    💎⚠️ 超级博弈信号：热点 + 机构 + 散户
    """
    inst_ratio = signal['institutional_inflow'] / (signal['institutional_inflow'] + signal['retail_inflow']) * 100

    message = f"""💎⚠️ 超级博弈信号

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

🔥 热点趋势:
  • 关键词: {signal['keyword']}
  • K值: {signal['k_value']} ({signal['trend']})

💰 资金博弈:
  • 机构净流入: {signal['institutional_inflow']} 亿元（{inst_ratio:.1f}%）
  • 散户净流入: {signal['retail_inflow']} 亿元（{100-inst_ratio:.1f}%）

⚖️ 综合评价:
  • 信号强度: {'⭐️⭐️⭐️⭐️' if inst_ratio > 50 else '⭐️⭐️⭐️'}
  • {signal['recommendation']}
  • {'机构占优势，可轻仓试探' if inst_ratio > 50 else '散户占优势，谨慎追高'}

💡 操作建议:
  • 建议仓位: {'20-30%' if inst_ratio > 50 else '10-20%'}
  • 入场策略: 轻仓试探
  • 止损位: -3%

⏰ {signal['timestamp']}"""

    return message


def format_institutional_only(signal: Dict) -> str:
    """
    👍 纯机构买入（无热点支撑）
    """
    # 只推送大额机构流入（> 1亿）
    if signal['institutional_inflow'] < 1.0:
        return None

    message = f"""👍 机构稳健增持

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

💰 机构资金:
  • 机构净流入: {signal['institutional_inflow']} 亿元
  • 资金类型: 超大单 + 大单
  • 特点: 无热点炒作，稳健增持

✅ 综合评价:
  • 信号强度: ⭐️⭐️⭐️
  • {signal['recommendation']}
  • 适合稳健型投资者

💡 操作建议:
  • 建议仓位: {'20-30%' if signal['institutional_inflow'] > 1.5 else '10-20%'}
  • 入场策略: 低吸为主
  • 止损位: -5%

⏰ {signal['timestamp']}"""

    return message


def format_trend_only(signal: Dict) -> str:
    """
    🤔 仅热点（无机构流入）- 仅供参考
    """
    # 只推送高K值热点（K > 0.5）
    if signal['k_value'] < 0.5:
        return None

    message = f"""🤔 热点信号 - 观望为主

📊 相关股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

🔥 热点趋势:
  • 关键词: {signal['keyword']}
  • K值: {signal['k_value']} ({signal['trend']})
  • 热度: 快速上升

⚠️ 风险提示:
  • 无明显机构资金流入
  • 可能仅为短期炒作
  • {signal['recommendation']}

💡 操作建议:
  • 仅供参考，谨慎参与
  • 如参与，轻仓短线
  • 快进快出，止损位 -3%

⏰ {signal['timestamp']}"""

    return message


def format_warning_signal(signal: Dict) -> str:
    """
    ⚠️ 追高警告
    """
    message = f"""⚠️ 追高警告 - 避雷

📊 股票: {signal['stock_name']} ({signal['stock_code']})
🏷️ 板块: {signal['sector']}

🔥 热点趋势:
  • 关键词: {signal['keyword']}
  • K值: {signal['k_value']}

💰 资金流向:
  • 散户净流入: {signal['retail_inflow']} 亿元（散户追高）
  • 机构流入: {'少量' if signal['institutional_inflow'] < 0.5 else f"{signal['institutional_inflow']}亿"}

🚫 风险提示:
  • {signal['recommendation']}
  • 散户追高，容易成接盘侠
  • 不建议跟进

⏰ {signal['timestamp']}"""

    return message


def main():
    """主函数"""
    print(f"📝 开始格式化综合信号消息... {datetime.now().strftime('%H:%M:%S')}")

    # 读取综合信号
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    signals = data.get('signals', [])
    stats = data.get('stats', {})

    messages = []

    for sig in signals:
        msg = None

        if sig['type'] == 'diamond':
            msg = format_diamond_signal(sig)
        elif sig['type'] == 'super':
            msg = format_super_signal(sig)
        elif sig['type'] == 'institutional_only':
            msg = format_institutional_only(sig)
        elif sig['type'] == 'trend_only':
            msg = format_trend_only(sig)
        elif sig['type'] == 'warning':
            msg = format_warning_signal(sig)

        if msg:
            messages.append(msg)

    output = {
        'messages': messages,
        'count': len(messages),
        'stats': stats,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 格式化完成：")
    print(f"  💎 钻石信号: {stats.get('diamond', 0)} 个")
    print(f"  💎⚠️  博弈信号: {stats.get('super', 0)} 个")
    print(f"  👍 纯机构: {stats.get('institutional_only', 0)} 个（筛选后推送大额）")
    print(f"  🤔 仅热点: {stats.get('trend_only', 0)} 个（筛选后推送高K值）")
    print(f"  ⚠️  警告: {stats.get('warning', 0)} 个")
    print(f"  📊 总消息数: {len(messages)} 条（筛选后）")
    print(f"📁 消息已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
