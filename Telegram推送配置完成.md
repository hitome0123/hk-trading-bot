# ✅ Telegram推送配置完成

## 📊 配置信息

**Bot信息**：
- Bot名称: Rich (@AskTokenBot)
- Bot ID: 8590123130
- Chat ID: 7082819163

**推送状态**：✅ 已测试成功

---

## 🚀 Workflow更新内容

### 新增节点：

1. **发送到Telegram** (HTTP Request节点)
   - 类型: POST请求
   - API: Telegram Bot API
   - 功能: 发送推荐消息到你的Telegram

2. **延迟1秒** (Wait节点)
   - 功能: 避免Telegram API频率限制
   - 确保每条消息之间间隔1秒

### 完整流程：

```
⏰ 定时触发器 (每10分钟)
    ↓
🔧 执行推荐系统
    ↓
📄 读取推荐结果
    ↓
💬 格式化消息
    ↓
🔍 过滤空消息
    ↓
📱 发送到Telegram  ← 新增
    ↓
⏱️ 延迟1秒        ← 新增
```

---

## 📱 你将收到的消息

### 1. 汇总消息
```
📊 港股智能推荐系统 - 2026-02-03 14:00:00

本次信号统计:
💎 钻石: 0  💎⚠️ 博弈: 0
👍 机构: 23  🤔 热点: 0
⚠️ 警告: 0

推送消息: 4 条
━━━━━━━━━━━━━━━━
```

### 2. 详细推荐
```
👍 机构稳健增持

📊 股票: 比亚迪股份 (HK.01211)
🏷️ 板块: 新能源汽车

💰 机构资金:
  • 机构净流入: 2.01 亿元
  • 资金类型: 超大单 + 大单
  • 特点: 无热点炒作，稳健增持

✅ 综合评价:
  • 信号强度: ⭐️⭐️⭐️
  • 可考虑，机构稳健增持
  • 适合稳健型投资者

💡 操作建议:
  • 建议仓位: 20-30%
  • 入场策略: 低吸为主
  • 止损位: -5%

⏰ 2026-02-03 14:00:00
```

---

## 🎯 查看workflow

1. 打开n8n控制台: http://localhost:5678
2. 找到 **"港股智能推荐系统"**
3. 点击进入查看完整流程图

**Workflow ID**: `lhcc3Vp6QWj4UdBM`

---

## 🧪 手动测试

### 方法1: 在n8n中测试
1. 打开workflow
2. 点击右上角 "Test workflow"
3. 查看Telegram是否收到消息

### 方法2: 命令行测试
```bash
# 运行完整流程
cd /Users/mantou/hk-trading-bot
bash run_all_signals.sh

# 然后手动发送到Telegram
curl -X POST "https://api.telegram.org/bot8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":"7082819163","text":"测试消息"}'
```

---

## ⚙️ 自定义配置

### 调整推送频率
在"定时触发器"节点中修改：
- 当前: 10分钟
- 可选: 5分钟、15分钟、30分钟

### 调整推送格式
在"格式化消息"节点中修改JavaScript代码，自定义：
- 汇总消息格式
- 详细消息格式
- Emoji使用

### 添加过滤条件
在"过滤空消息"节点后添加新的IF节点，例如：
- 只推送💎钻石信号
- 只推送机构流入>1亿的
- 只推送特定板块

---

## 📊 监控和维护

### 查看推送历史
```bash
# 在n8n UI中
Executions → 港股智能推荐系统 → 查看每次执行记录
```

### 查看推送失败原因
如果Telegram没收到消息，检查：
1. n8n执行日志 (Executions标签)
2. Telegram Bot是否被封禁
3. Chat ID是否正确
4. 网络连接是否正常

### 修改Bot Token
如果需要更换Bot：
1. 在workflow中找到"发送到Telegram"节点
2. 修改URL中的bot token
3. 修改bodyParametersJson中的chat_id
4. 保存并测试

---

## ⚠️ 注意事项

### Telegram API限制
- 每秒最多发送30条消息
- 每分钟最多发送20条消息给同一用户
- 建议使用延迟节点避免触发限制

### n8n和Cron同时运行
**当前状态**: cron和n8n都在每10分钟执行

**建议**: 停用其中一个
```bash
# 停用cron（推荐）
crontab -l | grep -v "run_all_signals.sh" | crontab -

# 或停用n8n workflow
# 在n8n UI中将workflow切换为Inactive
```

---

## 📈 下次收到推送时间

如果workflow已激活，下次推送时间为：
- **当前时间** + 10分钟
- 例如: 现在是14:07，下次推送在14:17

你可以在Telegram中查看实时推送！

---

**配置完成时间**: 2026-02-03 14:07
**测试状态**: ✅ 成功
**推送状态**: ✅ 已激活

🎉 享受你的智能港股推荐系统吧！
