#!/usr/bin/env python3
"""
Gemini Deep Research - 板块深度研究
模拟 Gemini Deep Research 功能，进行多维度深度分析

功能：
1. 多轮搜索：行业政策、公司基本面、竞争格局、技术趋势
2. 综合分析：整合多来源信息
3. 深度报告：生成投资研究报告

使用方法：
    python gemini_deep_research.py 人形机器人
    python gemini_deep_research.py --stock HK.09880
"""
import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from google import genai
    from google.genai.types import Tool, GoogleSearch
except ImportError:
    print("⚠️ 需要安装 google-genai:")
    print("pip install google-genai")
    sys.exit(1)


@dataclass
class ResearchDimension:
    """研究维度"""
    name: str           # 维度名称
    query: str          # 搜索查询
    weight: float       # 权重 (0-1)
    results: str = ""   # 搜索结果
    analysis: str = ""  # 分析结论


@dataclass
class DeepResearchReport:
    """深度研究报告"""
    subject: str                    # 研究主题
    timestamp: str                  # 时间戳
    executive_summary: str          # 执行摘要
    dimensions: List[Dict]          # 各维度分析
    investment_thesis: str          # 投资逻辑
    catalysts: List[str]            # 催化剂
    risks: List[str]                # 风险因素
    price_targets: Dict             # 目标价
    recommendation: str             # 投资建议
    confidence: float               # 置信度
    sources: List[str]              # 信息来源


# 常见港股代码 -> 名称映射
HK_STOCK_NAMES = {
    '09880': '优必选',
    '09988': '阿里巴巴',
    '00700': '腾讯',
    '03690': '美团',
    '09999': '网易',
    '09618': '京东',
    '01024': '快手',
    '02382': '舜宇光学',
    '09888': '百度',
    '06082': '壁仞科技',
    '02513': '智谱',
    '00100': 'MiniMax',
    '09903': '天数智芯',
    '02675': '精锋医疗',
    '01164': '中广核矿业',
    '00470': '先导智能',
    '02432': '协鑫科技',
    '00388': '香港交易所',
    '00005': '汇丰控股',
    '00941': '中国移动',
    '02318': '中国平安',
    '01810': '小米',
    '09626': '哔哩哔哩',
    '02015': '理想汽车',
    '09866': '蔚来',
    '09868': '小鹏汽车',
}


def get_stock_name_from_futu(stock_code: str) -> Optional[str]:
    """从富途 OpenD 获取股票名称"""
    try:
        import os
        os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'
        from futu import OpenQuoteContext, RET_OK

        # 标准化代码格式
        if not stock_code.startswith('HK.'):
            code = f'HK.{stock_code.zfill(5)}'
        else:
            code = stock_code

        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        ret, data = quote_ctx.get_market_snapshot([code])
        quote_ctx.close()

        if ret == RET_OK and len(data) > 0:
            return data.iloc[0]['name']
        return None
    except Exception as e:
        return None


def get_stock_name(stock_code: str) -> str:
    """获取股票名称 - 优先富途，备用本地映射"""
    code_num = stock_code.replace('HK.', '').lstrip('0') or '0'
    code_5 = stock_code.replace('HK.', '').zfill(5)

    # 1. 先查本地映射 (快)
    if code_5 in HK_STOCK_NAMES:
        return HK_STOCK_NAMES[code_5]

    # 2. 尝试富途 OpenD (准确)
    futu_name = get_stock_name_from_futu(stock_code)
    if futu_name:
        # 缓存到本地映射
        HK_STOCK_NAMES[code_5] = futu_name
        return futu_name

    # 3. 返回代码本身
    return stock_code


class DeepResearch:
    """深度研究引擎 - 支持 Gemini 和 OpenAI"""

    def __init__(self, api_key: str = None, model: str = 'auto'):
        """
        初始化深度研究引擎

        参数：
        - api_key: API Key (自动检测)
        - model: 模型选择
          - 'auto': 自动选择可用的 (优先 Gemini)
          - 'gemini': 使用 Gemini
          - 'openai' / 'gpt-4': 使用 OpenAI GPT-4
        """
        self.gemini_key = os.getenv('GEMINI_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')

        # 自动选择引擎 (优先 OpenAI)
        if model == 'auto':
            if self.openai_key:
                self.engine = 'openai'
                self.model = 'gpt-4o'
            elif self.gemini_key:
                self.engine = 'gemini'
                self.model = 'gemini-2.5-flash'
            else:
                raise ValueError("需要设置 GEMINI_API_KEY 或 OPENAI_API_KEY")
        elif model in ['openai', 'gpt-4', 'gpt-4o']:
            if not self.openai_key:
                raise ValueError("需要设置 OPENAI_API_KEY")
            self.engine = 'openai'
            self.model = 'gpt-4o'
        else:
            if not self.gemini_key:
                raise ValueError("需要设置 GEMINI_API_KEY")
            self.engine = 'gemini'
            self.model = model

        # 初始化客户端
        if self.engine == 'gemini':
            self.client = genai.Client(api_key=self.gemini_key)

        self.search_count = 0
        self.max_searches = 10

        print(f"🤖 引擎: {self.engine.upper()} ({self.model})")

    def research_sector(self, sector_name: str, top_stocks: List[Dict] = None) -> DeepResearchReport:
        """
        对板块进行深度研究

        参数：
        - sector_name: 板块名称（如"人形机器人"、"AI大模型"）
        - top_stocks: 龙头股票列表 [{'code': 'HK.09880', 'name': '优必选'}, ...]

        返回：
        - DeepResearchReport: 深度研究报告
        """
        print(f"\n{'='*70}")
        print(f"🔬 Gemini Deep Research - {sector_name}")
        print(f"{'='*70}")
        print(f"📅 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🤖 模型: {self.model}")
        print()

        self.search_count = 0
        start_time = time.time()

        # 1. 定义研究维度
        dimensions = self._define_dimensions(sector_name, top_stocks)
        print(f"📊 研究维度: {len(dimensions)}个\n")

        # 2. 并行执行多维度搜索
        print("🔍 Phase 1: 多维度信息收集")
        print("-" * 50)
        self._execute_searches(dimensions)

        # 3. 深度分析各维度
        print(f"\n🧠 Phase 2: 深度分析")
        print("-" * 50)
        self._analyze_dimensions(dimensions, sector_name)

        # 4. 综合研判
        print(f"\n📝 Phase 3: 综合研判")
        print("-" * 50)
        report = self._synthesize_report(sector_name, dimensions, top_stocks)

        elapsed = time.time() - start_time
        print(f"\n✅ 研究完成 (耗时: {elapsed:.1f}秒, 搜索: {self.search_count}次)")

        return report

    def research_stock(self, stock_code: str, stock_name: str = None) -> DeepResearchReport:
        """
        对单只股票进行深度研究

        参数：
        - stock_code: 股票代码（如"HK.09880"）
        - stock_name: 股票名称（可选，会自动查找常见港股）

        返回：
        - DeepResearchReport: 深度研究报告
        """
        # 获取股票名称 (优先富途 OpenD)
        if not stock_name:
            stock_name = get_stock_name(stock_code)

        print(f"\n{'='*70}")
        print(f"🔬 Gemini Deep Research - {stock_name} ({stock_code})")
        print(f"{'='*70}")

        self.search_count = 0
        start_time = time.time()

        # 定义个股研究维度
        dimensions = self._define_stock_dimensions(stock_code, stock_name)

        # 执行搜索
        print("🔍 Phase 1: 信息收集")
        print("-" * 50)
        self._execute_searches(dimensions)

        # 深度分析
        print(f"\n🧠 Phase 2: 深度分析")
        print("-" * 50)
        self._analyze_dimensions(dimensions, stock_name)

        # 综合研判
        print(f"\n📝 Phase 3: 综合研判")
        print("-" * 50)
        report = self._synthesize_stock_report(stock_code, stock_name, dimensions)

        elapsed = time.time() - start_time
        print(f"\n✅ 研究完成 (耗时: {elapsed:.1f}秒, 搜索: {self.search_count}次)")

        return report

    def _define_dimensions(self, sector_name: str, top_stocks: List[Dict] = None) -> List[ResearchDimension]:
        """定义板块研究维度"""
        dimensions = [
            ResearchDimension(
                name="行业政策",
                query=f"{sector_name} 政策 支持 规划 2025 2026 最新",
                weight=0.25
            ),
            ResearchDimension(
                name="市场规模",
                query=f"{sector_name} 市场规模 增长率 预测 2026",
                weight=0.15
            ),
            ResearchDimension(
                name="竞争格局",
                query=f"{sector_name} 龙头企业 市场份额 竞争格局",
                weight=0.20
            ),
            ResearchDimension(
                name="技术趋势",
                query=f"{sector_name} 技术突破 创新 最新进展 2026",
                weight=0.15
            ),
            ResearchDimension(
                name="资金动向",
                query=f"{sector_name} 板块 资金流向 机构持仓 港股",
                weight=0.15
            ),
            ResearchDimension(
                name="近期催化",
                query=f"{sector_name} 最新消息 利好 催化剂 今天 本周",
                weight=0.10
            ),
        ]

        # 如果有龙头股，添加龙头股研究
        if top_stocks:
            for stock in top_stocks[:2]:  # 只研究前2只龙头
                dimensions.append(ResearchDimension(
                    name=f"龙头-{stock.get('name', stock.get('code', 'Unknown'))}",
                    query=f"{stock.get('name', '')} {stock.get('code', '').replace('HK.', '')} 最新消息 业绩 订单",
                    weight=0.00  # 龙头股单独分析，不计入总权重
                ))

        return dimensions

    def _define_stock_dimensions(self, stock_code: str, stock_name: str) -> List[ResearchDimension]:
        """定义个股研究维度"""
        code_num = stock_code.replace('HK.', '')

        return [
            ResearchDimension(
                name="公司基本面",
                query=f"{stock_name} {code_num} 业绩 营收 利润 2025 2026",
                weight=0.25
            ),
            ResearchDimension(
                name="业务进展",
                query=f"{stock_name} 订单 合同 项目 客户 最新",
                weight=0.20
            ),
            ResearchDimension(
                name="竞争优势",
                query=f"{stock_name} 核心竞争力 技术壁垒 市场地位",
                weight=0.15
            ),
            ResearchDimension(
                name="券商研报",
                query=f"{stock_name} {code_num} 研究报告 目标价 评级",
                weight=0.20
            ),
            ResearchDimension(
                name="风险因素",
                query=f"{stock_name} 风险 挑战 问题 下跌",
                weight=0.10
            ),
            ResearchDimension(
                name="近期动态",
                query=f"{stock_name} 最新消息 今天 本周 港股",
                weight=0.10
            ),
        ]

    def _execute_searches(self, dimensions: List[ResearchDimension]):
        """执行多维度搜索（串行+速率限制，避免配额超限）"""
        for dim in dimensions:
            result = self._google_search(dim.query)
            dim.results = result
            status = "✅" if result and len(result) > 50 else "⚠️"
            print(f"  {status} {dim.name}: {len(result) if result else 0} 字符")
            time.sleep(12)  # 免费版限制：5次/分钟，间隔12秒

    def _google_search(self, query: str) -> str:
        """搜索信息 (Gemini 或 OpenAI)"""
        if self.search_count >= self.max_searches:
            return ""

        self.search_count += 1

        if self.engine == 'openai':
            return self._openai_search(query)
        else:
            return self._gemini_search(query)

    def _gemini_search(self, query: str) -> str:
        """Gemini + Google Search"""
        try:
            prompt = f"""搜索并总结以下主题的最新信息：

{query}

请提供：
1. 关键事实和数据
2. 最新动态和趋势
3. 重要信息来源

直接返回搜索结果摘要，不要废话。"""

            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    'temperature': 0.2,
                    'max_output_tokens': 1024,
                    'tools': [Tool(google_search=GoogleSearch())],
                }
            )

            return response.text if response.text else ""

        except Exception as e:
            print(f"    Gemini搜索错误: {e}")
            return ""

    def _openai_search(self, query: str) -> str:
        """OpenAI GPT-4 分析 (基于模型知识)"""
        try:
            import requests

            prompt = f"""基于你的知识，提供以下主题的深度分析：

{query}

请提供：
1. 关键事实和数据
2. 最新动态和趋势 (截至你的知识截止日期)
3. 重要信息来源

直接返回分析结果，不要废话。"""

            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.openai_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': '你是专业的金融研究分析师，擅长深度分析行业和公司。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 1024
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                print(f"    OpenAI错误: {response.status_code}")
                return ""

        except Exception as e:
            print(f"    OpenAI搜索错误: {e}")
            return ""

    def _analyze_dimensions(self, dimensions: List[ResearchDimension], subject: str):
        """分析各维度结果"""
        for dim in dimensions:
            if not dim.results or len(dim.results) < 50:
                dim.analysis = "数据不足，无法分析"
                print(f"  ⚠️ {dim.name}: 数据不足")
                continue

            try:
                prompt = f"""基于以下关于"{subject}"的"{dim.name}"信息，提取关键洞察：

{dim.results[:2000]}

请用3-5句话总结关键发现，直接给结论，不要废话。"""

                if self.engine == 'openai':
                    dim.analysis = self._openai_analyze(prompt)
                else:
                    response = self.client.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config={'temperature': 0.3, 'max_output_tokens': 500}
                    )
                    dim.analysis = response.text if response.text else "分析失败"
                    time.sleep(12)  # Gemini 速率限制

                print(f"  ✅ {dim.name}: 分析完成")

            except Exception as e:
                dim.analysis = f"分析失败: {e}"
                print(f"  ❌ {dim.name}: {e}")

    def _openai_analyze(self, prompt: str) -> str:
        """OpenAI 分析"""
        import requests
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.openai_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': '你是专业的金融研究分析师。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 500
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            return "分析失败"
        except Exception as e:
            return f"分析失败: {e}"

    def _openai_synthesize(self, prompt: str) -> Dict:
        """OpenAI 综合研判 - 返回 JSON 结构"""
        import requests
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.openai_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': self.model,
                    'messages': [
                        {'role': 'system', 'content': '你是顶级投资研究分析师。请严格返回JSON格式。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.3,
                    'max_tokens': 1500,
                    'response_format': {'type': 'json_object'}
                },
                timeout=60
            )
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content']
                return json.loads(content)
            else:
                print(f"    OpenAI错误: {response.status_code}")
                return {}
        except json.JSONDecodeError as e:
            print(f"    JSON解析错误: {e}")
            return {}
        except Exception as e:
            print(f"    OpenAI综合分析错误: {e}")
            return {}

    def _synthesize_report(self, sector_name: str, dimensions: List[ResearchDimension],
                          top_stocks: List[Dict] = None) -> DeepResearchReport:
        """综合研判，生成最终报告"""

        # 汇总各维度分析
        analysis_text = ""
        for dim in dimensions:
            if dim.analysis and dim.analysis != "数据不足，无法分析":
                analysis_text += f"\n【{dim.name}】(权重:{dim.weight*100:.0f}%)\n{dim.analysis}\n"

        # 使用 Gemini 生成综合报告
        prompt = f"""你是顶级投资研究分析师。基于以下多维度研究，对"{sector_name}"板块生成投资研究报告。

{analysis_text}

请返回JSON格式报告：
{{
  "executive_summary": "执行摘要（100字内，核心结论）",
  "investment_thesis": "投资逻辑（150字内，为什么值得投资或不值得）",
  "catalysts": ["催化剂1", "催化剂2", "催化剂3"],
  "risks": ["风险1", "风险2", "风险3"],
  "cycle": "短线(1-3天)/中线(1-4周)/长线(1-6月)",
  "recommendation": "强烈买入/买入/观望/回调买入/卖出",
  "confidence": 0.75,
  "entry_timing": "进场时机建议（50字内）",
  "price_target": {{
    "upside": "上涨空间%",
    "downside": "下跌风险%"
  }}
}}

要求：
1. 基于搜索到的真实信息，不要编造
2. 给出明确的投资建议，不要模棱两可
3. confidence 是 0-1 的小数
4. 如果信息不足，降低 confidence"""

        try:
            if self.engine == 'openai':
                result = self._openai_synthesize(prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        'temperature': 0.3,
                        'max_output_tokens': 1500,
                        'response_mime_type': 'application/json',
                    }
                )
                result = json.loads(response.text)

            print("  ✅ 综合报告生成完成")

        except Exception as e:
            print(f"  ⚠️ JSON解析失败，使用默认结构: {e}")
            result = {
                "executive_summary": "深度研究完成，详见各维度分析",
                "investment_thesis": "需要进一步分析",
                "catalysts": [],
                "risks": [],
                "cycle": "未知",
                "recommendation": "观望",
                "confidence": 0.5,
                "entry_timing": "等待更多信息",
                "price_target": {"upside": "未知", "downside": "未知"}
            }

        # 构建报告
        report = DeepResearchReport(
            subject=sector_name,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            executive_summary=result.get('executive_summary', ''),
            dimensions=[{
                'name': d.name,
                'weight': d.weight,
                'analysis': d.analysis
            } for d in dimensions if d.weight > 0],
            investment_thesis=result.get('investment_thesis', ''),
            catalysts=result.get('catalysts', []),
            risks=result.get('risks', []),
            price_targets=result.get('price_target', {}),
            recommendation=result.get('recommendation', '观望'),
            confidence=result.get('confidence', 0.5),
            sources=[f"Deep Research ({self.engine.upper()} - {self.model})",
                     "Google Search" if self.engine == 'gemini' else "GPT-4 Knowledge"]
        )

        return report

    def _synthesize_stock_report(self, stock_code: str, stock_name: str,
                                 dimensions: List[ResearchDimension]) -> DeepResearchReport:
        """综合研判个股，生成报告"""
        return self._synthesize_report(f"{stock_name}({stock_code})", dimensions)

    def format_report(self, report: DeepResearchReport) -> str:
        """格式化报告为可读文本"""
        output = []
        output.append("\n" + "=" * 70)
        output.append(f"📊 深度研究报告 - {report.subject}")
        output.append("=" * 70)
        output.append(f"📅 时间: {report.timestamp}")
        output.append(f"🎯 建议: {report.recommendation} (置信度: {report.confidence*100:.0f}%)")
        output.append("")

        # 执行摘要
        output.append("【执行摘要】")
        output.append(report.executive_summary)
        output.append("")

        # 投资逻辑
        output.append("【投资逻辑】")
        output.append(report.investment_thesis)
        output.append("")

        # 催化剂
        if report.catalysts:
            output.append("【催化剂】")
            for i, cat in enumerate(report.catalysts, 1):
                output.append(f"  {i}. {cat}")
            output.append("")

        # 风险
        if report.risks:
            output.append("【风险因素】")
            for i, risk in enumerate(report.risks, 1):
                output.append(f"  {i}. {risk}")
            output.append("")

        # 目标价
        if report.price_targets:
            output.append("【目标价】")
            output.append(f"  上涨空间: {report.price_targets.get('upside', 'N/A')}")
            output.append(f"  下跌风险: {report.price_targets.get('downside', 'N/A')}")
            output.append("")

        # 各维度分析
        output.append("【分维度分析】")
        for dim in report.dimensions:
            if dim.get('analysis') and dim['analysis'] != "数据不足，无法分析":
                output.append(f"\n▸ {dim['name']} (权重: {dim['weight']*100:.0f}%)")
                output.append(f"  {dim['analysis'][:200]}...")

        output.append("")
        output.append("=" * 70)
        output.append(f"📚 数据来源: {', '.join(report.sources)}")
        output.append("=" * 70)

        return "\n".join(output)

    def format_report_markdown(self, report: DeepResearchReport) -> str:
        """格式化报告为 Markdown（适合 Telegram）"""
        output = []
        output.append(f"*📊 深度研究报告 - {report.subject}*")
        output.append(f"_{report.timestamp}_")
        output.append("")

        # 核心建议
        emoji_map = {
            '强烈买入': '🟢🟢',
            '买入': '🟢',
            '回调买入': '🟡',
            '观望': '⚪',
            '卖出': '🔴'
        }
        emoji = emoji_map.get(report.recommendation, '⚪')
        output.append(f"{emoji} *{report.recommendation}* (置信度: {report.confidence*100:.0f}%)")
        output.append("")

        # 执行摘要
        output.append(f"*📝 核心结论*")
        output.append(report.executive_summary)
        output.append("")

        # 投资逻辑
        output.append(f"*💡 投资逻辑*")
        output.append(report.investment_thesis)
        output.append("")

        # 催化剂
        if report.catalysts:
            output.append(f"*🚀 催化剂*")
            for cat in report.catalysts[:3]:
                output.append(f"• {cat}")
            output.append("")

        # 风险
        if report.risks:
            output.append(f"*⚠️ 风险*")
            for risk in report.risks[:3]:
                output.append(f"• {risk}")
            output.append("")

        output.append(f"_数据来源: {', '.join(report.sources)}_")

        return "\n".join(output)


def main():
    """CLI 入口"""
    import argparse
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # dotenv is optional

    parser = argparse.ArgumentParser(description='Deep Research - 板块/个股深度研究')
    parser.add_argument('subject', nargs='?', help='研究主题（板块名称）')
    parser.add_argument('--stock', '-s', help='研究个股代码（如 HK.09880）')
    parser.add_argument('--name', '-n', help='股票名称（如 优必选），提高准确性')
    parser.add_argument('--model', '-m', default='auto',
                       help='模型选择: auto, gemini, openai/gpt-4')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser.add_argument('--markdown', action='store_true', help='输出 Markdown 格式')

    args = parser.parse_args()

    # 检查 API Key
    gemini_key = os.getenv('GEMINI_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')

    if not gemini_key and not openai_key:
        print("❌ 未设置 API Key 环境变量")
        print("\n需要设置以下任一:")
        print("export GEMINI_API_KEY='your-gemini-key'")
        print("export OPENAI_API_KEY='your-openai-key'")
        print("\n申请地址:")
        print("Gemini: https://aistudio.google.com/app/apikey")
        print("OpenAI: https://platform.openai.com/api-keys")
        sys.exit(1)

    # 创建研究引擎
    researcher = DeepResearch(model=args.model)

    # 执行研究
    if args.stock:
        report = researcher.research_stock(args.stock, args.name)
    elif args.subject:
        report = researcher.research_sector(args.subject)
    else:
        # 默认研究人形机器人板块
        report = researcher.research_sector("人形机器人", [
            {'code': 'HK.09880', 'name': '优必选'},
            {'code': 'HK.02432', 'name': '协鑫科技'}
        ])

    # 输出报告
    if args.json:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    elif args.markdown:
        print(researcher.format_report_markdown(report))
    else:
        print(researcher.format_report(report))


if __name__ == '__main__':
    main()
