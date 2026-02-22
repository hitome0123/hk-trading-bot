#!/bin/bash

echo "======================================================================"
echo "🔍 富途OpenD API 快速检测"
echo "======================================================================"
echo ""

# 检查端口
if lsof -nP -iTCP:11111 | grep -q LISTEN; then
    echo "✅ 富途OpenD API 已启动！"
    echo ""
    echo "您现在可以运行交易程序了："
    echo "  python3 quick_analysis.py 1024      # 分析快手"
    echo "  python3 t0_check_now.py 1024        # T+0实时监控"
    echo "  python3 full_market_scanner.py      # 全市场扫描"
else
    echo "❌ 富途OpenD API 未启动"
    echo ""
    echo "请在富途OpenD应用中："
    echo "  1. 登录账号"
    echo "  2. 点击右上角'设置'"
    echo "  3. 找到'API接入'"
    echo "  4. 勾选'启用API'"
    echo "  5. 点击'确定'"
    echo ""
    echo "完成后再次运行此脚本检测"
fi

echo "======================================================================"
