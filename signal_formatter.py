#!/usr/bin/env python3
"""
信号格式化器 - 为Telegram推送生成消息
输入：趋势信号数据
输出：格式化的Telegram消息列表
"""
import json
from datetime import datetime
from typing import List, Dict

INPUT_FILE = '/Users/mantou/.n8n-files/trend_signals.json'
OUTPUT_FILE = '/Users/mantou/.n8n-files/telegram_messages.json'


def format_signal_message(signal: Dict) -> str:
    """
    格式化单个信号为Telegram消息
    """
    # 强度emoji
    strength_emoji = {
        'strong': '🔥',
        'medium': '✅',
        'weak': '💡'
    }
    emoji = strength_emoji.get(signal['strength'], '📊')

    # 趋势描述
    trend_desc = {
        'explosive': '爆发式上涨',
        'rising': '加速上涨',
        'stable': '平稳',
        'declining': '下降'
    }
    trend = trend_desc.get(signal['trend'], signal['trend'])

    # 构建消息
    message = f"""{emoji} 热点上升信号

📰 热点关键词: {signal['keyword']}
🏷️ 相关板块: {signal['sector']}

📊 热度分析:
  • K值: {signal['k_value']} ({trend})
  • 当前热度: {signal['current_heat']:,}
  • 平均热度: {signal['avg_heat']:,}
  • 来源: {signal['source']}

💼 相关港股:
  {', '.join(signal['stocks'][:3])}
  {f"等{len(signal['stocks'])}只股票" if len(signal['stocks']) > 3 else ""}

💡 投资建议:
  • 关注度: {signal['strength']}
  • 趋势: {trend}
  • K值0.3-1.0为理想入场区间

⏰ {signal['timestamp']}"""

    return message


def main():
    """主函数"""
    print(f"📝 开始格式化信号消息... {datetime.now().strftime('%H:%M:%S')}")

    # 读取信号数据
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        signal_data = json.load(f)

    signals = signal_data.get('signals', [])

    if not signals:
        print("⚠️ 没有找到信号，跳过推送")
        output = {
            'messages': [],
            'count': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        # 格式化所有信号
        messages = [format_signal_message(sig) for sig in signals]

        output = {
            'messages': messages,
            'count': len(messages),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f"✅ 格式化完成：{len(messages)} 条消息")

    # 保存输出
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"📁 消息已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
