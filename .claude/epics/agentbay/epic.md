---
name: agentbay
status: in-progress
created: 2026-02-16T03:07:33Z
progress: 0%
prd: .claude/prds/agentbay.md
github: https://github.com/hitome0123/agentbay/issues/1
---

# Epic: AgentBay - Agent-to-Agent Task Marketplace

## Overview

构建首个 Agent-to-Agent 任务交易平台，部署在 Monad 链上。核心是一个 USDC Escrow 智能合约 + LLM 自动验证系统，让 AI Agent 可以发布任务、接单、自动支付。

**技术核心**：
- Solidity Escrow 合约处理 USDC 托管
- GPT-4 验证交付物质量
- Next.js 前端 + Node.js 后端
- 3天内完成可演示 MVP

## Architecture Decisions

| 决策 | 选择 | 理由 |
|------|------|------|
| **区块链** | Monad Testnet | 10,000 TPS, 0.8s确认, EVM兼容, 原生USDC |
| **支付代币** | USDC | 稳定币，Agent友好，Circle原生支持 |
| **合约模式** | 单一Escrow | MVP简化，避免多合约复杂性 |
| **验证方式** | GPT-4 LLM | 灵活判断交付物质量，无需预定义规则 |
| **前端框架** | Next.js 14 | SSR快速，wagmi钱包集成成熟 |
| **数据库** | PostgreSQL | 可靠，JSON支持好 |

## Technical Approach

### Frontend Components
```
src/
├── app/
│   ├── page.tsx           # 首页/任务大厅
│   ├── tasks/
│   │   ├── page.tsx       # 任务列表
│   │   ├── new/page.tsx   # 发布任务
│   │   └── [id]/page.tsx  # 任务详情
│   └── layout.tsx         # 全局布局+钱包Provider
├── components/
│   ├── TaskCard.tsx       # 任务卡片
│   ├── TaskForm.tsx       # 发布表单
│   ├── WalletButton.tsx   # 连接钱包
│   └── VerifyStatus.tsx   # 验证状态
└── hooks/
    └── useContract.ts     # 合约交互Hook
```

### Backend Services
```
server/
├── routes/
│   ├── tasks.ts           # 任务CRUD
│   ├── agents.ts          # Agent注册
│   └── verify.ts          # LLM验证
├── services/
│   ├── llmVerifier.ts     # GPT-4验证逻辑
│   └── blockchain.ts      # 链上交互
└── db/
    └── schema.sql         # 数据库Schema
```

### Smart Contract
```solidity
// contracts/AgentEscrow.sol
- createTask(amount, deadline) → 锁定USDC
- acceptTask(taskId) → 卖方接单
- release(taskId) → 平台释放资金
- refund(taskId) → 平台退款
- claimExpired(taskId) → 过期自动退款
```

### Infrastructure
- **前端部署**: Vercel (免费，快速)
- **后端部署**: Railway (简单，自动HTTPS)
- **数据库**: Railway PostgreSQL
- **合约**: Monad Testnet

## Implementation Strategy

### Phase 1: 基础设施 (Day 1)
1. 初始化 Next.js + Node.js 项目
2. 部署 PostgreSQL，创建 Schema
3. 编写 AgentEscrow.sol 合约
4. 部署合约到 Monad Testnet
5. 实现基础 Task CRUD API

### Phase 2: 核心功能 (Day 2)
1. 前端任务列表 + 发布页面
2. wagmi 钱包连接集成
3. 合约读写功能
4. LLM 验证服务
5. 端到端流程联调

### Phase 3: Demo 准备 (Day 3)
1. 创建 2 个 Demo Agent (买方+卖方)
2. 自动化交易脚本
3. UI 美化
4. 录制 Demo 视频
5. 准备 Pitch PPT

## Task Breakdown Preview

- [ ] **Task 1: 项目初始化** - Next.js + Node.js + PostgreSQL 搭建
- [ ] **Task 2: 智能合约** - AgentEscrow.sol 编写 + 部署到 Monad
- [ ] **Task 3: 后端API** - Task CRUD + Agent 注册接口
- [ ] **Task 4: 前端页面** - 任务列表 + 发布 + 详情页
- [ ] **Task 5: 钱包集成** - wagmi 连接 + 合约交互
- [ ] **Task 6: LLM验证** - GPT-4 验证服务 + 自动释放
- [ ] **Task 7: Demo Agent** - 买方/卖方Agent脚本
- [ ] **Task 8: 演示准备** - 视频录制 + PPT

## Dependencies

### 外部依赖
- Monad Testnet RPC (需要申请)
- Monad Testnet USDC (水龙头)
- OpenAI API Key (GPT-4 验证)
- Vercel / Railway 账号

### 技术依赖
- Node.js 18+
- PostgreSQL 14+
- Solidity 0.8.20
- OpenZeppelin Contracts

## Success Criteria (Technical)

| 指标 | 目标 |
|------|------|
| 合约部署 | Monad Testnet 成功部署 |
| 交易时间 | createTask → release < 30秒 |
| LLM验证 | 准确率 > 90% |
| 页面加载 | < 2秒 |
| Demo流程 | 端到端无人工干预 |

## Estimated Effort

| 任务 | 预估时间 |
|------|----------|
| 项目初始化 | 2h |
| 智能合约 | 3h |
| 后端API | 3h |
| 前端页面 | 4h |
| 钱包集成 | 2h |
| LLM验证 | 2h |
| Demo Agent | 2h |
| 演示准备 | 3h |
| **总计** | **21h (3天)** |

## Risk Mitigation

| 风险 | 应对 |
|------|------|
| Monad Testnet 不稳定 | 准备 Base Sepolia 作为备选 |
| LLM 验证不准 | 准备人工验证兜底按钮 |
| USDC 水龙头问题 | 使用 Mock ERC20 代替 |
| 时间不够 | 砍掉 Agent 注册，硬编码 2 个 Demo Agent |

---

## Tasks Created

| # | 任务 | 预估 | 依赖 | 并行 |
|---|------|------|------|------|
| #2 | 项目初始化 - Next.js + Node.js + PostgreSQL | 2h | - | ✅ |
| #3 | 智能合约 - AgentEscrow.sol 编写与部署 | 3h | #2 | ❌ |
| #4 | 后端API - Task CRUD + Agent 注册 | 3h | #2 | ✅ |
| #5 | 前端页面 - 任务列表 + 发布 + 详情 | 4h | #2 | ✅ |
| #6 | 钱包集成 - wagmi 连接 + 合约交互 | 2h | 3, 5 | ❌ |
| #7 | LLM验证 - GPT-4 验证服务 + 自动释放 | 2h | #4 | ❌ |
| #8 | Demo Agent - 买方/卖方Agent脚本 | 2h | 4, 6, 7 | ❌ |
| #9 | 演示准备 - 视频录制 + PPT | 3h | #8 | ❌ |

**总计: 8 个任务**
- 可并行任务: 3 个 (001, 003, 004)
- 顺序任务: 5 个
- 预估总工时: 21 小时

### 执行顺序建议

```
Day 1 (8h):
  001 项目初始化 (2h)
  ├── 002 智能合约 (3h) ─┐
  ├── 003 后端API (3h) ──┼── 并行
  └── 004 前端页面 (开始)┘

Day 2 (8h):
  004 前端页面 (完成, 4h)
  005 钱包集成 (2h)
  006 LLM验证 (2h)

Day 3 (5h):
  007 Demo Agent (2h)
  008 演示准备 (3h)
```
