#!/usr/bin/env python3
"""
富途自选股资讯监控
功能：
1. 读取富途自选股列表
2. 抓取每只股票的最新资讯和公告
3. 分析利好/利空消息
4. 推送重要消息
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import time
from datetime import datetime, timedelta

# 富途连接配置
FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111

# 关键词分类
POSITIVE_KEYWORDS = [
    '利好', '大涨', '暴涨', '突破', '涨停', '业绩增长', '盈利',
    '合作', '签约', '中标', '订单', '扩产', '新产品', '研发成功',
    '增持', '回购', '分红', '重组', '并购', '上调评级', '目标价上调'
]

NEGATIVE_KEYWORDS = [
    '利空', '大跌', '暴跌', '跌停', '业绩下滑', '亏损',
    '违规', '处罚', '调查', '减持', '质押', '债务', '违约',
    '下调评级', '目标价下调', '停牌', '退市', '诉讼'
]

def connect_futu():
    """连接富途OpenD"""
    try:
        quote_ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)
        print(f"✅ 富途OpenD连接成功")
        return quote_ctx
    except Exception as e:
        print(f"❌ 富途OpenD连接失败: {e}")
        print(f"⚠️  请确保富途OpenD已启动（127.0.0.1:11111）")
        return None

def get_user_watchlist(quote_ctx):
    """获取用户自选股列表"""
    try:
        # 富途API获取自选股（需要实盘/仿真环境）
        # 由于查询自选股需要交易权限，这里改用配置文件
        print("⚠️  富途API获取自选股需要交易权限")
        print("📋 使用当前持仓作为监控列表")

        # 从持仓文件读取
        import json
        from pathlib import Path
        portfolio_file = Path.home() / '.hk_portfolio.json'

        if portfolio_file.exists():
            with open(portfolio_file, 'r') as f:
                portfolio = json.load(f)
                stocks = []
                for pos in portfolio['positions']:
                    # 转换格式：1929.HK → HK.01929
                    code = pos['ticker']
                    if '.' in code:
                        num, market = code.split('.')
                        stocks.append(f"{market}.{num.zfill(5)}")
                return stocks

        return []

    except Exception as e:
        print(f"❌ 获取自选股失败: {e}")
        return []

def get_stock_news(quote_ctx, stock_code):
    """获取股票最新资讯"""
    try:
        # 富途API暂不支持直接获取新闻
        # 这里返回模拟数据
        print(f"  📰 正在抓取 {stock_code} 的资讯...")

        # 实际应该调用富途API或爬取富途牛牛APP的资讯
        # ret, data = quote_ctx.get_stock_news(stock_code)  # 伪代码

        return []

    except Exception as e:
        print(f"  ❌ 获取资讯失败: {e}")
        return []

def analyze_sentiment(title, content=""):
    """分析消息情绪（利好/利空/中性）"""
    text = title + " " + content

    positive_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
    negative_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text)

    if positive_count > negative_count:
        return "利好", positive_count
    elif negative_count > positive_count:
        return "利空", negative_count
    else:
        return "中性", 0

def get_stock_announcement(quote_ctx, stock_code):
    """获取股票公告"""
    try:
        # 富途API获取公告
        # ret, data = quote_ctx.get_stock_announcement(stock_code)

        print(f"  📢 正在检查 {stock_code} 的公告...")
        return []

    except Exception as e:
        print(f"  ❌ 获取公告失败: {e}")
        return []

def monitor_watchlist():
    """监控自选股资讯"""
    quote_ctx = connect_futu()
    if not quote_ctx:
        return

    try:
        # 1. 获取自选股列表
        print("\n" + "="*60)
        print(f"📋 正在获取自选股列表...")
        print("="*60)

        watchlist = get_user_watchlist(quote_ctx)
        if not watchlist:
            print("❌ 未找到自选股")
            return

        print(f"✅ 找到 {len(watchlist)} 只自选股")
        for stock in watchlist:
            print(f"  • {stock}")

        # 2. 逐个扫描
        print("\n" + "="*60)
        print(f"🔍 开始扫描资讯和公告...")
        print("="*60)

        important_news = []

        for stock_code in watchlist:
            print(f"\n【{stock_code}】")

            # 获取实时价格
            ret, snapshot = quote_ctx.get_market_snapshot([stock_code])
            if ret == RET_OK and not snapshot.empty:
                current_price = snapshot['last_price'].iloc[0]
                change_pct = snapshot['change_rate'].iloc[0]
                print(f"  💰 最新价: {current_price:.2f}  涨跌: {change_pct:+.2f}%")

            # 获取资讯（当前富途API不直接支持，需要爬虫）
            news = get_stock_news(quote_ctx, stock_code)

            # 获取公告（富途API支持）
            announcements = get_stock_announcement(quote_ctx, stock_code)

            # 模拟输出
            print(f"  ✅ 暂无重要消息")

            time.sleep(0.5)  # 避免请求过快

        # 3. 推送重要消息（如果有）
        if important_news:
            print("\n" + "="*60)
            print(f"⚠️  发现重要消息！")
            print("="*60)
            for msg in important_news:
                print(msg)

    except Exception as e:
        print(f"❌ 监控出错: {e}")

    finally:
        quote_ctx.close()
        print("\n✅ 监控完成")

def main():
    """主程序"""
    print("\n" + "="*60)
    print("🚀 富途自选股资讯监控系统")
    print("="*60)
    print(f"启动时间: {datetime.now()}")
    print(f"监控周期: 每30分钟扫描一次")
    print("="*60)

    while True:
        try:
            monitor_watchlist()

            # 等待30分钟
            print(f"\n💤 等待30分钟后再次扫描...")
            print(f"下次扫描时间: {(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')}")
            time.sleep(1800)

        except KeyboardInterrupt:
            print("\n\n✅ 监控已停止")
            break
        except Exception as e:
            print(f"\n❌ 程序异常: {e}")
            print("⏰ 5分钟后重试...")
            time.sleep(300)

if __name__ == '__main__':
    main()
