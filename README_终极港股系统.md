# 港股终极智能监控系统 v4.0

## 🚀 系统特色

### 多平台社交媒体监控
- ✅ 微博热搜（财经相关）
- ✅ 抖音热榜（今日头条API）
- ✅ 雪球热股（港股专区）
- ✅ 淘股吧（龙头股讨论）
- ✅ 东方财富股吧（热帖）
- ✅ 集思录（套利机会）
- ✅ 知乎财经话题
- ✅ 财联社快讯（实时新闻）
- ✅ 豆瓣投资理财小组（ID: 648435）

### 智能板块识别
自动将社交媒体热搜关键词映射到港股板块：
- 商业航天
- AI人工智能
- 新能源汽车
- 半导体芯片
- 光伏太阳能
- 医药生物
- 消费零售
- 科技互联网

### 动态股票筛选
- ✅ 不再限制固定股票池
- ✅ 优先推荐：**中低市值** + **高波动** + **热门板块**
- ✅ 完整技术指标（RSI、MACD、布林带、量比）
- ✅ 增强评分系统（考虑社交热度）

---

## 📁 文件说明

### 核心文件

#### 1. `n8n_ultimate_hk_system.py` （推荐）
**终极版本**，整合所有功能：
- 多平台社交媒体采集
- 智能板块识别
- 动态股票筛选
- 增强评分系统

**使用：**
```bash
python3 /Users/mantou/hk-trading-bot/n8n_ultimate_hk_system.py
```

**输出格式：**
```json
{
  "stocks": [
    {
      "code": "01045",
      "name": "亚太卫星",
      "price": 4.44,
      "changePct": 11.0,
      "amplitude": 11.25,
      "score": 70,
      "rating": "buy",
      "sectors": ["商业航天", "卫星通信"],
      "reasons": ["强势上涨11.0%", "放量57.1倍", "热门板块:商业航天"]
    }
  ],
  "hot_sectors": ["商业航天", "新能源汽车"],
  "keyword_analysis": {...},
  "social_data_summary": {
    "weibo_count": 0,
    "douyin_count": 20,
    "cls_count": 0,
    "douban_count": 0
  }
}
```

---

#### 2. `n8n_hk_social_sector_bridge.py`
**社交媒体+板块联动版**：
- 基础社交媒体采集
- 板块映射
- 候选股票池

---

#### 3. `n8n_futu_bridge.py`（之前的增强版）
**完整技术指标版**：
- 固定股票池
- 完整技术指标
- 社交媒体热度（东财股吧）

---

#### 4. `n8n_market_data_futu.py`（备用）
**简单市场数据版**：
- 东财API兼容格式
- 快速返回100只股票
- 无技术指标

---

#### 5. `n8n_multi_platform_social.py`（独立采集器）
**纯社交媒体采集器**：
- 9大平台数据采集
- 关键词聚合分析
- 独立运行

**使用：**
```bash
python3 /Users/mantou/hk-trading-bot/n8n_multi_platform_social.py
```

---

## 🔧 n8n集成方案

### 方案1: 使用终极版本（推荐）

**n8n Code节点配置：**
```javascript
const { execSync } = require('child_process');

try {
  const raw = execSync(
    'python3 /Users/mantou/hk-trading-bot/n8n_ultimate_hk_system.py 2>/dev/null',
    { timeout: 60000, encoding: 'utf-8' }
  );

  const data = JSON.parse(raw);
  return [{ json: data }];

} catch(e) {
  return [{ json: { error: e.message, stocks: [] } }];
}
```

---

### 方案2: 分步执行

**步骤1: 采集社交媒体**
```javascript
// Code节点1: 社交媒体采集
const { execSync } = require('child_process');
const social = JSON.parse(execSync('python3 /Users/mantou/hk-trading-bot/n8n_multi_platform_social.py'));
return [{ json: social }];
```

**步骤2: 股票分析**
```javascript
// Code节点2: 基于社交数据分析股票
const { execSync } = require('child_process');
const stocks = JSON.parse(execSync('python3 /Users/mantou/hk-trading-bot/n8n_futu_bridge.py'));
return [{ json: stocks }];
```

---

## 📊 n8n工作流示例

### 完整工作流

```
[定时触发 - 每30分钟]
    ↓
[Code节点: 执行终极版脚本]
    ↓
[IF节点: 筛选score >= 60的股票]
    ↓        ↓
[买入]    [观望]
    ↓
[Function节点: 格式化通知消息]
    ↓
[HTTP Request: 发送钉钉/飞书通知]
```

---

### IF节点配置

**条件1: 强烈推荐（score >= 80）**
```json
{
  "conditions": {
    "number": [
      {
        "value1": "={{ $json.score }}",
        "operation": "largerEqual",
        "value2": 80
      }
    ]
  }
}
```

**条件2: 热门板块**
```json
{
  "conditions": {
    "boolean": [
      {
        "value1": "={{ $json.sectors.includes('商业航天') || $json.sectors.includes('AI人工智能') }}"
      }
    ]
  }
}
```

---

### Function节点: 格式化通知

```javascript
const stock = $input.all()[0].json;

const ratingEmoji = {
  'strong_buy': '🔥 强烈推荐',
  'buy': '✅ 建议关注',
  'neutral': '⚠️ 观望',
  'sell': '❌ 不推荐'
};

const message = `
📈 港股推荐 | ${stock.name} (${stock.code})

💰 现价: ${stock.price} HKD
📊 涨幅: ${stock.changePct > 0 ? '+' : ''}${stock.changePct}%
📏 振幅: ${stock.amplitude}%
🎯 评分: ${stock.score}/100

${ratingEmoji[stock.rating]}

🏷️ 板块: ${stock.sectors.join(', ')}
💡 理由: ${stock.reasons.join(' | ')}

⏰ ${new Date().toLocaleString('zh-CN')}
`;

return [{ json: { message } }];
```

---

## 🔄 数据库更新（直接修改n8n工作流）

### SQL方案: 更新现有节点

```sql
-- 更新"监控行情"节点（假设索引为6）
UPDATE workflow_entity
SET nodes = json_replace(
  nodes,
  '$[6].type', 'n8n-nodes-base.code',
  '$[6].name', '港股终极监控',
  '$[6].parameters', json('{"jsCode": "const { execSync } = require(''child_process'');\\ntry {\\n  const raw = execSync(''python3 /Users/mantou/hk-trading-bot/n8n_ultimate_hk_system.py 2>/dev/null'', { timeout: 60000, encoding: ''utf-8'' });\\n  const data = JSON.parse(raw);\\n  return [{ json: data }];\\n} catch(e) {\\n  return [{ json: { error: e.message, stocks: [] } }];\\n}", "mode": "runOnceForEachItem"}')
)
WHERE id = 'OjAShr4BbxlocAUf';
```

**执行：**
```bash
sqlite3 ~/.n8n/database.sqlite < update_workflow.sql
```

---

## 🎯 使用场景

### 1. 日常监控
**需求:** 每30分钟扫描一次热门股票

**配置:**
- 使用终极版脚本
- 定时触发: `*/30 * * * *`
- 筛选: score >= 50

---

### 2. 突发热点追踪
**需求:** 实时追踪社交媒体热搜，发现题材炒作

**配置:**
- 每10分钟执行
- 关注 `hot_sectors` 变化
- 检测新增板块

**示例通知：**
```
🚨 新增热门板块: 商业航天
📈 相关股票:
  • 亚太卫星 +11.0% (评分70)
  • 航天控股 +1.67% (评分55)
```

---

### 3. 盘前选股
**需求:** 每天开盘前筛选当日重点关注股票

**配置:**
- 定时: 每天 09:00
- 只看 rating = 'strong_buy'
- 发送详细报告到邮箱

---

## ⚙️ 高级配置

### 1. 提升社交媒体采集成功率

**问题:** 微博/豆瓣等平台需要登录

**解决方案:** 添加Cookie

编辑 `n8n_ultimate_hk_system.py`:

```python
self.headers = {
    "User-Agent": "Mozilla/5.0...",
    "Cookie": "你的Cookie字符串",  # 从浏览器F12复制
}
```

**获取Cookie步骤:**
1. 浏览器登录目标网站
2. F12打开开发者工具
3. Network → 刷新页面 → 找到请求
4. Headers → Cookie → 复制

---

### 2. 添加自定义板块

编辑 `HK_SECTORS` 字典:

```python
HK_SECTORS = {
    # ... 现有板块 ...

    '固态电池': [
        'HK.02460',  # 赣锋锂业
        'HK.01772',  # 江特电机
    ],

    '脑机接口': [
        'HK.09988',  # 阿里巴巴（达摩院）
        'HK.00020',  # 商汤科技
    ],
}
```

并更新 `KEYWORD_SECTOR_MAP`:

```python
KEYWORD_SECTOR_MAP = {
    # ... 现有映射 ...

    '固态电池': ['固态电池', '全固态', '锂电池', '电池技术'],
    '脑机接口': ['脑机接口', 'BCI', 'Neuralink', '脑科学'],
}
```

---

### 3. 调整评分权重

编辑 `calculate_enhanced_score` 函数:

```python
# 提高社交媒体权重
if social_mentions > 0:
    bonus = min(25, social_mentions * 8)  # 改为25分，每次提及8分
    score += bonus
```

---

## 🐛 故障排查

### 问题1: "futu-api not installed"

**解决:**
```bash
pip3 install futu-api
```

---

### 问题2: "requests not installed"

**解决:**
```bash
pip3 install requests beautifulsoup4
```

---

### 问题3: FutuOpenD未运行

**检查:**
```bash
ps aux | grep FutuOpenD
```

**解决:** 手动启动FutuOpenD应用

---

### 问题4: n8n节点超时

**原因:** 脚本执行时间超过默认60秒

**解决:** 修改Code节点timeout:
```javascript
{ timeout: 120000 }  // 2分钟
```

---

### 问题5: 社交媒体数据为空

**可能原因:**
1. 网络问题
2. 需要Cookie/登录
3. API限流

**解决:**
1. 检查网络连接
2. 添加Cookie（见高级配置）
3. 降低请求频率

---

## 📈 性能优化

### 1. 并发采集

修改社交媒体采集部分使用并发:

```python
import concurrent.futures

def collect_all(self):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            'weibo': executor.submit(self.get_weibo_hot),
            'douyin': executor.submit(self.get_douyin_hot),
            'cls': executor.submit(self.get_cls_news),
            # ...
        }

        results = {}
        for platform, future in futures.items():
            try:
                results[platform] = future.result(timeout=8)
            except:
                results[platform] = []

        return results
```

---

### 2. 缓存机制

**避免频繁调用Futu API**

```python
import time
import pickle

CACHE_FILE = '/tmp/hk_stock_cache.pkl'
CACHE_TTL = 300  # 5分钟

def get_cached_data():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as f:
            cache = pickle.load(f)
            if time.time() - cache['timestamp'] < CACHE_TTL:
                return cache['data']
    return None

def save_cache(data):
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump({
            'timestamp': time.time(),
            'data': data
        }, f)
```

---

## 📝 版本历史

### v4.0 Ultimate (当前)
- ✅ 多平台社交媒体监控（9大平台）
- ✅ 智能板块识别
- ✅ 动态股票池
- ✅ 社交媒体提及统计
- ✅ 增强评分系统

### v3.0
- 社交媒体+板块联动
- 基础关键词映射

### v2.0
- 完整技术指标
- 智能评分系统

### v1.0
- 基础市场数据获取

---

## 🔮 未来计划

- [ ] 增加更多社交平台（小红书、B站）
- [ ] AI大模型分析新闻情绪
- [ ] 自动识别龙头股
- [ ] 板块轮动预测
- [ ] 量化回测功能
- [ ] Web可视化界面

---

## 📞 技术支持

如有问题，请检查：
1. FutuOpenD是否运行
2. n8n是否运行
3. Python依赖是否安装
4. 日志输出（添加 `2>&1 | tee log.txt`）

---

**祝交易顺利！🚀📈**
