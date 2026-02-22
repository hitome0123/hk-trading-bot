# API集成指南 - 跨境电商AI全栈智能运营系统

完整的API集成配置和使用说明

---

## 📊 集成API总览

本系统集成了以下API服务：

| API类别 | 服务 | 用途 | 文档链接 |
|---------|------|------|----------|
| 电商平台 | Amazon SP-API | 订单、库存、产品管理 | [docs.developer.amazonservices.com](https://developer-docs.amazon.com/sp-api/) |
| 电商平台 | eBay API | 订单、listing管理 | [developer.ebay.com](https://developer.ebay.com/) |
| 电商平台 | Shopify API | 店铺、订单、产品 | [shopify.dev](https://shopify.dev/docs/api) |
| AI/ML | OpenAI GPT-4 | 智能客服、内容生成 | [platform.openai.com](https://platform.openai.com/) |
| 翻译 | DeepL API | 多语言翻译 | [deepl.com/pro-api](https://www.deepl.com/pro-api) |
| 汇率 | ExchangeRate-API | 实时汇率 | [exchangerate-api.com](https://www.exchangerate-api.com/) |
| 通知 | Telegram Bot API | 实时告警推送 | [core.telegram.org/bots/api](https://core.telegram.org/bots/api) |

---

## 1. Amazon SP-API 集成

### 1.1 注册和授权

**步骤**:
1. 注册Amazon Seller Central账号
2. 访问 [Seller Central → Apps & Services → Develop Apps](https://sellercentral.amazon.com/apps/manage)
3. 创建新的Developer Application
4. 获取:
   - Client ID
   - Client Secret
   - Refresh Token

### 1.2 配置凭证

在n8n中配置Amazon SP-API凭证:

```json
{
  "clientId": "amzn1.application-oa2-client.xxxxx",
  "clientSecret": "your_client_secret",
  "refreshToken": "Atzr|xxxxx",
  "region": "na"
}
```

### 1.3 常用API端点

#### 获取订单
```javascript
// n8n HTTP Request节点配置
{
  "method": "GET",
  "url": "https://sellingpartnerapi-na.amazon.com/orders/v0/orders",
  "authentication": "predefinedCredentialType",
  "nodeCredentialType": "amazonSpApi",
  "queryParameters": {
    "CreatedAfter": "2026-01-01T00:00:00Z",
    "MarketplaceIds": "ATVPDKIKX0DER"
  }
}
```

#### 更新库存
```javascript
{
  "method": "POST",
  "url": "https://sellingpartnerapi-na.amazon.com/fba/inventory/v1/items/inventory",
  "body": {
    "sellerSku": "PROD-A-001",
    "marketplaceId": "ATVPDKIKX0DER",
    "quantity": 150
  }
}
```

### 1.4 错误处理

| 错误码 | 原因 | 解决方案 |
|--------|------|----------|
| 403 | Refresh token过期 | 重新授权获取新token |
| 429 | 超过速率限制 | 添加重试逻辑，指数退避 |
| 400 | 参数错误 | 检查API参数格式 |

---

## 2. eBay API 集成

### 2.1 获取API凭证

**步骤**:
1. 注册 [eBay Developer Program](https://developer.ebay.com/)
2. 创建Application
3. 获取:
   - App ID
   - Cert ID
   - OAuth Token

### 2.2 OAuth 2.0认证

```javascript
// 获取Access Token
POST https://api.ebay.com/identity/v1/oauth2/token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic <Base64(AppID:CertID)>

grant_type=client_credentials&scope=https://api.ebay.com/oauth/api_scope
```

### 2.3 常用API端点

#### 获取订单
```javascript
{
  "method": "GET",
  "url": "https://api.ebay.com/sell/fulfillment/v1/order",
  "headers": {
    "Authorization": "Bearer {{$credentials.accessToken}}",
    "Content-Type": "application/json"
  },
  "queryParameters": {
    "filter": "creationdate:[2026-01-01T00:00:00.000Z..2026-02-01T00:00:00.000Z]"
  }
}
```

#### 更新价格
```javascript
{
  "method": "PUT",
  "url": "https://api.ebay.com/sell/inventory/v1/offer/{{offerId}}",
  "body": {
    "pricingSummary": {
      "price": {
        "currency": "USD",
        "value": "29.99"
      }
    }
  }
}
```

---

## 3. Shopify API 集成

### 3.1 获取API凭证

**步骤**:
1. 登录Shopify Admin
2. Settings → Apps and sales channels → Develop apps
3. 创建自定义app
4. 获取:
   - API Key
   - API Secret Key
   - Admin API access token

### 3.2 配置权限Scopes

推荐scopes:
```
read_orders, write_orders
read_products, write_products
read_inventory, write_inventory
read_customers
```

### 3.3 常用API端点

#### 获取订单
```javascript
{
  "method": "GET",
  "url": "https://{{$credentials.shopName}}.myshopify.com/admin/api/2024-01/orders.json",
  "headers": {
    "X-Shopify-Access-Token": "{{$credentials.accessToken}}"
  },
  "queryParameters": {
    "status": "any",
    "created_at_min": "2026-01-01T00:00:00Z"
  }
}
```

#### 更新库存
```javascript
{
  "method": "POST",
  "url": "https://{{shopName}}.myshopify.com/admin/api/2024-01/inventory_levels/set.json",
  "body": {
    "location_id": 123456789,
    "inventory_item_id": 987654321,
    "available": 150
  }
}
```

---

## 4. OpenAI GPT-4 集成

### 4.1 获取API Key

**步骤**:
1. 访问 [platform.openai.com](https://platform.openai.com/)
2. 注册账号并绑定支付方式
3. API Keys → Create new secret key
4. 复制并保存key（仅显示一次）

### 4.2 智能客服使用示例

```javascript
// n8n HTTP Request或OpenAI节点
{
  "method": "POST",
  "url": "https://api.openai.com/v1/chat/completions",
  "headers": {
    "Authorization": "Bearer {{$credentials.apiKey}}",
    "Content-Type": "application/json"
  },
  "body": {
    "model": "gpt-4",
    "messages": [
      {
        "role": "system",
        "content": "You are a professional e-commerce customer service agent."
      },
      {
        "role": "user",
        "content": "Customer message: Where is my order #12345?"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

### 4.3 成本优化

| 策略 | 说明 | 节省比例 |
|------|------|----------|
| 使用GPT-3.5-turbo | 对于简单查询 | 90% |
| 缓存常见问题 | Redis缓存FAQ | 70% |
| 限制max_tokens | 控制响应长度 | 30% |
| 批处理请求 | 减少API调用 | 40% |

---

## 5. DeepL翻译 集成

### 5.1 获取API Key

**步骤**:
1. 访问 [deepl.com/pro](https://www.deepl.com/pro)
2. 注册DeepL Pro账号
3. Account → API keys → Create key

### 5.2 翻译使用示例

```javascript
{
  "method": "POST",
  "url": "https://api.deepl.com/v2/translate",
  "body": {
    "auth_key": "{{$credentials.apiKey}}",
    "text": "My order hasn't arrived yet",
    "source_lang": "EN",
    "target_lang": "ZH"
  }
}
```

### 5.3 支持的语言

| 语言代码 | 语言名称 | 常用场景 |
|----------|----------|----------|
| EN | English | 默认语言 |
| ZH | Chinese (Simplified) | 中国市场 |
| ES | Spanish | 西班牙、拉美 |
| DE | German | 德国市场 |
| FR | French | 法国市场 |
| JA | Japanese | 日本市场 |

**完整列表**: https://www.deepl.com/docs-api/translate-text/

---

## 6. ExchangeRate-API 集成

### 6.1 获取API Key

**步骤**:
1. 访问 [exchangerate-api.com](https://www.exchangerate-api.com/)
2. 注册免费账号（1500次/月免费）
3. 获取API key

### 6.2 获取汇率示例

```javascript
{
  "method": "GET",
  "url": "https://v6.exchangerate-api.com/v6/{{apiKey}}/latest/USD",
  "queryParameters": {}
}

// 响应示例
{
  "result": "success",
  "base_code": "USD",
  "rates": {
    "CNY": 7.24,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 148.50
  }
}
```

### 6.3 定价算法应用

```javascript
// 在Code节点中使用
const basePrice = 20.00;  // USD
const fxRate = $('获取汇率').first().json.rates.CNY;
const localPrice = basePrice * fxRate;  // CNY
const finalPrice = localPrice * 1.05;  // 5%利润

return [{json: {
  base_price_usd: basePrice,
  fx_rate: fxRate,
  local_price_cny: localPrice,
  final_price_cny: finalPrice
}}];
```

---

## 7. Telegram Bot API 集成

### 7.1 创建Bot

**步骤**:
1. 在Telegram中搜索 @BotFather
2. 发送 `/newbot`
3. 按提示设置bot名称
4. 获取Bot Token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 7.2 获取Chat ID

```bash
# 1. 与你的bot对话，发送任意消息
# 2. 访问以下URL
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# 3. 从响应中找到chat.id
{
  "result": [{
    "message": {
      "chat": {
        "id": 7082819163  // 这就是你的chat_id
      }
    }
  }]
}
```

### 7.3 发送消息示例

```javascript
{
  "method": "POST",
  "url": "https://api.telegram.org/bot{{botToken}}/sendMessage",
  "body": {
    "chat_id": "{{chatId}}",
    "text": "🔔 订单 #12345 需要处理",
    "parse_mode": "Markdown"
  }
}
```

### 7.4 富文本格式

```markdown
# Markdown支持
*粗体*
_斜体_
`代码`
[链接](https://example.com)

# Emoji
✅ ❌ ⚠️ 📦 💰 🔔 🚀

# 示例
*订单提醒* 🔔

订单号: `AMZ-12345`
状态: ⚠️ 需要人工审核
金额: *$159.99*

[查看详情](https://yoursite.com/orders/12345)
```

---

## 8. API速率限制和重试策略

### 8.1 各平台速率限制

| API | 速率限制 | 重试策略 |
|-----|---------|----------|
| Amazon SP-API | 5请求/秒 | 指数退避，最多3次 |
| eBay API | 5000请求/天 | 固定延迟1秒 |
| Shopify API | 2请求/秒 | Leaky bucket算法 |
| OpenAI | 3500请求/分 | 自动重试，429时等待 |
| DeepL | 无限制（Pro） | 无需重试 |

### 8.2 n8n中的重试配置

**方法1: 节点级别重试**
```javascript
// 在HTTP Request节点的Options中
{
  "retry": {
    "maxRetries": 3,
    "waitBetween": 1000  // 1秒
  }
}
```

**方法2: Try-Catch重试**
```javascript
// 使用Error Trigger + Wait节点
Try → HTTP Request (失败)
  → Error Handler
    → Wait 2秒
      → HTTP Request (重试)
```

**方法3: Code节点实现指数退避**
```javascript
const maxRetries = 3;
let attempt = 0;

async function makeRequest() {
  try {
    const response = await $http.get(url);
    return response;
  } catch (error) {
    if (attempt < maxRetries && error.response?.status === 429) {
      attempt++;
      const delay = Math.pow(2, attempt) * 1000;  // 2s, 4s, 8s
      await new Promise(resolve => setTimeout(resolve, delay));
      return makeRequest();
    }
    throw error;
  }
}

const result = await makeRequest();
return [{json: result.data}];
```

---

## 9. 安全最佳实践

### 9.1 凭证管理

✅ **推荐做法**:
- 使用n8n内置的凭证系统
- 定期轮换API keys（90天）
- 不同环境使用不同凭证
- 启用MFA（如支持）

❌ **避免**:
- 硬编码API keys在workflow中
- 在日志中打印敏感信息
- 将凭证提交到Git
- 与他人共享API keys

### 9.2 数据加密

```javascript
// 敏感数据加密存储
const crypto = require('crypto');

function encrypt(text, key) {
  const cipher = crypto.createCipher('aes-256-cbc', key);
  let encrypted = cipher.update(text, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  return encrypted;
}

// 在存储前加密
const encrypted = encrypt(customerData, process.env.ENCRYPTION_KEY);
```

### 9.3 Webhook安全

```javascript
// 验证webhook签名（以Shopify为例）
const crypto = require('crypto');

function verifyWebhook(body, hmacHeader, secret) {
  const hash = crypto
    .createHmac('sha256', secret)
    .update(body, 'utf8')
    .digest('base64');

  return crypto.timingSafeEqual(
    Buffer.from(hash),
    Buffer.from(hmacHeader)
  );
}

// 在Webhook节点后添加Code节点
if (!verifyWebhook(body, headers['x-shopify-hmac-sha256'], secret)) {
  throw new Error('Invalid webhook signature');
}
```

---

## 10. 监控和告警

### 10.1 API健康检查

```javascript
// 定时检查API可用性（每5分钟）
const apis = [
  {name: 'Amazon', url: 'https://sellingpartnerapi-na.amazon.com/orders/v0/orders'},
  {name: 'eBay', url: 'https://api.ebay.com/sell/fulfillment/v1/order'},
  {name: 'Shopify', url: `https://${shop}.myshopify.com/admin/api/2024-01/orders.json`}
];

const results = [];
for (const api of apis) {
  try {
    const response = await $http.get(api.url, {timeout: 5000});
    results.push({
      name: api.name,
      status: 'OK',
      response_time: response.duration
    });
  } catch (error) {
    results.push({
      name: api.name,
      status: 'FAIL',
      error: error.message
    });
    // 发送Telegram告警
  }
}

return results.map(r => ({json: r}));
```

### 10.2 关键指标监控

在PostgreSQL中记录：
```sql
CREATE TABLE api_metrics (
    id SERIAL PRIMARY KEY,
    api_name VARCHAR(50),
    endpoint VARCHAR(255),
    response_time_ms INT,
    status_code INT,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 查询成功率（过去24小时）
SELECT
    api_name,
    COUNT(*) as total_calls,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
    AVG(response_time_ms) as avg_response_time
FROM api_metrics
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY api_name;
```

---

## 📚 参考资源

### 官方文档
- [Amazon SP-API Developer Guide](https://developer-docs.amazon.com/sp-api/)
- [eBay API Documentation](https://developer.ebay.com/docs)
- [Shopify API Reference](https://shopify.dev/docs/api)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [n8n Documentation](https://docs.n8n.io/)

### 社区资源
- [n8n Community Forum](https://community.n8n.io/)
- [Shopify Developer Community](https://community.shopify.com/)
- [Stack Overflow - Amazon SP-API](https://stackoverflow.com/questions/tagged/amazon-sp-api)

---

**最后更新**: 2026-02-03
**版本**: 1.0.0
