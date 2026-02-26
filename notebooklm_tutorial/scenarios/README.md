# Claude Financial Skills + NotebookLM 实战教程

## 📚 项目概览

**完整的金融分析实战教程** - 通过 23 个真实案例，掌握 Anthropic 官方 5 大金融插件的使用方法。

### 核心特色

- 🎯 **实战驱动**: 每个场景都基于真实交易案例，不只是理论讲解
- 🧰 **技能覆盖**: 涵盖 DCF/Comps/Earnings/3-Statements/TAM 等 42 个金融技能
- 🌐 **全市场**: 港股 + 美股 + A股 + 跨市场，完整覆盖全球主要市场
- 🤖 **NotebookLM 增强**: 利用 AI 问答、笔记生成、深度提问功能加深理解
- 📊 **循序渐进**: 从基础到专家，5 个难度等级，适合不同水平投资者

### 学习方法

1. **选择场景** - 根据难度或兴趣选择场景
2. **理解背景** - 阅读背景故事，代入真实交易情境
3. **动手调用** - 在 Claude Code 中调用对应的 Financial Skills
4. **深度思考** - 使用 NotebookLM Q&A 功能深化理解
5. **实战应用** - 用学到的方法分析自己关注的股票

---

## 🗂️ 场景导航

### 🇭🇰 港股场景 (8 个)

| # | 场景名称 | 难度 | 核心技能 | 股票 |
|---|----------|------|----------|------|
| 1 | 阿里巴巴抄底时机 | ⭐⭐ | DCF 估值, Sum-of-Parts | 09988.HK |
| 2 | 腾讯控股分红策略 | ⭐⭐⭐ | Dividend Analysis | 00700.HK |
| 3 | 小米汽车催化剂 | ⭐⭐⭐ | Catalyst Calendar | 01810.HK |
| 4 | 海致科技卖出时机 | ⭐⭐⭐⭐ | 3-Statements, DCF | 06820.HK |
| 6 | 中国移动 vs 电信 vs 联通 | ⭐⭐⭐ | Comps Analysis | 00941, 00728, 00762 |
| 7 | 港交所新规影响 | ⭐⭐⭐⭐ | Event Impact | 00388.HK |
| 10 | 比亚迪 vs 理想汽车 | ⭐⭐⭐⭐ | Cross-Border Comps | 01211.HK, LI |
| 15 | 药明生物 vs 康龙化成 | ⭐⭐⭐⭐ | Sector Comps | 02269, 03759 |

### 🇺🇸 美股场景 (8 个)

| # | 场景名称 | 难度 | 核心技能 | 股票 |
|---|----------|------|----------|------|
| 5 | 英伟达财报超预期 | ⭐⭐⭐ | Earnings Analysis | NVDA |
| 8 | 特斯拉产能爬坡 | ⭐⭐⭐⭐ | Catalyst Analysis | TSLA |
| 11 | 苹果发布会交易 | ⭐⭐⭐ | Event-Driven | AAPL |
| 12 | Palantir 卖出时机 | ⭐⭐⭐⭐⭐ | 3-Statements, Valuation | PLTR |
| 13 | AI 板块泡沫识别 | ⭐⭐⭐⭐⭐ | Sector Comps, Bubble | NVDA, MSFT, GOOGL |
| 16 | Meta vs Google 广告 | ⭐⭐⭐⭐ | Cross-Sector Comps | META, GOOGL |
| 17 | Snowflake 估值合理性 | ⭐⭐⭐⭐⭐ | Revenue Multiple, TAM | SNOW |
| 20 | OpenAI IPO 估值 | ⭐⭐⭐⭐⭐ | Revenue Multiple, TAM | OpenAI (未上市) |

### 🇨🇳 A 股场景 (6 个)

| # | 场景名称 | 难度 | 核心技能 | 股票 |
|---|----------|------|----------|------|
| 9 | 比亚迪产能爬坡 | ⭐⭐⭐⭐ | Catalyst Analysis | 002594.SZ |
| 14 | 贵州茅台分红策略 | ⭐⭐⭐ | Dividend Analysis | 600519.SH |
| 18 | 宁德时代估值泡沫 | ⭐⭐⭐⭐ | Comps, Cyclical Valuation | 300750.SZ |
| 19 | 隆基绿能财务危机 | ⭐⭐⭐⭐⭐ | 3-Statements, Crisis Detection | 601012.SH |
| 21 | 中芯国际国产替代 | ⭐⭐⭐⭐⭐ | TAM Analysis | 688981.SH |
| 22 | 北交所专精特新 | ⭐⭐⭐⭐⭐ | Small Cap Screening | 北交所小盘股 |

### 🌐 跨市场场景 (1 个)

| # | 场景名称 | 难度 | 核心技能 | 股票 |
|---|----------|------|----------|------|
| 27 | OpenAI 发新品策略 | ⭐⭐⭐⭐⭐ | Event-Driven, Cross-Market | 美股+港股+A股 AI 概念 |

---

## 🎯 按技能分类

### 估值分析 (Valuation)

| 技能 | 场景编号 | 适用场景 |
|------|----------|----------|
| **DCF 估值** | 1, 4 | 成熟公司内在价值计算 |
| **Revenue Multiple** | 17, 20 | 亏损公司估值 (P/S) |
| **Sum-of-Parts** | 1 | 多业务板块公司估值 |
| **Comps 分析** | 6, 10, 13, 15, 16, 18 | 可比公司相对估值 |
| **TAM 分析** | 17, 20, 21 | 长期成长空间测算 |

### 财报分析 (Financial Statements)

| 技能 | 场景编号 | 适用场景 |
|------|----------|----------|
| **Earnings 分析** | 5 | 财报超预期信号 |
| **3-Statements** | 4, 12, 19 | 财务质量 + 危机预警 |
| **Dividend 分析** | 2, 14 | 分红策略 + 填权/贴权 |

### 事件驱动 (Event-Driven)

| 技能 | 场景编号 | 适用场景 |
|------|----------|----------|
| **Catalyst 分析** | 3, 8, 9 | 产能爬坡 + 产品发布 |
| **Event Impact** | 7, 11, 27 | 政策变化 + 发布会交易 |
| **Cross-Market** | 27 | 跨市场联动 + 时差套利 |

### 特殊情况 (Special Situations)

| 技能 | 场景编号 | 适用场景 |
|------|----------|----------|
| **Bubble 识别** | 13, 18 | 板块泡沫 + 周期股陷阱 |
| **Crisis 预警** | 19 | 财务危机早期信号 |
| **Small Cap** | 22 | 小盘股筛选 + 流动性陷阱 |

---

## 📈 学习路径建议

### 🟢 入门级 (⭐⭐ 难度)

**目标**: 掌握基础估值和分析方法

1. **场景 1**: 阿里巴巴抄底 - 学习 DCF 估值基础
2. **场景 2**: 腾讯分红 - 理解分红策略
3. **场景 11**: 苹果发布会 - 事件驱动交易入门

**预计学习时间**: 1-2 周
**技能收获**: DCF, Dividend, Event-Driven 基础

---

### 🟡 进阶级 (⭐⭐⭐ 难度)

**目标**: 理解多维度分析框架

4. **场景 3**: 小米汽车 - 催化剂分析
5. **场景 6**: 三大运营商 - Comps 分析
6. **场景 5**: 英伟达财报 - Earnings 分析
7. **场景 14**: 贵州茅台 - A 股分红策略

**预计学习时间**: 2-3 周
**技能收获**: Catalyst, Comps, Earnings 分析

---

### 🟠 高级 (⭐⭐⭐⭐ 难度)

**目标**: 掌握复杂估值和跨市场比较

8. **场景 4**: 海致科技 - 3-Statements + DCF 组合
9. **场景 8**: 特斯拉 - 产能爬坡催化剂
10. **场景 10**: 比亚迪 vs 理想 - 跨境 Comps
11. **场景 18**: 宁德时代 - 周期股估值陷阱
12. **场景 9**: 比亚迪产能 - A 股催化剂

**预计学习时间**: 3-4 周
**技能收获**: 三表模型, 跨市场分析, 周期股估值

---

### 🔴 专家级 (⭐⭐⭐⭐⭐ 难度)

**目标**: 精通高级估值和风险识别

13. **场景 12**: Palantir - 复杂估值 + 卖出时机
14. **场景 13**: AI 板块泡沫 - 板块估值 + 泡沫识别
15. **场景 17**: Snowflake - Revenue Multiple + TAM
16. **场景 20**: OpenAI IPO - 亏损公司估值
17. **场景 19**: 隆基绿能 - 财务危机预警
18. **场景 21**: 中芯国际 - TAM 分析 + 国产替代
19. **场景 22**: 北交所 - 小盘股筛选
20. **场景 27**: OpenAI 发新品 - 跨市场事件驱动

**预计学习时间**: 4-6 周
**技能收获**: Revenue Multiple, TAM, 财务危机识别, 跨市场交易

---

## 🚀 快速开始

### 1. 选择你的第一个场景

**如果你是港股投资者**: 从 **场景 1 (阿里巴巴)** 开始
**如果你是美股投资者**: 从 **场景 5 (英伟达)** 开始
**如果你是 A 股投资者**: 从 **场景 14 (贵州茅台)** 开始

### 2. 阅读场景文件

```bash
# 示例: 打开场景 1
open ~/hk-trading-bot/notebooklm_tutorial/scenarios/scenario-01-阿里巴巴抄底.md
```

### 3. 在 Claude Code 中调用技能

```bash
# 在 Claude Code CLI 中
cd ~/hk-trading-bot
claude code

# 调用 DCF 估值
/dcf 09988.HK

# 调用 Comps 分析
/comps 港股互联网

# 调用 Earnings 分析
/earnings NVDA
```

### 4. 使用 NotebookLM 深化学习

1. 打开 [NotebookLM](https://notebooklm.google.com/)
2. 上传场景 markdown 文件
3. 使用"深度提问"功能探索知识点
4. 生成学习笔记和总结

---

## 📊 技能覆盖矩阵

| Financial Skill | 港股场景 | 美股场景 | A 股场景 | 跨市场 | 难度 |
|-----------------|----------|----------|----------|--------|------|
| **DCF 估值** | 1, 4 | 12 | - | - | ⭐⭐⭐ |
| **Revenue Multiple** | - | 17, 20 | - | - | ⭐⭐⭐⭐⭐ |
| **Sum-of-Parts** | 1 | - | - | - | ⭐⭐⭐ |
| **Comps 分析** | 6, 10, 15 | 13, 16 | 18 | - | ⭐⭐⭐⭐ |
| **TAM 分析** | - | 17, 20 | 21 | - | ⭐⭐⭐⭐⭐ |
| **Earnings 分析** | - | 5 | - | - | ⭐⭐⭐ |
| **3-Statements** | 4 | 12 | 19 | - | ⭐⭐⭐⭐⭐ |
| **Dividend 分析** | 2 | - | 14 | - | ⭐⭐⭐ |
| **Catalyst 分析** | 3 | 8 | 9 | - | ⭐⭐⭐⭐ |
| **Event-Driven** | 7, 11 | - | - | 27 | ⭐⭐⭐⭐⭐ |
| **Bubble 识别** | - | 13 | 18 | - | ⭐⭐⭐⭐⭐ |
| **Small Cap 筛选** | - | - | 22 | - | ⭐⭐⭐⭐⭐ |

---

## 💡 使用技巧

### 1. NotebookLM 深度提问模板

每个场景都预设了 5 个深度问题，可以直接在 NotebookLM 中使用：

```
Q: 为什么周期股用 PE 估值会踩雷? 应该用什么指标?
Q: TAM/SAM/SOM 分别是什么? 如何计算?
Q: 如何判断发布会是否成功? 看哪些指标?
```

### 2. 实战练习方法

**方法 A**: 复现案例
- 用相同技能分析文件中的股票
- 对比你的结果和场景中的结论
- 找出差异并思考原因

**方法 B**: 迁移应用
- 用学到的技能分析其他股票
- 例: 学完场景 1 (阿里 DCF) → 分析京东 DCF
- 验证方法的普适性

**方法 C**: 组合技能
- 同时使用多个技能分析同一只股票
- 例: DCF + Comps + 3-Statements 三重验证
- 提高分析准确性

### 3. 数据源整合

部分场景标注了 **⏳ 待补充: Python 代码示例**，可以自己实现：

```python
# 示例: 抓取财报数据
from openbb import obb
import pandas as pd

# 获取财务数据
financials = obb.equity.fundamental.income('09988.HK', provider='yfinance')
print(financials.to_df())
```

---

## 🔗 相关资源

### 官方文档
- [Claude for Financial Services Skills](https://support.claude.com/en/articles/12663107-claude-for-financial-services-skills)
- [GitHub - financial-services-plugins](https://github.com/anthropics/financial-services-plugins)

### 本地工具
- HK Trading Bot: `~/hk-trading-bot/` (港股实盘系统)
- OpenBB-Alice: `~/OpenBB-Alice/` (全球金融数据终端)
- 研报分析: `python ~/hk-trading-bot/research_analyzer.py 02382`

### 数据源
- **港股**: Futu OpenD API (`127.0.0.1:11111`)
- **全球**: OpenBB API (`127.0.0.1:6900`)
- **新闻**: WebSearch, Gemini Search

---

## 📝 贡献指南

### 场景完善建议

每个场景目前是"基础框架 (待填充详细内容)"，可以补充：

1. **数据源整合** - 添加 Python 代码示例
2. **NotebookLM Q&A** - 补充更多深度问题
3. **实战案例** - 添加更多历史案例对比
4. **Excel 模板** - 提供可下载的估值模型

### 新场景提案

如果想添加新场景，建议包含：
- 真实背景故事 (具体日期 + 股价 + 事件)
- Financial Skills 调用示例
- 5 个核心知识点 (每个 < 200 字)
- 实战决策部分 (买入信号 + 风险提示 + 操作策略)

---

## ⚠️ 免责声明

**本教程仅供学习参考，不构成投资建议。**

- 所有案例基于历史数据，过去表现不代表未来
- Financial Skills 输出仅供参考，需结合实际情况判断
- 投资有风险，决策需谨慎
- 建议咨询专业投资顾问

---

**最后更新**: 2026-02-26
**状态**: ✅ 全部 23 个场景框架已完成，欢迎补充完善
**作者**: Mantou (mantou@example.com)
**License**: MIT
