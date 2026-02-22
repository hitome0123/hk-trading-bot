# 部署指南 - 跨境电商AI全栈智能运营系统

## 📋 前置要求

### 硬件要求
- CPU: 4核心以上
- 内存: 8GB以上（推荐16GB）
- 存储: 50GB以上可用空间
- 网络: 稳定的互联网连接

### 软件依赖
```bash
Node.js >= 18.x
PostgreSQL >= 14
Redis >= 6.2
Docker >= 20.10 (可选但推荐)
Docker Compose >= 2.0 (可选但推荐)
Git
```

---

## 🚀 部署方式

### 方式1: Docker部署（推荐）

#### 1.1 创建Docker Compose文件

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    container_name: ecommerce-postgres
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/schema.sql:/docker-entrypoint-initdb.d/1-schema.sql
      - ./sql/sample-data.sql:/docker-entrypoint-initdb.d/2-data.sql
    ports:
      - "5432:5432"
    networks:
      - ecommerce-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: ecommerce-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - ecommerce-net
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  n8n:
    image: n8nio/n8n:latest
    container_name: ecommerce-n8n
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=${N8N_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=${N8N_HOST}
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://${N8N_HOST}:5678/
      - GENERIC_TIMEZONE=UTC
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=n8n
      - DB_POSTGRESDB_USER=postgres
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
      - ./workflows:/workflows
    networks:
      - ecommerce-net
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  n8n_data:

networks:
  ecommerce-net:
    driver: bridge
```

#### 1.2 启动服务

```bash
# 1. 克隆项目
git clone <your-repo>
cd cross-border-ecommerce-ai-system

# 2. 配置环境变量
cp config/environment-variables.env.example .env
# 编辑.env文件，填入真实值

# 3. 启动所有服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 验证服务状态
docker-compose ps
```

#### 1.3 导入Workflows

```bash
# 访问n8n界面
# http://localhost:5678

# 使用n8n CLI导入（需要在n8n容器内执行）
docker exec -it ecommerce-n8n sh

# 导入主workflow
n8n import:workflow --input=/workflows/main-workflow.json

# 导入子workflows
n8n import:workflow --input=/workflows/customer-service-agent.json
n8n import:workflow --input=/workflows/dynamic-pricing-agent.json
n8n import:workflow --input=/workflows/inventory-management-agent.json

exit
```

---

### 方式2: 本地安装

#### 2.1 安装PostgreSQL

**macOS (Homebrew):**
```bash
brew install postgresql@14
brew services start postgresql@14

# 创建数据库
psql postgres
CREATE DATABASE ecommerce;
\q
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql-14
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 创建数据库
sudo -u postgres psql
CREATE DATABASE ecommerce;
\q
```

#### 2.2 安装Redis

**macOS:**
```bash
brew install redis
brew services start redis
```

**Ubuntu/Debian:**
```bash
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

#### 2.3 安装n8n

```bash
# 全局安装
npm install -g n8n

# 或使用npx（无需安装）
npx n8n
```

#### 2.4 初始化数据库

```bash
cd cross-border-ecommerce-ai-system

# 导入schema
psql -U postgres -d ecommerce -f sql/schema.sql

# 导入示例数据
psql -U postgres -d ecommerce -f sql/sample-data.sql
```

#### 2.5 启动n8n

```bash
# 设置环境变量
export N8N_BASIC_AUTH_ACTIVE=true
export N8N_BASIC_AUTH_USER=admin
export N8N_BASIC_AUTH_PASSWORD=your_password

# 启动
n8n start

# 或在后台运行
nohup n8n start > n8n.log 2>&1 &
```

---

## 🔐 配置n8n凭证

访问 http://localhost:5678 后，需要配置以下凭证：

### 1. PostgreSQL

**Settings → Credentials → New → Postgres**

```
Host: localhost (或postgres容器名)
Database: ecommerce
User: postgres
Password: <your_password>
Port: 5432
SSL: Disable (本地环境)
```

### 2. Redis

**Settings → Credentials → New → Redis**

```
Host: localhost (或redis容器名)
Port: 6379
Password: (留空，如未设置密码)
Database: 0
```

### 3. Amazon SP-API

**Settings → Credentials → New → Amazon SP-API**

```json
{
  "clientId": "your_amazon_client_id",
  "clientSecret": "your_amazon_client_secret",
  "refreshToken": "your_amazon_refresh_token",
  "region": "na"
}
```

**获取方式**: https://developer-docs.amazon.com/sp-api/

### 4. eBay API

**Settings → Credentials → New → eBay OAuth2 API**

```json
{
  "appId": "your_ebay_app_id",
  "certId": "your_ebay_cert_id",
  "accessToken": "your_oauth_token"
}
```

**获取方式**: https://developer.ebay.com/

### 5. Shopify API

**Settings → Credentials → New → Shopify API**

```json
{
  "shopName": "your-shop",
  "apiKey": "your_api_key",
  "password": "your_password",
  "sharedSecret": "your_shared_secret"
}
```

**获取方式**: https://shopify.dev/docs/api

### 6. OpenAI API

**Settings → Credentials → New → OpenAI API**

```json
{
  "apiKey": "sk-your-openai-api-key"
}
```

**获取方式**: https://platform.openai.com/api-keys

### 7. DeepL API

**Settings → Credentials → New → DeepL API**

```json
{
  "apiKey": "your-deepl-api-key"
}
```

**获取方式**: https://www.deepl.com/pro-api

### 8. Telegram Bot

**Settings → Credentials → New → Telegram API**

```json
{
  "botToken": "your_bot_token",
  "chatId": "your_chat_id"
}
```

**获取方式**:
1. 与 @BotFather 对话创建bot
2. 获取token
3. 与bot对话后访问: `https://api.telegram.org/bot<token>/getUpdates` 获取chat_id

---

## 📊 导入和激活Workflows

### 通过UI导入

1. 访问 http://localhost:5678
2. 点击 **Workflows** → **Import**
3. 依次导入:
   - `workflows/main-workflow.json`
   - `workflows/customer-service-agent.json`
   - `workflows/dynamic-pricing-agent.json`
   - `workflows/inventory-management-agent.json`

### 通过CLI导入

```bash
# 进入n8n容器（如使用Docker）
docker exec -it ecommerce-n8n sh

# 或直接在本地执行（如本地安装）
n8n import:workflow --input=./workflows/main-workflow.json
n8n import:workflow --input=./workflows/customer-service-agent.json
n8n import:workflow --input=./workflows/dynamic-pricing-agent.json
n8n import:workflow --input=./workflows/inventory-management-agent.json
```

### 配置Workflow关联

1. 打开主workflow: **跨境电商全栈智能运营系统**
2. 找到3个 "Execute Workflow" 节点
3. 分别配置:
   - **调用-智能客服Agent** → 选择 "智能客服Agent" workflow
   - **调用-动态定价Agent** → 选择 "动态定价Agent" workflow
   - **调用-库存管理Agent** → 选择 "智能库存管理Agent" workflow
4. 保存workflow

### 激活Workflows

1. 打开主workflow
2. 点击右上角的 **Active** 开关
3. 确认激活成功

---

## ✅ 验证部署

### 1. 检查数据库连接

```bash
# 进入PostgreSQL
psql -U postgres -d ecommerce

# 查看表
\dt

# 查询示例数据
SELECT * FROM inventory LIMIT 5;
SELECT * FROM orders LIMIT 5;

\q
```

### 2. 检查Redis连接

```bash
# 连接Redis
redis-cli

# 测试
ping
# 应该返回: PONG

# 退出
exit
```

### 3. 测试Workflow

#### 方法1: 手动触发

1. 打开主workflow
2. 点击 **Execute Workflow** 按钮
3. 查看执行结果

#### 方法2: Webhook测试

```bash
curl -X POST http://localhost:5678/webhook/new-order \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "TEST-001",
    "platform": "amazon",
    "customer_id": "CUST-123",
    "customer_message": "Where is my order?",
    "customer_language": "en",
    "items": [
      {"sku": "PROD-A-001", "quantity": 2, "price": 29.99}
    ],
    "total_amount": 59.98,
    "status": "pending"
  }'
```

#### 方法3: 查看执行日志

```bash
# Docker
docker-compose logs -f n8n

# 本地
tail -f ~/.n8n/n8n.log
```

---

## 🔧 常见问题排查

### 问题1: PostgreSQL连接失败

**错误**: `ECONNREFUSED ::1:5432`

**解决**:
```bash
# 检查PostgreSQL是否运行
docker-compose ps postgres  # Docker
brew services list | grep postgres  # macOS
systemctl status postgresql  # Linux

# 检查端口
lsof -i :5432

# 修改连接配置（Docker）
# 将 localhost 改为容器名 postgres
```

### 问题2: Redis连接超时

**错误**: `Redis connection timeout`

**解决**:
```bash
# 检查Redis
docker-compose ps redis
redis-cli ping

# 检查防火墙
sudo ufw allow 6379
```

### 问题3: n8n Workflow执行失败

**错误**: `Workflow execution failed`

**解决**:
1. 检查 Executions 标签的错误详情
2. 验证所有凭证配置正确
3. 检查API配额和限制
4. 查看节点的错误输出

### 问题4: API调用失败

**错误**: `401 Unauthorized` 或 `403 Forbidden`

**解决**:
1. 重新生成API keys
2. 检查API权限和scope
3. 验证refresh token是否过期
4. 查看API提供商的状态页

### 问题5: Webhook不触发

**错误**: Webhook请求无响应

**解决**:
```bash
# 检查n8n是否运行
curl http://localhost:5678/healthz

# 检查webhook路径
# 在n8n中查看Webhook节点的URL

# 测试webhook
curl -X POST <webhook-url> -H "Content-Type: application/json" -d '{}'
```

---

## 📈 性能优化

### 1. PostgreSQL优化

```sql
-- 增加连接池
ALTER SYSTEM SET max_connections = 200;

-- 增加共享内存
ALTER SYSTEM SET shared_buffers = '2GB';

-- 重启PostgreSQL
SELECT pg_reload_conf();
```

### 2. Redis优化

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
```

### 3. n8n优化

```bash
# 环境变量
export N8N_PAYLOAD_SIZE_MAX=16  # MB
export EXECUTIONS_DATA_PRUNE=true
export EXECUTIONS_DATA_MAX_AGE=168  # 7天
export N8N_LOG_LEVEL=info
```

---

## 🔒 生产环境检查清单

部署到生产环境前，请确认：

- [ ] 所有默认密码已更改
- [ ] 启用HTTPS (使用nginx/caddy反向代理)
- [ ] 配置防火墙规则
- [ ] 启用n8n身份验证
- [ ] API keys定期轮换（建议90天）
- [ ] 配置数据库自动备份（每日）
- [ ] 设置审计日志保留策略（建议90天）
- [ ] 配置速率限制
- [ ] 加密敏感数据
- [ ] 遵守GDPR/CCPA等法规
- [ ] 配置监控告警（Grafana/Prometheus）
- [ ] 准备灾难恢复计划

---

## 📚 下一步

- 阅读 [API集成指南](api-integration-guide.md)
- 阅读 [求职演示指南](../求职演示指南.md)
- 查看 [架构设计文档](../跨境电商全栈智能系统_架构设计.md)

---

**最后更新**: 2026-02-03
**版本**: 1.0.0
