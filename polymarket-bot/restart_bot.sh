#!/bin/bash
echo "停止旧bot..."
pkill -9 -f "python3 main.py"
sleep 2

echo "启动新bot..."
export $(cat .env | grep -v '^#' | xargs)
nohup python3 main.py > logs/bot_live.log 2>&1 &

sleep 3

if ps aux | grep "python3 main.py" | grep -v grep > /dev/null; then
    echo "✅ Bot已启动"
    echo ""
    echo "查看日志："
    echo "  tail -f logs/bot_live.log"
else
    echo "❌ Bot启动失败"
fi
