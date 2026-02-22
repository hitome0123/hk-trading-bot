#!/bin/bash
# 港股实时信号系统启动脚本

echo "🚀 启动港股实时信号系统..."

# 检查FutuOpenD是否运行
if ! pgrep -f "FutuOpenD" > /dev/null; then
    echo "⚠️  FutuOpenD未运行，请先启动FutuOpenD！"
    exit 1
fi

# 停止旧的信号API服务
pkill -f "signal_api.py"
sleep 1

# 启动信号API服务
echo "📡 启动信号API服务 (端口5001)..."
nohup python3 /Users/mantou/hk-trading-bot/signal_api.py > /tmp/signal_api.log 2>&1 &
API_PID=$!
echo "   PID: $API_PID"

# 等待API启动
sleep 3

# 测试API
echo "🔍 测试API连接..."
if curl -s http://localhost:5001/health | grep -q "ok"; then
    echo "✅ API服务正常"
else
    echo "❌ API服务启动失败"
    exit 1
fi

# 检查n8n是否运行
if ! pgrep -f "n8n start" > /dev/null; then
    echo "🔄 启动n8n服务..."
    nohup n8n start > ~/.n8n/n8n.log 2>&1 &
    sleep 5
fi

echo ""
echo "✅ 系统启动完成！"
echo ""
echo "📊 服务状态："
echo "   - 信号API: http://localhost:5001"
echo "   - n8n工作流: http://localhost:5678"
echo ""
echo "🔗 工作流地址："
echo "   http://localhost:5678/workflow/J511ETlwVKZUUCDQ"
echo ""
echo "📝 日志文件："
echo "   - API日志: /tmp/signal_api.log"
echo "   - n8n日志: ~/.n8n/n8n.log"
echo ""
echo "⏰ 系统将每5分钟自动扫描，发现买入信号后推送到钉钉"
echo ""
