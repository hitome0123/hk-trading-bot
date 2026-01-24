#!/usr/bin/env python3
"""
盘中异动监控 - 实时监控快速拉升股 + 板块异动
增强版：集成板块扫描，不再错过商业航天等热点
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from hk_trading_bot.data_providers.futu_provider import FutuProvider
import futu as ft
from datetime import datetime
import time

# 监控股票池（可自定义添加）
WATCH_LIST = [
    # 商业航天 - 重点监控!!!
    ('HK.01045', '亚太卫星'),
    ('HK.02865', '钧达股份'),
    ('HK.00031', '航天控股'),
    ('HK.02357', '中航科工'),
    ('HK.02382', '蓝思科技'),
    ('HK.01725', '中国技术'),
    ('HK.02208', '金风科技'),
    # 芯片
    ('HK.00981', '中芯国际'),
    ('HK.01347', '华虹半导体'),
    # AI/科技
    ('HK.09988', '阿里巴巴'),
    ('HK.00700', '腾讯'),
    ('HK.09618', '京东'),
    ('HK.01024', '快手'),
    ('HK.03690', '美团'),
    ('HK.01810', '小米'),
    ('HK.09888', '百度'),
    ('HK.00020', '商汤'),
    # 新能源
    ('HK.02015', '理想汽车'),
    ('HK.09868', '小鹏汽车'),
    ('HK.09866', '蔚来'),
    ('HK.01211', '比亚迪'),
    # 光伏
    ('HK.03800', '协鑫科技'),
    ('HK.00968', '信义光能'),
    # 你的持仓
    ('HK.00386', '中石化'),
    ('HK.06082', '壁仞科技'),
]

# 预警阈值
ALERT_THRESHOLD = 3.0  # 涨跌幅超过3%提醒
VOL_THRESHOLD = 2.0    # 量比超过2提醒
SECTOR_SCAN_INTERVAL = 60   # 板块扫描间隔(秒) - 每分钟
NEWS_SCAN_INTERVAL = 60     # 新闻扫描间隔(秒) - 每分钟
MARKET_SCAN_INTERVAL = 120  # 全市场扫描间隔(秒) - 每2分钟


def scan_sectors(provider) -> list:
    """扫描板块异动"""
    from hk_sector_scanner import HKSectorScanner
    scanner = HKSectorScanner()
    scanner.provider = provider
    scanner.connected = True

    alerts = []
    try:
        explosive = scanner.find_explosive_sectors(threshold=4.0)
        for s in explosive:
            alerts.append({
                'type': 'sector',
                'name': s['name'],
                'change': s['avg_change'],
                'leader': s['leader']['name'],
                'leader_chg': s['leader']['change_pct'],
                'is_hot': s['is_hot'],
            })
    except Exception as e:
        print(f"板块扫描异常: {e}")

    return alerts


def scan_news() -> list:
    """扫描新闻热点"""
    from news_tracker import NewsTracker
    tracker = NewsTracker()

    alerts = []
    try:
        hot_news = tracker.get_high_priority_alerts()
        for n in hot_news:
            alerts.append({
                'type': 'news',
                'title': n['news']['title'][:40],
                'source': n['news']['source'],
                'sectors': n['sectors'],
                'stocks': n['stocks'],
                'priority': n['alert_level'],
            })
    except Exception as e:
        print(f"新闻扫描异常: {e}")

    return alerts


def smart_pick_stocks(sector_name: str, provider) -> list:
    """智能选股 - 从指定板块选出最佳股票"""
    from smart_picker import SmartPicker

    picker = SmartPicker()
    picker.provider = provider  # 复用连接

    picks = []
    try:
        results = picker.pick_from_sector(sector_name, top_n=2)
        for r in results:
            if r['total_score'] >= 50:  # 只推荐50分以上的
                picks.append({
                    'code': r['code'],
                    'name': r['name'],
                    'price': r['price'],
                    'change_pct': r['change_pct'],
                    'score': r['total_score'],
                    'recommendation': r['recommendation'],
                    'heat_level': r['heat']['heat_level'],
                })
    except Exception as e:
        print(f"智能选股异常: {e}")

    return picks


def scan_full_market() -> list:
    """全市场扫描 - 发现任何板块异动"""
    from market_scanner import MarketScanner
    scanner = MarketScanner()

    alerts = []
    try:
        result = scanner.scan_full_market()
        for a in result.get('alerts', []):
            alerts.append({
                'type': 'market',
                'name': a['name'],
                'change': a['change'],
                'count': a['count'],
                'leader_name': a['leader']['name'],
                'leader_code': a['leader']['code'],
                'leader_change': a['leader']['change_pct'],
                'level': a['level'],
            })
    except Exception as e:
        print(f"全市场扫描异常: {e}")

    return alerts


def monitor():
    """实时监控 - 个股 + 板块 + 新闻 + 钉钉推送"""
    provider = FutuProvider()
    provider.connect()

    # 初始化钉钉推送
    from dingtalk_notifier import DingTalkNotifier
    notifier = DingTalkNotifier()
    has_dingtalk = bool(notifier.webhook_url)

    print("=" * 65)
    print(f"🔔 港股全方位监控启动 (增强版v3)")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"📊 个股监控: {len(WATCH_LIST)} 只 (每20秒)")
    print(f"📈 预设板块: 每{SECTOR_SCAN_INTERVAL}秒")
    print(f"🌐 全市场扫描: 每{MARKET_SCAN_INTERVAL}秒 (发现新板块)")
    print(f"📰 新闻追踪: 每{NEWS_SCAN_INTERVAL}秒")
    print(f"📱 钉钉推送: {'✅ 已启用' if has_dingtalk else '❌ 未配置 (运行 python dingtalk_notifier.py setup)'}")
    print(f"⚠️ 预警条件: 涨跌>{ALERT_THRESHOLD}% / 板块>4% / 重要新闻")
    print("=" * 65)

    last_sector_scan = 0
    last_news_scan = 0
    last_market_scan = 0
    notified_sectors = set()
    notified_news = set()
    notified_industries = set()  # 全市场发现的行业

    try:
        while True:
            stock_alerts = []
            current_time = time.time()

            # 1. 个股异动扫描
            for code, name in WATCH_LIST:
                try:
                    ret, quote = provider.quote_ctx.get_stock_quote([code])
                    if ret != ft.RET_OK or quote.empty:
                        continue

                    row = quote.iloc[0]
                    price = row['last_price']
                    prev = row['prev_close_price']

                    if price <= 0 or prev <= 0:
                        continue

                    chg = (price - prev) / prev * 100

                    if abs(chg) >= ALERT_THRESHOLD:
                        stock_alerts.append({
                            'name': name, 'code': code,
                            'price': price, 'chg': chg,
                            'type': '涨幅' if chg > 0 else '跌幅'
                        })

                except Exception as e:
                    continue

            # 输出个股预警
            if stock_alerts:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"\n{'='*55}")
                print(f"🚨 [{now}] 个股异动预警!")
                print(f"{'='*55}")
                for a in stock_alerts:
                    icon = "🔴" if a['chg'] < 0 else "🟢"
                    print(f"{icon} {a['name']} {a['price']:.2f} {a['chg']:+.1f}% ← {a['type']}异动!")

                    # 钉钉推送
                    if has_dingtalk:
                        notifier.notify_stock_alert(a['name'], a['code'], a['price'], a['chg'], a['type'])

            # 2. 定期板块扫描
            if current_time - last_sector_scan >= SECTOR_SCAN_INTERVAL:
                print(f"\n🔍 扫描板块异动...")
                sector_alerts = scan_sectors(provider)

                new_sectors = [s for s in sector_alerts if s['name'] not in notified_sectors]

                if new_sectors:
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"\n{'='*55}")
                    print(f"🔥 [{now}] 板块暴涨预警!")
                    print(f"{'='*55}")
                    for s in new_sectors:
                        hot = "🌟" if s['is_hot'] else ""
                        print(f"📈 {s['name']}{hot}: +{s['change']:.2f}% | 领涨: {s['leader']} +{s['leader_chg']:.1f}%")
                        notified_sectors.add(s['name'])

                        # 钉钉推送板块预警
                        if has_dingtalk:
                            notifier.notify_sector_alert(s['name'], s['change'], s['leader'], s['leader_chg'], s['is_hot'])

                        # 🎯 自动智能选股
                        if s['is_hot'] and s['change'] >= 4.0:
                            print(f"\n🎯 智能选股: {s['name']}")
                            picks = smart_pick_stocks(s['name'], provider)
                            if picks:
                                print(f"{'─'*55}")
                                for p in picks:
                                    print(f"   ⭐ {p['name']} ({p['code']}) "
                                          f"现价:{p['price']:.2f} "
                                          f"涨幅:{p['change_pct']:+.1f}% "
                                          f"评分:{p['score']:.0f}")
                                    print(f"      {p['heat_level']} | {p['recommendation']}")

                                # 钉钉推送选股推荐
                                if has_dingtalk:
                                    notifier.notify_stock_pick(s['name'], picks)
                else:
                    print(f"   暂无新的暴涨板块")

                last_sector_scan = current_time

            # 3. 定期新闻扫描
            if current_time - last_news_scan >= NEWS_SCAN_INTERVAL:
                print(f"\n📰 扫描新闻热点...")
                news_alerts = scan_news()

                new_news = [n for n in news_alerts if n['title'] not in notified_news]

                if new_news:
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"\n{'='*55}")
                    print(f"📰 [{now}] 新闻热点预警!")
                    print(f"{'='*55}")
                    for n in new_news[:3]:
                        level = "🔴" if n['priority'] == 'HIGH' else "🟡"
                        print(f"{level} {n['title']}")
                        print(f"   板块: {', '.join(n['sectors'][:2])} | 关注: {', '.join(n['stocks'][:3])}")
                        notified_news.add(n['title'])

                        # 钉钉推送新闻预警（只推送高优先级）
                        if has_dingtalk and n['priority'] == 'HIGH':
                            notifier.notify_news_alert(n['title'], n['source'], n['sectors'], n['stocks'])
                else:
                    print(f"   暂无新热点新闻")

                last_news_scan = current_time

            # 4. 全市场扫描（发现新板块）
            if current_time - last_market_scan >= MARKET_SCAN_INTERVAL:
                print(f"\n🌐 全市场扫描...")
                market_alerts = scan_full_market()

                # 过滤已通知的行业
                new_industries = [a for a in market_alerts if a['name'] not in notified_industries]

                if new_industries:
                    now = datetime.now().strftime('%H:%M:%S')
                    print(f"\n{'='*55}")
                    print(f"🌐 [{now}] 发现新热点板块!")
                    print(f"{'='*55}")
                    for a in new_industries[:3]:
                        level = "🔴" if a['level'] == 'HIGH' else "🟡"
                        print(f"{level} {a['name']}: +{a['change']:.2f}% ({a['count']}只)")
                        print(f"   └─ 领涨: {a['leader_name']} ({a['leader_code']}) +{a['leader_change']:.2f}%")
                        notified_industries.add(a['name'])

                        # 钉钉推送
                        if has_dingtalk:
                            notifier.notify_sector_alert(
                                a['name'], a['change'],
                                a['leader_name'], a['leader_change'],
                                is_hot=True
                            )
                else:
                    print(f"   暂无新热点板块")

                last_market_scan = current_time

            if not stock_alerts:
                now = datetime.now().strftime('%H:%M:%S')
                print(f"[{now}] 监控中... 暂无异动", end='\r')

            time.sleep(20)  # 每20秒循环一次，更快响应

    except KeyboardInterrupt:
        print("\n\n监控已停止")
    finally:
        provider.disconnect()

if __name__ == "__main__":
    monitor()
