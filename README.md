# 港股交易机器人 (HK Trading Bot)

> 整合 Larry Williams、Victor Sperandeo、Jesse Livermore、Mark Minervini 四大交易大师方法论
>
> 5万本金，日赚300→500→800→1000元渐进体系

一个基于四大师交易理论的港股T+0交易系统，使用Python + 富途OpenD实现。

## 📚 完整策略手册

**⭐ 核心文档**：[港股交易完整策略手册 v2.0](./港股交易完整策略手册_v2.0.md)

包含：
- ✅ 五条铁律（必须打印贴在屏幕旁）
- ✅ 四大师方法论整合（Williams/Sperandeo/Livermore/Minervini）
- ✅ 三大策略组合（T+0狙击/堕落天使/稀缺股波段）
- ✅ 渐进目标体系（Lv.1→Lv.4）
- ✅ 完整选股系统（40+只股票池）
- ✅ 实战案例分析

## 🎯 项目特性

## 🎯 项目特性

### 基础功能
- **纸上交易**: 100% 模拟交易，无真实资金风险
- **技术指标**: 集成EMA20、EMA50、RSI14、ATR14指标计算
- **智能入场**: 基于技术分析的自动入场价格计算
- **风险控制**: 多重风险检查机制
- **模块化设计**: 清晰的代码结构，易于扩展

### 🚀 增强功能 (New!)
- **真实数据**: Yahoo Finance MCP + 直接API双重数据源
- **AI基本面分析**: Gemini AI驱动的公司基本面分析
- **市场情绪分析**: 基于AI的市场情绪判断
- **综合评分系统**: 技术面+基本面+情绪面综合评分
- **智能缓存**: 节省API调用，提高响应速度
- **数据质量评估**: 自动评估数据可靠性

## 📁 项目结构

```
hk_trading_bot/
├── modules/
│   ├── indicators/          # 技术指标模块
│   ├── entry_pricing/       # 入场定价策略
│   ├── risk_gate/          # 风险控制
│   └── execution_paper/    # 模拟交易执行
├── data/                   # 交易数据存储
├── logs/                   # 日志文件
└── tests/                  # 测试文件

main.py                     # 主程序入口
demo_script.py             # 完整演示脚本
requirements.txt           # 依赖包
```

## ⚙️ 安装和运行

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 基础版本 (模拟数据)
```bash
python main.py 0700.HK                    # 单次分析
python demo_script.py                     # 完整演示
```

### 3. 增强版本 (真实数据 + AI分析)
```bash
# 设置Gemini API密钥 (可选，用于AI分析)
export GEMINI_API_KEY="your_api_key_here"

# 运行增强分析
python enhanced_main.py 0700.HK
```

详细配置请参考 [setup_guide.md](setup_guide.md)

## 🧠 核心逻辑

### 技术指标计算
- **EMA20/EMA50**: 指数移动平均线，判断趋势方向
- **RSI14**: 相对强弱指数，识别超买超卖
- **ATR14**: 平均真实波幅，衡量波动性

### 入场策略
1. **上升趋势**: EMA20 > EMA50 且 RSI < 70
2. **超卖反弹**: RSI < 30（抄底机会）
3. **ATR缓冲**: 使用ATR确定合理入场价格区间

### 风险控制
- 最大单仓位: 10,000 HKD
- 每日交易限制: 5笔
- 价格范围检查: 1.0 - 1000.0 HKD
- 交易时间限制: 09:30 - 16:00
- 港股格式验证: 必须以.HK结尾

## 💡 使用示例

```python
from hk_trading_bot.modules.indicators import TechnicalIndicators
from hk_trading_bot.modules.entry_pricing import EntryStrategy
from hk_trading_bot.modules.execution_paper import PaperTrader

# 计算技术指标
price_data = {'close': [50, 51, 49, 52, 48]}  # 历史价格
indicators = TechnicalIndicators.calculate_all_indicators(price_data)

# 计算入场价格
strategy = EntryStrategy()
entry_info = strategy.calculate_entry_price(50.0, indicators)

# 执行模拟交易
trader = PaperTrader()
result = trader.place_order('0700.HK', 'buy', 100, 50.0)
```

## 📊 输出示例

```
🤖 HK Trading Bot initialized
💰 Initial cash: 100,000.00 HKD

📊 Analyzing 0700.HK...
💲 Current price: 72.25 HKD

📈 Technical Indicators:
   EMA20: 76.35
   EMA50: 80.78
   RSI14: 29.27
   ATR14: 1.57

🎯 Entry Analysis:
   Signal: LONG
   Reason: Oversold bounce opportunity (RSI=29.3 < 30)
   Entry Price: 71.86 HKD
   Discount: 0.5%

💼 Portfolio Summary:
   Cash: 100,000.00 HKD
   Total Value: 100,000.00 HKD
   P&L: 0.00 HKD (0.0%)
```

## 🔧 配置说明

### 风险控制配置
```python
{
    'max_position_size': 10000,      # 最大单仓位金额 (HKD)
    'max_daily_trades': 5,           # 每日最大交易次数
    'max_portfolio_risk': 0.02,      # 组合最大风险比例
    'min_price_threshold': 1.0,      # 最低价格阈值
    'max_price_threshold': 1000.0,   # 最高价格阈值
}
```

### 入场策略配置
```python
{
    'atr_multiplier': 0.5,    # ATR倍数
    'max_discount': 0.02,     # 最大折扣比例
    'rsi_oversold': 30,       # RSI超卖阈值
    'rsi_overbought': 70      # RSI超买阈值
}
```

## ⚠️ 免责声明

- 本项目仅用于学习和研究目的
- 所有交易均为模拟，不涉及真实资金
- 不构成任何投资建议
- 使用者需自行承担所有风险

## 🎓 交易系统技能

### 📚 港股日赚300元交易系统
- **位置**: `docs/skills/港股日赚300元交易系统.md`
- **完整指南**: `docs/交易系统使用指南.md`
- **技能名**: `hk-stock-daily-profit`
- **特点**:
  - 基于Larry Williams、Oliver Velez等大师方法论
  - 5万本金日赚300元进阶方案
  - 完整的买卖点判断系统
  - 11个实战场景测试
  - 清晰的进阶路径（300→500→1000元/天）

### 🔗 技能+Bot联动
- **Bot负责**: 扫描市场、实时监控、数据分析
- **技能负责**: 买卖决策、风险管理、心理纪律
- **配合使用**: 查看 `docs/交易系统使用指南.md`

### 快速使用
```bash
# 在Claude Code中调用
/hk-stock-daily-profit

# 或查看完整文档
cat docs/skills/港股日赚300元交易系统.md
```

---

## 🚀 扩展计划

- [ ] 支持更多技术指标
- [ ] 回测功能
- [ ] Web界面
- [ ] 实时行情接入
- [ ] 更复杂的交易策略
- [x] **交易系统技能整合** ✅