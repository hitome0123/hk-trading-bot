#!/usr/bin/env python3
"""
信号整合器 - 交叉验证
整合社交媒体热点趋势和机构资金流向，生成综合推荐
"""
import json
from datetime import datetime
from typing import List, Dict

# 输入文件
TREND_SIGNALS_FILE = '/Users/mantou/.n8n-files/trend_signals.json'
INSTITUTIONAL_SIGNALS_FILE = '/Users/mantou/.n8n-files/institutional_signals.json'

# 输出文件
OUTPUT_FILE = '/Users/mantou/.n8n-files/integrated_signals.json'


class SignalIntegrator:
    """信号整合器"""

    def __init__(self):
        self.trend_signals = []
        self.institutional_recommend = []
        self.institutional_warning = []

    def load_signals(self):
        """加载所有信号"""
        # 加载热点趋势信号
        try:
            with open(TREND_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                trend_data = json.load(f)
                self.trend_signals = trend_data.get('signals', [])
                print(f"✓ 加载热点趋势信号: {len(self.trend_signals)} 个")
        except FileNotFoundError:
            print("⚠️ 未找到热点趋势信号文件")
            self.trend_signals = []

        # 加载机构资金流向信号
        try:
            with open(INSTITUTIONAL_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                inst_data = json.load(f)
                self.institutional_recommend = inst_data.get('recommend_signals', [])
                self.institutional_warning = inst_data.get('warning_signals', [])
                print(f"✓ 加载机构买入信号: {len(self.institutional_recommend)} 个")
                print(f"✓ 加载散户追高信号: {len(self.institutional_warning)} 个")
        except FileNotFoundError:
            print("⚠️ 未找到机构资金流向信号文件")
            self.institutional_recommend = []
            self.institutional_warning = []

    def map_keyword_to_stocks(self, keyword: str, sector: str) -> List[str]:
        """
        根据关键词和板块，映射到具体股票代码

        这里使用简化的映射逻辑：
        - 如果关键词包含公司名称，直接映射
        - 否则返回该板块的所有股票
        """
        # 从 institutional_monitor.py 导入股票信息
        from institutional_monitor import STOCK_INFO

        # 关键词精确匹配
        keyword_stock_map = {
            '比亚迪': 'HK.01211',
            '理想汽车': 'HK.02015',
            '蔚来': 'HK.09866',
            '小米汽车': 'HK.01810',
            '长城汽车': 'HK.02333',
            '中芯国际': 'HK.00981',
            '腾讯': 'HK.00700',
            '阿里巴巴': 'HK.09988',
            '美团': 'HK.03690',
            '宁德时代': 'HK.03931',  # 中创新航
            '药明康德': 'HK.02359',
            '贵州茅台': None,  # 不在港股列表
        }

        # 先尝试精确匹配
        for name, code in keyword_stock_map.items():
            if name in keyword:
                return [code] if code else []

        # 否则返回该板块的所有股票
        sector_stocks = []
        for code, info in STOCK_INFO.items():
            if info['sector'] == sector:
                sector_stocks.append(code)

        return sector_stocks

    def integrate(self) -> Dict:
        """整合信号，生成综合推荐"""
        print(f"\n🔗 开始整合信号... {datetime.now().strftime('%H:%M:%S')}")

        # 1. 将机构信号转换为字典（按股票代码索引）
        inst_recommend_dict = {sig['stock_code']: sig for sig in self.institutional_recommend}
        inst_warning_dict = {sig['stock_code']: sig for sig in self.institutional_warning}

        integrated_signals = []

        # 2. 遍历热点趋势信号
        for trend_sig in self.trend_signals:
            keyword = trend_sig['keyword']
            sector = trend_sig['sector']
            k_value = trend_sig['k_value']
            stocks = trend_sig.get('stocks', [])

            # 如果stocks为空，尝试映射
            if not stocks:
                stocks = self.map_keyword_to_stocks(keyword, sector)

            # 检查每只股票的机构资金流向
            for stock_code in stocks:
                has_institutional = stock_code in inst_recommend_dict
                has_retail = stock_code in inst_warning_dict

                # 获取股票名称
                from institutional_monitor import STOCK_INFO
                stock_info = STOCK_INFO.get(stock_code, {'name': stock_code, 'sector': sector})

                # 交叉验证生成综合信号
                if has_institutional and has_retail:
                    # 💎 热点 + 机构 + 散户（博弈）
                    signal_type = 'super'  # 超级信号，但有博弈
                    strength = 'strong'
                    reason = f"热点K值{k_value} + 机构流入{inst_recommend_dict[stock_code]['net_inflow']}亿 + 散户流入{inst_warning_dict[stock_code]['net_inflow']}亿（博弈）"
                    recommendation = "机构占优可轻仓试探，散户占优需谨慎"

                elif has_institutional:
                    # 💎💎 热点 + 机构（强烈推荐）
                    signal_type = 'diamond'  # 钻石信号
                    strength = 'very_strong'
                    reason = f"热点K值{k_value} + 机构流入{inst_recommend_dict[stock_code]['net_inflow']}亿"
                    recommendation = "强烈推荐，热点上升且机构增持"

                elif has_retail:
                    # ⚠️ 热点 + 散户（谨慎追高）
                    signal_type = 'warning'
                    strength = 'weak'
                    reason = f"热点K值{k_value} + 散户流入{inst_warning_dict[stock_code]['net_inflow']}亿"
                    recommendation = "谨慎追高，散户资金占优"

                else:
                    # 🤔 仅热点（观望）
                    signal_type = 'trend_only'
                    strength = 'medium'
                    reason = f"热点K值{k_value}，无明显机构或散户流入"
                    recommendation = "观望为主，可关注"

                # 构建综合信号
                integrated_signal = {
                    'type': signal_type,
                    'stock_code': stock_code,
                    'stock_name': stock_info['name'],
                    'sector': sector,
                    'keyword': keyword,
                    'k_value': k_value,
                    'trend': trend_sig['trend'],
                    'strength': strength,
                    'has_institutional': has_institutional,
                    'has_retail': has_retail,
                    'institutional_inflow': inst_recommend_dict[stock_code]['net_inflow'] if has_institutional else 0,
                    'retail_inflow': inst_warning_dict[stock_code]['net_inflow'] if has_retail else 0,
                    'reason': reason,
                    'recommendation': recommendation,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                integrated_signals.append(integrated_signal)

        # 3. 添加纯机构买入信号（无热点支撑）
        for inst_sig in self.institutional_recommend:
            stock_code = inst_sig['stock_code']

            # 检查是否已经被热点覆盖
            if any(sig['stock_code'] == stock_code for sig in integrated_signals):
                continue  # 已经在热点信号中了

            # 检查是否也有散户
            has_retail = stock_code in inst_warning_dict

            if has_retail:
                # 🤝 机构 + 散户（无热点）
                signal_type = 'institutional_retail'
                strength = 'medium'
                reason = f"机构流入{inst_sig['net_inflow']}亿 + 散户流入{inst_warning_dict[stock_code]['net_inflow']}亿（无热点支撑）"
                recommendation = "博弈信号，谨慎参与"
            else:
                # 👍 纯机构买入
                signal_type = 'institutional_only'
                strength = 'medium'
                reason = f"机构流入{inst_sig['net_inflow']}亿（无热点，稳健）"
                recommendation = "可考虑，机构稳健增持"

            integrated_signal = {
                'type': signal_type,
                'stock_code': stock_code,
                'stock_name': inst_sig['stock_name'],
                'sector': inst_sig['sector'],
                'keyword': None,
                'k_value': None,
                'trend': None,
                'strength': strength,
                'has_institutional': True,
                'has_retail': has_retail,
                'institutional_inflow': inst_sig['net_inflow'],
                'retail_inflow': inst_warning_dict[stock_code]['net_inflow'] if has_retail else 0,
                'reason': reason,
                'recommendation': recommendation,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            integrated_signals.append(integrated_signal)

        # 排序：钻石信号 > 超级信号 > 纯机构 > 仅热点 > 警告
        priority = {
            'diamond': 1,
            'super': 2,
            'institutional_only': 3,
            'trend_only': 4,
            'institutional_retail': 5,
            'warning': 6,
        }

        integrated_signals.sort(key=lambda x: (priority.get(x['type'], 99), -x.get('institutional_inflow', 0)))

        # 统计
        stats = {
            'diamond': len([s for s in integrated_signals if s['type'] == 'diamond']),
            'super': len([s for s in integrated_signals if s['type'] == 'super']),
            'institutional_only': len([s for s in integrated_signals if s['type'] == 'institutional_only']),
            'trend_only': len([s for s in integrated_signals if s['type'] == 'trend_only']),
            'warning': len([s for s in integrated_signals if s['type'] == 'warning']),
        }

        print(f"\n✅ 整合完成:")
        print(f"  💎💎 钻石信号（热点+机构）: {stats['diamond']} 个")
        print(f"  💎⚠️  超级博弈（热点+机构+散户）: {stats['super']} 个")
        print(f"  👍 纯机构买入: {stats['institutional_only']} 个")
        print(f"  🤔 仅热点（无机构）: {stats['trend_only']} 个")
        print(f"  ⚠️  追高警告: {stats['warning']} 个")

        return {
            'signals': integrated_signals,
            'stats': stats,
            'total': len(integrated_signals),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def main():
    """主函数"""
    integrator = SignalIntegrator()

    # 加载信号
    integrator.load_signals()

    # 整合信号
    result = integrator.integrate()

    # 保存结果
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n📁 综合信号已保存到: {OUTPUT_FILE}")
    print(f"📊 总信号数: {result['total']}")


if __name__ == "__main__":
    main()
