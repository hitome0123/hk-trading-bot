#!/usr/bin/env python3
"""
趋势分析器 - K值计算和股票映射
输入：社交媒体热点数据
输出：带K值的投资信号
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

# 文件路径
INPUT_FILE = '/Users/mantou/.n8n-files/social_media_hotspots.json'
HISTORY_FILE = '/Users/mantou/.n8n-files/hotspot_history.json'
OUTPUT_FILE = '/Users/mantou/.n8n-files/trend_signals.json'

# 关键词到港股板块的映射
KEYWORD_TO_SECTOR = {
    # 新能源汽车
    '比亚迪': '新能源汽车',
    '理想汽车': '新能源汽车',
    '小米汽车': '新能源汽车',
    '长城汽车': '新能源汽车',
    '新能源车': '新能源汽车',

    # AI科技
    '腾讯AI': 'AI科技',
    '阿里巴巴': 'AI科技',
    '云计算': 'AI科技',

    # 半导体
    '中芯国际': '半导体',
    '芯片': '半导体',
    '海康威视': '半导体',

    # 锂电池
    '宁德时代': '锂电池',
    '电池': '锂电池',

    # 医药生物
    '药明康德': '医药生物',
    '新药': '医药生物',

    # 消费/互联网
    '美团': '互联网',
    '京东方': '消费',

    # 金融
    '中国平安': '券商',
    '贵州茅台': '消费',
}

# 板块到港股代码的映射（使用之前的SECTORS）
SECTOR_TO_STOCKS = {
    '新能源汽车': ['HK.09866', 'HK.02015', 'HK.01211', 'HK.00175'],
    'AI科技': ['HK.00700', 'HK.09988', 'HK.09618'],
    '半导体': ['HK.00981', 'HK.01347', 'HK.01478'],
    '锂电池': ['HK.01772', 'HK.02460', 'HK.03931'],
    '医药生物': ['HK.06160', 'HK.02269', 'HK.02359'],
    '互联网': ['HK.03690', 'HK.09999', 'HK.09961'],
    '消费': ['HK.01929', 'HK.09633', 'HK.02331'],
    '券商': ['HK.06098', 'HK.06066', 'HK.03908'],
}


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self):
        self.history = self.load_history()

    def load_history(self) -> Dict:
        """加载历史数据"""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_history(self):
        """保存历史数据"""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def calculate_k_value(self, keyword: str, current_heat: int) -> Dict:
        """
        计算K值（热度加速系数）
        K = (current_heat - avg_heat_past_N) / avg_heat_past_N

        返回：{
            'k_value': float,
            'trend': 'rising' | 'stable' | 'declining',
            'strength': 'strong' | 'medium' | 'weak'
        }
        """
        # 获取历史数据
        if keyword not in self.history:
            self.history[keyword] = []

        history_records = self.history[keyword]

        # 添加当前记录
        now = datetime.now()
        history_records.append({
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'heat': current_heat
        })

        # 只保留最近24小时的数据
        cutoff_time = now - timedelta(hours=24)
        history_records = [
            r for r in history_records
            if datetime.strptime(r['timestamp'], '%Y-%m-%d %H:%M:%S') > cutoff_time
        ]
        self.history[keyword] = history_records

        # 计算K值
        if len(history_records) < 2:
            # 数据不足，默认K=0
            return {
                'k_value': 0.0,
                'trend': 'new',
                'strength': 'unknown',
                'history_count': len(history_records)
            }

        # 计算过去N小时的平均热度（排除当前）
        past_heats = [r['heat'] for r in history_records[:-1]]
        avg_heat = sum(past_heats) / len(past_heats)

        # K = (当前 - 均值) / 均值
        if avg_heat == 0:
            k_value = 0.0
        else:
            k_value = (current_heat - avg_heat) / avg_heat

        # 判断趋势
        if k_value > 1.0:
            trend = 'explosive'
            strength = 'strong'
        elif k_value > 0.3:
            trend = 'rising'
            strength = 'strong'
        elif k_value > 0.1:
            trend = 'rising'
            strength = 'medium'
        elif k_value > 0:
            trend = 'stable'
            strength = 'weak'
        else:
            trend = 'declining'
            strength = 'weak'

        return {
            'k_value': round(k_value, 3),
            'trend': trend,
            'strength': strength,
            'current_heat': current_heat,
            'avg_heat': int(avg_heat),
            'history_count': len(history_records)
        }

    def map_keyword_to_sector(self, keyword: str) -> str:
        """将关键词映射到板块"""
        for key, sector in KEYWORD_TO_SECTOR.items():
            if key in keyword:
                return sector
        return None

    def analyze(self) -> List[Dict]:
        """分析所有热点，输出信号"""
        # 读取最新热点数据
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            hotspot_data = json.load(f)

        signals = []

        # 遍历所有平台的数据
        for platform, items in hotspot_data['data'].items():
            for item in items:
                keyword = item['keyword']
                heat = item['heat_score']

                # 计算K值
                k_analysis = self.calculate_k_value(keyword, heat)

                # 映射到板块
                sector = self.map_keyword_to_sector(keyword)

                # 只关注上升趋势 (K > 0.3) 且能映射到板块的热点
                if k_analysis['k_value'] >= 0.3 and sector:
                    # 获取该板块的股票
                    stocks = SECTOR_TO_STOCKS.get(sector, [])

                    signal = {
                        'keyword': keyword,
                        'sector': sector,
                        'stocks': stocks,
                        'k_value': k_analysis['k_value'],
                        'trend': k_analysis['trend'],
                        'strength': k_analysis['strength'],
                        'current_heat': k_analysis['current_heat'],
                        'avg_heat': k_analysis['avg_heat'],
                        'source': item['source'],
                        'rank': item['rank'],
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }

                    signals.append(signal)

        return signals


def main():
    """主函数"""
    print(f"🔍 开始趋势分析... {datetime.now().strftime('%H:%M:%S')}")

    analyzer = TrendAnalyzer()
    signals = analyzer.analyze()

    # 保存历史数据
    analyzer.save_history()

    # 按K值排序
    signals.sort(key=lambda x: x['k_value'], reverse=True)

    # 输出结果
    output = {
        'signals': signals,
        'total_signals': len(signals),
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ 分析完成：找到 {len(signals)} 个上升趋势信号")
    for sig in signals[:5]:  # 显示前5个
        print(f"  📈 {sig['keyword']} -> {sig['sector']}")
        print(f"     K值: {sig['k_value']}, 趋势: {sig['trend']}, 股票: {len(sig['stocks'])}只")

    print(f"📁 信号已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
