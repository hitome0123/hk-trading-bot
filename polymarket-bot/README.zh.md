# 🎯 Polymarket高胜率跟单机器人

基于Sharp交易员识别 + 凯利准则 + 多层风险管理的自动化跟单系统

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📊 核心特性

- ✅ **Sharp交易员识别**：自动跟随70%+胜率的顶级交易员（如Erasmus）
- ✅ **凯利准则仓位管理**：科学计算最优下注金额（半凯利/四分之一凯利）
- ✅ **4层风险防护**：仓位限制 + 熔断器 + 交易员监控 + 市场质量过滤
- ✅ **实时Telegram通知**：详细推送交易建议（赔率、胜率、预估收益）
- ✅ **模拟交易模式**：无风险测试策略
- ✅ **多用户支持**：一键分享推送给朋友

## 🎓 方法论来源

基于 **skill-from-masters** 收集的顶级专家方法论：
- **Ed Thorp**：凯利准则发明者，数学家，对冲基金传奇
- **Larry Williams**：交易大赛冠军，风险管理专家
- **Nate Silver**：预测市场分析大师

---

## 📦 快速开始

### 前置要求

- Python 3.8+
- Telegram账号
- Polymarket账号（如需真实交易）

### 安装步骤

```bash
# 1. 进入项目目录
cd /path/to/polymarket-bot

# 2. 安装依赖
pip3 install -r requirements-core.txt

# 3. 配置环境变量
echo "WALLET_PRIVATE_KEY=0x你的私钥" > .env

# 4. 编辑配置文件（见下方详细步骤）
cp config.example.yaml config.yaml
vim config.yaml

# 5. 启动bot（模拟模式）
python3 main.py
```

---

## ⚙️ 配置指南

### 第1步：创建Telegram Bot

1. 在Telegram搜索 `@BotFather`
2. 发送 `/newbot` 创建新bot
3. 获取 `bot_token`（类似：`1234567890:AAGxxxxxxxxxxxxxxx`）
4. 保存bot用户名（如 `@MyPolymarketBot`）

### 第2步：获取Chat ID

```bash
# 先给你的bot发送 /start
# 然后运行
python3 src/get_chat_id.py
```

会输出你的 `chat_id`（如：`7082819163`）

### 第3步：编辑 config.yaml

打开 `config.yaml`，修改以下关键配置：

```yaml
# ===== Telegram通知配置 =====
notifications:
  telegram:
    enabled: true
    bot_token: "你的bot_token"  # ← 第1步获取的
    chat_id: "你的chat_id"      # ← 第2步获取的

# ===== 模拟交易设置 =====
paper_trading:
  enabled: true              # 首次运行必须设为true
  initial_balance: 10000     # 模拟起始资金$10,000

# ===== 风险管理 =====
risk_management:
  max_per_trade_pct: 0.10    # 单笔最大10%
  max_total_exposure_pct: 0.30  # 总敞口30%
  max_slippage_pct: 0.15     # 最大滑点15%

# ===== 凯利准则 =====
kelly_sizing:
  use_half_kelly: true       # 半凯利（保守）
  max_bet_pct: 0.10          # 单笔上限10%
  min_edge_pct: 0.02         # 最小Edge 2%
```

### 第4步：添加Sharp交易员

编辑 `main.py`，找到这一行（第112行左右）：

```python
# Sharp交易员地址列表
self.sharp_traders = [
    "0xc6587b11a2209e46dfe3928b31c5514a8e33b784",  # Erasmus
    # 可以添加更多Sharp交易员地址
]
```

**推荐的Sharp交易员**：
- **Erasmus**: `0xc6587b11a2209e46dfe3928b31c5514a8e33b784`
  - 专长：政治+宏观预测
  - 累计利润：$1.3M+
  - 更多交易员：[Polymarket Leaderboard](https://polymarket.com/leaderboard)

### 第5步：设置私钥（真实交易时）

⚠️ **模拟模式可跳过此步**

```bash
# 编辑 .env 文件
echo "WALLET_PRIVATE_KEY=0x你的私钥" > .env
```

**安全提醒**：
- ❌ 绝不要把私钥写在config.yaml
- ❌ 绝不要提交.env到git
- ✅ 只通过环境变量加载私钥

---

## 🚀 启动Bot

### 方式1：前台运行（推荐测试时使用）

```bash
python3 main.py
```

**输出示例**：
```
================================================================================
  🎯 Polymarket高胜率跟单机器人
  📊 基于Sharp交易员识别 + 凯利准则 + 多层风险管理
================================================================================

✓ Sharp交易员识别器
✓ 凯利准则计算器
✓ 风险管理器
✓ Telegram通知器
✓ 已加载1个Sharp交易员
✓ 交易执行引擎

🚀 Polymarket跟单机器人启动！
 模式: 🎮 模拟交易
 Sharp交易员: 1个
 轮询间隔: 4秒
 凯利模式: 半凯利
 单笔上限: 10%
 总敞口上限: 30%
================================================================================
```

### 方式2：后台运行（推荐生产时使用）

```bash
# 启动
nohup python3 main.py > logs/bot_live.log 2>&1 &

# 查看日志
tail -f logs/bot_live.log

# 停止
pkill -9 -f "python3 main.py"
```

### 便捷脚本

已为你创建快捷脚本：

```bash
# 重启bot
./restart_bot.sh

# 检查新用户（添加朋友时用）
./check_friends.sh
```

---

## 📱 Telegram推送示例

### 启动通知
```
🚀 Polymarket Bot 已启动

📊 配置信息
━━━━━━━━━━━━━━━━━━━━
• 模式: 🎮 模拟交易
• Sharp交易员: 1个
• 初始余额: $10,000
• 轮询间隔: 4秒

⏰ 2026-01-27 13:09:08
```

### 交易推荐（✅ 通过风险验证）
```
✅ 交易推荐
🟢━━━━━━━━━━━━━━━━━━━━

📊 市场
Khamenei out as supreme leader

📈 盘口详情
• 方向: No
• 当前价格: $0.490
• 隐含概率: 49.0%

👤 Sharp交易员
0xc6587b...33b784
• 历史胜率: 75.0%

💰 凯利推荐
• 下注金额: $900.00
• 凯利分数: 0.255
• 账户比例: 9.0%

📊 赔率分析
• 市场赔率: 0.490
• Sharp胜率: 75.0%
• Edge优势: +26.0%

💵 预估收益
• 赢时收益: $936.73
• ROI: 104.1%
• 输时损失: -$900.00

💡 逻辑
Sharp trader win rate: 75.0%
Market odds: 49.0%
Full Kelly: 0.510, Half Kelly: 0.255
Half Kelly策略

⏰ 13:09:18
```

### 风险拒绝通知（❌ 未通过）
```
❌ 风险拒绝
🔴━━━━━━━━━━━━━━━━━━━━

📊 市场
Iranian regime fall

⚠️ 拒绝原因
━━━━━━━━━━━━━━━━━━━━
• Excessive slippage: 40.2% > 15.0%
  (Sharp trader: 0.460, Current: 0.645)

⏰ 13:09:17
```

---

## 👥 添加多个用户（分享推送给朋友）

### 步骤1：朋友发送 /start

**分享这个链接给朋友**：
```
https://t.me/你的bot用户名
```

例如：`https://t.me/AskTokenBot`

让朋友点击并发送 `/start`

### 步骤2：获取朋友的chat_id

朋友发送后，你运行：

```bash
./check_friends.sh
```

**输出示例**：
```
✅ 找到 2 个对话

用户 1:
  Chat ID: 7082819163
  姓名: kitty

用户 2:
  Chat ID: 8286305017
  姓名: Alina Xie

📋 复制下面这行到 config.yaml 的 chat_id 字段：
chat_id: "7082819163,8286305017"
```

### 步骤3：更新配置并重启

1. 复制输出的 `chat_id` 那一行
2. 粘贴到 `config.yaml` 的 `telegram.chat_id` 字段
3. 运行 `./restart_bot.sh`

完成！所有用户都会同时收到推送。

**验证**：Bot重启时，所有用户都会收到启动通知。

---

## 🛡️ 风险管理机制

### 4层防护体系

**第1层：仓位限制**
- 单笔最大：10%（可配置）
- 总敞口：30%
- 单市场：15%
- 单交易员：20%

**第2层：熔断器**
- 日亏损超10%自动停止
- 连续5次亏损暂停

**第3层：交易员监控**
- Sharp交易员回撤20%停止跟随
- API错误超10次暂停

**第4层：市场质量过滤**
- 最小流动性$10K
- 滑点限制15%
- 交易延迟<5分钟

### 凯利准则仓位计算

使用 **半凯利公式**（比全凯利保守50%）：

```
凯利分数 = (胜率 × 赔率 - (1 - 胜率)) / 赔率
推荐仓位 = 账户余额 × 凯利分数 × 0.5
```

**示例计算**：
- Sharp交易员胜率：75%
- 市场赔率：0.49（隐含概率49%）
- 账户余额：$10,000

```
市场赔付比 = 1 / 0.49 = 2.04
凯利分数 = (0.75 × 2.04 - 0.25) / 2.04 = 0.51
半凯利 = 0.51 × 0.5 = 0.255 (25.5%)
推荐金额 = $10,000 × 0.255 = $2,550

实际下注 = min($2,550, $1,000) = $1,000
# 受config.yaml中max_per_trade_usd: 1000限制
```

---

## 🔍 监控与调试

### 查看日志

```bash
# 实时日志
tail -f logs/bot_live.log

# 最近100行
tail -100 logs/bot_live.log

# 搜索关键词
grep "✅" logs/bot_live.log      # 查看成功的订单
grep "❌" logs/bot_live.log      # 查看被拒绝的交易
grep "凯利计算" logs/bot_live.log  # 查看凯利计算过程
grep "Telegram" logs/bot_live.log  # 查看推送记录
```

### 检查运行状态

```bash
# 检查进程是否运行
ps aux | grep "python3 main.py" | grep -v grep

# 查看已配置用户
./check_friends.sh
```

### Bot运行统计

从日志中可以看到：
- 检测到的仓位数
- 凯利推荐次数
- 风险拒绝次数
- 执行的交易数
- 模拟账户余额

---

## 🐛 常见问题

### Q1: Bot启动后没有推送？

**检查清单**：

1. **Telegram配置是否正确**？
   ```bash
   grep "telegram" config.yaml
   ```

2. **Bot token是否有效**？
   ```bash
   # 测试token（替换YOUR_TOKEN）
   curl https://api.telegram.org/botYOUR_TOKEN/getMe
   ```

3. **是否给bot发送过 /start**？
   必须先给bot发送 `/start`，bot才能主动推送

### Q2: 所有交易都被拒绝？

**可能原因**：

1. **负凯利分数**（最常见）
   - 原因：Sharp交易员胜率假设为75%，但市场赔率>75%时没有Edge
   - 示例：市场赔率98% > 胜率75% → 无优势 → 跳过
   - 解决：等待新交易机会，或降低 `min_edge_pct`

2. **滑点过大**
   - 原因：Sharp交易员买入价 vs 当前市场价差异超过15%
   - 示例：Sharp买入0.45，当前0.65，滑点44% > 15%上限
   - 解决：提高 `max_slippage_pct` 到0.20（20%）

3. **价格数据异常**
   - 原因：部分市场价格为0或>0.99
   - 解决：这些市场会自动跳过，属于正常现象

### Q3: 如何切换到真实交易？

⚠️ **风险警告**：真实交易会使用真金白银，请确保：
- ✅ 已充分测试模拟模式（建议1个月以上）
- ✅ 理解凯利准则和风险管理原理
- ✅ 准备好承受可能的损失
- ✅ 从小资金开始（建议≤$500）

**切换步骤**：

1. 修改 `config.yaml`：
```yaml
paper_trading:
  enabled: false  # ← 改为false启用真实交易
```

2. 设置真实私钥：
```bash
echo "WALLET_PRIVATE_KEY=0x你的真实私钥" > .env
```

3. 配置代理钱包地址：
```yaml
wallet:
  proxy_wallet_address: "0x你的Polymarket代理钱包"
```

4. 配置区块链RPC（建议用付费服务如Infura）：
```yaml
blockchain:
  rpc_url: "https://polygon-mainnet.infura.io/v3/你的项目ID"
```

### Q4: 如何调整仓位大小？

**更保守策略**（推荐新手）：
```yaml
# config.yaml
kelly_sizing:
  use_half_kelly: false      # 关闭半凯利
  use_quarter_kelly: true    # 启用四分之一凯利（更保守）
  max_bet_pct: 0.05          # 降低单笔上限到5%

risk_management:
  max_per_trade_usd: 500     # 降低单笔美元上限
  max_total_exposure_pct: 0.20  # 降低总敞口到20%
```

**更激进策略**（不推荐新手）：
```yaml
kelly_sizing:
  use_half_kelly: true       # 半凯利
  max_bet_pct: 0.15          # 提高到15%

risk_management:
  max_total_exposure_pct: 0.40  # 提高到40%
```

### Q5: 如何暂停bot？

```bash
# 临时暂停（进程还在，只是停止运行）
pkill -STOP -f "python3 main.py"

# 恢复运行
pkill -CONT -f "python3 main.py"

# 完全停止
pkill -9 -f "python3 main.py"
```

### Q6: 如何备份配置？

```bash
# 备份所有配置和日志
tar -czf polymarket-bot-backup-$(date +%Y%m%d).tar.gz \
  config.yaml \
  .env \
  logs/ \
  main.py \
  src/

# 恢复
tar -xzf polymarket-bot-backup-20260127.tar.gz
```

### Q7: API限流怎么办？

Polymarket免费API有限流。如遇到：

```yaml
# config.yaml - 降低轮询频率
polling:
  position_check_seconds: 10  # 从4秒改为10秒
```

或升级到付费RPC服务（Infura/Alchemy）。

---

## 📁 项目结构

```
polymarket-bot/
├── README.md                    # 英文文档
├── README.zh.md                 # 中文文档（本文件）
├── 如何添加新用户.md              # 多用户配置指南
├── config.yaml                  # 主配置文件
├── .env                         # 环境变量（私钥）
├── main.py                      # 主程序入口
├── requirements-core.txt        # Python依赖
├── restart_bot.sh               # 重启脚本
├── check_friends.sh             # 检查用户脚本
│
├── src/                         # 源代码目录
│   ├── config.py                # 配置加载器
│   ├── sharp_trader_identifier.py  # Sharp交易员识别
│   ├── kelly_criterion.py       # 凯利准则计算
│   ├── risk_manager.py          # 风险管理器
│   ├── trade_executor.py        # 交易执行引擎
│   ├── telegram_notifier.py     # Telegram通知
│   ├── utils.py                 # 工具函数
│   └── get_chat_id.py           # Chat ID获取工具
│
└── logs/                        # 日志文件夹
    └── bot_live.log             # 运行日志
```

---

## 📊 技术架构

```
┌─────────────────────────────────────────────┐
│         Polymarket跟单Bot架构                │
└─────────────────────────────────────────────┘

┌──────────────┐
│  main.py     │  主程序入口，初始化所有组件
└──────┬───────┘
       │
       ├─► ┌───────────────────────────┐
       │   │ sharp_trader_identifier   │  识别Sharp交易员
       │   │ • API获取交易历史          │
       │   │ • 计算胜率/ROI/一致性       │
       │   └───────────────────────────┘
       │
       ├─► ┌───────────────────────────┐
       │   │ kelly_criterion           │  凯利准则计算
       │   │ • 计算Edge优势            │
       │   │ • 半凯利/四分之一凯利       │
       │   │ • 应用仓位上限             │
       │   └───────────────────────────┘
       │
       ├─► ┌───────────────────────────┐
       │   │ risk_manager              │  4层风险验证
       │   │ • 仓位限制检查             │
       │   │ • 熔断器状态               │
       │   │ • 市场质量过滤             │
       │   │ • 滑点检查                │
       │   └───────────────────────────┘
       │
       ├─► ┌───────────────────────────┐
       │   │ trade_executor            │  交易执行引擎
       │   │ ├─ 每4秒轮询Sharp仓位      │
       │   │ ├─ 调用凯利计算           │
       │   │ ├─ 调用风险验证           │
       │   │ └─ 执行模拟/真实订单       │
       │   └───────────────────────────┘
       │
       └─► ┌───────────────────────────┐
           │ telegram_notifier         │  Telegram推送
           │ ├─ 启动通知               │
           │ ├─ 交易推荐（详细）         │
           │ ├─ 风险拒绝               │
           │ └─ 订单执行结果            │
           │ • 支持多用户同时推送        │
           └───────────────────────────┘

外部API调用：
  • Polymarket Data API    - 获取市场价格和交易数据
  • PolyTrack API          - 获取交易员历史表现
  • Polygon RPC            - 区块链交易（真实交易时）
  • Telegram Bot API       - 推送通知
```

---

## 📚 学习资源

### 凯利准则
- [Ed Thorp - The Kelly Criterion](https://en.wikipedia.org/wiki/Kelly_criterion)
- [Fortune's Formula (书籍)](https://www.amazon.com/Fortunes-Formula-Scientific-Betting-Casinos/dp/0809045990)
- [凯利公式详解（中文）](https://zhuanlan.zhihu.com/p/34919982)

### 预测市场
- [Polymarket 文档](https://docs.polymarket.com/)
- [Nate Silver - The Signal and the Noise](https://www.amazon.com/Signal-Noise-Many-Predictions-Fail-but/dp/0143125087)

### 风险管理
- [Larry Williams - Long-Term Secrets](https://www.amazon.com/Long-Term-Secrets-Short-Term-Trading/dp/0470915730)

---

## ⚠️ 免责声明

1. **投资风险**：预测市场交易存在风险，可能损失全部本金
2. **无收益保证**：过去的表现不代表未来收益
3. **仅供教育**：本项目仅用于学习研究，不构成投资建议
4. **自负责任**：使用本软件的所有后果由用户自行承担
5. **遵守法律**：请确保在你所在地区使用Polymarket合法

**Polymarket可用性**：
- ❌ 不可用地区：美国、英国等部分国家
- ✅ 使用前请检查当地法律法规

---

## 🤝 贡献与改进

欢迎提交Issue和Pull Request！

**开发计划**：
- [ ] 支持更多Sharp交易员
- [ ] Web监控面板
- [ ] 机器学习优化胜率预测
- [ ] 自动止盈止损
- [ ] Discord推送支持

---

## 📞 支持

- **Telegram Bot**: [@AskTokenBot](https://t.me/AskTokenBot)
- **问题反馈**: 提交GitHub Issue
- **使用讨论**: 加入Telegram群组

---

## 📄 开源协议

MIT License

---

## 🙏 致谢

**方法论来源**：
- skill-from-masters framework
- Ed Thorp: Kelly Criterion数学
- Larry Williams: 交易系统设计
- Polymarket社区: Sharp交易员研究

**技术栈**：
- Python 3.8+
- py-clob-client (Polymarket交易)
- httpx (异步HTTP)
- structlog (日志)
- pyyaml (配置)

---

**⚠️ 记住：先从模拟交易开始，充分测试后再考虑真实交易，永远不要投入超过你能承受损失的资金。**

**🚀 祝交易顺利！**

---

最后更新：2026-01-27
