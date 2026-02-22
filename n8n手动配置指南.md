# n8n港股实时信号系统 - 手动配置指南

## 方法1: 直接访问工作流（推荐先试这个）

等待30秒让n8n完全启动，然后访问：

```
http://localhost:5678/workflows
```

在列表中找到：**港股做T智能交易系统 v2.0 (Futu+Claude)**

---

## 方法2: 手动创建新工作流（如果上面不行）

### 步骤1: 创建新工作流

1. 访问 http://localhost:5678
2. 点击左侧 "+" 创建新工作流
3. 命名为：**港股实时信号推送**

---

### 步骤2: 添加触发器节点

1. 点击 "Add first step"
2. 搜索并选择 **Schedule Trigger**
3. 配置如下：

```
Trigger Rules:
- Trigger Interval: Minutes
- Minutes Between Triggers: 5
```

4. 点击 "Execute Node" 测试

---

### 步骤3: 添加Code节点（核心！）

1. 点击 "+" 添加节点
2. 搜索并选择 **Code**
3. 在代码框中粘贴以下内容：

```javascript
const { execSync } = require('child_process');

try {
  const raw = execSync(
    'python3 /Users/mantou/hk-trading-bot/n8n_realtime_signal.py 2>/dev/null',
    { timeout: 120000, encoding: 'utf-8' }
  );

  const data = JSON.parse(raw);
  return [{ json: data }];

} catch(e) {
  return [{ json: { error: e.message, signals: [] } }];
}
```

4. 点击 "Test step" 测试
   - 应该看到返回的信号数据

---

### 步骤4: 添加IF节点（过滤）

1. 点击 "+" 添加节点
2. 搜索并选择 **IF**
3. 配置条件：

```
Conditions:
- Value 1: {{ $json.buy_signals }}
- Operation: larger
- Value 2: 0
```

这样只有当有买入信号时才会继续

---

### 步骤5: 添加Function节点（格式化消息）

1. 在IF节点的 "true" 分支添加节点
2. 搜索并选择 **Code**
3. 粘贴以下代码：

```javascript
const data = $input.all()[0].json;
const buySignals = data.signals.filter(s => s.signal.type === '买入');

const messages = buySignals.map(stock => {
  const signal = stock.signal;

  const emoji = signal.strength === '强' ? '🔥' : '✅';

  return `${emoji} ${signal.strength}买入信号

📈 股票: ${stock.name} (${stock.code})
🏷️ 板块: ${stock.sector}

💰 当前价: ${stock.price} HKD
📊 涨幅: ${stock.changePct > 0 ? '+' : ''}${stock.changePct}%

📉 RSI: ${signal.rsi} ${signal.rsi < 30 ? '(超卖)' : ''}
📏 位置: 布林带${signal.bollinger_position.toFixed(0)}%
🚀 量比: ${signal.vol_ratio}倍

💡 建议操作:
  • 仓位: ${signal.suggested_position}
  • 买入: ${signal.entry_price}
  • 止损: ${signal.stop_loss}
  • 目标1: ${signal.target1} (日内)
  • 目标2: ${signal.target2} (激进)

${signal.note ? '⚠️ ' + signal.note : ''}

⏰ ${stock.timestamp}`;
});

return messages.map(msg => ({ json: { message: msg } }));
```

---

### 步骤6: 添加HTTP Request节点（钉钉推送）

1. 点击 "+" 添加节点
2. 搜索并选择 **HTTP Request**
3. 配置如下：

```
Method: POST
URL: https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN

Send Body: Yes
Body Content Type: JSON

Body:
{
  "msgtype": "text",
  "text": {
    "content": "{{ $json.message }}"
  }
}
```

**⚠️ 重要：** 将 `YOUR_TOKEN` 替换为您的钉钉机器人access_token

---

### 步骤7: 连接节点

确保节点按以下顺序连接：

```
Schedule Trigger
    ↓
Code (实时信号检测)
    ↓
IF (有买入信号?)
    ↓ (true分支)
Code (格式化消息)
    ↓
HTTP Request (发送钉钉)
```

---

### 步骤8: 保存并激活

1. 点击右上角 "Save"
2. 打开右上角的 "Active" 开关
3. ✅ 完成！

---

## 测试工作流

### 手动测试

1. 点击 "Execute Workflow" 按钮
2. 查看每个节点的输出
3. 检查钉钉是否收到消息

### 查看执行历史

1. 点击左侧 "Executions"
2. 查看历史执行记录
3. 点击任一记录查看详情

---

## 快速测试脚本（命令行）

如果想快速测试Python脚本是否正常：

```bash
cd ~/hk-trading-bot
python3 n8n_realtime_signal.py | python3 -m json.tool
```

应该看到类似输出：

```json
{
  "signals": [
    {
      "code": "01045",
      "name": "亚太卫星",
      "sector": "商业航天",
      "signal": {
        "type": "买入",
        "strength": "强",
        ...
      }
    }
  ],
  "buy_signals": 1,
  "sell_signals": 0
}
```

---

## 获取钉钉Webhook

### 步骤：

1. 打开钉钉PC客户端
2. 进入要接收通知的群聊
3. 点击右上角 "..." → 群设置 → 智能群助手
4. 点击 "添加机器人" → "自定义"
5. 名称：港股信号机器人
6. 复制 Webhook 地址
7. 粘贴到n8n的HTTP Request节点中

格式类似：
```
https://oapi.dingtalk.com/robot/send?access_token=abcd1234567890...
```

---

## 常见问题

### Q1: Code节点报错 "command not found"

**原因：** Python路径不对

**解决：** 查找正确路径
```bash
which python3
# 将输出的路径替换到代码中
```

### Q2: 没有收到钉钉消息

**检查：**
1. Webhook URL是否正确？
2. IF节点的true分支是否有数据？
3. 钉钉机器人是否被限流？

### Q3: 信号太少/太多

**调整：** 编辑 `n8n_realtime_signal.py` 中的条件

```python
# 放宽条件（更多信号）
if (rsi < 45 and position < 40 ...):

# 收紧条件（更少信号）
if (rsi < 35 and position < 25 ...):
```

---

## 工作流备份

建议定期导出工作流：

1. 点击右上角 "..." → Download
2. 保存为JSON文件
3. 放到安全位置

---

## 下一步优化

### 1. 添加飞书推送

复制HTTP Request节点，修改URL和格式

### 2. 添加数据库记录

在HTTP Request前添加一个节点，将信号保存到SQLite

### 3. 添加回测功能

记录每次推送的信号，1周后验证准确率

---

**完成后，您将拥有：**
- ✅ 每5分钟自动扫描
- ✅ 发现信号立即推送钉钉
- ✅ 包含完整的交易建议
- ✅ 全自动，无需人工干预

祝您交易顺利！🚀
