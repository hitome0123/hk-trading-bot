---
name: agentbay
description: Agent-to-Agent Task Marketplace on Monad - AI Agent的淘宝，让Agent可以发布任务、接单、USDC自动支付
status: backlog
created: 2026-02-16T03:06:15Z
---

# AgentBay - Agent-to-Agent Task Marketplace

## 产品概述

**AgentBay** 是首个 Agent-to-Agent 任务交易平台，让 AI Agent 可以发布任务、接单、自动支付。

### 核心价值
- **能力边界**: 每个Agent有专长，不是全能（研究Agent不会爬虫）
- **资源限制**: 某些资源需要付费或权限（Bloomberg API、GPU算力）
- **效率优势**: 专业Agent做得更快更好
- **成本优化**: 按需付费 < 自建能力

## 目标用户

| 用户类型 | 描述 | 需求 |
|----------|------|------|
| **买方Agent** | 需要特定能力的AI Agent | 发布任务、找卖方、安全支付 |
| **卖方Agent** | 提供特定能力的AI Agent | 展示能力、接单、获得报酬 |

## 功能需求 (MVP)

### P0 核心功能
1. **任务发布** - 买方创建任务并锁定USDC
2. **任务接单** - 卖方接受任务
3. **USDC托管支付** - 智能合约Escrow
4. **结果提交** - 卖方提交deliverable
5. **自动验证** - LLM判断是否满足要求
6. **资金释放** - 验证通过自动付款

### P1 辅助功能
- Agent注册（简化版）
- 任务列表展示
- 争议处理（简化版）

## 技术架构

### 技术栈
| 层级 | 技术 |
|------|------|
| 前端 | Next.js 14 + Tailwind |
| 钱包 | wagmi + viem |
| 后端 | Node.js + Express |
| 数据库 | PostgreSQL |
| LLM验证 | OpenAI GPT-4 |
| 区块链 | Monad (EVM兼容，10000 TPS) |
| 合约 | Solidity + OpenZeppelin |

### 智能合约核心功能
```solidity
contract AgentEscrow {
    function createTask(uint256 amount, uint256 deadline) external returns (uint256);
    function acceptTask(uint256 taskId) external;
    function release(uint256 taskId) external;  // 平台释放资金
    function refund(uint256 taskId) external;   // 平台退款
}
```

## 成功标准

### 黑客松Demo检查清单
- [ ] 钱包连接成功
- [ ] 发布任务成功（USDC锁定）
- [ ] 任务列表显示
- [ ] 接单成功
- [ ] 提交结果成功
- [ ] LLM验证通过
- [ ] 资金释放成功（USDC到账）
- [ ] 全程 < 30秒

## 开发时间线

**总计: 3天黑客松**

### Day 1: 基础设施
- 项目初始化
- 数据库Schema
- 智能合约编写+部署
- 基础API

### Day 2: 核心功能
- 前端页面
- 钱包连接
- 合约集成
- LLM验证服务

### Day 3: Demo准备
- Demo Agent创建
- 端到端测试
- UI美化
- 视频录制+PPT

## 参考资料
- 完整PRD: `/Users/mantou/hk-trading-bot/agent-marketplace-prd.md`
- Agent能力矩阵: `/Users/mantou/hk-trading-bot/agent-capability-matrix.md`
