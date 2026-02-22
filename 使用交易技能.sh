#!/bin/bash
# 港股交易系统技能快速访问脚本

echo "=========================================="
echo "  港股日赚300元交易系统 - 快速访问"
echo "=========================================="
echo ""

# 菜单
echo "请选择操作："
echo "1. 查看完整技能文档"
echo "2. 查看使用指南"
echo "3. 查看买点策略"
echo "4. 查看卖点策略"
echo "5. 查看风险控制"
echo "6. 查看测试场景"
echo "7. 在Claude Code中打开技能"
echo ""

read -p "输入选项 (1-7): " choice

case $choice in
  1)
    echo "正在打开完整技能文档..."
    less ~/hk-trading-bot/docs/skills/港股日赚300元交易系统.md
    ;;
  2)
    echo "正在打开使用指南..."
    less ~/hk-trading-bot/docs/交易系统使用指南.md
    ;;
  3)
    echo "📊 买点策略（4选1）："
    echo ""
    grep -A 30 "买点1：" ~/hk-trading-bot/docs/skills/港股日赚300元交易系统.md | head -35
    ;;
  4)
    echo "💰 卖点策略（3选1）："
    echo ""
    grep -A 25 "退出1：" ~/hk-trading-bot/docs/skills/港股日赚300元交易系统.md | head -30
    ;;
  5)
    echo "⚠️ 风险控制系统："
    echo ""
    grep -A 20 "单日最大亏损" ~/hk-trading-bot/docs/skills/港股日赚300元交易系统.md | head -25
    ;;
  6)
    echo "🧪 实战测试场景："
    echo ""
    grep "场景[0-9]：" ~/hk-trading-bot/docs/skills/港股日赚300元交易系统.md
    ;;
  7)
    echo "💡 提示：在Claude Code中输入以下命令："
    echo ""
    echo "   /hk-stock-daily-profit"
    echo ""
    echo "或者直接问问题："
    echo "   '用技能帮我分析这只港股'"
    echo "   '我被套了，应该怎么办？'"
    echo ""
    ;;
  *)
    echo "无效选项"
    ;;
esac

echo ""
echo "=========================================="
echo "技能位置: ~/hk-trading-bot/docs/skills/"
echo "完整文档: 港股日赚300元交易系统.md"
echo "使用指南: 交易系统使用指南.md"
echo "=========================================="
