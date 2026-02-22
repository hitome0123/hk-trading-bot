#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试T+0监控系统"""

from kuaishou_t0_monitor import KuaishouT0Monitor

monitor = KuaishouT0Monitor()

# 获取一次数据并显示
price_data = monitor.get_realtime_price()
if price_data:
    monitor.display_status(price_data)
else:
    print("❌ 无法获取数据")

monitor.quote_ctx.close()
