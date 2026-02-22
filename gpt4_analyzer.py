#!/usr/bin/env python3
"""
GPT-4分析模块 - 深度分析板块炒作周期
使用OpenAI GPT-4 API进行智能分析
"""
import requests
import json
import os

class GPT4Analyzer:
    """使用GPT-4分析板块炒作潜力"""

    def __init__(self, api_key=None):
        """
        初始化GPT-4分析器
        api_key: OpenAI API密钥
                可以从环境变量OPENAI_API_KEY读取
                或者直接传入
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1/chat/completions"

    def analyze_sector_potential(self, sector_name, sector_data, news_list):
        """
        使用GPT-4深度分析板块炒作潜力

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
            'recommendation': '买入/观望/回调买入',
            'confidence': 0.8,
            'risk': '风险提示',
            'price_target': '预期涨幅空间'
        }
        """
        if not self.api_key:
            raise ValueError("需要设置OPENAI_API_KEY环境变量")

        # 构建提示词
        prompt = self._build_analysis_prompt(sector_name, sector_data, news_list)

        # 调用GPT-4
        response = self._call_gpt4(prompt)

        # 解析响应
        analysis = self._parse_response(response)

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
## 分析维度

请从以下角度进行专业分析：

### 1. 涨的根本原因
- 是政策驱动、业绩驱动、还是概念炒作？
- 有实质性利好支撑，还是纯资金推动？
- 这波上涨的核心逻辑是什么？

### 2. 炒作周期预判 vs 长期投资价值
**炒作周期判断**：
- **1-3天**：纯情绪炒作，无实质利好，快进快出
- **5-10天**：中线题材，有催化剂支撑
- **10天+**：长线趋势，有基本面或政策支撑

**长期持有价值判断（重要！）**：
如果符合以下条件，应推荐"长期持有"而非短线炒作：
1. **业绩驱动**：公司业绩持续增长，盈利能力强
2. **政策扶持**：国家级产业政策支持，行业长期向好
3. **技术壁垒**：核心技术领先，竞争优势明显
4. **行业龙头**：市场份额第一，定价权强
5. **估值合理**：PE/PB处于合理区间，有安全边际

**区分标准**：
- 短线炒作：靠消息、概念、资金推动，持续性差
- 长期持有：靠业绩、政策、技术壁垒，可穿越周期

### 3. 当前所处阶段
- **早期**：刚启动，涨幅<5%，成交量温和放大
- **中期**：加速期，涨幅5-10%，成交量显著放大
- **后期**：末期，涨幅>10%，可能见顶

### 4. 进场时机判断
- 现在适合进场吗？
- 如果不适合，什么时候进场更好？
- 止损位设在哪里？

### 5. 风险评估
- 这波炒作的风险点在哪里？
- 什么信号出现时应该离场？

## 输出格式

请用以下JSON格式回复（不要包含```json标记，直接返回JSON）：

{{
    "reason": "涨的核心原因（一句话，30字内）",
    "catalyst": "具体催化剂是什么",
    "cycle": "1-3天" 或 "5-10天" 或 "10天+",
    "stage": "早期" 或 "中期" 或 "后期",
    "entry_timing": "进场时机分析（50字内）",
    "recommendation": "买入" 或 "观望" 或 "回调买入" 或 "长期持有",
    "confidence": 0.8,
    "risk": "主要风险点",
    "price_target": "预期还有10-15%空间" 或 "涨幅已大，空间有限",
    "hold_strategy": {{
        "type": "短线" 或 "中线" 或 "长线",
        "reason": "为什么适合长期持有的理由（如果是长线）",
        "fundamentals": "基本面支撑（如业绩、政策、行业趋势等）",
        "exit_signal": "什么情况下应该卖出"
    }}
}}

**重要**:
1. 必须基于数据和资讯做出客观判断
2. 如果没有明确利好，不要推荐买入
3. confidence要实事求是，不要虚高
"""
        return prompt

    def _call_gpt4(self, prompt):
        """调用GPT-4 API"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': 'gpt-4',  # 或 'gpt-4-turbo-preview'
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一位专业的港股短线交易分析师，擅长分析板块炒作周期和进场时机。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 800
        }

        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                raise Exception(f"API调用失败: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"⚠️ GPT-4调用失败: {e}")
            return None

    def _parse_response(self, response):
        """解析GPT-4响应"""
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
                'price_target': '未知'
            }

        try:
            # 尝试解析JSON
            analysis = json.loads(response)
            return analysis
        except:
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
            'price_target': '未知'
        }


# 测试代码
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试GPT-4分析模块")
    print("="*60 + "\n")

    # 检查API密钥
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("⚠️ 未设置OPENAI_API_KEY环境变量")
        print("\n设置方法:")
        print("export OPENAI_API_KEY='your-api-key-here'")
        print("\n或者在 ~/.zshrc 中添加:")
        print("echo 'export OPENAI_API_KEY=\"your-api-key\"' >> ~/.zshrc")
        print("source ~/.zshrc")
    else:
        print(f"✅ API密钥已配置: {api_key[:20]}...")

        # 测试分析
        analyzer = GPT4Analyzer()

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
        print("调用GPT-4 API...\n")

        result = analyzer.analyze_sector_potential(test_sector, test_data, test_news)

        print("分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
