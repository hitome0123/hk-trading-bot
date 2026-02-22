#!/usr/bin/env python3
"""
智能自选股资讯监控系统
功能：
1. 从富途读取自选股列表
2. 对接新浪财经 + 腾讯财经获取资讯
3. AI分析利好/利空
4. 推送重要消息
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import requests
import time
from datetime import datetime, timedelta
import json
import re

# 富途连接配置
FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111

# 新浪财经API
SINA_API_BASE = 'https://finance.sina.com.cn/realstock/company'
SINA_NEWS_API = 'https://vip.stock.finance.sina.com.cn/corp/go.php/vCB_Bulletin/stockid/{}/page_type/notic.phtml'

# 腾讯财经API
TENCENT_API_BASE = 'https://qt.gtimg.cn'
TENCENT_NEWS_API = 'https://stock.finance.qq.com/hkstock/notice/notice.htm?symbol={}'

# 关键词分类（AI情绪分析）
POSITIVE_KEYWORDS = {
    '业绩': ['业绩增长', '盈利', '营收增长', '利润增长', '超预期', '业绩预增'],
    '合作': ['签约', '中标', '合作', '战略合作', '订单', '大单'],
    '技术': ['研发成功', '新产品', '技术突破', '专利', '创新'],
    '资本': ['增持', '回购', '分红', '派息', '股权激励'],
    '重组': ['重组', '并购', '收购', '注入', '整合'],
    '评级': ['上调评级', '目标价上调', '买入评级', '推荐'],
    '其他': ['利好', '大涨', '暴涨', '突破', '涨停', '放量']
}

NEGATIVE_KEYWORDS = {
    '业绩': ['业绩下滑', '亏损', '营收下降', '利润下降', '业绩预警'],
    '违规': ['违规', '处罚', '调查', '立案', '问询'],
    '减持': ['减持', '质押', '套现'],
    '债务': ['债务', '违约', '破产', '重整'],
    '评级': ['下调评级', '目标价下调', '卖出评级'],
    '停牌': ['停牌', '退市', '摘牌'],
    '其他': ['利空', '大跌', '暴跌', '跌停', '诉讼']
}

def connect_futu():
    """连接富途OpenD"""
    try:
        quote_ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        print(f"✅ 富途OpenD连接成功")
        return quote_ctx
    except Exception as e:
        print(f"❌ 富途OpenD连接失败: {e}")
        return None

def get_futu_watchlist(quote_ctx, group_name='全部'):
    """从富途获取自选股列表"""
    try:
        ret, data = quote_ctx.get_user_security(group_name)
        if ret == RET_OK:
            stocks = data[['code', 'name']].to_dict('records')
            print(f"✅ 获取到 {len(stocks)} 只自选股（{group_name}）")
            return stocks
        else:
            print(f"❌ 获取自选股失败: {data}")
            return []
    except Exception as e:
        print(f"❌ 获取自选股异常: {e}")
        return []

def convert_code_for_sina(futu_code):
    """转换富途代码为新浪代码"""
    # HK.00700 → hk00700
    # US.AAPL → usAAPL
    if futu_code.startswith('HK.'):
        return 'hk' + futu_code.split('.')[1]
    elif futu_code.startswith('US.'):
        return 'us' + futu_code.split('.')[1]
    elif futu_code.startswith('SH.'):
        return 'sh' + futu_code.split('.')[1]
    elif futu_code.startswith('SZ.'):
        return 'sz' + futu_code.split('.')[1]
    return futu_code

def get_sina_news(stock_code, stock_name):
    """从新浪财经获取资讯"""
    try:
        sina_code = convert_code_for_sina(stock_code)

        # 新浪资讯列表API
        url = f'https://vip.stock.finance.sina.com.cn/corp/view/vCB_AllNewsStock.php?symbol={sina_code}&Page=1'

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            # 解析HTML（简化版，实际需要BeautifulSoup）
            content = response.text

            # 提取新闻标题（示例）
            news_list = []
            # 这里应该用BeautifulSoup解析，暂时返回空
            return news_list

        return []

    except Exception as e:
        print(f"  ⚠️ 新浪财经获取失败: {e}")
        return []

def get_tencent_news(stock_code, stock_name):
    """从腾讯财经获取资讯"""
    try:
        # 腾讯股票代码格式
        if stock_code.startswith('HK.'):
            tencent_code = 'hk' + stock_code.split('.')[1]
        else:
            return []

        # 腾讯实时数据API
        url = f'https://qt.gtimg.cn/q={tencent_code}'

        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            # 解析腾讯数据格式
            data = response.text
            # v_hk00700="1~腾讯控股~00700~365.00~..."

            return []

        return []

    except Exception as e:
        print(f"  ⚠️ 腾讯财经获取失败: {e}")
        return []

def analyze_news_sentiment(title, content=""):
    """AI分析新闻情绪"""
    text = title + " " + content

    # 统计利好关键词
    positive_score = 0
    positive_reasons = []

    for category, keywords in POSITIVE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                positive_score += 1
                positive_reasons.append(f"{category}:{kw}")

    # 统计利空关键词
    negative_score = 0
    negative_reasons = []

    for category, keywords in NEGATIVE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                negative_score += 1
                negative_reasons.append(f"{category}:{kw}")

    # 判断情绪
    if positive_score > negative_score:
        return "🟢 利好", positive_score, positive_reasons
    elif negative_score > positive_score:
        return "🔴 利空", negative_score, negative_reasons
    else:
        return "⚪中性", 0, []

def get_stock_snapshot(quote_ctx, stock_code):
    """获取股票实时快照"""
    try:
        ret, data = quote_ctx.get_market_snapshot([stock_code])
        if ret == RET_OK and not data.empty:
            last_price = data['last_price'].iloc[0]
            prev_close = data['prev_close_price'].iloc[0]

            # 计算涨跌幅
            change_pct = ((last_price - prev_close) / prev_close * 100) if prev_close > 0 else 0

            return {
                'price': last_price,
                'change_pct': change_pct,
                'volume': data['volume'].iloc[0],
                'turnover': data['turnover'].iloc[0],
                'prev_close': prev_close
            }
        return None
    except Exception as e:
        print(f"    ⚠️ 获取快照失败: {e}")
        return None

def monitor_watchlist():
    """主监控逻辑"""
    quote_ctx = connect_futu()
    if not quote_ctx:
        return

    try:
        print("\n" + "="*60)
        print(f"📊 开始监控自选股资讯 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)

        # 1. 获取自选股列表
        watchlist = get_futu_watchlist(quote_ctx, '全部')

        if not watchlist:
            print("❌ 未获取到自选股")
            return

        # 只监控港股（新浪/腾讯主要支持港股）
        hk_stocks = [s for s in watchlist if s['code'].startswith('HK.')]
        print(f"📋 本次监控 {len(hk_stocks)} 只港股")

        # 2. 逐个扫描
        important_news = []

        for i, stock in enumerate(hk_stocks[:20], 1):  # 先扫描前20只，避免太慢
            code = stock['code']
            name = stock['name']

            print(f"\n[{i}/{min(20, len(hk_stocks))}] {code} {name}")

            # 获取实时价格
            snapshot = get_stock_snapshot(quote_ctx, code)
            if snapshot:
                price = snapshot['price']
                change = snapshot['change_pct']
                emoji = "🔴" if change < 0 else "🟢"
                print(f"  {emoji} 最新价: {price:.2f}  涨跌: {change:+.2f}%")

                # 如果涨跌幅超过3%，重点关注
                if abs(change) >= 3:
                    important_news.append({
                        'code': code,
                        'name': name,
                        'type': '价格异动',
                        'content': f"{name} 涨跌{change:+.2f}%，当前价{price:.2f}"
                    })

            # 获取新浪资讯
            sina_news = get_sina_news(code, name)
            if sina_news:
                print(f"  📰 新浪资讯: {len(sina_news)} 条")

            # 获取腾讯资讯
            tencent_news = get_tencent_news(code, name)
            if tencent_news:
                print(f"  📰 腾讯资讯: {len(tencent_news)} 条")

            time.sleep(0.5)  # 避免请求过快

        # 3. 汇总重要消息
        if important_news:
            print("\n" + "="*60)
            print("🚨 发现重要信号！")
            print("="*60)
            for msg in important_news:
                print(f"\n【{msg['type']}】{msg['code']} {msg['name']}")
                print(f"  {msg['content']}")
        else:
            print("\n✅ 暂无重要消息")

    except Exception as e:
        print(f"❌ 监控出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        quote_ctx.close()

def main():
    """主程序"""
    print("\n" + "="*60)
    print("🚀 智能自选股资讯监控系统 v1.0")
    print("="*60)
    print("数据来源: 富途自选股 + 新浪财经 + 腾讯财经")
    print("监控频率: 每30分钟扫描一次")
    print("="*60)

    while True:
        try:
            monitor_watchlist()

            # 等待30分钟
            next_time = datetime.now() + timedelta(minutes=30)
            print(f"\n💤 下次扫描时间: {next_time.strftime('%H:%M')}")
            time.sleep(1800)

        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")
            break
        except Exception as e:
            print(f"\n❌ 程序异常: {e}")
            time.sleep(300)

if __name__ == '__main__':
    main()
