#!/bin/bash
# 港股智能推荐系统 - 完整流程
# 整合：社交媒体热点 + 机构资金流向 → 综合信号推送

set -e  # 遇到错误就停止

cd /Users/mantou/hk-trading-bot

echo "========================================="
echo "🚀 启动港股智能推荐系统"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="

# ============ 第一部分：社交媒体热点监控 ============
echo ""
echo "📡 第1步：采集社交媒体热点数据..."
python3 social_media_collector.py

echo ""
echo "📊 第2步：趋势分析和K值计算..."
python3 trend_analyzer.py

# ============ 第二部分：机构资金流向监控 ============
echo ""
echo "🏦 第3步：监控机构资金流向（富途API）..."
python3 institutional_monitor.py

# ============ 第三部分：信号整合和推送 ============
echo ""
echo "🔗 第4步：整合信号（交叉验证）..."
python3 signal_integrator.py

echo ""
echo "💬 第5步：格式化推送消息..."
python3 integrated_formatter.py

echo ""
echo "========================================="
echo "✅ 流程执行完成"
echo ""
echo "📊 查看结果:"
echo "   - 热点信号: cat /Users/mantou/.n8n-files/trend_signals.json"
echo "   - 机构信号: cat /Users/mantou/.n8n-files/institutional_signals.json"
echo "   - 综合信号: cat /Users/mantou/.n8n-files/integrated_signals.json"
echo "   - 推送消息: cat /Users/mantou/.n8n-files/final_messages.json"
echo "========================================="
