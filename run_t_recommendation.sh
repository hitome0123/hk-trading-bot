#!/bin/bash
# 港股做T推荐快捷启动脚本

echo "========================================"
echo "🎯 港股智能做T推荐系统"
echo "========================================"
echo ""

# 检查FutuOpenD是否运行
if ! pgrep -x "FutuOpenD" > /dev/null; then
    echo "⚠️  警告: FutuOpenD未运行，尝试打开..."
    open -a "/Users/mantou/Downloads/Futu_OpenD_9.6.5618_Mac/Futu_OpenD_9.6.5618_Mac/FutuOpenD.app"
    echo "请在FutuOpenD中登录并启动API服务器，然后重新运行此脚本"
    exit 1
fi

# 检查交易时间
hour=$(date +%H)
minute=$(date +%M)
day=$(date +%u)

if [ $day -eq 6 ] || [ $day -eq 7 ]; then
    echo "⚠️  今天是周末，港股休市"
    read -p "是否继续运行？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

if (( hour < 9 || (hour == 9 && minute < 30) || hour > 16 )); then
    echo "⚠️  当前非交易时间（港股交易时间: 09:30-12:00, 13:00-16:00）"
    read -p "是否继续运行？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

echo "✅ 开始分析..."
echo ""

# 运行主脚本
cd /Users/mantou/hk-trading-bot
python3 hot_sector_smart_t.py

echo ""
echo "========================================"
echo "✅ 分析完成！"
echo "========================================"
