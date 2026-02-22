#!/usr/bin/env python3
"""
Gemini分析模块 - 深度分析板块炒作周期
使用Google Gemini API进行智能分析（免费额度大，国内可用）
"""
import os
import json

try:
    from google import genai
except ImportError:
    print("⚠️ 需要安装 google-genai:")
    print("pip install google-genai")
    raise

class GeminiAnalyzer:
    """使用Gemini分析板块炒作潜力"""

    def __init__(self, api_key=None, model='gemini-2.5-flash'):
        """
        初始化Gemini分析器

        参数：
        - api_key: Google API密钥（可从环境变量GEMINI_API_KEY读取）
        - model: 模型选择
          - 'gemini-2.5-flash'（推荐）：最新模型，速度快，免费额度大
          - 'gemini-1.5-pro'：稳定版本，质量高
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("需要设置GEMINI_API_KEY环境变量")

        self.model_name = model
        self.client = genai.Client(api_key=self.api_key)

    def analyze_sector_potential(self, sector_name, sector_data, news_list):
        """
        使用Gemini深度分析板块炒作潜力

        参数：
        - sector_name: 板块名称
        - sector_data: 板块数据（涨幅、个股等）
        - news_list: 相关资讯列表

        返回：
        {
            'reason': '涨的核心原因',
            'catalyst': '具体催化剂',
            'cycle': '1-3天/5-10天/10天+',
            'stage': '早期/中期/后期',
            'entry_timing': '进场时机分析',
            'recommendation': '买入/观望/回调买入/长期持有',
            'confidence': 0.8,
            'risk': '风险提示',
            'price_target': '预期涨幅空间',
            'hold_strategy': {
                'type': '短线/中线/长线',
                'reason': '持有理由',
                'fundamentals': '基本面支撑',
                'exit_signal': '卖出信号'
            }
        }
        """
        # 构建提示词
        prompt = self._build_analysis_prompt(sector_name, sector_data, news_list)

        # 调用Gemini
        response_text = self._call_gemini(prompt)

        # 解析响应
        analysis = self._parse_response(response_text)

        return analysis

    def _build_analysis_prompt(self, sector_name, sector_data, news_list):
        """构建分析提示词"""
        avg_change = sector_data['avg_change']
        stocks = sector_data['stocks']

        # 计算换手率
        high_volume_stocks = [s for s in stocks if s.get('turnover_rate', 0) > 10]

        prompt = f"""你是一位经验丰富的港股短线交易专家，专注于板块炒作分析。请深度分析以下板块的交易潜力。

## 板块基本信息
- **板块名称**: {sector_name}
- **今日平均涨幅**: {avg_change:.2f}%
- **高换手个股**: {len(high_volume_stocks)}只（换手率>10%）

## 个股表现
"""
        for i, stock in enumerate(stocks[:5], 1):
            prompt += f"{i}. {stock['name']}: {stock['change_pct']:+.2f}% (换手率: {stock.get('turnover_rate', 0):.1f}%, 成交量: {stock.get('volume', 0)/1e8:.2f}亿)\n"

        prompt += f"\n## 相关资讯\n"
        if news_list:
            for i, news in enumerate(news_list[:5], 1):
                prompt += f"{i}. {news['title']}\n"
        else:
            prompt += "**无直接相关资讯** - 仅基于价格和成交量异动\n"

        prompt += """
## 分析任务

你是港股短线交易专家，分析板块炒作潜力：
1. reason - 涨的核心原因（政策/业绩/概念/资金）
2. cycle - 炒作能持续多久（必须是："1-3天"或"5-10天"或"10天+"）
3. stage - 当前阶段（早期/中期/后期）
4. recommendation - 操作建议（买入/观望/回调买入/长期持有）

## 返回JSON（严格按此格式）

{
  "reason": "涨的原因（20字内）",
  "catalyst": "催化剂（20字内）",
  "cycle": "1-3天",
  "stage": "中期",
  "entry_timing": "进场时机（30字内）",
  "recommendation": "观望",
  "confidence": 0.75,
  "risk": "风险（20字内）",
  "price_target": "空间（15字内）",
  "hold_strategy": {
    "type": "短线",
    "reason": "理由（20字内）",
    "fundamentals": "基本面（20字内）",
    "exit_signal": "卖出信号（20字内）"
  }
}

重要：
- cycle必须是："1-3天"或"5-10天"或"10天+"（表示炒作持续时间）
- recommendation必须是："买入"或"观望"或"回调买入"或"长期持有"
- confidence是0-1的小数
- 每个字段一句话，不换行
"""
        return prompt

    def _call_gemini(self, prompt):
        """调用Gemini API"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    'temperature': 0.3,  # 降低温度保证JSON格式稳定
                    'max_output_tokens': 2048,  # 增大输出限制
                    'response_mime_type': 'application/json',  # 强制JSON输出
                }
            )
            # Debug: 打印原始返回（如需调试请取消注释）
            # print(f"\n[DEBUG] 原始返回:\n{repr(response.text)}\n")
            return response.text
        except Exception as e:
            print(f"⚠️ Gemini调用失败: {e}")
            return None

    def _parse_response(self, response):
        """解析Gemini响应"""
        if not response:
            # 返回默认分析
            return {
                'reason': '数据分析中',
                'catalyst': '未知',
                'cycle': '1-3天',
                'stage': '未知',
                'entry_timing': '建议观望',
                'recommendation': '观望',
                'confidence': 0.5,
                'risk': 'API调用失败',
                'price_target': '未知',
                'hold_strategy': {
                    'type': '短线',
                    'reason': '未知',
                    'fundamentals': '未知',
                    'exit_signal': '未知'
                }
            }

        try:
            # 去掉markdown代码块标记
            clean_response = response.strip()
            if clean_response.startswith('```json'):
                clean_response = clean_response[7:]  # 去掉 ```json
            if clean_response.startswith('```'):
                clean_response = clean_response[3:]  # 去掉 ```
            if clean_response.endswith('```'):
                clean_response = clean_response[:-3]  # 去掉结尾 ```
            clean_response = clean_response.strip()

            # 尝试解析JSON
            analysis = json.loads(clean_response)

            # 确保包含hold_strategy
            if 'hold_strategy' not in analysis:
                analysis['hold_strategy'] = {
                    'type': '短线',
                    'reason': '未提供',
                    'fundamentals': '未提供',
                    'exit_signal': '未提供'
                }

            return analysis
        except Exception as e:
            print(f"⚠️ JSON解析失败: {e}")
            # 如果不是标准JSON，尝试提取关键信息
            return self._extract_from_text(response)

    def _extract_from_text(self, text):
        """从文本中提取分析结果"""
        # 简化处理，返回默认值
        return {
            'reason': '分析中',
            'catalyst': '详见完整分析',
            'cycle': '1-3天',
            'stage': '中期',
            'entry_timing': text[:100] if text else '建议观望',
            'recommendation': '观望',
            'confidence': 0.6,
            'risk': '详见完整分析',
            'price_target': '未知',
            'hold_strategy': {
                'type': '短线',
                'reason': '未提供',
                'fundamentals': '未提供',
                'exit_signal': '未提供'
            }
        }


# 测试代码
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试Gemini分析模块")
    print("="*60 + "\n")

    # 检查API密钥
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("⚠️ 未设置GEMINI_API_KEY环境变量")
        print("\n设置方法:")
        print("export GEMINI_API_KEY='your-api-key-here'")
        print("\n或者在 ~/.zshrc 中添加:")
        print("echo 'export GEMINI_API_KEY=\"your-api-key\"' >> ~/.zshrc")
        print("source ~/.zshrc")
        print("\n申请地址:")
        print("https://aistudio.google.com/app/apikey")
    else:
        print(f"✅ API密钥已配置: {api_key[:20]}...")

        # 测试分析
        analyzer = GeminiAnalyzer(model='gemini-2.5-flash')

        test_sector = "人形机器人"
        test_data = {
            'avg_change': 8.5,
            'stocks': [
                {'name': '优必选', 'change_pct': 12.3, 'turnover_rate': 15.2, 'volume': 5e8},
                {'name': '天弘基金', 'change_pct': 6.8, 'turnover_rate': 8.5, 'volume': 2e8}
            ]
        }
        test_news = [
            {'title': '优必选获得特斯拉大订单，人形机器人订单暴增'},
            {'title': '人形机器人产业迎来政策支持'}
        ]

        print(f"\n分析板块: {test_sector}")
        print(f"使用模型: {analyzer.model_name}")
        print("调用Gemini API...\n")

        result = analyzer.analyze_sector_potential(test_sector, test_data, test_news)

        print("分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
