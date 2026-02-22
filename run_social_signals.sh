#!/bin/bash
# 社交媒体热点信号系统 - 完整流程
# 1. 采集数据 -> 2. 分析趋势 -> 3. 格式化消息

set -e  # 遇到错误就停止

cd /Users/mantou/hk-trading-bot

echo "========================================="
echo "🚀 启动社交媒体热点信号系统"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# Step 1: 采集社交媒体数据
echo ""
echo "📡 Step 1/3: 采集社交媒体热点数据..."
python3 social_media_collector.py

# Step 2: 分析趋势和计算K值
echo ""
echo "📊 Step 2/3: 趋势分析和K值计算..."
python3 trend_analyzer.py

# Step 3: 格式化Telegram消息
echo ""
echo "💬 Step 3/3: 格式化推送消息..."
python3 signal_formatter.py

echo ""
echo "========================================="
echo "✅ 流程执行完成"
echo "========================================="
