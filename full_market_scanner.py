#!/usr/bin/env python3
"""
港股全市场异动扫描器
扫描所有港股，找出涨跌幅异动股
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from hk_trading_bot.data_providers.futu_provider import FutuProvider
import futu as ft
from datetime import datetime
import time

# 预警阈值
ALERT_THRESHOLD = 5.0  # 涨跌幅超过5%
MIN_PRICE = 1.0        # 最低股价（过滤仙股）
MIN_TURNOVER = 1000000 # 最低成交额100万

def get_all_hk_stocks(provider):
    """获取所有港股代码"""
    ret, data = provider.quote_ctx.get_stock_basicinfo(ft.Market.HK, ft.SecurityType.STOCK)
    if ret == ft.RET_OK:
        return data['code'].tolist()
    return []

def scan_market(provider, stock_codes, batch_size=100):
    """批量扫描市场"""
    alerts = []
    total = len(stock_codes)
    
    for i in range(0, total, batch_size):
        batch = stock_codes[i:i+batch_size]
        
        try:
            ret, quotes = provider.quote_ctx.get_stock_quote(batch)
            if ret != ft.RET_OK:
                continue
            
            for _, row in quotes.iterrows():
                try:
                    price = row['last_price']
                    prev = row['prev_close_price']
                    turnover = row.get('turnover', 0)
                    name = row.get('name', row['code'])
                    code = row['code']
                    
                    # 过滤
                    if price < MIN_PRICE or prev <= 0:
                        continue
                    if turnover < MIN_TURNOVER:
                        continue
                    
                    chg = (price - prev) / prev * 100
                    
                    if abs(chg) >= ALERT_THRESHOLD:
                        alerts.append({
                            'code': code,
                            'name': name,
                            'price': price,
                            'chg': chg,
                            'turnover': turnover
                        })
                except:
                    continue
                    
        except Exception as e:
            continue
        
        # 进度
        progress = min(i + batch_size, total)
        print(f"\r扫描进度: {progress}/{total} ({progress*100//total}%)", end='', flush=True)
    
    print()
    return alerts

def main():
    provider = FutuProvider()
    provider.connect()
    
    print("=" * 65)
    print(f"🔍 港股全市场异动扫描")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⚠️ 筛选条件: 涨跌>{ALERT_THRESHOLD}% 股价>{MIN_PRICE} 成交额>100万")
    print("=" * 65)
    
    # 获取股票列表
    print("\n📋 获取港股列表...")
    stocks = get_all_hk_stocks(provider)
    print(f"✅ 共 {len(stocks)} 只股票待扫描\n")
    
    # 扫描
    print("🔍 开始扫描...\n")
    alerts = scan_market(provider, stocks)
    
    # 排序输出
    alerts.sort(key=lambda x: -x['chg'])
    
    print("\n" + "=" * 65)
    print(f"🔥 异动股票 (共{len(alerts)}只)")
    print("=" * 65)
    
    # 涨幅榜
    gainers = [a for a in alerts if a['chg'] > 0]
    if gainers:
        print(f"\n📈 涨幅榜 TOP10:")
        print(f"{'股票':<15} {'现价':>8} {'涨幅':>8} {'成交额(万)':>10}")
        print("-" * 50)
        for a in gainers[:10]:
            print(f"{a['name']:<12} {a['price']:>8.2f} {a['chg']:>+7.1f}% {a['turnover']/10000:>10.0f}")
    
    # 跌幅榜
    losers = [a for a in alerts if a['chg'] < 0]
    losers.sort(key=lambda x: x['chg'])
    if losers:
        print(f"\n📉 跌幅榜 TOP10:")
        print(f"{'股票':<15} {'现价':>8} {'跌幅':>8} {'成交额(万)':>10}")
        print("-" * 50)
        for a in losers[:10]:
            print(f"{a['name']:<12} {a['price']:>8.2f} {a['chg']:>+7.1f}% {a['turnover']/10000:>10.0f}")
    
    print("\n" + "=" * 65)
    provider.disconnect()

if __name__ == "__main__":
    main()
