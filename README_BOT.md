# 港股智能交易助手 使用说明书

## 系统概述

一套完整的港股监控、分析、推送系统，帮助你：
- 实时监控板块异动
- 追踪热点新闻和社交媒体
- 智能选股推荐
- 钉钉实时推送
- 马斯克动态追踪

---

## 核心功能模块

### 1. 实时监控系统 (`realtime_alert.py`)

**功能：** 盘中实时监控，自动发现异动

**监控内容：**
| 监控项 | 频率 | 预警条件 |
|--------|------|----------|
| 个股异动 | 每20秒 | 涨跌幅 > 3% |
| 预设板块 | 每60秒 | 板块涨幅 > 4% |
| 新闻热点 | 每60秒 | 关键词匹配 |
| 全市场扫描 | 每120秒 | 行业涨幅 > 5% |

**预设监控板块（12个）：**
- 商业航天、卫星通信
- AI人工智能、机器人
- 新能源汽车、光伏太阳能
- 芯片半导体、消费电子
- 互联网科技、生物医药
- 新能源、锂电池

**启动命令：**
```bash
cd /Users/mantou/hk-trading-bot
python realtime_alert.py
```

---

### 2. 全市场扫描器 (`market_scanner.py`)

**功能：** 扫描全港股市场，发现任意板块异动（不限于预设板块）

**扫描逻辑：**
- 获取港股涨幅榜TOP200
- 按行业聚类分析
- 找出平均涨幅>3%的行业
- 发现大涨股集中的概念

**使用方式：**
```bash
# 完整报告
python market_scanner.py

# 快速扫描（只看预警）
python market_scanner.py quick
```

**输出内容：**
- 热门行业排行
- 概念聚类分析
- 涨幅榜TOP10
- 跌幅榜TOP5
- 异动预警

---

### 3. 智能选股器 (`smart_picker.py`)

**功能：** 从热门板块中筛选最值得买入的股票

**评分维度：**
| 维度 | 权重 | 数据来源 |
|------|------|----------|
| 涨幅+成交额 | 40% | 实时行情 |
| 社交热度 | 30% | 雪球+东财股吧 |
| 资金流向 | 30% | 主力净流入 |

**评分标准：**
- ⭐⭐⭐ 75分以上：强烈推荐
- ⭐⭐ 60-74分：可以关注
- ⭐ 45-59分：谨慎参与
- ❌ 45分以下：不推荐

**使用方式：**
```bash
python smart_picker.py 商业航天
python smart_picker.py AI
```

---

### 4. 钉钉推送 (`dingtalk_notifier.py`)

**功能：** 实时推送预警到钉钉群

**推送类型：**
- 个股异动提醒
- 板块暴涨预警
- 智能选股推荐
- 新闻热点预警
- 早盘快报/收盘总结

**配置方式：**
```bash
python dingtalk_notifier.py setup
```

**配置文件：** `~/.dingtalk_config.json`

---

### 5. 定时推送服务 (`auto_push.py`)

**功能：** 自动定时推送市场信息

**推送时间表：**
| 时间 | 内容 |
|------|------|
| 09:30 | 早盘快报 |
| 每30分钟 | 热门板块（交易时间） |
| 每小时 | 涨幅榜 + 资金流向 |
| 16:30 | 收盘总结 |

**启动命令：**
```bash
# 启动定时服务
python auto_push.py

# 手动推送
python auto_push.py hot      # 热门板块
python auto_push.py gainers  # 涨幅榜
python auto_push.py flow     # 资金流向
python auto_push.py test     # 测试所有
```

---

### 6. 钉钉问答机器人 (`dingtalk_bot_server.py`)

**功能：** 在钉钉群或浏览器提问，自动回复

**支持的问题：**
| 问题类型 | 示例 | 返回内容 |
|----------|------|----------|
| 股票查询 | 阿里、腾讯、09988 | 行情+量价+资金+热度 |
| 热门板块 | 热点、热门 | 板块涨幅排行 |
| 涨幅榜 | 涨幅榜、TOP | 涨幅TOP10 |
| 新闻 | 新闻、快讯 | 财经新闻速览 |
| 板块分析 | 科技板块、新能源 | 板块详情 |
| 马斯克 | 马斯克、SpaceX | 关联板块+港股+资金 |

**启动服务：**
```bash
# 启动问答服务
python dingtalk_bot_server.py server &

# 启动公网隧道
npx localtunnel --port 8080
```

**浏览器访问：**
```
https://你的隧道地址/test?q=阿里
https://你的隧道地址/test?q=热点
https://你的隧道地址/test?q=马斯克
```

---

### 7. 马斯克动态追踪 (`musk_tracker.py`)

**功能：** 追踪马斯克推文/采访，分析关联板块

**关键词映射：**
| 马斯克关键词 | 关联板块 | 港股标的 |
|--------------|----------|----------|
| SpaceX/Starship | 商业航天 | 亚太卫星 01045 |
| Starlink | 卫星互联网 | 中播数据 00471 |
| Tesla/FSD | 新能源汽车 | 比亚迪 01211 |
| Optimus | 人形机器人 | 小米 01810 |
| Grok/xAI | AI大模型 | 百度 09888 |
| Doge/Bitcoin | 加密货币 | - |

**使用方式：**
```bash
python musk_tracker.py        # 查看报告
python musk_tracker.py push   # 推送到钉钉
```

---

### 8. 新闻追踪器 (`news_tracker.py`)

**功能：** 监控财经新闻，匹配热点关键词

**数据来源：**
- 财联社快讯
- 新浪财经
- 微博热搜

**关键词优先级：**
- HIGH: 航天、火箭、卫星、AI、机器人
- MEDIUM: 芯片、新能源、锂电池
- LOW: 医药、消费

---

### 9. 热门板块+做T推荐 (`hot_sector_t.py`) ⭐核心功能

**功能：** 检测热门板块 → 自动推荐板块内做T股票

**一体化输出：**
- 今日热门板块（涨幅、领涨股）
- 板块内做T推荐（股票、代码、现价）
- 买入位置（支撑位）
- 卖出位置（压力位）
- 止损位置
- 预期收益率

**使用方式：**
```bash
python hot_sector_t.py
```

**输出示例：**
```
热门板块: 原材料 +52%、地产 +24%、电讯 +24%

做T推荐:
大森控股 01580 | 买入0.13 | 卖出0.35 | 预期+169%
莱蒙国际 03688 | 买入0.23 | 卖出0.73 | 预期+217%
```

---

### 10. 做T推荐系统 (`t_trading.py`)

**功能：** 基于富途API实时数据，提供做T交易建议

**分析维度：**
| 维度 | 权重 | 说明 |
|------|------|------|
| 波动率(ATR) | 40% | 波动大更适合做T |
| 日内振幅 | 30% | 振幅>2%为佳 |
| 价格位置 | 30% | 接近支撑/压力位 |

**输出内容：**
- 推荐股票及评分
- 买入位置（支撑位）
- 卖出位置（压力位）
- 止损位置
- 预期收益率
- 风险收益比

**使用方式：**
```bash
# 需要先启动FutuOpenD

python t_trading.py           # 查看推荐
python t_trading.py push      # 推送到钉钉
python t_trading.py analyze HK.09988  # 分析单只
```

**候选股池（16只）：**
阿里、腾讯、美团、小米、京东、快手、百度、比亚迪、理想、小鹏、蔚来、中芯国际、华虹半导体、协鑫科技、商汤、亚太卫星

---

### 10. 板块扫描器 (`hk_sector_scanner.py`)

**功能：** 扫描预设的12个港股板块

**板块列表：**
```
商业航天、卫星通信、AI人工智能、机器人
新能源汽车、光伏太阳能、芯片半导体、消费电子
互联网科技、生物医药、新能源、锂电池
```

---

## 快速开始

### 1. 启动完整监控（交易日）
```bash
cd /Users/mantou/hk-trading-bot

# 终端1: 实时监控
python realtime_alert.py

# 终端2: 定时推送
python auto_push.py

# 终端3: 问答服务
python dingtalk_bot_server.py server &
npx localtunnel --port 8080
```

### 2. 周末/非交易时间
```bash
# 手动查询
python market_scanner.py          # 全市场扫描
python musk_tracker.py push       # 马斯克动态
python auto_push.py hot           # 推送热点
```

### 3. 浏览器问答
```
http://localhost:8080/test?q=阿里
http://localhost:8080/test?q=热点
http://localhost:8080/test?q=马斯克
```

---

## 文件结构

```
/Users/mantou/hk-trading-bot/
├── realtime_alert.py      # 实时监控主程序
├── market_scanner.py      # 全市场扫描器
├── hk_sector_scanner.py   # 板块扫描器
├── smart_picker.py        # 智能选股器
├── news_tracker.py        # 新闻追踪器
├── musk_tracker.py        # 马斯克追踪器
├── dingtalk_notifier.py   # 钉钉推送
├── dingtalk_bot_server.py # 问答机器人
├── auto_push.py           # 定时推送
└── README_BOT.md          # 本说明书
```

---

## 配置文件

| 文件 | 用途 |
|------|------|
| `~/.dingtalk_config.json` | 钉钉Webhook配置 |

---

## 依赖安装

```bash
pip install flask requests schedule futu-api
npm install -g localtunnel
```

---

## 注意事项

1. **Futu OpenD**: 实时行情需要启动富途牛牛OpenD
2. **隧道地址**: localtunnel地址会变化，需要更新钉钉配置
3. **API限制**: 东财接口有频率限制，不要过于频繁调用
4. **交易时间**: 港股交易时间 9:30-12:00, 13:00-16:00

---

## 更新日志

- 2026-01-24: 添加马斯克动态追踪
- 2026-01-24: 添加全市场扫描器
- 2026-01-24: 添加钉钉问答机器人
- 2026-01-24: 添加定时推送服务
- 2026-01-23: 创建智能选股器
- 2026-01-23: 创建新闻追踪器
