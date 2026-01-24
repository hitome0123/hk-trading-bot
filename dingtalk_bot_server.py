#!/usr/bin/env python3
"""
钉钉智能机器人服务 - 港股助手
支持：股票查询、资金流向、雪球热议、新闻热点、板块分析等
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

import json
import hmac
import hashlib
import base64
import time
import re
import requests
from flask import Flask, request, jsonify
from datetime import datetime

from smart_picker import CapitalFlowTracker, SocialHeatTracker
from market_scanner import MarketScanner
from dingtalk_notifier import DingTalkNotifier

app = Flask(__name__)

# 初始化组件
flow_tracker = CapitalFlowTracker()
heat_tracker = SocialHeatTracker()
market_scanner = MarketScanner()
notifier = DingTalkNotifier()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15',
    'Accept': 'application/json',
}

# 股票代码映射
STOCK_ALIASES = {
    '阿里': ('09988', '阿里巴巴'),
    '阿里巴巴': ('09988', '阿里巴巴'),
    '腾讯': ('00700', '腾讯控股'),
    '美团': ('03690', '美团'),
    '小米': ('01810', '小米集团'),
    '京东': ('09618', '京东集团'),
    '百度': ('09888', '百度集团'),
    '快手': ('01024', '快手'),
    '比亚迪': ('01211', '比亚迪'),
    '理想': ('02015', '理想汽车'),
    '小鹏': ('09868', '小鹏汽车'),
    '蔚来': ('09866', '蔚来'),
    '中芯': ('00981', '中芯国际'),
    '华虹': ('01347', '华虹半导体'),
    '商汤': ('00020', '商汤'),
    '中石化': ('00386', '中国石化'),
    '亚太卫星': ('01045', '亚太卫星'),
    '金风': ('02208', '金风科技'),
    '航天': ('01045', '亚太卫星'),
}


# ==================== 功能函数 ====================

def get_xueqiu_hot_topics() -> str:
    """获取雪球热门讨论"""
    content = "### ❄️ 雪球热门讨论\n\n"

    try:
        # 方法1: 雪球热帖
        url = "https://xueqiu.com/statuses/hot/listV2.json"
        params = {'since_id': -1, 'max_id': -1, 'size': 10}
        headers = {
            **HEADERS,
            'Cookie': 'xq_a_token=test;',
            'Referer': 'https://xueqiu.com/',
        }

        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            for i, item in enumerate(items[:8], 1):
                text = item.get('original_status', {}).get('text', '')
                # 清理HTML
                text = re.sub(r'<[^>]+>', '', text)[:60]
                if text:
                    content += f"{i}. {text}...\n"
    except Exception as e:
        content += f"获取失败，尝试备用方案...\n"

    # 备用：东财股吧港股热帖
    try:
        url = "https://guba.eastmoney.com/interface/GetData.aspx"
        params = {
            'path': 'topiclist/hk_topiclist',
            'param': 'ps=10',
        }
        resp = requests.get(url, headers=HEADERS, timeout=10)

        if '热帖' not in content and 'title' in resp.text.lower():
            content += "\n**东财港股热帖:**\n"
            # 简单解析
            titles = re.findall(r'"title":"([^"]+)"', resp.text)
            for i, t in enumerate(titles[:5], 1):
                content += f"{i}. {t[:40]}\n"
    except:
        pass

    # 备用2：直接搜索港股讨论
    try:
        content += "\n**港股热议关键词:**\n"
        hot_keywords = ['商业航天', 'AI', '机器人', '新能源', '芯片']
        for kw in hot_keywords:
            content += f"• {kw}\n"
    except:
        pass

    content += f"\n---\n*更新: {datetime.now().strftime('%H:%M')}*"
    return content


def get_eastmoney_news() -> str:
    """获取东财财经新闻"""
    content = "### 📰 财经新闻速览\n\n"

    try:
        # 东财快讯
        url = "https://np-listapi.eastmoney.com/comm/web/getFastNewsList"
        params = {
            'client': 'web',
            'biz': 'web_724',
            'req_trace': str(int(time.time() * 1000)),
            'page_index': 1,
            'page_size': 10,
        }

        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()

        if data.get('data') and data['data'].get('fastNewsList'):
            for item in data['data']['fastNewsList'][:8]:
                title = item.get('title', '')[:45]
                digest = item.get('digest', '')[:30]
                time_str = item.get('showTime', '')

                if '港股' in title or '港' in title:
                    content += f"🔴 **{title}**\n"
                else:
                    content += f"• {title}\n"

                if digest:
                    content += f"  _{digest}_\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    content += f"\n---\n*更新: {datetime.now().strftime('%H:%M')}*"
    return content


def get_hk_top_gainers() -> str:
    """获取港股涨幅榜"""
    content = "### 🏆 港股涨幅榜 TOP10\n\n"

    try:
        gainers = market_scanner._get_eastmoney_hk_rank('asc', top_n=10)

        content += f"| 股票 | 涨幅 | 行业 |\n"
        content += f"|------|------|------|\n"

        for s in gainers[:10]:
            content += f"| {s['name'][:6]} | +{s['change_pct']:.1f}% | {s['industry'][:4]} |\n"

    except Exception as e:
        content += f"获取失败: {e}\n"

    content += f"\n---\n*更新: {datetime.now().strftime('%H:%M')}*"
    return content


def get_market_hot() -> str:
    """获取热门板块"""
    content = "### 🔥 港股热门板块\n\n"

    try:
        hot = market_scanner.detect_hot_industries(min_stocks=2, min_avg_change=2.0)

        for i, ind in enumerate(hot[:6], 1):
            leader = ind['leader']
            content += f"**{i}. {ind['industry']}** +{ind['avg_change']:.2f}%\n"
            content += f"> 领涨: {leader['name']} +{leader['change_pct']:.1f}%\n\n"
    except Exception as e:
        content += f"获取失败: {e}\n"

    content += f"\n---\n*更新: {datetime.now().strftime('%H:%M')}*"
    return content


def get_stock_analysis(code: str, name: str = None) -> str:
    """获取股票完整分析 - 包含量价指标"""
    display_name = name or code

    # 1. 实时行情 + 量价数据
    price_info = ""
    vol_info = ""
    tech_info = ""

    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"
        params = {
            'secid': f'116.{code}',
            'fields': 'f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f62,f71,f116,f117,f162,f163,f164,f167,f168,f169,f170,f171,f177,f193'
        }
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        data = resp.json()

        if data.get('data'):
            d = data['data']
            price = d.get('f43', 0) / 1000  # 现价
            change = d.get('f170', 0) / 100  # 涨跌幅
            high = d.get('f44', 0) / 1000   # 最高
            low = d.get('f45', 0) / 1000    # 最低
            open_p = d.get('f46', 0) / 1000 # 开盘
            volume = d.get('f47', 0)        # 成交量(手)
            amount = d.get('f48', 0) / 100000000  # 成交额(亿)
            vol_ratio = d.get('f50', 0) / 100     # 量比
            turnover = d.get('f168', 0) / 100     # 换手率
            pe = d.get('f162', 0) / 100     # 市盈率
            pb = d.get('f167', 0) / 100     # 市净率
            total_mv = d.get('f116', 0) / 100000000  # 总市值(亿)
            amp = d.get('f171', 0) / 100    # 振幅

            price_info = f"现价: **{price:.2f}** | 涨跌: **{change:+.2f}%**"

            # 量价分析
            vol_info = f"""
**量价指标:**
| 指标 | 数值 | 说明 |
|------|------|------|
| 成交额 | {amount:.2f}亿 | {'活跃' if amount > 10 else '一般'} |
| 量比 | {vol_ratio:.2f} | {'放量' if vol_ratio > 1.5 else '缩量' if vol_ratio < 0.8 else '正常'} |
| 换手率 | {turnover:.2f}% | {'高换手' if turnover > 5 else '低换手' if turnover < 1 else '适中'} |
| 振幅 | {amp:.2f}% | {'大波动' if amp > 5 else '小波动'} |
"""

            # 技术指标
            tech_info = f"""
**估值指标:**
- 市盈率(PE): {pe:.2f}
- 市净率(PB): {pb:.2f}
- 总市值: {total_mv:.0f}亿

**价格区间:** {low:.2f} - {high:.2f} (开盘{open_p:.2f})
"""
    except Exception as e:
        price_info = f"行情暂无: {e}"

    # 2. 资金流向
    flow = flow_tracker.get_capital_flow(code)
    main_inflow = flow['main_inflow']
    flow_icon = "🟢" if main_inflow > 0 else "🔴"
    flow_info = f"{flow_icon} 主力净流入: **{main_inflow/10000:.2f}亿** (评分{flow['flow_score']})"

    # 3. 热度
    heat = heat_tracker.get_combined_heat(code)

    # 4. 综合评价
    score = flow['flow_score']
    if vol_ratio > 1.5 and main_inflow > 0:
        verdict = "🟢 放量上涨，资金流入，短期看多"
    elif vol_ratio < 0.8 and main_inflow < 0:
        verdict = "🔴 缩量下跌，资金流出，谨慎观望"
    elif main_inflow > 0:
        verdict = "🟡 资金流入，可关注"
    else:
        verdict = "⚪ 资金流出，观望为主"

    content = f"""### 📊 {display_name} ({code}.HK)

{price_info}

---
{vol_info}
{tech_info}
**资金:** {flow_info}

**热度:** {heat['combined_score']:.0f}/100 {heat['heat_level']}

---

**综合判断:** {verdict}

*{datetime.now().strftime('%H:%M:%S')}*
"""
    return content


def get_sector_analysis(sector_name: str) -> str:
    """分析某个板块"""
    content = f"### 📈 {sector_name}板块分析\n\n"

    try:
        # 搜索相关行业
        hot = market_scanner.detect_hot_industries(min_stocks=1, min_avg_change=0)

        found = None
        for ind in hot:
            if sector_name in ind['industry'] or ind['industry'] in sector_name:
                found = ind
                break

        if found:
            content += f"**涨幅:** +{found['avg_change']:.2f}%\n"
            content += f"**股票数:** {found['stock_count']}只\n\n"
            content += f"**TOP股票:**\n"
            for s in found['top_stocks'][:5]:
                content += f"• {s['name']} +{s['change_pct']:.1f}%\n"
        else:
            content += f"未找到该板块数据，可能名称不匹配\n"
            content += f"\n**热门板块:**\n"
            for ind in hot[:5]:
                content += f"• {ind['industry']} +{ind['avg_change']:.1f}%\n"

    except Exception as e:
        content += f"分析失败: {e}\n"

    content += f"\n---\n*{datetime.now().strftime('%H:%M')}*"
    return content


def get_help_message() -> str:
    """帮助信息"""
    return """### 🤖 港股助手

**股票查询:**
`阿里` `腾讯` `美团` `小米` `比亚迪`...

**市场信息:**
`雪球` - 雪球热议
`新闻` - 财经新闻
`热点` - 热门板块
`涨幅榜` - 涨幅TOP10

**板块分析:**
`科技板块` `新能源` `地产`...

**特色功能:**
`马斯克` - 追踪马斯克动态和关联板块

**示例:**
- @机器人 阿里
- @机器人 热点
- @机器人 马斯克最近说了什么
"""


# ==================== 消息处理 ====================

def parse_stock_query(text: str) -> tuple:
    """解析股票查询"""
    for alias, (code, name) in STOCK_ALIASES.items():
        if alias in text:
            return code, name

    # 匹配5位代码
    code_match = re.search(r'(\d{5})', text)
    if code_match:
        return code_match.group(1), None

    return None, None


def get_musk_update() -> str:
    """获取马斯克动态"""
    from musk_tracker import MuskTracker
    tracker = MuskTracker()
    report = tracker.get_musk_report()
    return tracker.format_report(report)


def process_message(text: str) -> str:
    """智能处理消息"""
    text_lower = text.lower().strip()

    # 0. 马斯克相关
    if any(k in text_lower for k in ['马斯克', 'musk', 'elon', '特斯拉', 'spacex', 'starlink']):
        return get_musk_update()

    # 1. 帮助
    if any(k in text_lower for k in ['帮助', 'help', '怎么用', '用法', '功能']):
        return get_help_message()

    # 2. 雪球讨论
    if any(k in text_lower for k in ['雪球', '讨论', '热议', '聊啥', '在说']):
        return get_xueqiu_hot_topics()

    # 3. 新闻
    if any(k in text_lower for k in ['新闻', '快讯', '消息', '资讯']):
        return get_eastmoney_news()

    # 4. 涨幅榜
    if any(k in text_lower for k in ['涨幅榜', '涨幅', '排行', 'top']):
        return get_hk_top_gainers()

    # 5. 热点/板块
    if any(k in text_lower for k in ['热点', '热门', '板块热']):
        return get_market_hot()

    # 6. 特定板块分析
    sector_keywords = ['科技', '新能源', '汽车', '地产', '金融', '航天', '芯片', 'ai', '机器人', '光伏', '医药']
    for kw in sector_keywords:
        if kw in text_lower:
            return get_sector_analysis(kw)

    # 7. 股票查询
    code, name = parse_stock_query(text)
    if code:
        return get_stock_analysis(code, name)

    # 8. 默认
    return get_help_message()


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收钉钉消息 - 保存到文件供Claude读取"""
    try:
        data = request.json
        msg_type = data.get('msgtype', '')

        if msg_type == 'text':
            content = data.get('text', {}).get('content', '').strip()
            sender = data.get('senderNick', '用户')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            print(f"📩 [{timestamp}] [{sender}]: {content}")

            # 保存消息到文件，供Claude读取
            msg_file = '/tmp/dingtalk_messages.txt'
            with open(msg_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] [{sender}]: {content}\n")

            # 同时保存最新一条到单独文件
            with open('/tmp/dingtalk_latest.txt', 'w', encoding='utf-8') as f:
                f.write(f"{content}")

            print(f"💾 消息已保存，等待Claude处理...")

        return jsonify({'success': True})

    except Exception as e:
        print(f"❌ 错误: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/test', methods=['GET'])
def test():
    """测试接口 - 浏览器访问测试"""
    query = request.args.get('q', '帮助')
    reply = process_message(query)
    notifier.send_markdown("港股助手", reply)
    return f"<pre>{reply}</pre><br>已推送到钉钉"


def run_server(port=8080):
    print("=" * 60)
    print("🤖 港股智能助手启动")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 端口: {port}")
    print("=" * 60)
    print("\n支持的问题:")
    print("  • 股票查询: 阿里、腾讯、09988...")
    print("  • 雪球热议: 雪球在聊啥")
    print("  • 财经新闻: 今天新闻")
    print("  • 热门板块: 热点")
    print("  • 涨幅榜: 涨幅榜")
    print("  • 板块分析: 科技板块、新能源...")
    print("\n")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'test':
            query = ' '.join(sys.argv[2:]) if len(sys.argv) > 2 else '帮助'
            print(f"测试: {query}\n")
            reply = process_message(query)
            print(reply)
            print("\n推送到钉钉...")
            notifier.send_markdown("港股助手", reply)
            print("✅ 完成")
        elif cmd == 'server':
            run_server()
    else:
        run_server()
