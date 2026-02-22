#!/usr/bin/env python3
"""
测试真实资讯抓取功能
"""
from real_news_fetcher import RealNewsFetcher
import sys

def test_news_fetcher():
    print("\n" + "="*60)
    print("🧪 测试真实资讯抓取")
    print("="*60 + "\n")

    # 初始化
    fetcher = RealNewsFetcher('news_config.json')

    # 测试股票列表（你的热门股）
    test_stocks = [
        ('HK.09880', '优必选'),
        ('HK.02432', '天弘基金'),
        ('HK.02513', '智谱'),
        ('HK.00100', 'MiniMax')
    ]

    print("📋 配置状态:")
    print(f"  • 股吧 (东方财富): {'✅ 已启用' if fetcher.config.get('eastmoney', {}).get('enabled', True) else '❌ 未启用'}")
    print(f"  • 雪球: {'✅ 已启用' if fetcher.config.get('xueqiu', {}).get('enabled') else '❌ 未启用 (需配置cookie)'}")
    print(f"  • 淘股吧: ⏸️  暂时禁用")
    print(f"  • 富途公告: {'✅ 已启用' if fetcher.config.get('futu', {}).get('enabled', True) else '❌ 未启用'}")
    print()

    for code, name in test_stocks:
        print(f"\n{'='*60}")
        print(f"📊 测试: {name} ({code})")
        print(f"{'='*60}\n")

        # 1. 测试股吧
        print("🔍 抓取股吧...")
        guba_news = fetcher.fetch_guba_posts(code, limit=3)
        if guba_news:
            print(f"✅ 找到 {len(guba_news)} 条股吧帖子:")
            for i, news in enumerate(guba_news, 1):
                print(f"  {i}. {news['title'][:60]}...")
                if news.get('time'):
                    print(f"     时间: {news['time']}")
        else:
            print("⚠️ 未找到股吧内容")

        print()

        # 2. 测试雪球
        if fetcher.config.get('xueqiu', {}).get('enabled'):
            print("🔍 抓取雪球...")
            xueqiu_news = fetcher.fetch_xueqiu_posts(code, limit=3)
            if xueqiu_news:
                print(f"✅ 找到 {len(xueqiu_news)} 条雪球讨论:")
                for i, news in enumerate(xueqiu_news, 1):
                    author = news.get('author', '匿名')
                    print(f"  {i}. [{author}] {news['title'][:60]}...")
                    if news.get('time'):
                        print(f"     时间: {news['time']}")
            else:
                print("⚠️ 未找到雪球内容")
        else:
            print("⏸️  雪球未启用 (需配置cookie)")

        print()

        # 3. 综合结果
        print("🔍 综合抓取...")
        all_news = fetcher.fetch_all_news(code, name)
        print(f"\n📰 综合结果: {len(all_news)} 条资讯\n")

        if all_news:
            for i, news in enumerate(all_news[:5], 1):
                print(f"{i}. [{news['source']}] {news['title'][:70]}")
                if news.get('time'):
                    print(f"   {news['time']}")
                print()
        else:
            print("⚠️ 未抓取到任何资讯")

        print("-" * 60)

    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)
    print("\n💡 提示:")
    print("  • 如果股吧有内容 → 说明基础功能正常")
    print("  • 如果雪球没内容 → 需要配置 news_config.json 中的雪球cookie")
    print("  • 配置步骤:")
    print("    1. 复制 news_config_template.json 为 news_config.json")
    print("    2. 登录 https://xueqiu.com")
    print("    3. F12开发者工具 -> Network -> 复制Cookie")
    print("    4. 填入 news_config.json 的 xueqiu.cookie 字段")
    print("    5. 设置 xueqiu.enabled: true")
    print()


if __name__ == '__main__':
    test_news_fetcher()
