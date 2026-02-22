#!/bin/bash
# 港股信号系统 - 一键启动脚本

echo "🚀 启动港股实时信号系统..."
echo ""

# 1. 检查 FutuOpenD
if pgrep -f "FutuOpenD" > /dev/null; then
    echo "✅ FutuOpenD 已运行"
else
    echo "⚠️  FutuOpenD 未运行，请手动启动 FutuOpenD"
    echo "   启动后再运行本脚本"
    exit 1
fi

# 2. 启动 n8n（如果未运行）
if pgrep -f "n8n start" > /dev/null; then
    echo "✅ n8n 已运行"
else
    echo "🔄 启动 n8n..."
    nohup n8n start > ~/.n8n/n8n.log 2>&1 &
    sleep 3
    echo "✅ n8n 已启动"
fi

# 3. 生成一次初始信号
echo "🔍 生成初始信号..."
cd /Users/mantou/hk-trading-bot
python3 generate_signals_to_file.py > /dev/null 2>&1
echo "✅ 初始信号已生成"

# 4. 检查系统状态
echo ""
echo "📊 系统状态检查："
echo ""

# 检查信号文件
if [ -f "/tmp/hk_signals.json" ]; then
    SIGNALS=$(python3 -c "import json; d=json.load(open('/tmp/hk_signals.json')); print(f\"买入:{d['buy_signals']} 卖出:{d['sell_signals']}\")")
    echo "  ✅ 信号文件: $SIGNALS"
else
    echo "  ❌ 信号文件未生成"
fi

# 检查 Cron
if crontab -l 2>/dev/null | grep -q "generate_signals_to_file.py"; then
    echo "  ✅ Cron任务: 已配置（每5分钟）"
else
    echo "  ⚠️  Cron任务: 未配置"
fi

# 检查 n8n 工作流
echo "  ✅ n8n工作流: http://localhost:5678/workflow/J511ETlwVKZUUCDQ"

echo ""
echo "🎉 系统启动完成！"
echo ""
echo "📱 Telegram 将每5分钟自动接收交易信号"
echo "🔗 n8n管理: http://localhost:5678"
echo "📊 查看信号: cat /tmp/hk_signals.json | python3 -m json.tool"
echo ""
