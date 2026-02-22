# n8n港股监控使用指南

## 问题诊断

您遇到的错误：`The connection to the server was closed unexpectedly`

**原因：**
- 增强版脚本执行时间过长（社交媒体API调用、新闻抓取）
- 超过了n8n Execute Command节点的默认超时时间
- 某些外部API（微博、抖音）可能被限流

---

## 解决方案

### 方案1：使用简化稳定版（推荐）

**文件：** `n8n_futu_bridge_simple.py`

**优点：**
- 速度快（2-3秒内完成）
- 稳定可靠
- 只依赖FutuOpenD，无外部API调用

**在n8n中配置：**

1. **Execute Command节点**
```json
{
  "command": "python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge_simple.py"
}
```

2. **输出数据格式**
```json
{
  "success": true,
  "stocks": [
    {
      "code": "09988",
      "name": "阿里巴巴",
      "price": 158.1,
      "change_pct": -3.18,
      "amplitude": 6.61,
      "volume": 61.5,
      "score": 40,
      "rating": "buy",
      "reasons": ["振幅大", "成交活跃"]
    }
  ],
  "count": 10
}
```

---

### 方案2：使用增强版（需要调整n8n超时）

**文件：** `n8n_futu_bridge_enhanced.py`

**在n8n中配置：**

1. **Execute Command节点 - 增加超时时间**

在节点的"Options"中设置：
- **Timeout**: 60000（60秒）
- **Continue On Fail**: true

```json
{
  "command": "python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge_enhanced.py",
  "options": {
    "timeout": 60000
  }
}
```

---

## n8n工作流配置示例

### 基础工作流（简化版）

```
[Schedule Trigger]
  每30分钟触发
    ↓
[Execute Command]
  运行: n8n_futu_bridge_simple.py
    ↓
[IF节点]
  条件: score >= 50
    ↓
[HTTP Request]
  发送钉钉/飞书通知
```

**Schedule Trigger配置：**
```json
{
  "rule": {
    "interval": [
      {
        "field": "minutes",
        "minutesInterval": 30
      }
    ]
  }
}
```

**Execute Command配置：**
```json
{
  "command": "python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge_simple.py"
}
```

**IF节点配置：**
```json
{
  "conditions": {
    "number": [
      {
        "value1": "={{ $json.score }}",
        "operation": "larger",
        "value2": 50
      }
    ]
  }
}
```

---

## 数据处理示例

### 1. 提取TOP 5股票

在**Function节点**中：
```javascript
const stocks = $input.all()[0].json.stocks;

// 按评分排序，取前5
const top5 = stocks
  .sort((a, b) => b.score - a.score)
  .slice(0, 5);

return top5.map(s => ({
  json: {
    name: s.name,
    price: s.price,
    change: s.change_pct,
    score: s.score,
    rating: s.rating
  }
}));
```

### 2. 筛选强势股（涨幅>2% 且 评分>60）

```javascript
const stocks = $input.all()[0].json.stocks;

const strongStocks = stocks.filter(s =>
  s.change_pct > 2 && s.score > 60
);

return strongStocks.map(s => ({ json: s }));
```

### 3. 格式化通知消息

```javascript
const stock = $input.all()[0].json;

const message = `
📈 港股推荐

股票: ${stock.name} (${stock.code})
现价: ${stock.price} HKD
涨幅: ${stock.change_pct > 0 ? '+' : ''}${stock.change_pct}%
振幅: ${stock.amplitude}%
评分: ${stock.score}/100

${stock.rating === 'strong_buy' ? '🔥 强烈推荐' : stock.rating === 'buy' ? '✅ 建议关注' : '⚠️ 观望'}

理由: ${stock.reasons.join('、')}
`;

return [{ json: { message } }];
```

---

## 钉钉机器人通知配置

### HTTP Request节点配置

```json
{
  "url": "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN",
  "method": "POST",
  "sendBody": true,
  "bodyParameters": {
    "msgtype": "text",
    "text": {
      "content": "={{ $json.message }}"
    }
  }
}
```

---

## 飞书机器人通知配置

```json
{
  "url": "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK",
  "method": "POST",
  "sendBody": true,
  "bodyParameters": {
    "msg_type": "text",
    "content": {
      "text": "={{ $json.message }}"
    }
  }
}
```

---

## 完整工作流示例（JSON格式）

保存以下内容为 `hk_stock_monitor.json`，然后在n8n中导入：

```json
{
  "nodes": [
    {
      "name": "定时触发",
      "type": "n8n-nodes-base.scheduleTrigger",
      "position": [250, 300],
      "parameters": {
        "rule": {
          "interval": [{"field": "minutes", "minutesInterval": 30}]
        }
      }
    },
    {
      "name": "监控行情",
      "type": "n8n-nodes-base.executeCommand",
      "position": [450, 300],
      "parameters": {
        "command": "python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge_simple.py"
      }
    },
    {
      "name": "筛选强势股",
      "type": "n8n-nodes-base.function",
      "position": [650, 300],
      "parameters": {
        "functionCode": "const stocks = $input.all()[0].json.stocks;\nconst filtered = stocks.filter(s => s.score >= 50);\nreturn filtered.map(s => ({json: s}));"
      }
    },
    {
      "name": "发送通知",
      "type": "n8n-nodes-base.httpRequest",
      "position": [850, 300],
      "parameters": {
        "url": "YOUR_WEBHOOK_URL",
        "method": "POST",
        "sendBody": true,
        "bodyParameters": {
          "text": "={{ $json.name }}: {{ $json.change_pct }}%"
        }
      }
    }
  ],
  "connections": {
    "定时触发": {"main": [[{"node": "监控行情", "type": "main", "index": 0}]]},
    "监控行情": {"main": [[{"node": "筛选强势股", "type": "main", "index": 0}]]},
    "筛选强势股": {"main": [[{"node": "发送通知", "type": "main", "index": 0}]]}
  }
}
```

---

## 常见问题

### Q1: 如何修改监控的股票？
编辑 `n8n_futu_bridge_simple.py`，在 `candidates` 列表中添加或删除股票。

### Q2: 如何调整评分规则？
在 `n8n_futu_bridge_simple.py` 的 `main()` 函数中，修改评分逻辑。

### Q3: 能否同时使用简化版和增强版？
可以。创建两个不同的n8n工作流，分别调用不同的脚本。

### Q4: 如何避免频繁触发通知？
在IF节点中设置更高的评分阈值，或者使用n8n的"Wait"节点控制通知频率。

---

## 性能对比

| 版本 | 执行时间 | 股票数量 | 功能 | 稳定性 |
|------|---------|---------|------|--------|
| 简化版 | 2-3秒 | 10只 | 基础指标 | ⭐⭐⭐⭐⭐ |
| 增强版 | 30-60秒 | 30-50只 | 完整指标+社交热度 | ⭐⭐⭐ |

---

## 建议

1. **日常使用**：使用简化版，稳定快速
2. **深度分析**：手动运行增强版，获取完整数据
3. **混合使用**：简化版做实时监控，增强版做每日复盘

---

**当前测试结果：** ✅ 简化版运行成功，2秒内返回10只股票数据

需要帮助？请查看完整文档或联系技术支持。
