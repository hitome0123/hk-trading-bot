#!/usr/bin/env python3
"""
测试盘前扫描器 v3.0 - 强制执行版
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

# 导入主程序
from premarket_news_scanner import PremarketScanner

print("\n" + "="*60)
print("🧪 测试盘前扫描器 v3.0")
print("="*60 + "\n")

scanner = PremarketScanner()

# 1. 连接富途
if not scanner.connect_futu():
    print("❌ 无法连接富途")
    exit(1)

# 2. 加载自选股
if not scanner.load_watchlist():
    print("❌ 无法加载自选股")
    exit(1)

# 3. 执行扫描
print(f"\n✅ 强制执行扫描（测试模式）\n")
signals = scanner.scan_premarket()

# 4. 生成报告
report = scanner.generate_report(signals)

# 5. 显示报告
if report:
    print("\n" + "="*60)
    print("📱 Telegram推送预览")
    print("="*60 + "\n")
    print(report)

scanner.close()
print("\n✅ 测试完成\n")
