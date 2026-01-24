#!/usr/bin/env python3
"""
早盘扫描器 - 扫描异动股和重大公告
每天开盘前运行
"""
import sys
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from hk_trading_bot.data_providers.futu_provider import FutuProvider
import futu as ft
from datetime import datetime

# 监控股票池
WATCH_LIST = [
    # 航天板块
    ('HK.01045', '亚太卫星'),
    ('HK.02357', '中航科工'),
    # 芯片板块  
    ('HK.00981', '中芯国际'),
    ('HK.01347', '华虹半导体'),
    # 科技龙头
    ('HK.09988', '阿里巴巴'),
    ('HK.00700', '腾讯'),
    ('HK.09618', '京东'),
    ('HK.01024', '快手'),
    ('HK.03690', '美团'),
    ('HK.01810', '小米'),
    # 新能源车
    ('HK.02015', '理想汽车'),
    ('HK.09868', '小鹏汽车'),
    ('HK.09866', '蔚来'),
    ('HK.01211', '比亚迪'),
]

def scan_premarket():
    """扫描盘前异动"""
    provider = FutuProvider()
    provider.connect()
    
    print("=" * 60)
    print(f"🌅 早盘扫描 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    results = []
    
    for code, name in WATCH_LIST:
        try:
            ret, quote = provider.quote_ctx.get_stock_quote([code])
            if ret == ft.RET_OK and not quote.empty:
                row = quote.iloc[0]
                price = row['last_price']
                prev = row['prev_close_price']
                vol = row['volume']
                
                if price > 0 and prev > 0:
                    chg = (price - prev) / prev * 100
                    results.append({
                        'name': name, 'code': code, 
                        'price': price, 'chg': chg, 'vol': vol
                    })
        except:
            pass
    
    # 按涨跌幅排序
    results.sort(key=lambda x: -abs(x['chg']))
    
    print("\n📊 异动排行:\n")
    for r in results[:10]:
        icon = "🔴" if r['chg'] < 0 else "🟢"
        alert = "⚠️" if abs(r['chg']) > 3 else ""
        print(f"{icon} {r['name']:<10} {r['price']:>8.2f} {r['chg']:>+6.1f}% {alert}")
    
    # 找出大涨股
    hot = [r for r in results if r['chg'] > 3]
    if hot:
        print("\n🔥 涨幅>3% 关注:")
        for r in hot:
            print(f"   {r['name']} +{r['chg']:.1f}%")
    
    provider.disconnect()
    return results

if __name__ == "__main__":
    scan_premarket()
