# Telegram通知配置指南

## 方案A：使用现有Bot (@askTokenBot)

### 1. 获取Bot Token
1. 打开Telegram，搜索 `@BotFather`
2. 发送 `/mybots`
3. 选择 `@askTokenBot`
4. 点击 "API Token"
5. 复制token（格式：`1234567890:ABC...`）

### 2. 获取Chat ID
```bash
# 先给你的bot发送消息
# 在Telegram中打开 @askTokenBot，发送 /start

# 然后运行：
python3 get_chat_id.py YOUR_BOT_TOKEN

# 脚本会输出你的chat_id
```

---

## 方案B：创建新Bot（推荐）

### 1. 创建专用Bot
1. 打开Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 输入bot名称：`Polymarket Alerts`
4. 输入username：`polymarket_alerts_bot`（或其他可用名称）
5. BotFather会返回token，复制保存

### 2. 启动Bot
- 在Telegram中搜索你的新bot
- 发送 `/start`

### 3. 获取Chat ID
```bash
python3 get_chat_id.py YOUR_BOT_TOKEN
```

---

## 配置到config.yaml

脚本会输出配置内容，复制到 `config.yaml`：

```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN_HERE"
    chat_id: "YOUR_CHAT_ID_HERE"
```

---

## 测试发送

配置完成后，重启bot：
```bash
pkill -f "python3 main.py"
export $(cat .env | xargs)
nohup python3 main.py > logs/bot_live.log 2>&1 &
```

你会收到启动通知！

---

## 通知内容

Bot会在以下情况发送Telegram消息：

✅ **Bot启动/停止**
- "🚀 Polymarket Bot 已启动"
- "⏹️ Polymarket Bot 已停止"

🔔 **检测到新仓位**
- Sharp交易员的新开仓
- 市场名称、方向、价格

📊 **交易决策**
- 凯利推荐金额
- 风险验证结果
- 是否执行跟单

🚨 **熔断器触发**
- 日亏损超限
- 连续亏损
- API错误过多

💰 **交易结果**
- 订单执行成功/失败
- P&L更新
- 当前余额

---

## 故障排除

### 问题1：收不到消息
- 检查是否向bot发送过 `/start`
- 确认bot_token和chat_id正确
- 查看日志：`grep "telegram" logs/bot_live.log`

### 问题2：消息延迟
- Telegram API有时会延迟，属正常

### 问题3：Bot Token失效
- 重新从 @BotFather 获取token
