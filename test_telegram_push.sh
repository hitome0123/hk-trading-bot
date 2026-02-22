#!/bin/bash
# 港股智能推荐系统 - Telegram推送测试脚本

set -e

echo "========================================="
echo "🧪 测试Telegram推送"
echo "========================================="
echo ""

# 1. 运行完整推荐流程
echo "📊 第1步: 生成推荐信号..."
cd /Users/mantou/hk-trading-bot
bash run_all_signals.sh > /tmp/run_signals.log 2>&1

# 2. 读取推荐结果
echo ""
echo "📄 第2步: 读取推荐结果..."
if [ ! -f "/Users/mantou/.n8n-files/final_messages.json" ]; then
    echo "❌ 错误: 推荐结果文件不存在"
    exit 1
fi

MESSAGE_COUNT=$(cat /Users/mantou/.n8n-files/final_messages.json | python3 -c "import json,sys; data=json.load(sys.stdin); print(data.get('count', 0))")
echo "   找到 $MESSAGE_COUNT 条推荐消息"

# 3. 发送到Telegram
echo ""
echo "📱 第3步: 发送到Telegram..."

BOT_TOKEN="8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
CHAT_ID="7082819163"

# 读取并发送每条消息
python3 << 'EOPYTHON'
import json
import requests
import time

BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
CHAT_ID = "7082819163"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

# 读取消息
with open('/Users/mantou/.n8n-files/final_messages.json') as f:
    data = json.load(f)

messages = data.get('messages', [])
stats = data.get('stats', {})
timestamp = data.get('timestamp', '')

if len(messages) == 0:
    print("   ⚠️  本次没有推荐信号")
    # 发送空消息通知
    requests.post(API_URL, json={
        'chat_id': CHAT_ID,
        'text': f'📊 港股智能推荐系统 - {timestamp}\n\n暂无推荐信号\n\n数据采集正常，等待下次机会 🎯'
    })
else:
    # 发送汇总
    summary = (
        f"📊 港股智能推荐系统 - {timestamp}\n\n"
        f"本次信号统计:\n"
        f"💎 钻石: {stats.get('diamond', 0)}  "
        f"💎⚠️ 博弈: {stats.get('super', 0)}\n"
        f"👍 机构: {stats.get('institutional_only', 0)}  "
        f"🤔 热点: {stats.get('trend_only', 0)}\n"
        f"⚠️ 警告: {stats.get('warning', 0)}\n\n"
        f"推送消息: {len(messages)} 条\n"
        f"━━━━━━━━━━━━━━━━"
    )

    print(f"   发送汇总消息...")
    response = requests.post(API_URL, json={'chat_id': CHAT_ID, 'text': summary})
    if response.json().get('ok'):
        print(f"   ✅ 汇总发送成功")
    time.sleep(1)

    # 发送详细消息
    for idx, msg in enumerate(messages, 1):
        print(f"   发送第 {idx}/{len(messages)} 条推荐...")
        response = requests.post(API_URL, json={'chat_id': CHAT_ID, 'text': msg})
        if response.json().get('ok'):
            print(f"   ✅ 第 {idx} 条发送成功")
        else:
            print(f"   ❌ 第 {idx} 条发送失败: {response.text}")
        time.sleep(1)  # 避免触发频率限制

print(f"\n✅ 推送完成！共发送 {len(messages) + 1} 条消息")
EOPYTHON

echo ""
echo "========================================="
echo "✅ 测试完成！请检查你的Telegram"
echo "========================================="
