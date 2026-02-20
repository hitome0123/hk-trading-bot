#!/bin/bash
# 安装社交媒体API依赖

echo "🚀 开始安装社交媒体API依赖..."
echo ""

# 检查Python版本
python3 --version

echo ""
echo "📦 安装PRAW (Reddit API Wrapper)..."
pip3 install praw

echo ""
echo "📦 安装VADER Sentiment (情绪分析)..."
pip3 install vaderSentiment

echo ""
echo "📦 安装requests..."
pip3 install requests

echo ""
echo "✅ 安装完成!"
echo ""
echo "📝 使用说明:"
echo ""
echo "1. Reddit (推荐 - 使用ApeWisdom API，无需配置):"
echo "   python social_api_integration.py reddit"
echo ""
echo "2. 马斯克追踪 (WebSearch方案):"
echo "   python social_api_integration.py musk"
echo ""
echo "3. 完整演示:"
echo "   python social_api_integration.py demo"
echo ""
echo "4. 集成到策略助手:"
echo "   python my_strategy_helper.py sentiment usa"
echo "   python my_strategy_helper.py sentiment musk"
echo ""
echo "🔧 可选: 配置Reddit PRAW (高级用户)"
echo "   1. 访问 https://www.reddit.com/prefs/apps"
echo "   2. 创建应用获取credentials"
echo "   3. 设置环境变量:"
echo "      export REDDIT_CLIENT_ID='your_id'"
echo "      export REDDIT_CLIENT_SECRET='your_secret'"
echo ""
