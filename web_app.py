#!/usr/bin/env python3
"""
港股交易助手 - Web界面
运行: python web_app.py
访问: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, request
import yfinance as yf
import numpy as np
import json
import os
from datetime import datetime

app = Flask(__name__)

# 导入现有模块
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fund_flow import FundFlowMonitor
    from crypto_monitor import CryptoMonitor
    from portfolio import load_portfolio, get_realtime_prices, calculate_fees
except:
    pass

# ============ 工具函数 ============

def analyze_stock(ticker: str) -> dict:
    """分析单只股票"""
    try:
        ticker = ticker.upper()
        if not any(ticker.endswith(x) for x in ['.HK', '.SZ', '.SS']):
            ticker += '.HK'

        stock = yf.Ticker(ticker)
        hist = stock.history(period='3mo')
        info = stock.info

        if len(hist) < 20:
            return {'error': '数据不足'}

        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2]
        change = (current - prev) / prev * 100

        # 均线
        ma5 = hist['Close'].tail(5).mean()
        ma10 = hist['Close'].tail(10).mean()
        ma20 = hist['Close'].tail(20).mean()

        # RSI
        delta = hist['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])

        # 量比
        vol_today = hist['Volume'].iloc[-1]
        vol_avg = hist['Volume'].tail(5).mean()
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 0

        # 套牢盘
        closes = hist['Close'].values
        trapped = (closes[:-1] > current).sum() / len(closes[:-1]) * 100

        # 趋势
        trend = '上涨' if ma5 > ma10 > ma20 else ('下跌' if ma5 < ma10 < ma20 else '震荡')

        # 支撑阻力
        high_20d = float(hist['High'].tail(20).max())
        low_20d = float(hist['Low'].tail(20).min())

        return {
            'ticker': ticker,
            'name': info.get('shortName', ticker),
            'price': float(current),
            'change': float(change),
            'ma5': float(ma5),
            'ma10': float(ma10),
            'ma20': float(ma20),
            'rsi': rsi,
            'vol_ratio': float(vol_ratio),
            'trapped': float(trapped),
            'trend': trend,
            'high_20d': high_20d,
            'low_20d': low_20d,
            'rsi_signal': '超买' if rsi > 70 else ('超卖' if rsi < 30 else '中性')
        }
    except Exception as e:
        return {'error': str(e)}


# ============ 路由 ============

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/analyze/<ticker>')
def api_analyze(ticker):
    """分析股票API"""
    result = analyze_stock(ticker)
    return jsonify(result)


@app.route('/api/portfolio')
def api_portfolio():
    """获取持仓"""
    try:
        portfolio = load_portfolio()
        positions = portfolio.get('positions', [])

        if positions:
            tickers = [p['ticker'] for p in positions]
            prices = get_realtime_prices(tickers)

            total_cost = 0
            total_value = 0

            for p in positions:
                ticker = p['ticker']
                current = prices.get(ticker, 0)
                if current > 0:
                    p['current_price'] = current
                    p['market_value'] = p['shares'] * current
                    p['pnl'] = p['market_value'] - p['total_cost']
                    p['pnl_pct'] = p['pnl'] / p['total_cost'] * 100
                    total_cost += p['total_cost']
                    total_value += p['market_value']

            return jsonify({
                'positions': positions,
                'total_cost': total_cost,
                'total_value': total_value,
                'total_pnl': total_value - total_cost
            })
    except:
        pass

    return jsonify({'positions': [], 'total_cost': 0, 'total_value': 0, 'total_pnl': 0})


@app.route('/api/fund_flow')
def api_fund_flow():
    """资金流向"""
    try:
        monitor = FundFlowMonitor()
        inflow = monitor.get_hk_top_flow('in', 10)
        outflow = monitor.get_hk_top_flow('out', 10)
        return jsonify({'inflow': inflow, 'outflow': outflow})
    except:
        return jsonify({'inflow': [], 'outflow': []})


@app.route('/api/crypto')
def api_crypto():
    """加密货币"""
    try:
        monitor = CryptoMonitor()
        btc = monitor.get_price('bitcoin')
        eth = monitor.get_price('ethereum')
        fng = monitor.get_fear_greed_index()
        pred = monitor.predict_direction('bitcoin')

        return jsonify({
            'btc': btc,
            'eth': eth,
            'fear_greed': fng,
            'prediction': pred
        })
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/api/scan')
def api_scan():
    """快速扫描热门股"""
    hot_stocks = [
        '0700.HK', '9888.HK', '9618.HK', '3690.HK',
        '1929.HK', '0386.HK', '0981.HK', '1024.HK',
        '1211.HK', '2015.HK', '6160.HK', '1816.HK'
    ]

    results = []
    for ticker in hot_stocks:
        data = analyze_stock(ticker)
        if 'error' not in data:
            results.append(data)

    # 按涨跌排序
    results.sort(key=lambda x: x['change'], reverse=True)
    return jsonify(results)


# ============ 模板 ============

# 创建templates目录
templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(templates_dir, exist_ok=True)

# 写入HTML模板
html_template = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>港股交易助手</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #1a1a2e; color: #eee; }
        .card { background: #16213e; border: none; margin-bottom: 15px; }
        .card-header { background: #0f3460; border-bottom: 1px solid #1a1a2e; }
        .table { color: #eee; }
        .text-success { color: #00ff88 !important; }
        .text-danger { color: #ff4757 !important; }
        .badge-up { background: #00ff88; color: #000; }
        .badge-down { background: #ff4757; color: #fff; }
        .stock-card { cursor: pointer; transition: transform 0.2s; }
        .stock-card:hover { transform: scale(1.02); }
        #searchInput { background: #0f3460; border: none; color: #fff; }
        #searchInput::placeholder { color: #888; }
        .loading { text-align: center; padding: 20px; }
        .nav-tabs .nav-link { color: #888; }
        .nav-tabs .nav-link.active { background: #0f3460; color: #fff; border-color: #0f3460; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark">
        <div class="container">
            <span class="navbar-brand">📈 港股交易助手</span>
            <span class="text-muted" id="updateTime"></span>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- 搜索框 -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="input-group">
                    <input type="text" id="searchInput" class="form-control" placeholder="输入股票代码，如 0700.HK">
                    <button class="btn btn-primary" onclick="searchStock()">分析</button>
                </div>
            </div>
        </div>

        <!-- 分析结果 -->
        <div id="analysisResult" class="mb-4" style="display:none;">
            <div class="card">
                <div class="card-header">
                    <h5 id="stockName">股票分析</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <h3 id="stockPrice">--</h3>
                            <span id="stockChange">--</span>
                        </div>
                        <div class="col-md-3">
                            <p>趋势: <strong id="stockTrend">--</strong></p>
                            <p>RSI: <span id="stockRSI">--</span></p>
                        </div>
                        <div class="col-md-3">
                            <p>量比: <span id="stockVol">--</span></p>
                            <p>套牢盘: <span id="stockTrapped">--</span></p>
                        </div>
                        <div class="col-md-3">
                            <p>20日高: <span id="stockHigh">--</span></p>
                            <p>20日低: <span id="stockLow">--</span></p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 标签页 -->
        <ul class="nav nav-tabs" id="mainTabs">
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="#tabScan">热门扫描</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#tabPortfolio">我的持仓</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#tabFundFlow">资金流向</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#tabCrypto">加密货币</a>
            </li>
        </ul>

        <div class="tab-content mt-3">
            <!-- 热门扫描 -->
            <div class="tab-pane fade show active" id="tabScan">
                <div id="scanLoading" class="loading">加载中...</div>
                <div id="scanResults" class="row"></div>
            </div>

            <!-- 持仓 -->
            <div class="tab-pane fade" id="tabPortfolio">
                <div id="portfolioLoading" class="loading">加载中...</div>
                <div id="portfolioContent"></div>
            </div>

            <!-- 资金流向 -->
            <div class="tab-pane fade" id="tabFundFlow">
                <div id="fundFlowLoading" class="loading">加载中...</div>
                <div class="row" id="fundFlowContent"></div>
            </div>

            <!-- 加密货币 -->
            <div class="tab-pane fade" id="tabCrypto">
                <div id="cryptoLoading" class="loading">加载中...</div>
                <div id="cryptoContent"></div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 更新时间
        function updateTime() {
            document.getElementById('updateTime').textContent = new Date().toLocaleString('zh-CN');
        }
        updateTime();
        setInterval(updateTime, 1000);

        // 搜索股票
        function searchStock() {
            const ticker = document.getElementById('searchInput').value.trim();
            if (!ticker) return;

            fetch('/api/analyze/' + ticker)
                .then(r => r.json())
                .then(data => {
                    if (data.error) {
                        alert('错误: ' + data.error);
                        return;
                    }
                    showAnalysis(data);
                });
        }

        // 显示分析结果
        function showAnalysis(data) {
            document.getElementById('analysisResult').style.display = 'block';
            document.getElementById('stockName').textContent = data.name + ' (' + data.ticker + ')';
            document.getElementById('stockPrice').textContent = data.price.toFixed(2) + ' HKD';

            const changeEl = document.getElementById('stockChange');
            changeEl.textContent = (data.change >= 0 ? '+' : '') + data.change.toFixed(2) + '%';
            changeEl.className = data.change >= 0 ? 'text-success' : 'text-danger';

            document.getElementById('stockTrend').textContent = data.trend;
            document.getElementById('stockRSI').textContent = data.rsi.toFixed(1) + ' (' + data.rsi_signal + ')';
            document.getElementById('stockVol').textContent = data.vol_ratio.toFixed(2) + 'x';
            document.getElementById('stockTrapped').textContent = data.trapped.toFixed(0) + '%';
            document.getElementById('stockHigh').textContent = data.high_20d.toFixed(2);
            document.getElementById('stockLow').textContent = data.low_20d.toFixed(2);
        }

        // 加载热门扫描
        function loadScan() {
            fetch('/api/scan')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('scanLoading').style.display = 'none';
                    let html = '';
                    data.forEach(s => {
                        const changeClass = s.change >= 0 ? 'text-success' : 'text-danger';
                        const badge = s.change >= 0 ? 'badge-up' : 'badge-down';
                        html += `
                            <div class="col-md-3 mb-3">
                                <div class="card stock-card" onclick="searchAndShow('${s.ticker}')">
                                    <div class="card-body">
                                        <h6>${s.name}</h6>
                                        <small class="text-muted">${s.ticker}</small>
                                        <h4 class="${changeClass}">${s.price.toFixed(2)}</h4>
                                        <span class="badge ${badge}">${s.change >= 0 ? '+' : ''}${s.change.toFixed(2)}%</span>
                                        <p class="mt-2 mb-0 small">
                                            趋势:${s.trend} | 套牢:${s.trapped.toFixed(0)}%
                                        </p>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    document.getElementById('scanResults').innerHTML = html;
                });
        }

        function searchAndShow(ticker) {
            document.getElementById('searchInput').value = ticker;
            searchStock();
        }

        // 加载持仓
        function loadPortfolio() {
            fetch('/api/portfolio')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('portfolioLoading').style.display = 'none';
                    if (!data.positions || data.positions.length === 0) {
                        document.getElementById('portfolioContent').innerHTML = '<p>暂无持仓</p>';
                        return;
                    }

                    let html = '<table class="table"><thead><tr><th>股票</th><th>股数</th><th>成本</th><th>现价</th><th>盈亏</th></tr></thead><tbody>';
                    data.positions.forEach(p => {
                        const pnlClass = p.pnl >= 0 ? 'text-success' : 'text-danger';
                        html += `<tr>
                            <td>${p.name || p.ticker}</td>
                            <td>${p.shares}</td>
                            <td>${p.cost.toFixed(2)}</td>
                            <td>${p.current_price ? p.current_price.toFixed(2) : '-'}</td>
                            <td class="${pnlClass}">${p.pnl ? p.pnl.toFixed(0) : '-'} (${p.pnl_pct ? p.pnl_pct.toFixed(1) + '%' : '-'})</td>
                        </tr>`;
                    });
                    html += '</tbody></table>';
                    html += `<p>总盈亏: <strong class="${data.total_pnl >= 0 ? 'text-success' : 'text-danger'}">${data.total_pnl.toFixed(0)} HKD</strong></p>`;
                    document.getElementById('portfolioContent').innerHTML = html;
                });
        }

        // 加载资金流向
        function loadFundFlow() {
            fetch('/api/fund_flow')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('fundFlowLoading').style.display = 'none';
                    let html = '<div class="col-md-6"><div class="card"><div class="card-header">📈 主力流入</div><div class="card-body"><table class="table table-sm"><tbody>';
                    data.inflow.slice(0,8).forEach(s => {
                        const net = s.main_net >= 10000 ? (s.main_net/10000).toFixed(1) + '亿' : s.main_net.toFixed(0) + '万';
                        html += `<tr><td>${s.name}</td><td class="text-success">+${net}</td><td class="${s.change_pct >= 0 ? 'text-success' : 'text-danger'}">${s.change_pct.toFixed(1)}%</td></tr>`;
                    });
                    html += '</tbody></table></div></div></div>';

                    html += '<div class="col-md-6"><div class="card"><div class="card-header">📉 主力流出</div><div class="card-body"><table class="table table-sm"><tbody>';
                    data.outflow.slice(0,8).forEach(s => {
                        const net = Math.abs(s.main_net) >= 10000 ? (Math.abs(s.main_net)/10000).toFixed(1) + '亿' : Math.abs(s.main_net).toFixed(0) + '万';
                        html += `<tr><td>${s.name}</td><td class="text-danger">-${net}</td><td class="${s.change_pct >= 0 ? 'text-success' : 'text-danger'}">${s.change_pct.toFixed(1)}%</td></tr>`;
                    });
                    html += '</tbody></table></div></div></div>';
                    document.getElementById('fundFlowContent').innerHTML = html;
                });
        }

        // 加载加密货币
        function loadCrypto() {
            fetch('/api/crypto')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('cryptoLoading').style.display = 'none';
                    if (data.error) {
                        document.getElementById('cryptoContent').innerHTML = '<p>加载失败</p>';
                        return;
                    }

                    let html = '<div class="row">';

                    // BTC
                    if (data.btc) {
                        const btcClass = data.btc.change_24h >= 0 ? 'text-success' : 'text-danger';
                        html += `<div class="col-md-4"><div class="card"><div class="card-body">
                            <h5>Bitcoin</h5>
                            <h3 class="${btcClass}">$${data.btc.price.toLocaleString()}</h3>
                            <span class="${btcClass}">${data.btc.change_24h >= 0 ? '+' : ''}${data.btc.change_24h.toFixed(2)}%</span>
                        </div></div></div>`;
                    }

                    // ETH
                    if (data.eth) {
                        const ethClass = data.eth.change_24h >= 0 ? 'text-success' : 'text-danger';
                        html += `<div class="col-md-4"><div class="card"><div class="card-body">
                            <h5>Ethereum</h5>
                            <h3 class="${ethClass}">$${data.eth.price.toLocaleString()}</h3>
                            <span class="${ethClass}">${data.eth.change_24h >= 0 ? '+' : ''}${data.eth.change_24h.toFixed(2)}%</span>
                        </div></div></div>`;
                    }

                    // 恐惧贪婪
                    if (data.fear_greed) {
                        html += `<div class="col-md-4"><div class="card"><div class="card-body">
                            <h5>恐惧贪婪指数</h5>
                            <h3>${data.fear_greed.value}</h3>
                            <span>${data.fear_greed.classification}</span>
                        </div></div></div>`;
                    }

                    html += '</div>';

                    // 预测
                    if (data.prediction) {
                        const p = data.prediction;
                        const predClass = p.direction === '看涨' ? 'text-success' : (p.direction === '看跌' ? 'text-danger' : 'text-warning');
                        html += `<div class="card mt-3"><div class="card-header">BTC预测</div><div class="card-body">
                            <h4 class="${predClass}">${p.direction} (${p.confidence})</h4>
                            <p>看涨指数: ${p.bull_pct.toFixed(0)}%</p>
                        </div></div>`;
                    }

                    document.getElementById('cryptoContent').innerHTML = html;
                });
        }

        // 标签切换时加载数据
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', e => {
                const target = e.target.getAttribute('href');
                if (target === '#tabPortfolio') loadPortfolio();
                if (target === '#tabFundFlow') loadFundFlow();
                if (target === '#tabCrypto') loadCrypto();
            });
        });

        // 回车搜索
        document.getElementById('searchInput').addEventListener('keypress', e => {
            if (e.key === 'Enter') searchStock();
        });

        // 初始加载
        loadScan();
    </script>
</body>
</html>'''

with open(os.path.join(templates_dir, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html_template)


if __name__ == '__main__':
    print("=" * 50)
    print("港股交易助手 Web版")
    print("=" * 50)
    print("访问地址: http://localhost:5001")
    print("按 Ctrl+C 停止")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5001)
