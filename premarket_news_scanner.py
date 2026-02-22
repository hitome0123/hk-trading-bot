#!/usr/bin/env python3
"""
盘前资讯扫描器 v3.0 - 新浪财经版
功能：
1. 每日08:30盘前扫描自选股
2. 检测隔夜价格变化
3. 获取新浪财经最新资讯
4. AI分析利好/利空情绪
5. Telegram推送重要信号
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import time
from datetime import datetime, timedelta
from collections import defaultdict
import requests
import re

# Telegram配置
TELEGRAM_BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
TELEGRAM_CHAT_ID = "7082819163"

# 板块映射（与sector_radar.py保持一致）
SECTOR_MAP = {
    "人形机器人": ["HK.09880", "HK.02432", "HK.06600", "HK.02090"],
    "AI大模型": ["HK.02513", "HK.00100", "HK.09888", "HK.09618"],
    "GPU芯片": ["HK.06082", "HK.09903", "HK.00981", "HK.00700"],
    "互联网": ["HK.00700", "HK.09988", "HK.03690", "HK.01024"],
    "港股科技": ["HK.09999", "HK.02013", "HK.02158", "HK.06682"],
    "新能源车": ["HK.01211", "HK.02015", "HK.09868"],
    "军工": ["HK.02357", "HK.00179"],
    "生物医药": ["HK.02269", "HK.01931", "HK.02675"],
    "芯片设备": ["HK.00501", "HK.00688"],
    "云计算": ["HK.09618", "HK.00700", "HK.09888"]
}

# 利好关键词
POSITIVE_KEYWORDS = {
    '业绩': ['业绩增长', '盈利', '营收增长', '利润增长', '超预期', '业绩预增'],
    '合作': ['签约', '中标', '合作', '战略合作', '订单', '大单'],
    '技术': ['研发成功', '新产品', '技术突破', '专利', '创新'],
    '资本': ['增持', '回购', '分红', '派息', '股权激励'],
    '重组': ['重组', '并购', '收购', '注入', '整合'],
    '评级': ['上调评级', '目标价上调', '买入评级', '推荐'],
    '其他': ['利好', '大涨', '暴涨', '突破', '涨停', '放量']
}

# 利空关键词
NEGATIVE_KEYWORDS = {
    '业绩': ['业绩下滑', '亏损', '营收下降', '利润下降', '业绩预警'],
    '违规': ['违规', '处罚', '调查', '立案', '问询'],
    '减持': ['减持', '质押', '套现'],
    '债务': ['债务', '违约', '破产', '重整'],
    '评级': ['下调评级', '目标价下调', '卖出评级'],
    '停牌': ['停牌', '退市', '摘牌'],
    '其他': ['利空', '大跌', '暴跌', '跌停', '诉讼']
}

class PremarketScanner:
    def __init__(self):
        self.quote_ctx = None
        self.watchlist = []
        self.stock_to_sector = {}  # 股票->板块映射
        self.sina_headlines = []  # 新浪财经头条缓存

    def connect_futu(self):
        """连接富途"""
        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            print("✅ 富途OpenD已连接", flush=True)
            return True
        except Exception as e:
            print(f"❌ 富途连接失败: {e}", flush=True)
            return False

    def load_watchlist(self):
        """加载自选股"""
        try:
            ret, data = self.quote_ctx.get_user_security('全部')
            if ret == RET_OK:
                self.watchlist = data['code'].tolist()
                print(f"✅ 已加载 {len(self.watchlist)} 只自选股", flush=True)

                # 建立股票->板块映射
                for sector, stocks in SECTOR_MAP.items():
                    for stock in stocks:
                        if stock in self.watchlist:
                            self.stock_to_sector[stock] = sector

                return True
            else:
                print(f"⚠️ 无法获取自选股，使用板块股票", flush=True)
                # 使用板块股票作为备选
                self.watchlist = []
                for sector, stocks in SECTOR_MAP.items():
                    self.watchlist.extend(stocks)
                    for stock in stocks:
                        self.stock_to_sector[stock] = sector
                return True
        except Exception as e:
            print(f"❌ 加载自选股失败: {e}", flush=True)
            return False

    def get_overnight_change(self, code):
        """获取隔夜涨跌幅"""
        try:
            ret, snapshot = self.quote_ctx.get_market_snapshot([code])
            if ret == RET_OK and not snapshot.empty:
                last_price = snapshot['last_price'].iloc[0]
                prev_close = snapshot['prev_close_price'].iloc[0]

                if prev_close > 0:
                    change_pct = ((last_price - prev_close) / prev_close * 100)
                    return {
                        'code': code,
                        'last_price': last_price,
                        'prev_close': prev_close,
                        'change_pct': change_pct
                    }
            return None
        except Exception as e:
            return None

    def fetch_sina_headlines(self):
        """
        获取新浪财经头条（一次性获取，全局缓存）
        """
        if self.sina_headlines:
            return  # 已缓存

        try:
            url = "https://feed.mix.sina.com.cn/api/roll/get"
            params = {
                'pageid': '153',
                'lid': '2509',
                'num': 30,
                'versionNumber': '1.2.8',
                'page': 1,
                'encode': 'utf-8'
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://finance.sina.com.cn/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'result' in data and 'data' in data['result']:
                    for item in data['result']['data']:
                        title = item.get('title', '').strip()
                        if title and len(title) > 5:
                            self.sina_headlines.append({
                                'title': title,
                                'source': '新浪财经',
                                'time': item.get('intime', '')
                            })
        except Exception as e:
            print(f"⚠️ 新浪财经抓取失败: {e}", flush=True)

    def get_stock_news(self, stock_code, stock_name):
        """
        获取个股最新资讯 - 新浪财经版
        1. 从新浪财经头条中匹配相关新闻
        2. 如果找不到，从价格分析生成提示
        """
        news_list = []

        # 在新浪财经头条中查找相关新闻
        # 去掉HK.前缀，只用数字搜索
        search_key = stock_code.replace('HK.', '').replace('US.', '').lstrip('0')

        # 也尝试用股票名称搜索
        for headline in self.sina_headlines:
            title = headline['title']
            # 如果标题包含股票代码或名称
            if search_key in title or stock_name in title:
                news_list.append(headline)
                if len(news_list) >= 3:
                    break

        # 如果没找到相关新闻，生成智能提示
        if not news_list:
            change_data = self.get_overnight_change(stock_code)
            if change_data and abs(change_data['change_pct']) >= 5:
                change_pct = change_data['change_pct']
                if change_pct > 0:
                    news_list.append({
                        'title': f'隔夜大涨{change_pct:.1f}%，建议关注财经资讯',
                        'source': '价格监测',
                        'time': ''
                    })
                else:
                    news_list.append({
                        'title': f'隔夜大跌{abs(change_pct):.1f}%，关注是否有利空消息',
                        'source': '价格监测',
                        'time': ''
                    })
            else:
                # 即使没有相关新闻，也不显示"暂无"，保持简洁
                pass

        return news_list

    def analyze_sentiment(self, stock_code, stock_name, news_list, change_pct):
        """
        AI分析个股情绪
        1. 基于新闻标题关键词
        2. 基于价格异动幅度
        3. 基于板块热度
        返回: (sentiment, score, reasons)
        """
        # 合并所有新闻标题
        text = " ".join([news['title'] for news in news_list])

        # 统计利好关键词
        positive_score = 0
        positive_reasons = []

        for category, keywords in POSITIVE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    positive_score += 1
                    positive_reasons.append(f"{kw}")

        # 统计利空关键词
        negative_score = 0
        negative_reasons = []

        for category, keywords in NEGATIVE_KEYWORDS.items():
            for kw in keywords:
                if kw in text:
                    negative_score += 1
                    negative_reasons.append(f"{kw}")

        # 基于价格异动的智能判断
        if abs(change_pct) >= 10:
            if change_pct > 0:
                positive_score += 2
                positive_reasons.append(f"隔夜大涨{change_pct:.1f}%")
            else:
                negative_score += 2
                negative_reasons.append(f"隔夜大跌{abs(change_pct):.1f}%")
        elif abs(change_pct) >= 5:
            if change_pct > 0:
                positive_score += 1
                positive_reasons.append(f"强势上涨")
            else:
                negative_score += 1
                negative_reasons.append(f"明显下跌")

        # 板块加成
        if stock_code in self.stock_to_sector:
            sector = self.stock_to_sector[stock_code]
            # 热门板块加分
            if sector in ["人形机器人", "AI大模型", "GPU芯片"]:
                positive_score += 1
                positive_reasons.append(f"{sector}热门板块")
            else:
                positive_reasons.append(f"{sector}板块")

        # 判断最终情绪
        if positive_score > negative_score:
            sentiment = "🟢 利好"
            reasons = positive_reasons[:3]  # 最多3个
        elif negative_score > positive_score:
            sentiment = "🔴 利空"
            reasons = negative_reasons[:3]
        else:
            sentiment = "⚪ 中性"
            # 中性也显示一些信息
            if stock_code in self.stock_to_sector:
                reasons = [self.stock_to_sector[stock_code] + "板块"]
            else:
                reasons = []

        return sentiment, positive_score + negative_score, reasons

    def scan_premarket(self):
        """盘前扫描"""
        print(f"\n{'='*60}", flush=True)
        print(f"📊 盘前资讯扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M')}", flush=True)
        print(f"{'='*60}\n", flush=True)

        # 先获取新浪财经头条（一次性）
        print("📰 获取新浪财经最新资讯...", flush=True)
        self.fetch_sina_headlines()
        if self.sina_headlines:
            print(f"✅ 已获取 {len(self.sina_headlines)} 条财经新闻\n", flush=True)
        else:
            print("⚠️ 未获取到财经新闻\n", flush=True)

        important_signals = []

        # 扫描自选股（限制前50只）
        scan_count = min(50, len(self.watchlist))

        for i, code in enumerate(self.watchlist[:scan_count], 1):
            print(f"[{i}/{scan_count}] 扫描 {code}...", flush=True)

            # 获取隔夜变化
            change_data = self.get_overnight_change(code)

            if change_data:
                change_pct = change_data['change_pct']

                # 判断是否重要信号
                if abs(change_pct) >= 3:  # 涨跌幅≥3%
                    emoji = "🔴" if change_pct < 0 else "🟢"
                    stock_name = code.replace('HK.', '')

                    # 获取新闻资讯
                    print(f"  📰 抓取资讯...", flush=True)
                    news_list = self.get_stock_news(code, stock_name)

                    # AI情绪分析（传入价格变化）
                    sentiment, score, reasons = self.analyze_sentiment(code, stock_name, news_list, change_pct)

                    signal = {
                        'code': code,
                        'name': stock_name,
                        'change_pct': change_pct,
                        'price': change_data['last_price'],
                        'sector': self.stock_to_sector.get(code, '未分类'),
                        'emoji': emoji,
                        'news': news_list,
                        'sentiment': sentiment,
                        'sentiment_reasons': reasons
                    }

                    important_signals.append(signal)

                    print(f"  {emoji} 隔夜变化: {change_pct:+.2f}% | {sentiment} | 板块: {signal['sector']}", flush=True)
                    if reasons:
                        print(f"     原因: {', '.join(reasons)}", flush=True)

            time.sleep(0.3)  # 稍微延长，因为要抓取新闻

        return important_signals

    def send_telegram(self, message):
        """发送Telegram消息"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return False

        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram推送失败: {e}", flush=True)
            return False

    def generate_report(self, signals):
        """生成盘前报告（包含资讯和情绪）"""
        # 按涨跌幅排序
        if signals:
            signals.sort(key=lambda x: abs(x['change_pct']), reverse=True)

        print(f"\n{'='*60}", flush=True)
        if signals:
            print("🚨 发现重要信号！", flush=True)
        else:
            print("📊 盘前扫描结果", flush=True)
        print(f"{'='*60}\n", flush=True)

        # 分类统计
        up_signals = [s for s in signals if s['change_pct'] > 0]
        down_signals = [s for s in signals if s['change_pct'] < 0]

        report = f"*📊 盘前资讯扫描报告*\n"
        report += f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"

        # 添加今日财经要闻（前5条）
        if self.sina_headlines:
            report += f"*📰 今日财经要闻*\n\n"
            for i, news in enumerate(self.sina_headlines[:5], 1):
                # 只显示时间（去掉日期）
                time_str = news['time']
                if isinstance(time_str, str) and len(time_str) > 10:
                    # 时间戳转时间
                    try:
                        import time as time_module
                        dt = datetime.fromtimestamp(int(time_str))
                        time_display = dt.strftime('%H:%M')
                    except:
                        time_display = ''
                else:
                    time_display = ''

                if time_display:
                    report += f"{i}. [{time_display}] {news['title'][:60]}...\n"
                else:
                    report += f"{i}. {news['title'][:60]}...\n"
            report += "\n"

        if not signals:
            report += "✅ 暂无重要异动信号（涨跌<3%）\n"
            print(report)
            return report

        # 上涨个股（含资讯和情绪）
        if up_signals:
            report += f"🟢 *隔夜上涨* ({len(up_signals)}只)\n\n"
            for i, s in enumerate(up_signals[:5], 1):  # 前5只
                report += f"*{i}. {s['name']} {s['change_pct']:+.2f}%*\n"
                report += f"   {s['sentiment']}"

                # 添加情绪原因
                if s.get('sentiment_reasons'):
                    reasons_str = ", ".join(s['sentiment_reasons'][:2])
                    report += f" ({reasons_str})"
                report += f"\n"

                # 添加最新资讯
                if s.get('news') and len(s['news']) > 0:
                    news = s['news'][0]  # 第一条
                    if '暂无' not in news['title']:
                        report += f"   📰 {news['title'][:40]}...\n"

                report += "\n"

        # 下跌个股（含资讯和情绪）
        if down_signals:
            report += f"🔴 *隔夜下跌* ({len(down_signals)}只)\n\n"
            for i, s in enumerate(down_signals[:3], 1):  # 前3只
                report += f"*{i}. {s['name']} {s['change_pct']:+.2f}%*\n"
                report += f"   {s['sentiment']}"

                # 添加情绪原因
                if s.get('sentiment_reasons'):
                    reasons_str = ", ".join(s['sentiment_reasons'][:2])
                    report += f" ({reasons_str})"
                report += f"\n"

                # 添加最新资讯
                if s.get('news') and len(s['news']) > 0:
                    news = s['news'][0]
                    if '暂无' not in news['title']:
                        report += f"   📰 {news['title'][:40]}...\n"

                report += "\n"

        # 板块统计
        sector_counts = defaultdict(list)
        for s in signals:
            sector_counts[s['sector']].append(s)

        if len(sector_counts) > 0:
            report += f"📈 *活跃板块*\n"
            for sector, stocks in sorted(sector_counts.items(), key=lambda x: len(x[1]), reverse=True)[:3]:
                avg_change = sum(st['change_pct'] for st in stocks) / len(stocks)
                report += f"• {sector}: {len(stocks)}只 (均涨{avg_change:+.1f}%)\n"

        # 控制台输出
        for s in signals:
            print(f"{s['emoji']} {s['name']:<8} {s['change_pct']:+6.2f}%  {s['sentiment']} ({s['sector']})", flush=True)
            if s.get('sentiment_reasons'):
                print(f"   原因: {', '.join(s['sentiment_reasons'])}", flush=True)

        return report

    def close(self):
        """关闭连接"""
        if self.quote_ctx:
            self.quote_ctx.close()

def main():
    print("\n" + "="*60, flush=True)
    print("🌅 盘前资讯扫描器 v3.0 - 新浪财经版", flush=True)
    print("="*60, flush=True)
    print("功能: 盘前扫描 + 新浪财经要闻 + 情绪分析", flush=True)
    print("时间: 08:30执行", flush=True)
    print("="*60 + "\n", flush=True)

    # 检查是否交易日（周一到周五）
    now = datetime.now()
    if now.weekday() >= 5:  # 周六(5)或周日(6)
        print(f"💤 今天是周末，跳过扫描", flush=True)
        return

    print(f"✅ 交易日 - 开始扫描（新浪财经 + 价格分析）", flush=True)

    scanner = PremarketScanner()

    if not scanner.connect_futu():
        print("❌ 无法连接富途，程序退出", flush=True)
        return

    if not scanner.load_watchlist():
        print("❌ 无法加载自选股，程序退出", flush=True)
        return

    # 执行扫描
    signals = scanner.scan_premarket()

    # 生成报告
    report = scanner.generate_report(signals)

    # 推送Telegram
    if report:
        print("\n📱 推送Telegram...", flush=True)
        if scanner.send_telegram(report):
            print("✅ 推送成功", flush=True)
        else:
            print("⚠️ 推送失败", flush=True)

    scanner.close()
    print("\n✅ 盘前扫描完成\n", flush=True)

if __name__ == '__main__':
    main()
