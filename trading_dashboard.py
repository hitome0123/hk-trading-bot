#!/usr/bin/env python3
"""
一体化交易看板
整合所有数据源，一个页面掌握全局
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from flask import Flask, render_template_string, jsonify
from datetime import datetime
import threading
import time

try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False

from market_scanner import MarketScanner
from entry_exit_signal import SignalCalculator

app = Flask(__name__)

# 全局数据缓存
DATA_CACHE = {
    'hot_sectors': [],
    'signals': [],
    'alerts': [],
    'capital_flow': [],
    'news': [],
    'last_update': None,
}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>港股追热点看板</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .header h1 {
            font-size: 24px;
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #00ff88;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .card-title {
            font-size: 16px;
            color: #00d4ff;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .sector-item {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
        }
        .sector-name { font-weight: 500; }
        .sector-change {
            font-weight: bold;
            color: #00ff88;
        }
        .sector-change.negative { color: #ff4757; }
        .signal-row {
            display: grid;
            grid-template-columns: 1fr 80px 80px 80px 60px;
            gap: 10px;
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            font-size: 14px;
        }
        .signal-header {
            color: #888;
            font-size: 12px;
        }
        .price { color: #ffd93d; }
        .buy { color: #00ff88; }
        .sell { color: #ff6b6b; }
        .stars { color: #ffd93d; }
        .alert-item {
            padding: 10px;
            margin: 5px 0;
            background: rgba(255,100,100,0.1);
            border-left: 3px solid #ff6b6b;
            border-radius: 0 8px 8px 0;
            font-size: 14px;
        }
        .alert-time { color: #888; font-size: 12px; }
        .shrink-up {
            background: rgba(255,215,0,0.15);
            border-left-color: #ffd700;
        }
        .flow-item {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            margin: 3px 0;
        }
        .inflow { color: #00ff88; }
        .outflow { color: #ff4757; }
        .refresh-btn {
            background: linear-gradient(90deg, #00d4ff, #00ff88);
            border: none;
            padding: 8px 20px;
            border-radius: 20px;
            color: #1a1a2e;
            font-weight: bold;
            cursor: pointer;
        }
        .time { color: #888; font-size: 14px; }
        .full-width { grid-column: 1 / -1; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.1); }
        th { color: #888; font-size: 12px; }
        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 12px;
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
        }
        .tag.hot { background: rgba(255,107,107,0.2); color: #ff6b6b; }
    </style>
</head>
<body>
    <div class="header">
        <h1>港股追热点看板</h1>
        <div class="status">
            <div class="status-dot"></div>
            <span id="time">--:--:--</span>
            <span id="market-status">交易中</span>
            <button class="refresh-btn" onclick="refresh()">刷新</button>
        </div>
    </div>

    <div class="grid">
        <!-- 热门板块 -->
        <div class="card">
            <div class="card-title">📈 今日热门板块</div>
            <div id="hot-sectors">
                <div class="sector-item">
                    <span class="sector-name">加载中...</span>
                    <span class="sector-change">-</span>
                </div>
            </div>
        </div>

        <!-- 资金流向 -->
        <div class="card">
            <div class="card-title">💰 资金流向TOP5</div>
            <div id="capital-flow">
                <div class="flow-item">
                    <span>加载中...</span>
                    <span>-</span>
                </div>
            </div>
        </div>

        <!-- 实时异动 -->
        <div class="card">
            <div class="card-title">🚨 实时异动</div>
            <div id="alerts">
                <div class="alert-item">
                    <div class="alert-time">--:--</div>
                    <div>等待异动信号...</div>
                </div>
            </div>
        </div>

        <!-- 缩量上涨 -->
        <div class="card">
            <div class="card-title">🔥 缩量上涨 (首推)</div>
            <div id="shrink-up">
                <div class="alert-item shrink-up">
                    <div>扫描中...</div>
                </div>
            </div>
        </div>

        <!-- 做T推荐 -->
        <div class="card full-width">
            <div class="card-title">🎯 做T推荐</div>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>现价</th>
                        <th>涨跌</th>
                        <th>RSI</th>
                        <th>买入位</th>
                        <th>卖出位</th>
                        <th>预期</th>
                        <th>信号</th>
                    </tr>
                </thead>
                <tbody id="signals">
                    <tr>
                        <td colspan="8">加载中...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('time').textContent =
                now.toTimeString().split(' ')[0];

            const hour = now.getHours();
            const isTrading = (hour >= 9 && hour < 12) || (hour >= 13 && hour < 16);
            document.getElementById('market-status').textContent =
                isTrading ? '交易中' : '已休市';
        }

        function refresh() {
            fetch('/api/data')
                .then(r => r.json())
                .then(data => {
                    // 更新热门板块
                    const sectorsHtml = data.hot_sectors.map(s => `
                        <div class="sector-item">
                            <span class="sector-name">${s.name}</span>
                            <span class="sector-change ${s.change < 0 ? 'negative' : ''}">${s.change > 0 ? '+' : ''}${s.change.toFixed(1)}%</span>
                        </div>
                    `).join('') || '<div class="sector-item">暂无数据</div>';
                    document.getElementById('hot-sectors').innerHTML = sectorsHtml;

                    // 更新资金流向
                    const flowHtml = data.capital_flow.map(f => `
                        <div class="flow-item">
                            <span>${f.name}</span>
                            <span class="${f.inflow > 0 ? 'inflow' : 'outflow'}">${f.inflow > 0 ? '+' : ''}${f.inflow.toFixed(2)}亿</span>
                        </div>
                    `).join('') || '<div class="flow-item">暂无数据</div>';
                    document.getElementById('capital-flow').innerHTML = flowHtml;

                    // 更新异动
                    const alertsHtml = data.alerts.map(a => `
                        <div class="alert-item ${a.type === 'shrink_up' ? 'shrink-up' : ''}">
                            <div class="alert-time">${a.time}</div>
                            <div>${a.message}</div>
                        </div>
                    `).join('') || '<div class="alert-item">暂无异动</div>';
                    document.getElementById('alerts').innerHTML = alertsHtml;

                    // 更新缩量上涨
                    const shrinkHtml = data.signals
                        .filter(s => s.is_shrink_up)
                        .map(s => `
                            <div class="alert-item shrink-up">
                                <div><strong>${s.name}</strong> (${s.code}) ${s.shrink_reason}</div>
                                <div>买入: ${s.buy_low.toFixed(2)} | 卖出: ${s.sell_low.toFixed(2)}</div>
                            </div>
                        `).join('') || '<div class="alert-item">暂无符合条件标的</div>';
                    document.getElementById('shrink-up').innerHTML = shrinkHtml;

                    // 更新信号表格
                    const signalsHtml = data.signals.map(s => `
                        <tr>
                            <td><strong>${s.name}</strong> <span class="tag">${s.sector || ''}</span></td>
                            <td class="price">${s.price.toFixed(2)}</td>
                            <td class="${s.change > 0 ? 'buy' : 'sell'}">${s.change > 0 ? '+' : ''}${s.change.toFixed(1)}%</td>
                            <td>${s.rsi.toFixed(0)}</td>
                            <td class="buy">${s.buy_low.toFixed(2)}-${s.buy_high.toFixed(2)}</td>
                            <td class="sell">${s.sell_low.toFixed(2)}-${s.sell_high.toFixed(2)}</td>
                            <td>${s.profit > 0 ? '+' : ''}${s.profit.toFixed(1)}%</td>
                            <td class="stars">${s.stars}</td>
                        </tr>
                    `).join('') || '<tr><td colspan="8">暂无数据</td></tr>';
                    document.getElementById('signals').innerHTML = signalsHtml;
                })
                .catch(e => console.error('刷新失败:', e));
        }

        setInterval(updateTime, 1000);
        setInterval(refresh, 30000);  // 30秒刷新
        updateTime();
        refresh();
    </script>
</body>
</html>
"""


class DashboardData:
    """看板数据管理"""

    def __init__(self):
        self.scanner = MarketScanner()
        self.signal_calc = SignalCalculator()
        self.connected = False

        self.watchlist = [
            ('HK.09888', '百度', 'AI'),
            ('HK.00020', '商汤', 'AI'),
            ('HK.01810', '小米', '机器人'),
            ('HK.00700', '腾讯', '互联网'),
            ('HK.09988', '阿里', '互联网'),
            ('HK.03690', '美团', '互联网'),
            ('HK.01211', '比亚迪', '新能源车'),
            ('HK.02015', '理想', '新能源车'),
            ('HK.00981', '中芯国际', '芯片'),
            ('HK.01045', '亚太卫星', '商业航天'),
        ]

    def connect(self):
        """连接数据源"""
        self.connected = self.signal_calc.connect()

    def disconnect(self):
        """断开连接"""
        self.signal_calc.disconnect()

    def get_hot_sectors(self) -> list:
        """获取热门板块"""
        try:
            industries = self.scanner.detect_hot_industries(min_stocks=2, min_avg_change=1.5)
            return [
                {'name': ind['industry'], 'change': ind['avg_change']}
                for ind in industries[:6]
            ]
        except Exception as e:
            print(f"获取热门板块失败: {e}")
            return []

    def get_capital_flow(self) -> list:
        """获取资金流向"""
        try:
            from fund_flow import CapitalFlowTracker
            tracker = CapitalFlowTracker()
            flows = tracker.get_hk_capital_flow(limit=5)
            return [
                {'name': f['name'], 'inflow': f['net_inflow']}
                for f in flows
            ]
        except Exception as e:
            print(f"获取资金流向失败: {e}")
            return []

    def get_signals(self) -> list:
        """获取交易信号"""
        signals = []

        for code, name, sector in self.watchlist:
            try:
                signal = self.signal_calc.generate_signal(code)
                if not signal.get('error'):
                    signals.append({
                        'code': signal['code'],
                        'name': signal['name'],
                        'sector': sector,
                        'price': signal['price'],
                        'change': signal['change_pct'],
                        'rsi': signal['rsi'],
                        'buy_low': signal['buy_zone'][0] or 0,
                        'buy_high': signal['buy_zone'][1] or 0,
                        'sell_low': signal['sell_zone'][0] or 0,
                        'sell_high': signal['sell_zone'][1] or 0,
                        'profit': signal['expected_profit'],
                        'stars': signal['stars'],
                        'is_shrink_up': signal['is_shrink_up'],
                        'shrink_reason': signal['shrink_reason'],
                    })
            except Exception as e:
                print(f"获取 {name} 信号失败: {e}")

        # 缩量上涨优先排序
        signals.sort(key=lambda x: (x['is_shrink_up'], x.get('profit', 0)), reverse=True)
        return signals

    def get_all_data(self) -> dict:
        """获取全部数据"""
        return {
            'hot_sectors': self.get_hot_sectors(),
            'capital_flow': self.get_capital_flow(),
            'signals': self.get_signals(),
            'alerts': DATA_CACHE.get('alerts', []),
            'last_update': datetime.now().strftime('%H:%M:%S'),
        }


dashboard_data = DashboardData()


@app.route('/')
def index():
    """主页"""
    return render_template_string(DASHBOARD_HTML)


@app.route('/api/data')
def api_data():
    """API数据接口"""
    try:
        data = dashboard_data.get_all_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def background_updater():
    """后台数据更新"""
    while True:
        try:
            data = dashboard_data.get_all_data()
            DATA_CACHE.update(data)
        except Exception as e:
            print(f"后台更新失败: {e}")
        time.sleep(60)


def main():
    import sys

    port = 8080
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)

    print(f"""
╔════════════════════════════════════════╗
║     港股追热点看板 v2.0                ║
╠════════════════════════════════════════╣
║  访问地址: http://localhost:{port}       ║
║  自动刷新: 每30秒                      ║
║  按 Ctrl+C 停止                        ║
╚════════════════════════════════════════╝
""")

    # 连接数据源
    dashboard_data.connect()

    # 启动后台更新
    updater = threading.Thread(target=background_updater, daemon=True)
    updater.start()

    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\n停止服务...")
    finally:
        dashboard_data.disconnect()


if __name__ == '__main__':
    main()
