#!/bin/bash
# 本地热门板块推送脚本
# 需要富途OpenD运行中

cd ~/hk-trading-bot

# 检查富途是否运行
if ! pgrep -f "Futu_OpenD" > /dev/null; then
    echo "❌ 富途OpenD未运行，跳过本次扫描"
    exit 0
fi

# 运行板块扫描
echo "🔍 $(date '+%H:%M') 开始扫描热门板块..."
python3 sector_trading_advisor.py >> logs/sector_advisor.log 2>&1

echo "✅ 扫描完成"
