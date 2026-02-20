# 社区情绪分析功能说明

## 📊 功能概述

本系统集成了Reddit WallStreetBets、韩国社区、Elon Musk动态追踪三大社区情绪分析模块，帮助发现热门股票并映射到港股对应标的。

## 🎯 核心功能

### 1. Reddit WallStreetBets 实时热门股
- **数据源**: ApeWisdom API (免费，无需认证)
- **更新频率**: 每2小时扫描一次
- **数据内容**: 过去24小时提及次数、点赞数、排名变化

**使用方法**:
```bash
# 查看Reddit热门股票
python my_strategy_helper.py sentiment reddit

# 或使用原始脚本
python social_api_integration.py reddit
```

**输出示例**:
```
📊 WallStreetBets 热门股票排行 (ApeWisdom)
======================================================================
排名     代码       提及次数         点赞数         24h变化
----------------------------------------------------------------------
#1     SPY      412          1547       📈 +5     🔥🔥🔥
#2     NVDA     93           344        ➡️ 0      🔥🔥
#3     TSLA     58           549        📉 -2     🔥🔥
```

### 2. 韩国社区情绪追踪
- **热门股票**: 三星电子、SK海力士 (HBM存储芯片龙头)
- **关注赛道**: HBM高带宽内存、AI存储芯片
- **港股映射**: 暂无直接对应（港股无HBM纯标的）

**使用方法**:
```bash
python community_sentiment.py korea
```

### 3. Elon Musk 动态追踪
- **数据源**: WebSearch (推荐)
- **追踪内容**: Tesla、SpaceX、xAI、Neuralink相关推文
- **受益股票**: TSLA → 小鹏(09868)、蔚来(09866)、理想(02015)

**使用方法**:
```bash
python community_sentiment.py musk
# 或
python social_api_integration.py musk
```

## 🔗 Reddit热门股 → 港股映射表

| Reddit热门美股 | 港股对应标的 | 代码 | 业务相似度 |
|--------------|------------|------|-----------|
| **NVDA** (AI芯片) | 壁仞科技 | 06082.HK | ⭐⭐⭐⭐⭐ GPU芯片 |
|  | 天数智芯 | 09903.HK | ⭐⭐⭐⭐⭐ GPU芯片 |
| **MSFT** (AI大模型) | 智谱AI | 02513.HK | ⭐⭐⭐⭐ 大模型 |
|  | MiniMax | 00100.HK | ⭐⭐⭐⭐ 大模型 |
| **TSLA** (电动车) | 小鹏汽车 | 09868.HK | ⭐⭐⭐⭐ 智能电动车 |
|  | 蔚来 | 09866.HK | ⭐⭐⭐⭐ 智能电动车 |
|  | 理想汽车 | 02015.HK | ⭐⭐⭐⭐ 智能电动车 |
| **AMZN** (电商) | 阿里巴巴 | 09988.HK | ⭐⭐⭐⭐ 电商+云 |
| **MU** (存储芯片) | 兆易创新 | 03986.HK | ⭐⭐⭐ 存储芯片 |
| **PLTR** (AI数据) | 暂无直接对应 | - | - |

## 📈 自动情绪分析器

`sentiment_auto_analyzer.py` 提供自动化WebSearch结果解析：

**功能**:
- 提取股票代码（US/HK/KR格式）
- 统计提及次数
- 检测情绪倾向（看涨/看跌/中性）
- 识别热门话题（AI/芯片/电动车/加密货币等）

**使用示例**:
```python
from sentiment_auto_analyzer import SentimentAutoAnalyzer

analyzer = SentimentAutoAnalyzer()

# 分析WebSearch结果
search_text = """
Reddit WallStreetBets: NVDA up 5%, TSLA mentioned 120 times
Bullish sentiment on AI chips, bearish on EV stocks
"""

result = analyzer.analyze_websearch_result(search_text, region='USA')
print(analyzer.format_analysis_report(result))
```

## 🛠️ 技术架构

### 依赖安装
```bash
bash install_social_deps.sh
```

安装内容:
- `praw` - Reddit API Wrapper (可选，需要API credentials)
- `vaderSentiment` - 社交媒体情绪分析
- `requests` - HTTP请求库

### API配置

**Reddit PRAW (高级用户可选)**:
1. 访问 https://www.reddit.com/prefs/apps
2. 创建应用获取 client_id 和 client_secret
3. 设置环境变量:
```bash
export REDDIT_CLIENT_ID='your_client_id'
export REDDIT_CLIENT_SECRET='your_client_secret'
```

**ApeWisdom API (推荐，无需配置)**:
- API地址: `https://apewisdom.io/api/v1.0/filter/all-stocks/page/1`
- 完全免费，无需认证
- 每2小时更新一次

## 📊 集成到策略助手

`my_strategy_helper.py` 已集成社区情绪分析命令：

```bash
# Reddit热门股
python my_strategy_helper.py sentiment reddit
python my_strategy_helper.py sentiment wsb

# 美国社区（通用）
python my_strategy_helper.py sentiment usa

# Elon Musk动态
python my_strategy_helper.py sentiment musk

# 韩国社区
python my_strategy_helper.py sentiment korea
```

## 🔍 实战案例

### 案例1: Reddit热捧NVDA → 投资壁仞科技

**逻辑链**:
1. ApeWisdom显示NVDA过去24h被提及93次，排名#6
2. NVDA是AI芯片龙头，市场需求旺盛
3. 港股对应: 壁仞科技(06082) - 国产GPU，BR100性能超A100
4. **估值优势**: 壁仞科技vs成本线仅+1.19%，远低于智谱(+112%)

**验证数据**:
```bash
python my_strategy_helper.py sentiment reddit
# 输出: NVDA #6, 提及93次

python my_strategy_helper.py research 06082
# 输出: 35.50 HKD, vs成本线 +1.19% ✅
```

### 案例2: 韩国狂买SK海力士 → 兆易创新间接受益

**逻辑链**:
1. 韩国散户单日买入3.21亿美元半导体3倍杠杆ETF (SOXL)
2. SK海力士HBM市占率64%，三星25%
3. 港股无HBM纯标的，但**兆易创新受益于DDR订单转移**
4. 三星/SK砍DDR产能做HBM → 传统DDR订单给兆易创新

**数据验证**:
```bash
python my_strategy_helper.py research 03986
# 兆易创新: 403 HKD, vs成本线 +21.25%
```

### 案例3: 智谱暴涨+45% → MiniMax补涨机会

**逻辑链**:
1. Reddit热捧MSFT (#3热门) → AI大模型板块升温
2. 智谱AI (02513) 单日暴涨+45%，龙头已大涨
3. **补涨策略**: 同板块掉队票MiniMax (00100) 补涨+16%
4. 工具: `python my_strategy_helper.py laggards` 找补涨标的

## ⚠️ 注意事项

1. **Reddit数据延迟**: ApeWisdom每2小时更新，非实时
2. **情绪≠基本面**: 热门≠值得买，需结合主力成本分析
3. **港股映射非直接**: 美股热门→港股对应标的是基于业务相似性，非Reddit直接推荐
4. **韩国HBM赛道**: 港股无纯HBM股，只能买间接受益股
5. **估值风险**: 优先买vs成本线<5%的股票，超买股追高风险大

## 📚 参考文档

- [ApeWisdom API文档](https://apewisdom.io/api/)
- [PRAW文档](https://praw.readthedocs.io/)
- [VADER情绪分析](https://github.com/cjhutto/vaderSentiment)
- [港股稀缺概念股图谱](./港股稀缺概念股图谱.md)
- [主力成本分析策略](./主力成本分析策略.md)

## 🎯 下一步优化

- [ ] 集成Twitter/X API（需$200/月）
- [ ] 添加Discord/Telegram群组监控
- [ ] 实时情绪仪表盘（WebSocket推送）
- [ ] 情绪指标与技术指标结合（RSI+社区热度）
- [ ] 自动Reddit→港股映射（LLM智能匹配）

---

**创建时间**: 2026-02-20
**作者**: Claude Opus 4.5
**版本**: v1.0
