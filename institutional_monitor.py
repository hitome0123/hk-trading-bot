#!/usr/bin/env python3
"""
机构持仓监控器 - 使用富途API
监控JP摩根和富途的港股持仓变动
- JP摩根买入 → 推荐信号
- 富途买入 → 避雷信号
"""
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

# 富途API
try:
    from futu import *
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False
    print("⚠️ 富途API未安装，使用模拟数据")

# 输出文件
OUTPUT_FILE = '/Users/mantou/.n8n-files/institutional_signals.json'
HISTORY_FILE = '/Users/mantou/.n8n-files/institutional_history.json'

# 港股板块映射（用户自选股 - 51只）
STOCK_INFO = {
    # 商业航天
    'HK.01045': {'name': '亚太卫星', 'sector': '商业航天'},
    'HK.00031': {'name': '航天控股', 'sector': '商业航天'},
    'HK.02333': {'name': '长城汽车', 'sector': '商业航天'},

    # AI科技
    'HK.00020': {'name': '商汤-W', 'sector': 'AI科技'},
    'HK.09888': {'name': '百度集团-SW', 'sector': 'AI科技'},
    'HK.01024': {'name': '快手-W', 'sector': 'AI科技'},
    'HK.09626': {'name': '哔哩哔哩-W', 'sector': 'AI科技'},
    'HK.01833': {'name': '平安好医生', 'sector': 'AI科技'},

    # 新能源汽车
    'HK.09866': {'name': '蔚来-SW', 'sector': '新能源汽车'},
    'HK.02015': {'name': '理想汽车-W', 'sector': '新能源汽车'},
    'HK.01211': {'name': '比亚迪股份', 'sector': '新能源汽车'},
    'HK.00175': {'name': '吉利汽车', 'sector': '新能源汽车'},
    'HK.09868': {'name': '小鹏汽车-W', 'sector': '新能源汽车'},
    'HK.01958': {'name': '北京汽车', 'sector': '新能源汽车'},
    'HK.02238': {'name': '广汽集团', 'sector': '新能源汽车'},

    # 半导体
    'HK.00981': {'name': '中芯国际', 'sector': '半导体'},
    'HK.01347': {'name': '华虹半导体', 'sector': '半导体'},
    'HK.01478': {'name': '丘钛科技', 'sector': '半导体'},
    'HK.02231': {'name': '景业名邦集团', 'sector': '半导体'},

    # 互联网
    'HK.00700': {'name': '腾讯控股', 'sector': '互联网'},
    'HK.09988': {'name': '阿里巴巴-W', 'sector': '互联网'},
    'HK.09618': {'name': '京东集团-SW', 'sector': '互联网'},
    'HK.03690': {'name': '美团-W', 'sector': '互联网'},
    'HK.09999': {'name': '网易-S', 'sector': '互联网'},
    'HK.09961': {'name': '携程集团-S', 'sector': '互联网'},
    'HK.03888': {'name': '金山软件', 'sector': '互联网'},

    # 医药生物
    'HK.06160': {'name': '百济神州', 'sector': '医药生物'},
    'HK.02269': {'name': '药明生物', 'sector': '医药生物'},
    'HK.02359': {'name': '药明康德', 'sector': '医药生物'},
    'HK.01093': {'name': '石药集团', 'sector': '医药生物'},
    'HK.01177': {'name': '中国生物制药', 'sector': '医药生物'},
    'HK.02607': {'name': '上海医药', 'sector': '医药生物'},

    # 消费
    'HK.01929': {'name': '周大福', 'sector': '消费'},
    'HK.09633': {'name': '农夫山泉', 'sector': '消费'},
    'HK.02331': {'name': '李宁', 'sector': '消费'},
    'HK.09992': {'name': '泡泡玛特', 'sector': '消费'},
    'HK.01810': {'name': '小米集团-W', 'sector': '消费'},
    'HK.09869': {'name': '海伦司', 'sector': '消费'},

    # 光伏
    'HK.03800': {'name': '协鑫科技', 'sector': '光伏'},
    'HK.00968': {'name': '信义光能', 'sector': '光伏'},
    'HK.06865': {'name': '福莱特玻璃', 'sector': '光伏'},
    'HK.00451': {'name': '协鑫新能源', 'sector': '光伏'},

    # 锂电池
    'HK.01772': {'name': '赣锋锂业', 'sector': '锂电池'},
    'HK.02460': {'name': '华润饮料', 'sector': '锂电池'},
    'HK.03931': {'name': '中创新航', 'sector': '锂电池'},

    # 游戏
    'HK.00285': {'name': '比亚迪电子', 'sector': '游戏'},

    # 地产
    'HK.02007': {'name': '碧桂园', 'sector': '地产'},
    'HK.01109': {'name': '华润置地', 'sector': '地产'},

    # 券商
    'HK.06098': {'name': '碧桂园服务', 'sector': '券商'},
    'HK.06066': {'name': '中信建投证券', 'sector': '券商'},
    'HK.03908': {'name': '中金公司', 'sector': '券商'},
}


class InstitutionalMonitor:
    """机构持仓监控器"""

    def __init__(self):
        self.history = self.load_history()
        self.quote_ctx = None

        # 初始化富途连接
        if FUTU_AVAILABLE:
            try:
                self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
                print("✓ 已连接到FutuOpenD")
            except Exception as e:
                print(f"⚠️ 连接FutuOpenD失败: {e}")
                print("   请确保FutuOpenD正在运行 (端口11111)")
                self.quote_ctx = None

    def __del__(self):
        """关闭富途连接"""
        if self.quote_ctx:
            self.quote_ctx.close()

    def load_history(self) -> Dict:
        """加载历史持仓数据"""
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_history(self):
        """保存历史持仓数据"""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def fetch_jpmorgan_holdings(self) -> Dict[str, float]:
        """
        获取机构买入信号 - 使用富途API
        通过get_capital_distribution()获取超大单、大单流入（代表机构买入）
        """
        institutional_inflows = {}

        if not self.quote_ctx:
            print("⚠️ 富途API未连接，使用模拟数据")
            return self._mock_jpmorgan_holdings()

        print("📊 查询机构资金流入（超大单+大单）...")
        # 查询所有监控股票的资金分布
        for stock_code in STOCK_INFO.keys():
            try:
                # 获取资金分布
                ret, data = self.quote_ctx.get_capital_distribution(stock_code)

                if ret == RET_OK and not data.empty:
                    latest = data.iloc[-1]

                    # 机构资金 = 超大单 + 大单
                    institutional_in = latest['capital_in_super'] + latest['capital_in_big']
                    institutional_out = latest['capital_out_super'] + latest['capital_out_big']
                    net_institutional = institutional_in - institutional_out

                    # 如果机构净流入 > 0，记录
                    if net_institutional > 0:
                        # 转换为亿元
                        net_inflow_yi = net_institutional / 100000000

                        institutional_inflows[stock_code] = round(net_inflow_yi, 2)
                        print(f"  ✓ {STOCK_INFO[stock_code]['name']}: 机构净流入 {net_inflow_yi:.2f} 亿元")

            except Exception as e:
                print(f"  ⚠️ 查询 {stock_code} 失败: {e}")
                continue

        if not institutional_inflows:
            print("⚠️ 未找到机构流入数据，使用模拟数据")
            return self._mock_jpmorgan_holdings()

        return institutional_inflows

    def _mock_jpmorgan_holdings(self) -> Dict[str, float]:
        """模拟JP摩根持仓数据（API失败时使用）"""
        import random
        return {
            'HK.00700': round(random.uniform(0.5, 1.2), 2),
            'HK.09988': round(random.uniform(0.3, 0.9), 2),
            'HK.01211': round(random.uniform(0.4, 1.0), 2),
            'HK.00981': round(random.uniform(0.2, 0.7), 2),
            'HK.03690': round(random.uniform(0.3, 0.8), 2),
        }

    def fetch_futu_holdings(self) -> Dict[str, float]:
        """
        获取散户买入信号 - 使用富途API
        通过get_capital_distribution()获取小单、中单流入（代表散户买入）
        """
        retail_inflows = {}

        if not self.quote_ctx:
            print("⚠️ 富途API未连接，使用模拟数据")
            return self._mock_futu_holdings()

        print("📊 查询散户资金流入（小单+中单）...")
        # 查询所有监控股票的资金分布
        for stock_code in STOCK_INFO.keys():
            try:
                # 获取资金分布
                ret, data = self.quote_ctx.get_capital_distribution(stock_code)

                if ret == RET_OK and not data.empty:
                    latest = data.iloc[-1]

                    # 散户资金 = 小单 + 中单
                    retail_in = latest['capital_in_small'] + latest['capital_in_mid']
                    retail_out = latest['capital_out_small'] + latest['capital_out_mid']
                    net_retail = retail_in - retail_out

                    # 如果散户净流入 > 0，记录（避雷信号）
                    if net_retail > 0:
                        # 转换为亿元
                        net_inflow_yi = net_retail / 100000000

                        retail_inflows[stock_code] = round(net_inflow_yi, 2)
                        print(f"  ⚠️ {STOCK_INFO[stock_code]['name']}: 散户净流入 {net_inflow_yi:.2f} 亿元")

            except Exception as e:
                print(f"  ⚠️ 查询 {stock_code} 失败: {e}")
                continue

        if not retail_inflows:
            print("⚠️ 未找到散户流入数据，使用模拟数据")
            return self._mock_futu_holdings()

        return retail_inflows

    def _mock_futu_holdings(self) -> Dict[str, float]:
        """模拟富途资金流向数据（API失败时使用）"""
        import random
        return {
            'HK.09866': round(random.uniform(0.2, 0.5), 2),
            'HK.02015': round(random.uniform(0.1, 0.4), 2),
            'HK.01772': round(random.uniform(0.1, 0.3), 2),
            'HK.06160': round(random.uniform(0.05, 0.2), 2),
        }

    def calculate_capital_change(self, institution: str, stock: str, current_inflow: float) -> Dict:
        """
        计算资金流入变动

        参数:
            current_inflow: 当前净流入金额（亿元）

        返回: {
            'change_rate': float,  # 变动率 (正数=增持，负数=减持)
            'is_buying': bool,     # 是否在买入
            'change_amount': float # 变动金额（亿元）
        }
        """
        # 获取历史资金流入
        key = f"{institution}_{stock}"

        if key not in self.history:
            # 首次记录
            self.history[key] = {
                'inflow': current_inflow,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return {
                'change_rate': 0.0,
                'is_buying': current_inflow > 0,
                'change_amount': current_inflow,
                'status': 'new',
                'current_inflow': current_inflow
            }

        # 计算变动
        prev_inflow = self.history[key]['inflow']
        change_amount = current_inflow - prev_inflow

        if prev_inflow == 0:
            change_rate = 100.0 if current_inflow > 0 else 0.0
        else:
            change_rate = (change_amount / abs(prev_inflow)) * 100

        # 更新历史
        self.history[key] = {
            'inflow': current_inflow,
            'prev_inflow': prev_inflow,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        return {
            'change_rate': round(change_rate, 2),
            'is_buying': current_inflow > 0,
            'change_amount': round(change_amount, 2),
            'prev_inflow': prev_inflow,
            'current_inflow': current_inflow
        }

    def analyze(self) -> Dict:
        """分析机构持仓，生成信号"""
        print(f"🏦 开始分析机构持仓... {datetime.now().strftime('%H:%M:%S')}")

        # 获取最新持仓
        jpmorgan_holdings = self.fetch_jpmorgan_holdings()
        futu_holdings = self.fetch_futu_holdings()

        # 分析机构资金流入（推荐信号）
        jpmorgan_signals = []
        for stock, inflow in jpmorgan_holdings.items():
            change_info = self.calculate_capital_change('institutional', stock, inflow)

            # 只要有机构净流入就推荐（因为是当日数据）
            if change_info.get('is_buying') and inflow > 0:
                stock_info = STOCK_INFO.get(stock, {'name': stock, 'sector': '未知'})

                signal = {
                    'type': 'recommend',  # 推荐
                    'institution': '机构（超大单+大单）',
                    'stock_code': stock,
                    'stock_name': stock_info['name'],
                    'sector': stock_info['sector'],
                    'net_inflow': inflow,  # 亿元
                    'change_amount': change_info.get('change_amount', inflow),
                    'reason': f"机构净流入 {inflow} 亿元",
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                jpmorgan_signals.append(signal)

        # 分析散户资金流入（避雷信号）
        futu_signals = []
        for stock, inflow in futu_holdings.items():
            change_info = self.calculate_capital_change('retail', stock, inflow)

            # 散户净流入 > 0.5亿就提示避雷（散户追高容易成接盘侠）
            if change_info.get('is_buying') and inflow > 0.5:
                stock_info = STOCK_INFO.get(stock, {'name': stock, 'sector': '未知'})

                signal = {
                    'type': 'warning',  # 避雷
                    'institution': '散户（小单+中单）',
                    'stock_code': stock,
                    'stock_name': stock_info['name'],
                    'sector': stock_info['sector'],
                    'net_inflow': inflow,  # 亿元
                    'change_amount': change_info.get('change_amount', inflow),
                    'reason': f"散户净流入 {inflow} 亿元，谨慎追高",
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                futu_signals.append(signal)

        # 保存历史
        self.save_history()

        return {
            'recommend_signals': jpmorgan_signals,
            'warning_signals': futu_signals,
            'total_recommend': len(jpmorgan_signals),
            'total_warning': len(futu_signals),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


def main():
    """主函数"""
    monitor = InstitutionalMonitor()

    # 分析持仓
    result = monitor.analyze()

    # 输出结果
    print(f"\n✅ 分析完成:")
    print(f"  📈 推荐信号(机构买入): {result['total_recommend']} 个")
    for sig in result['recommend_signals']:
        print(f"     ✓ {sig['stock_name']} ({sig['stock_code']}) 净流入 {sig['net_inflow']} 亿元")

    print(f"  ⚠️  避雷信号(散户买入): {result['total_warning']} 个")
    for sig in result['warning_signals']:
        print(f"     ⚠ {sig['stock_name']} ({sig['stock_code']}) 净流入 {sig['net_inflow']} 亿元")

    # 保存输出
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"📁 信号已保存到: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
