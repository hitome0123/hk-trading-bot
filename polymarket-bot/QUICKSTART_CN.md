# Polymarket跟单机器人 - 快速启动指南

## 🚀 5分钟快速开始

### 第一步：安装依赖

```bash
cd polymarket-bot

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 第二步：配置

```bash
# 1. 复制配置模板
cp config.example.yaml config.yaml

# 2. 设置环境变量（私钥）
export WALLET_PRIVATE_KEY="0x你的私钥"

# 或者创建.env文件：
echo "WALLET_PRIVATE_KEY=0x你的私钥" > .env
```

### 第三步：编辑配置文件

编辑 `config.yaml`：

```yaml
# 1. 配置钱包地址（不要填私钥！）
wallet:
  proxy_wallet_address: "0x你的Polymarket代理钱包地址"

# 2. 配置RPC（从Infura或Alchemy获取）
blockchain:
  rpc_url: "https://polygon-mainnet.infura.io/v3/你的PROJECT_ID"

# 3. 确保开启模拟交易（首次运行）
paper_trading:
  enabled: true
  initial_balance: 10000
```

### 第四步：获取Sharp交易员地址

1. 访问 [Polymarket排行榜](https://polymarket.com/leaderboard)
2. 复制前几名交易员的钱包地址
3. 在 `main.py` 中添加：

```python
# main.py 第97行左右
self.sharp_traders = [
    "0xABC123...",  # 第1名交易员
    "0xDEF456...",  # 第2名交易员
]
```

### 第五步：运行！

```bash
python main.py
```

你应该看到：

```
================================================================================
  🎯 Polymarket高胜率跟单机器人
  📊 基于Sharp交易员识别 + 凯利准则 + 多层风险管理
  🔬 方法论来源: skill-from-masters (Ed Thorp, Larry Williams)
================================================================================

🚀 Polymarket跟单机器人启动！
================================================================================
 模式: 🎮 模拟交易
 Sharp交易员: 2个
 轮询间隔: 4秒
 凯利模式: 半凯利
 单笔上限: 10%
 总敞口上限: 30%
================================================================================
⚠️  当前为模拟交易模式，不会执行真实订单
```

---

## ⚠️ 重要提示

### 首次运行必读

1. **必须使用模拟交易**：
   - 首次运行设置 `paper_trading: true`
   - 运行至少1个月，验证策略有效

2. **不要直接上真实资金**：
   - 模拟交易胜率达70%+
   - 无熔断器触发
   - 理解所有风险

3. **私钥安全**：
   - **永远不要**把私钥放在config.yaml
   - 使用环境变量
   - 不要提交到git

### 获取Infura RPC URL

1. 访问 [infura.io](https://infura.io)
2. 注册并创建项目
3. 选择 Polygon 网络
4. 复制 HTTP URL：`https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID`

### 获取Polymarket代理钱包

1. 访问 [Polymarket](https://polymarket.com)
2. 连接MetaMask或Phantom钱包
3. 查看你的Profile页面
4. 复制你的Polymarket代理钱包地址（不是你的MetaMask地址！）

---

## 📊 运行后查看

### 查看状态

```bash
# 检查当前持仓
python scripts/check_positions.py

# 查看性能报告
python scripts/performance_report.py
```

### 日志位置

```
logs/polymarket_bot.log
```

### 监控指标

机器人会显示：
- ✅ 成功的交易
- ⏳ 等待中的订单
- 🟢🟡🔴 风险等级
- 🚨 熔断器状态
- 💰 当前余额和P&L

---

## 🆘 常见问题

### Q: 找不到config.yaml?
A: 复制 `cp config.example.yaml config.yaml`

### Q: 环境变量未设置?
A: `export WALLET_PRIVATE_KEY="0x..."`

### Q: Sharp交易员列表为空?
A: 在main.py中手动添加地址（从polymarket.com/leaderboard获取）

### Q: API限流错误?
A: 降低轮询频率：`position_check_seconds: 10` （在config.yaml）

### Q: 想测试不想等?
A: 设置更短的轮询间隔，但注意API限制

---

## 📚 进阶使用

### 使用Telegram通知

```yaml
notifications:
  telegram:
    enabled: true
    bot_token: "从@BotFather获取"
    chat_id: "你的chat_id"
```

### 调整风险参数

```yaml
risk_management:
  max_per_trade_pct: 0.05  # 降低到5%（更保守）
  daily_loss_limit_pct: 0.05  # 日亏5%就停
```

### 添加更多Sharp交易员

```python
self.sharp_traders = [
    "0x...",  # 前10名
    "0x...",
    "0x...",
    # 最多跟踪10-20个
]
```

---

## 🔒 安全检查清单

上线前必须确认：

- [ ] `paper_trading: true`（模拟模式）
- [ ] 私钥在环境变量，不在config.yaml
- [ ] config.yaml在.gitignore中
- [ ] 已测试至少1个月
- [ ] 理解所有风险参数
- [ ] Sharp交易员地址已验证
- [ ] RPC URL可用
- [ ] 钱包有足够MATIC（gas费）

---

## 📞 获取帮助

- 查看完整文档：`README.md`
- 代码审查报告：`CODE_REVIEW.md`
- 安全审计：`SECURITY_AUDIT.md`
- 系统架构：`ARCHITECTURE.md`

---

**祝交易顺利！记住：先模拟，后真实。谨慎投资！** 🚀
