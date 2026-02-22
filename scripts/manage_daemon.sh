#!/bin/bash
# 守护进程管理脚本

case "$1" in
    start)
        echo "🚀 启动服务..."
        launchctl load ~/Library/LaunchAgents/com.mantou.futu.plist
        launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已启动"
        ;;
    stop)
        echo "🛑 停止服务..."
        launchctl unload ~/Library/LaunchAgents/com.mantou.futu.plist
        launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "🔄 重启服务..."
        launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist 2>/dev/null || true
        launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已重启"
        ;;
    status)
        echo "📊 服务状态："
        echo ""
        echo "富途OpenD："
        launchctl list | grep mantou.futu && echo "  ✅ 运行中" || echo "  ❌ 已停止"
        echo ""
        echo "交易监控："
        launchctl list | grep mantou.trading && echo "  ✅ 运行中" || echo "  ❌ 已停止"
        echo ""
        echo "进程："
        pgrep -f "Futu_OpenD" > /dev/null && echo "  富途: ✅" || echo "  富途: ❌"
        pgrep -f "trading_monitor" > /dev/null && echo "  监控: ✅" || echo "  监控: ❌"
        ;;
    logs)
        echo "📜 最近10条日志："
        echo ""
        echo "=== 交易监控日志 ==="
        tail -10 ~/hk-trading-bot/logs/trading_stdout.log 2>/dev/null || echo "暂无日志"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
