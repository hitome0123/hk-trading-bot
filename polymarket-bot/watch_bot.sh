#!/bin/bash
# 实时监控Bot活动

echo "================================================================================"
echo "  👀 实时监控 Polymarket Bot"
echo "  按 Ctrl+C 退出"
echo "================================================================================"
echo ""

# 检查bot是否运行
if ! ps aux | grep "python3 main.py" | grep -v grep > /dev/null; then
    echo "❌ Bot未运行！"
    echo "请先启动: python3 main.py &"
    exit 1
fi

PID=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $2}')
echo "✅ Bot进程ID: $PID"
echo "⏰ 开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "监控内容："
echo "  - CPU和内存使用"
echo "  - 最近检测到的仓位"
echo "  - 凯利计算决策"
echo ""
echo "================================================================================"
echo ""

# 实时监控循环
while true; do
    clear
    echo "================================================================================"
    echo "  Polymarket Bot 实时状态 - $(date '+%H:%M:%S')"
    echo "================================================================================"
    echo ""

    # 显示进程状态
    echo "📊 资源使用："
    ps aux | grep "python3 main.py" | grep -v grep | awk '{
        printf "   CPU: %s%%  |  内存: %s%%  |  运行时间: %s\n", $3, $4, $10
    }'

    echo ""
    echo "🔔 最近活动（最新5条）："
    echo "   [暂无日志文件，bot输出到后台进程]"
    echo "   提示：重启bot时使用 'python3 main.py > logs/bot_live.log 2>&1 &'"
    echo ""

    # 显示监控提示
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💡 提示："
    echo "   - Bot正在后台静默运行"
    echo "   - 每4秒检查一次Erasmus的新仓位"
    echo "   - 要查看详细输出，请重启bot并启用日志记录"
    echo ""
    echo "🛠️ 快速操作："
    echo "   1. 停止bot: pkill -f 'python3 main.py'"
    echo "   2. 启动并记录日志: python3 main.py > logs/bot_live.log 2>&1 &"
    echo "   3. 查看实时日志: tail -f logs/bot_live.log"
    echo "================================================================================"

    sleep 5
done
