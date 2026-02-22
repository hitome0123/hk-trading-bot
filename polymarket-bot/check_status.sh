#!/bin/bash
# Polymarket Bot 状态检查脚本

echo "================================================================================"
echo "  🔍 Polymarket Bot 状态检查"
echo "================================================================================"
echo ""

# 1. 检查进程
echo "1️⃣ 进程状态："
if ps aux | grep "python3 main.py" | grep -v grep > /dev/null; then
    PID=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $2}')
    CPU=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $3}')
    MEM=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $4}')
    RUNTIME=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $10}')

    echo "   ✅ Bot正在运行"
    echo "   进程ID: $PID"
    echo "   CPU使用: ${CPU}%"
    echo "   内存使用: ${MEM}%"
    echo "   运行时间: $RUNTIME"
else
    echo "   ❌ Bot未运行"
    echo "   提示：运行 'python3 main.py &' 启动bot"
fi

echo ""
echo "2️⃣ 配置状态："

# 2. 检查配置文件
if [ -f "config.yaml" ]; then
    echo "   ✅ config.yaml 存在"

    # 检查模拟模式
    if grep -q "enabled: true" config.yaml; then
        echo "   🎮 模拟交易模式"
    else
        echo "   💰 真实交易模式"
    fi
else
    echo "   ❌ config.yaml 不存在"
fi

# 3. 检查环境变量
if [ -f ".env" ]; then
    echo "   ✅ .env 文件存在"
else
    echo "   ❌ .env 文件不存在"
fi

echo ""
echo "3️⃣ 日志文件："

# 4. 检查日志
if [ -d "logs" ]; then
    LOG_COUNT=$(ls -1 logs/*.log 2>/dev/null | wc -l)
    if [ $LOG_COUNT -gt 0 ]; then
        echo "   ✅ 找到 $LOG_COUNT 个日志文件"
        echo "   最新日志："
        ls -lht logs/*.log 2>/dev/null | head -3 | awk '{print "      " $9 " (" $5 ")"}'
    else
        echo "   ⚠️  logs目录存在但没有日志文件"
    fi
else
    echo "   ❌ logs目录不存在"
fi

echo ""
echo "4️⃣ Sharp交易员："

# 5. 检查Sharp交易员配置
if grep -q "0xc6587b11a2209e46dfe3928b31c5514a8e33b784" main.py; then
    echo "   ✅ Erasmus (0xc6587b...33b784)"
else
    echo "   ⚠️  未配置Sharp交易员"
fi

echo ""
echo "================================================================================"
echo "  快速命令："
echo "================================================================================"
echo "  启动bot:  python3 main.py &"
echo "  停止bot:  pkill -f 'python3 main.py'"
echo "  查看日志: tail -f logs/polymarket_bot.log"
echo "================================================================================"
