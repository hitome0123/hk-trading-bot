# Gemini版板块交易顾问 - 快速使用指南

## ✅ 已完成配置

- **API密钥**: 已配置（AIzaSyAKEu9CUAnfLU_B...）
- **模型**: Gemini 2.5 Flash
- **环境**: 已保存到 `~/.zshrc`
- **SDK**: google-genai（最新版）

## 🚀 使用方法

### 方式1: 直接运行

```bash
cd ~/hk-trading-bot
python3 sector_trading_advisor.py
```

系统会：
1. 从富途扫描涨幅>5%的板块
2. 抓取新浪财经相关资讯
3. **用Gemini AI深度分析**
4. 推送到Telegram

### 方式2: 定时运行

每天盘中10:00自动分析，编辑crontab：

```bash
crontab -e
```

添加：

```bash
0 10 * * 1-5 cd /Users/mantou/hk-trading-bot && /Users/mantou/miniconda3/bin/python3 sector_trading_advisor.py
```

## 📊 Gemini分析示例

### 输入
- 板块：人形机器人 +8.06%
- 龙头：优必选 +12.3%
- 资讯：特斯拉大订单

### 输出
```json
{
  "reason": "概念炒作，特斯拉大订单驱动资金涌入",
  "catalyst": "特斯拉大订单，订单量暴增",
  "cycle": "5-10天",
  "stage": "中期",
  "entry_timing": "关注回调企稳后的低吸机会，不宜追高",
  "recommendation": "回调买入",
  "confidence": 0.75,
  "risk": "概念炒作风险，获利回吐压力",
  "price_target": "短线看涨，关注阻力",
  "hold_strategy": {
    "type": "短线",
    "reason": "概念驱动，短期资金追捧",
    "fundamentals": "行业前景广阔，短期业绩未兑现",
    "exit_signal": "涨幅放缓，量价背离或利好兑现"
  }
}
```

## 💰 费用说明

| 项目 | Gemini 2.5 Flash | OpenAI GPT-4 |
|------|------------------|--------------|
| **免费额度** | 1500次/天 | 无 |
| **单次费用** | ¥0 | ¥0.07-0.21 |
| **月成本** | ¥0 | ¥100-300 |
| **网络要求** | 国内直连 | 需要梯子 |

**结论**：Gemini完全免费，无需梯子，够用！

## 🔧 高级配置

### 切换到Pro模型（质量更高）

编辑 `sector_trading_advisor.py` 第196行：

```python
# 当前（Flash）
analyzer = GeminiAnalyzer(model='gemini-2.5-flash')

# 改为（Pro）
analyzer = GeminiAnalyzer(model='gemini-1.5-pro')
```

**注意**：Pro免费额度只有50次/天

### 查看详细日志

```bash
python3 sector_trading_advisor.py 2>&1 | tee analysis.log
```

### 测试单个板块

编辑 `gemini_analyzer.py` 底部测试代码，运行：

```bash
python3 gemini_analyzer.py
```

## ⚠️ 常见问题

### Q: JSON解析失败怎么办？

**A**: 正常现象，系统会自动降级到规则分析。Gemini偶尔返回格式不标准的JSON，不影响使用。

### Q: API调用失败？

**A**: 检查网络和API密钥：

```bash
echo $GEMINI_API_KEY
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$GEMINI_API_KEY"
```

### Q: 想禁用Gemini，用回规则分析？

**A**: 删除环境变量：

```bash
unset GEMINI_API_KEY
```

## 📈 效果对比

### 基础版（规则分析）
```
💡 跟风炒作: 跟随市场热点
⏱️ 预期周期: 1-3天
🎯 建议: 观望 (信心40%)
```

### Gemini版（AI分析）
```
💡 特斯拉大订单催化，概念炒作资金涌入
⏱️ 预期周期: 5-10天（中线持有）
🎯 建议: 回调买入 (信心75%)
📈 预期空间: 短线看涨，关注阻力
💎 长期持有: 行业前景广阔，短期业绩未兑现
🚪 卖出信号: 涨幅放缓，量价背离或利好兑现
```

**结论**：Gemini版提供更深度的分析和更高的信心度！

## 🎯 下一步

1. **观察准确率**：运行几天看看推荐准不准
2. **调整参数**：根据准确率调整confidence阈值
3. **优化推送**：只推送信心>70%的板块

---

**系统已就绪，随时可用！** 🚀
