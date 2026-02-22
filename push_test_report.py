#!/usr/bin/env python3
"""
立即推送测试报告到Telegram
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from premarket_news_scanner import PremarketScanner

print("\n" + "="*60)
print("📱 推送盘前报告到Telegram")
print("="*60 + "\n")

scanner = PremarketScanner()

if not scanner.connect_futu():
    print("❌ 无法连接富途")
    exit(1)

if not scanner.load_watchlist():
    print("❌ 无法加载自选股")
    exit(1)

# 执行扫描
signals = scanner.scan_premarket()

# 生成报告
report = scanner.generate_report(signals)

# 推送到Telegram
if report:
    print("\n📱 推送Telegram...")
    if scanner.send_telegram(report):
        print("✅ 推送成功！请检查你的Telegram")
    else:
        print("⚠️ 推送失败")
        print("\n报告预览:")
        print(report)
else:
    print("⚠️ 未生成报告")

scanner.close()
print("\n✅ 完成\n")
