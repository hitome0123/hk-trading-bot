#!/bin/bash
# 机构持仓监控系统 - 完整流程
# 1. 监控机构资金流向 -> 2. 格式化消息

set -e  # 遇到错误就停止

cd /Users/mantou/hk-trading-bot

echo "========================================="
echo "🏦 启动机构持仓监控系统"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# Step 1: 监控机构和散户资金流向
echo ""
echo "📊 Step 1/2: 监控资金流向（富途API）..."
python3 institutional_monitor.py

# Step 2: 格式化Telegram消息
echo ""
echo "💬 Step 2/2: 格式化推送消息..."
python3 institutional_formatter.py

echo ""
echo "========================================="
echo "✅ 流程执行完成"
echo "========================================="
