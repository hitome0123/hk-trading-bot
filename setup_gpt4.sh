#!/bin/bash
# GPT-4增强版配置脚本

echo "============================================================"
echo "🚀 配置GPT-4增强版板块交易顾问"
echo "============================================================"
echo ""

# 检查是否已配置
if [ -n "$OPENAI_API_KEY" ]; then
    echo "✅ 检测到已配置的API密钥: ${OPENAI_API_KEY:0:20}..."
    echo ""
    read -p "是否要更换密钥？(y/N): " replace
    if [ "$replace" != "y" ] && [ "$replace" != "Y" ]; then
        echo "保持现有配置"
        exit 0
    fi
fi

echo "📝 请输入你的OpenAI API密钥"
echo ""
echo "获取方式:"
echo "1. 访问 https://platform.openai.com/api-keys"
echo "2. 登录/注册账号"
echo "3. 点击 'Create new secret key'"
echo "4. 复制密钥（格式: sk-proj-xxxxx 或 sk-xxxxx）"
echo ""
read -p "请粘贴API密钥: " api_key

# 验证格式
if [[ ! $api_key =~ ^sk- ]]; then
    echo "❌ API密钥格式不正确，应该以 sk- 开头"
    exit 1
fi

echo ""
echo "🔍 测试API密钥..."

# 测试API
response=$(curl -s -w "\n%{http_code}" https://api.openai.com/v1/models \
  -H "Authorization: Bearer $api_key" \
  -H "Content-Type: application/json" \
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
if ! grep -q "export OPENAI_API_KEY" ~/.zshrc; then
    echo "" >> ~/.zshrc
    echo "# OpenAI API配置 (板块交易顾问)" >> ~/.zshrc
    echo "export OPENAI_API_KEY=\"$api_key\"" >> ~/.zshrc
    echo "✅ 已添加到 ~/.zshrc"
else
    # 更新现有配置
    sed -i.bak "s|export OPENAI_API_KEY=.*|export OPENAI_API_KEY=\"$api_key\"|" ~/.zshrc
    echo "✅ 已更新 ~/.zshrc 中的配置"
fi

# 立即生效
export OPENAI_API_KEY="$api_key"

echo ""
echo "============================================================"
echo "✅ 配置完成！"
echo "============================================================"
echo ""
echo "📋 配置信息:"
echo "  API密钥: ${api_key:0:20}..."
echo "  配置文件: ~/.zshrc"
echo ""
echo "🧪 测试GPT-4分析:"
echo "  cd ~/hk-trading-bot"
echo "  python3 gpt4_analyzer.py"
echo ""
echo "🚀 运行增强版系统:"
echo "  python3 sector_trading_advisor.py"
echo ""
echo "💡 提示:"
echo "  - GPT-4分析约 $0.01/次"
echo "  - 建议充值 $5 可用几百次"
echo "  - API密钥已保存，重启终端后自动生效"
echo ""
