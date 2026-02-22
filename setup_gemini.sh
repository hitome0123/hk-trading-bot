#!/bin/bash
# Gemini配置脚本

echo "============================================================"
echo "🚀 配置Gemini板块交易顾问（推荐）"
echo "============================================================"
echo ""

# 检查是否已配置
if [ -n "$GEMINI_API_KEY" ]; then
    echo "✅ 检测到已配置的API密钥: ${GEMINI_API_KEY:0:20}..."
    echo ""
    read -p "是否要更换密钥？(y/N): " replace
    if [ "$replace" != "y" ] && [ "$replace" != "Y" ]; then
        echo "保持现有配置"
        exit 0
    fi
fi

echo "📝 请输入你的Google API密钥"
echo ""
echo "获取方式:"
echo "1. 访问 https://aistudio.google.com/app/apikey"
echo "2. 登录Google账号"
echo "3. 点击 'Create API key'"
echo "4. 复制密钥（格式: AIzaSy...）"
echo ""
echo "💰 免费额度:"
echo "- Gemini 1.5 Flash: 1500次/天（推荐）"
echo "- Gemini 1.5 Pro: 50次/天"
echo ""
read -p "请粘贴API密钥: " api_key

# 验证格式
if [[ ! $api_key =~ ^AIza ]]; then
    echo "❌ API密钥格式不正确，应该以 AIza 开头"
    exit 1
fi

echo ""
echo "🔍 测试API密钥..."

# 测试API（使用curl测试Gemini API）
response=$(curl -s -w "\n%{http_code}" "https://generativelanguage.googleapis.com/v1beta/models?key=$api_key" \
  --max-time 10)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo "✅ API密钥有效！"
else
    echo "❌ API密钥验证失败"
    echo "状态码: $http_code"
    echo "响应: $body"
    exit 1
fi

echo ""
echo "💾 保存配置..."

# 保存到 ~/.zshrc
if ! grep -q "export GEMINI_API_KEY" ~/.zshrc; then
    echo "" >> ~/.zshrc
    echo "# Google Gemini API配置 (板块交易顾问)" >> ~/.zshrc
    echo "export GEMINI_API_KEY=\"$api_key\"" >> ~/.zshrc
    echo "✅ 已添加到 ~/.zshrc"
else
    # 更新现有配置
    sed -i.bak "s|export GEMINI_API_KEY=.*|export GEMINI_API_KEY=\"$api_key\"|" ~/.zshrc
    echo "✅ 已更新 ~/.zshrc 中的配置"
fi

# 立即生效
export GEMINI_API_KEY="$api_key"

echo ""
echo "📦 安装依赖..."
pip3 install -q google-generativeai

echo ""
echo "============================================================"
echo "✅ 配置完成！"
echo "============================================================"
echo ""
echo "📋 配置信息:"
echo "  API密钥: ${api_key:0:20}..."
echo "  配置文件: ~/.zshrc"
echo "  模型: Gemini 1.5 Flash (推荐)"
echo ""
echo "🧪 测试Gemini分析:"
echo "  cd ~/hk-trading-bot"
echo "  python3 gemini_analyzer.py"
echo ""
echo "🚀 运行增强版系统:"
echo "  python3 sector_trading_advisor.py"
echo ""
echo "💡 提示:"
echo "  - Gemini完全免费（1500次/天）"
echo "  - 国内可直接访问，无需梯子"
echo "  - 分析质量接近GPT-4"
echo "  - API密钥已保存，重启终端后自动生效"
echo ""
