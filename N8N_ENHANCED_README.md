# n8n港股智能做T系统 - 增强版使用指南

## 功能特性

### 1. 全市场扫描
- ✅ 不再限制固定股票列表
- ✅ 动态获取高波动股票（TOP 50）
- ✅ 支持市值、价格区间筛选
- ✅ 优先推荐中低市值、高波动股票

### 2. 社交媒体热搜集成
- ✅ **微博热搜** - 实时抓取微博热门话题
- ✅ **抖音热搜** - 抓取抖音热榜
- ✅ **雪球热股** - 获取雪球关注度高的股票
- ✅ **东财股吧** - 分析股吧讨论热度

### 3. 新闻热点分析
- ✅ 财联社快讯分析
- ✅ 自动识别热门板块（新能源、半导体、AI、医药等）
- ✅ 统计各板块新闻热度

### 4. 完整技术指标
- ✅ **RSI** - 相对强弱指标（超买超卖）
- ✅ **MACD** - 趋势指标（金叉死叉）
- ✅ **ATR** - 平均真实波幅
- ✅ **布林带** - 波动率指标
- ✅ **KDJ** - 随机指标
- ✅ **OBV** - 能量潮指标
- ✅ **量比** - 成交量对比
- ✅ **支撑/压力位** - Pivot Points

### 5. 智能评分系统
综合以下因素进行评分（满分100分）：
- 涨跌幅（20分）
- 振幅（15分）
- RSI（15分）
- MACD（15分）
- 布林带（10分）
- KDJ（10分）
- 量比（10分）
- 社交热度（5分）

**评级标准：**
- 80-100分：强烈买入 (strong_buy)
- 60-79分：买入 (buy)
- 40-59分：中性 (neutral)
- 0-39分：卖出 (sell)

---

## 安装依赖

```bash
cd /Users/mantou/hk-trading-bot
pip install futu-api requests
```

---

## 快速开始

### 1. 启动FutuOpenD
确保 FutuOpenD 已启动并监听在 `127.0.0.1:11111`

### 2. 运行增强版脚本
```bash
python n8n_futu_bridge_enhanced.py
```

### 3. 在n8n中使用

#### 方法A：Execute Command节点
```json
{
  "command": "python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge_enhanced.py"
}
```

#### 方法B：HTTP Request节点（需要配合Web服务）
见下文"Flask API模式"

---

## 输出数据格式

```json
{
  "success": true,
  "stocks": [
    {
      "code": "HK.09988",
      "name": "阿里巴巴",
      "price": 85.5,
      "change_pct": 3.5,
      "amplitude": 4.2,
      "volume": 25000000,
      "turnover_rate": 1.2,
      "volume_ratio": 2.3,
      "indicators": {
        "rsi": 45.5,
        "macd": {
          "macd": 0.45,
          "signal": 0.32,
          "histogram": 0.13,
          "trend": "bullish"
        },
        "bollinger": {
          "upper": 88.5,
          "middle": 85.0,
          "lower": 81.5,
          "position": "middle"
        },
        "kdj": {
          "k": 55.2,
          "d": 52.1,
          "j": 61.4,
          "signal": "neutral"
        },
        "atr": 2.5,
        "obv": 1500000000
      },
      "social_heat": {
        "guba_score": 65
      },
      "score": 78,
      "rating": "buy",
      "reasons": [
        "温和上涨",
        "振幅大",
        "MACD金叉",
        "放量",
        "社交热度高"
      ],
      "buy_price": 83.5,
      "sell_price": 87.2,
      "stop_loss": 82.0
    }
  ],
  "hot_sectors": [
    {
      "sector": "人工智能",
      "news_count": 15,
      "heat": 150
    },
    {
      "sector": "新能源",
      "news_count": 12,
      "heat": 120
    }
  ],
  "count": 30,
  "timestamp": "2026-02-03 14:30:00",
  "source": "FutuOpenD Enhanced"
}
```

---

## 配置文件说明

编辑 `n8n_config.json` 来自定义参数：

```json
{
  "stock_filters": {
    "max_stocks": 50,        // 最多扫描股票数
    "min_score": 40          // 最低评分（低于此分数不返回）
  },
  "technical_indicators": {
    "rsi_period": 14,        // RSI周期
    "bollinger_period": 20   // 布林带周期
  },
  "scoring_weights": {
    "change_pct": 20,        // 涨跌幅权重
    "macd": 15               // MACD权重
  },
  "social_media": {
    "enable_weibo": true,    // 启用微博热搜
    "enable_douyin": true    // 启用抖音热搜
  },
  "output": {
    "top_n": 30              // 返回TOP N股票
  }
}
```

---

## n8n工作流示例

### 基础工作流

```
[定时触发] → [Execute Command] → [过滤节点] → [钉钉/飞书通知]
    ↓
 每30分钟运行一次
    ↓
 只通知评分≥70的股票
```

### 进阶工作流

```
[定时触发]
    ↓
[Execute Command] - 运行增强版脚本
    ↓
[Function节点] - 解析JSON，提取TOP10
    ↓
    ├─→ [IF节点] - 评分≥80 → [钉钉通知] "强烈推荐"
    ├─→ [IF节点] - 评分60-79 → [飞书通知] "建议关注"
    └─→ [Google Sheets] - 记录所有推荐到表格
```

---

## 高级用法

### 1. 结合热搜数据
```python
# 在n8n Function节点中处理
const stocks = $input.all()[0].json.stocks;
const hotSectors = $input.all()[0].json.hot_sectors;

// 筛选热门板块的股票
const hotStocks = stocks.filter(stock => {
  return hotSectors.some(sector =>
    stock.name.includes(sector.sector)
  );
});

return hotStocks;
```

### 2. 多条件筛选
```javascript
// n8n Function节点
const stocks = $input.all()[0].json.stocks;

// 筛选条件：评分≥70 且 MACD金叉 且 RSI<50
const filtered = stocks.filter(s =>
  s.score >= 70 &&
  s.indicators.macd.trend === 'bullish' &&
  s.indicators.rsi < 50
);

return filtered;
```

### 3. 动态止损提醒
```javascript
// 监控持仓股票，价格跌破止损位时通知
const myStocks = ['HK.09988', 'HK.00700'];
const allStocks = $input.all()[0].json.stocks;

const alerts = allStocks
  .filter(s => myStocks.includes(s.code))
  .filter(s => s.price < s.stop_loss)
  .map(s => `${s.name} 跌破止损位！现价${s.price} 止损${s.stop_loss}`);

return alerts;
```

---

## 常见问题

### Q1: 为什么有些股票没有返回？
A: 因为设置了 `min_score: 40`，评分低于40的股票会被过滤。可以在配置文件中调低此值。

### Q2: 社交媒体热搜获取失败？
A: 微博、抖音等平台有反爬机制，建议：
1. 降低请求频率
2. 使用代理IP
3. 更新User-Agent

### Q3: 如何添加自定义股票池？
A: 修改 `get_volatile_stocks()` 函数中的 `volatile_stocks` 列表。

### Q4: 技术指标计算不准确？
A: 可以调整K线数据周期（默认60天），在 `request_history_kline()` 中修改 `max_count` 参数。

---

## 下一步优化建议

1. **实时推送**：使用富途的实时行情订阅，而不是定时轮询
2. **机器学习**：基于历史数据训练模型，优化评分算法
3. **回测系统**：验证推荐策略的历史收益
4. **风控模块**：加入仓位管理、止盈止损建议
5. **多市场支持**：扩展到A股、美股

---

## 联系方式

如有问题，请查看项目文档或联系开发者。

**祝您交易顺利！** 🚀
