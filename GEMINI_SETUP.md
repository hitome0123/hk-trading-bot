# 🧠 Gemini AI 配置完成

你的Gemini API密钥已经配置完成！

## 🔑 API密钥信息
- **API Key**: AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q
- **状态**: ✅ 已保存
- **位置**: `.env` 文件

## 🚀 如何使用AI功能

### 方法1: 使用启动脚本 (推荐)
```bash
cd /Users/mantou/hk-trading-bot
./launch_with_ai.sh
```

### 方法2: 直接命令行
```bash
cd /Users/mantou/hk-trading-bot
GEMINI_API_KEY="AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q" python enhanced_main.py 2807.HK
```

### 方法3: 导出环境变量
```bash
cd /Users/mantou/hk-trading-bot
export GEMINI_API_KEY="AIzaSyAr4MtcaHs5vOsrSe809gFFOApyAbmBC2Q"
python enhanced_main.py 2807.HK
```

## 🎯 AI功能包括

1. **基本面分析**
   - 公司财务健康度评分
   - 增长前景分析
   - 竞争地位评估
   - 投资评级建议

2. **市场情绪分析**
   - 市场情绪评分 (-10到10)
   - 情绪趋势分析
   - 关键影响因素识别

3. **综合投资建议**
   - 技术面 + 基本面 + 情绪面
   - 智能入场价格调整
   - 风险警告和建议

## ⚠️ 注意事项

- API有免费额度限制
- 分析结果会自动缓存24小时
- 如果API调用失败，会自动回退到默认分析

## 🔧 故障排除

如果遇到Gemini API问题：
1. 检查网络连接
2. 验证API密钥是否有效
3. 查看是否超出免费额度
4. 系统会自动回退到技术分析

你的AI驱动港股分析系统已经准备就绪！🎉