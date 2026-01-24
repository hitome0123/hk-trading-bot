# 集成配置指南

## 🔧 系统要求

- Python 3.8+
- 网络连接（用于获取实时股票数据）

## 📦 依赖安装

```bash
pip install -r requirements.txt
```

## 🔑 API密钥配置

### Gemini AI (基本面分析)

1. 获取Gemini API密钥：
   - 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
   - 创建新的API密钥

2. 配置方式 (选择一种)：
   ```bash
   # 方式1: 环境变量 (推荐)
   export GEMINI_API_KEY="你的API密钥"
   
   # 方式2: 命令行参数
   python enhanced_main.py 0700.HK your_api_key_here
   ```

### Yahoo Finance MCP (可选)

如果你已配置MCP Yahoo Finance服务：
```bash
# 检查MCP状态
mcp list

# 确保Yahoo Finance服务可用
mcp call yahoo-finance get_stock_data --ticker 0700.HK --period 1mo
```

## 🚀 使用方式

### 1. 基础版本 (模拟数据)
```bash
python main.py 0700.HK
```

### 2. 增强版本 (真实数据)
```bash
# 无AI分析
python enhanced_main.py 0700.HK

# 带AI分析
export GEMINI_API_KEY="你的密钥"
python enhanced_main.py 0700.HK
```

## 📊 功能对比

| 功能 | 基础版 | 增强版 |
|------|--------|--------|
| 技术指标分析 | ✅ | ✅ |
| 模拟交易 | ✅ | ✅ |
| 风险控制 | ✅ | ✅ |
| 真实价格数据 | ❌ | ✅ |
| 基本面分析 | ❌ | ✅ |
| 市场情绪分析 | ❌ | ✅ |
| 综合评分系统 | ❌ | ✅ |
| 智能缓存 | ❌ | ✅ |

## 🔍 数据来源

### 价格数据
1. **Yahoo Finance MCP** (优先)
2. **Yahoo Finance API** (备选)
3. **模拟数据** (最后备选)

### AI分析数据
1. **Gemini AI** (需要API密钥)
2. **默认分析** (无AI时使用)

## ⚠️ 注意事项

1. **API限制**: Gemini API有免费额度限制
2. **缓存机制**: AI分析会缓存24小时以节省API调用
3. **市场时间**: 系统会检查香港市场交易时间
4. **网络要求**: 需要稳定的网络连接获取实时数据

## 🛠️ 故障排除

### 常见问题

**Q: Gemini API调用失败**
```
⚠️ Gemini API key not found. Set GEMINI_API_KEY environment variable
```
A: 设置正确的API密钥，检查密钥是否有效

**Q: Yahoo Finance数据获取失败**
```
⚠️ Warning: Could not fetch real data for 0700.HK, using mock data
```
A: 检查网络连接，或等待几分钟后重试

**Q: MCP不可用**
```
📊 Real Data: Yahoo Finance fallback
```
A: 这是正常的，系统会自动使用备选数据源

## 🔧 高级配置

### 自定义策略参数
编辑 `enhanced_strategy.py` 中的配置：
```python
config = {
    'fundamental_weight': 0.4,  # 基本面权重
    'technical_weight': 0.4,   # 技术面权重  
    'sentiment_weight': 0.2,   # 情绪面权重
    'min_financial_health': 6, # 最低财务健康度
    # ... 更多参数
}
```

### 清除缓存
```python
from hk_trading_bot.data_providers import EnhancedDataProvider

provider = EnhancedDataProvider()
provider.clear_cache()  # 清除所有缓存
provider.clear_cache('0700.HK')  # 清除特定股票缓存
```

## 📈 示例输出

增强版系统会提供详细的分析报告：
```
🔬 Starting comprehensive analysis for 0700.HK
📊 Fetching price data...
🧠 Analyzing fundamentals with Gemini AI...
📈 Analyzing market sentiment...

📈 Technical Indicators:
   EMA20: 76.35, EMA50: 80.78, RSI14: 29.27, ATR14: 1.57

🏢 Fundamental Analysis (Confidence: 8/10):
   Investment Rating: 买入
   Financial Health: 8/10
   Growth Prospects: 7/10

🎯 Enhanced Entry Analysis:
   Overall Signal: BUY
   Entry Price: 74.20 HKD
   Recommendation: 建议买入，等待价格回落至74.20 HKD附近
```