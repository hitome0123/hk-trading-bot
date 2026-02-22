# HK Trading Bot - 港股智能交易系统

> 7×24 自动化监控 + AI 分析 + Telegram 实时推送

基于四大交易大师方法论（Larry Williams、Victor Sperandeo、Jesse Livermore、Mark Minervini），整合多平台情绪分析的港股智能交易系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    HK Trading Bot 双系统架构                      │
├─────────────────────────────┬───────────────────────────────────┤
│      本地 Mac (盘中)         │          阿里云 (7×24)            │
├─────────────────────────────┼───────────────────────────────────┤
│  📊 热门板块推送              │  🔔 情绪变化监控                   │
│  sector_trading_advisor.py   │  cloud_sentiment_monitor.py       │
│                             │                                    │
│  推送时间：                  │  推送时间：                        │
│  09:20 / 10:30              │  08:30 盘前提醒                    │
│  14:00 / 15:30              │  09:30-16:00 实时告警              │
│                             │  16:30 盘后报告                    │
│                             │                                    │
│  依赖：富途 OpenD            │  依赖：无 (纯云端)                  │
└─────────────────────────────┴───────────────────────────────────┘
```

## 核心功能

### 1. 热门板块推送 📊
扫描涨幅板块 → AI分析炒作周期 → 推荐进场时机

```bash
python sector_trading_advisor.py
```

**输出示例**：
```
🔥 1. AI大模型 +12.25%
   💡 原因: 概念炒作
   ⏱️ 周期: 1-3天
   🎯 建议: 观望
```

### 2. 多市场情绪分析 🌍
支持港股、美股、A股、韩股的情绪分析

```bash
python sentiment_hub.py 09880    # 港股-优必选
python sentiment_hub.py NVDA     # 美股-英伟达
python sentiment_hub.py 600519   # A股-茅台
python sentiment_hub.py 삼성전자   # 韩股-三星
```

**输出示例**：
```
📊 优必选 (09880.HK) 情绪分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 综合热度: 85/100
😊 情绪倾向: positive (72%)
📈 价格: 168.50 HKD (+8.2%)

📱 数据来源:
├─ 雪球: 127条讨论, 看多62%
├─ Reddit: 45条提及, bullish
└─ DC Inside: 23条, 긍정적
```

### 3. 深度研究 🔬
AI驱动的公司基本面分析

```bash
python gemini_deep_research.py 02513   # 智谱AI
```

**分析内容**：
- 公司基本面
- 行业趋势
- 竞争格局
- 投资建议

### 4. 策略助手 🎯

```bash
# 扫描稀缺股
python my_strategy_helper.py scan

# 找补涨机会
python my_strategy_helper.py laggards

# 研究报告分析
python my_strategy_helper.py research 02382
```

### 5. 研究报告分析 📈
券商研究报告 + 基本面分析

```bash
python research_analyzer.py 02382
```

**分析内容**：
- 实时行情 (Futu API)
- 20日VWAP主力成本
- 券商目标价汇总
- 投资评级分析

---

## 数据源

### 行情数据

| 数据源 | 用途 | 获取方式 |
|--------|------|----------|
| **富途 OpenD** | 实时行情、K线、资金流 | 下载 [Futu OpenD](https://openapi.futunn.com/)，本地运行 `127.0.0.1:11111` |
| Yahoo Finance | 备用行情数据 | `pip install yfinance`，免费无需注册 |

**富途 OpenD 数据获取代码**：
```python
from futu import OpenQuoteContext, RET_OK

quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

# 获取实时行情
ret, data = quote_ctx.get_market_snapshot(['HK.09880'])

# 获取K线
ret, data = quote_ctx.get_cur_kline('HK.09880', KLType.K_DAY, 20)

# 获取资金流
ret, data = quote_ctx.get_capital_flow(['HK.09880'])

quote_ctx.close()
```

---

### 社交媒体情绪

| 平台 | 市场 | 获取方式 |
|------|------|----------|
| **雪球** | 港股/A股 | 移动端API，无需登录 `stock.xueqiu.com/v5/stock/quote.json` |
| **东方财富股吧** | A股 | 公开API `guba.eastmoney.com` |
| **Reddit** | 美股 | 公开API `reddit.com/r/wallstreetbets.json` |
| **DC Inside** | 韩股 | 公开网页爬取 `gall.dcinside.com` |
| **Naver Finance** | 韩股 | 公开API `finance.naver.com` |

**雪球数据获取代码**：
```python
import requests

# 获取股票行情
url = "https://stock.xueqiu.com/v5/stock/quote.json"
params = {"symbol": "09880", "extend": "detail"}
headers = {"User-Agent": "Xueqiu iPhone"}
resp = requests.get(url, params=params, headers=headers)
data = resp.json()

# 获取讨论帖子
url = "https://xueqiu.com/query/v1/symbol/search/status"
params = {"symbol": "09880", "count": 20}
```

**Reddit 数据获取代码**：
```python
import requests

# 搜索WSB讨论
url = "https://www.reddit.com/r/wallstreetbets/search.json"
params = {"q": "NVDA", "sort": "new", "limit": 20}
headers = {"User-Agent": "Mozilla/5.0"}
resp = requests.get(url, params=params, headers=headers)
posts = resp.json()['data']['children']
```

**DC Inside 数据获取代码**：
```python
import requests
from bs4 import BeautifulSoup

# 获取韩国散户讨论
url = "https://gall.dcinside.com/mgallery/board/lists"
params = {"id": "tenbagger", "search_keyword": "테슬라"}
resp = requests.get(url)
soup = BeautifulSoup(resp.text, 'html.parser')
posts = soup.select('.gall_list tr')
```

---

### 财经资讯

| 来源 | 获取方式 |
|------|----------|
| **新浪财经** | 公开API `feed.mix.sina.com.cn/api/roll/get` |
| **财联社** | 公开网页 `cls.cn` |
| **富途资讯** | 富途OpenD API `get_stock_basicinfo` |

**新浪财经资讯获取代码**：
```python
import requests

url = "https://feed.mix.sina.com.cn/api/roll/get"
params = {
    'pageid': '153',
    'lid': '2509',
    'num': 50,
    'page': 1
}
resp = requests.get(url, params=params)
news = resp.json()['result']['data']

for item in news:
    print(f"{item['intime']} - {item['title']}")
```

---

### AI分析

| 服务 | 获取方式 | 费用 |
|------|----------|------|
| **Gemini 2.5 Flash** | [AI Studio](https://aistudio.google.com/) 申请 API Key | 免费额度充足 |
| **OpenAI GPT-4** | [OpenAI Platform](https://platform.openai.com/) 申请 API Key | 付费 |
| **Grok** | [X Developer](https://developer.x.com/) 申请 | 付费 |

**Gemini 分析代码**：
```python
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-2.5-flash')

prompt = f"""
分析港股 {stock_code} 的投资价值：
- 公司基本面
- 行业趋势
- 风险因素
- 投资建议
"""
response = model.generate_content(prompt)
print(response.text)
```

---

### 推送渠道

| 渠道 | 获取方式 |
|------|----------|
| **Telegram Bot** | [@BotFather](https://t.me/BotFather) 创建Bot获取Token |

**Telegram 推送代码**：
```python
import requests

TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=data)

# 获取Chat ID: 给Bot发消息后访问
# https://api.telegram.org/bot{TOKEN}/getUpdates
```

---

### 数据源汇总表

| 数据源 | 类型 | 是否免费 | 是否需要注册 | 限制 |
|--------|------|----------|--------------|------|
| 富途 OpenD | 行情 | 免费 | 需要 | 本地运行 |
| Yahoo Finance | 行情 | 免费 | 不需要 | 延迟15分钟 |
| 雪球 | 情绪 | 免费 | 不需要 | 频率限制 |
| Reddit | 情绪 | 免费 | 不需要 | 60次/分钟 |
| DC Inside | 情绪 | 免费 | 不需要 | 无 |
| 新浪财经 | 资讯 | 免费 | 不需要 | 无 |
| Gemini | AI | 免费额度 | 需要 | 20次/天(免费) |
| OpenAI | AI | 付费 | 需要 | 按量计费 |
| Telegram | 推送 | 免费 | 需要 | 无 |

---

## 板块股票池

### AI大模型
| 代码 | 名称 | 稀缺性 |
|------|------|--------|
| 02513 | 智谱 | 全球仅2只纯大模型股 |
| 00100 | MiniMax | 全球仅2只纯大模型股 |
| 09888 | 百度 | AI搜索龙头 |

### 人形机器人
| 代码 | 名称 | 稀缺性 |
|------|------|--------|
| 09880 | 优必选 | 全球首家纯人形机器人IPO |
| 02432 | 越疆 | 协作机器人龙头 |

### GPU芯片
| 代码 | 名称 | 稀缺性 |
|------|------|--------|
| 06082 | 壁仞科技 | 国产GPU龙头 |
| 09903 | 天数智芯 | 国产GPU设计 |

### 更多板块
- 互联网：00700(腾讯)、09988(阿里)、03690(美团)
- 新能源车：01211(比亚迪)、09868(小鹏)
- 生物医药：02269(药明)、02675(精锋医疗)

---

## 快速开始

### 1. 环境配置

```bash
# 克隆项目
git clone https://github.com/hitome0123/hk-trading-bot.git
cd hk-trading-bot

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
export GEMINI_API_KEY="your_gemini_key"
export OPENAI_API_KEY="your_openai_key"  # 可选
```

### 2. 启动富途 OpenD

```bash
# Mac
open "/path/to/Futu_OpenD-GUI"

# 等待连接成功
python test_futu_simple.py
```

### 3. 运行系统

```bash
# 热门板块扫描
python sector_trading_advisor.py

# 情绪分析
python sentiment_hub.py 09880

# 深度研究
python gemini_deep_research.py 02513
```

### 4. 部署云端监控 (可选)

```bash
# 部署到阿里云
./deploy/update_cloud_service.sh
```

---

## 交易策略

### 五条铁律
1. **只做热门龙头** - 不碰冷门股
2. **突破放量买入** - 量价配合
3. **2%止损** - 铁律执行
4. **达标收工** - 不贪心
5. **止损停手** - 当日不再交易

### 渐进目标
| 等级 | 日收益 | 本金要求 |
|------|--------|----------|
| Lv.1 | 300元 | 5万 |
| Lv.2 | 500元 | 8万 |
| Lv.3 | 800元 | 12万 |
| Lv.4 | 1000元 | 15万 |

### 主力成本分析
- **富途"主力"**: 按订单金额分类（特大单>100万, 大单20-100万）
- **主力成本估算**: 20日VWAP
- **买入信号**: 主力净流入>500万 + 现价≤20日VWAP
- **卖出信号**: 现价>VWAP×115% 或 主力连续3天净流出

---

## 项目结构

```
hk-trading-bot/
├── sector_trading_advisor.py   # 热门板块推送 (核心)
├── sentiment_hub.py            # 多市场情绪分析
├── gemini_deep_research.py     # AI深度研究
├── my_strategy_helper.py       # 策略助手
├── research_analyzer.py        # 研究报告分析
│
├── deploy/
│   ├── cloud_sentiment_monitor.py  # 云端情绪监控
│   └── update_cloud_service.sh     # 部署脚本
│
├── n8n_*.py                    # n8n工作流桥接
├── gemini_analyzer.py          # Gemini AI分析器
├── grok_sentiment_analyzer.py  # Grok情绪分析
│
├── 操作手册.md                  # 完整操作手册
├── 港股交易完整策略手册_v2.0.md  # 策略手册
└── 港股稀缺概念股图谱.md         # 稀缺股图谱
```

---

## Telegram 推送

### 配置
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
TELEGRAM_CHAT_ID = "your_chat_id"
```

### 推送内容
- 📊 **热门板块** - 涨幅板块 + 进场建议
- 🔔 **情绪告警** - 情绪突变提醒
- 📈 **盘前提醒** - 今日关注股票
- 📉 **盘后报告** - 当日复盘

---

## 常用命令

```bash
# 快捷别名 (添加到 ~/.zshrc)
alias 研究='python ~/hk-trading-bot/gemini_deep_research.py'
alias 情绪='python ~/hk-trading-bot/sentiment_hub.py'
alias 扫描='python ~/hk-trading-bot/my_strategy_helper.py scan'
alias 补涨='python ~/hk-trading-bot/my_strategy_helper.py laggards'

# 使用方式
研究 09880
情绪 NVDA
扫描
```

---

## 免责声明

- 本项目仅用于学习和研究目的
- 不构成任何投资建议
- 使用者需自行承担所有风险
- 富途 OpenD 仅用于只读查询，禁止交易操作

---

## License

MIT
