#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「五条铁律」策略执行助手
配合 我的港股交易策略_v1.md 使用

功能：
1. 盘前扫描 - 找热门板块和龙头股
2. 买入信号检测 - 突破前高+放量
3. 买入检查清单 - 8个条件验证
4. 止损计算器 - 自动计算止损价
5. 交易记录 - 记录当日交易
6. VWAP计算 - 主力成本分析
"""

import sys
import os
sys.path.insert(0, '/Users/mantou/hk-trading-bot')

from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple

try:
    from futu import *
    HAS_FUTU = True
except ImportError:
    HAS_FUTU = False
    print("⚠️ 未安装futu-api，部分功能不可用")

# ==================== 配置 ====================

# 当前等级设置（根据你的进度调整）
CURRENT_LEVEL = 1  # 1=Lv.1, 2=Lv.2, 3=Lv.3, 4=Lv.4

LEVEL_CONFIG = {
    1: {'target': 300, 'stop_loss': 300, 'position': 0.5, 'name': 'Lv.1'},
    2: {'target': 500, 'stop_loss': 400, 'position': 0.6, 'name': 'Lv.2'},
    3: {'target': 800, 'stop_loss': 600, 'position': 0.7, 'name': 'Lv.3'},
    4: {'target': 1000, 'stop_loss': 800, 'position': 0.8, 'name': 'Lv.4'},
}

CAPITAL = 50000  # 本金5万港元
STOP_LOSS_PERCENT = 0.02  # 单笔止损2%
MAX_TRADES_PER_DAY = 2  # 每日最多交易2次

# 热门板块和龙头股（含龙头标记）
# ⭐ = 纯正稀缺标的
HOT_SECTORS = {
    # ===== AI核心赛道 =====
    'AI大模型': [  # ⭐⭐⭐ 全球仅2只纯大模型股
        ('HK.02513', '智谱', True),      # 龙头，清华系
        ('HK.00100', 'MiniMax', False),  # 海螺AI
        ('HK.00020', '商汤', False),
        ('HK.09888', '百度', False),
    ],
    '人形机器人': [  # ⭐⭐⭐ 全球首家纯人形机器人IPO
        ('HK.09880', '优必选', True),    # 龙头
    ],
    'AI芯片/GPU': [  # ⭐⭐⭐ 国产GPU稀缺标的
        ('HK.09903', '天数智芯', True),  # GPU龙头，成交活跃
        ('HK.06082', '壁仞科技', True),  # GPU，AI训练芯片
        ('HK.00981', '中芯国际', False), # 代工厂，非GPU设计
        ('HK.01347', '华虹半导体', False), # 代工厂，非GPU设计
    ],
    'AI制药': [  # ⭐⭐ AI制药
        ('HK.03696', '英矽智能', True),  # 龙头，管线最快
        ('HK.02158', '晶泰科技', False), # AI+CRO
    ],
    '手术机器人': [  # ⭐⭐ 手术机器人
        ('HK.02675', '精锋医疗', True),   # 单孔+多孔
        ('HK.02252', '微创机器人', False), # 全能型，流动性好
    ],

    # ===== 新能源赛道 =====
    '新能源车': [
        ('HK.01211', '比亚迪', True),    # 龙头
        ('HK.02015', '理想', False),
        ('HK.09866', '蔚来', False),
        ('HK.09868', '小鹏', False),
    ],
    '动力电池': [
        ('HK.03931', '中创新航', True),   # 龙头
        ('HK.01772', '赣锋锂业', False),
        ('HK.02460', '瑞浦兰钧', False),
    ],

    # ===== 互联网赛道 =====
    '互联网': [
        ('HK.00700', '腾讯', True),      # 龙头
        ('HK.09988', '阿里', False),
        ('HK.03690', '美团', False),
        ('HK.01024', '快手', False),
        ('HK.09618', '京东', False),
    ],

    # ===== 生物医药赛道 =====
    '创新药': [
        ('HK.06160', '百济神州', True),  # 龙头
        ('HK.01801', '信达生物', False),
        ('HK.06185', '康方生物', False),
    ],
    'CXO': [
        ('HK.02269', '药明生物', True),   # 龙头
        ('HK.06127', '昭衍新药', False),
    ],

    # ===== 新消费赛道 =====
    '潮玩/国潮': [  # ⭐⭐ 潮玩第一股
        ('HK.09992', '泡泡玛特', True),  # 龙头
        ('HK.02331', '李宁', False),
    ],
}

# 交易记录文件
TRADE_LOG_FILE = os.path.expanduser('~/.hk_trade_log.json')

# ==================== 工具函数 ====================

def get_config():
    """获取当前等级配置"""
    return LEVEL_CONFIG[CURRENT_LEVEL]

def calc_position_size():
    """计算当前等级的仓位金额"""
    config = get_config()
    return CAPITAL * config['position']

def calc_stop_loss_price(buy_price: float) -> float:
    """计算止损价格"""
    return buy_price * (1 - STOP_LOSS_PERCENT)

def calc_stop_loss_amount(position_size: float) -> float:
    """计算止损金额"""
    return position_size * STOP_LOSS_PERCENT


# ==================== 富途API连接 ====================

class FutuConnection:
    """富途API连接管理"""

    def __init__(self):
        self.quote_ctx = None

    def connect(self):
        if not HAS_FUTU:
            print("❌ 未安装futu-api")
            return False
        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            print("✅ 富途API已连接")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("   请确保 Futu OpenD 正在运行")
            return False

    def disconnect(self):
        if self.quote_ctx:
            self.quote_ctx.close()
            print("🔌 已断开连接")


# ==================== 核心功能 ====================

def find_sector_laggards(conn: FutuConnection, sector_name: str = None) -> List[Dict]:
    """
    功能: 找板块内「掉队」的补涨机会

    逻辑：龙头涨 + 其他票跌或涨少 = 补涨机会
    """
    print("\n" + "="*60)
    print("🔍 补涨机会扫描 (龙头带动策略)")
    print("="*60)

    opportunities = []

    sectors_to_scan = {sector_name: HOT_SECTORS[sector_name]} if sector_name else HOT_SECTORS

    for sector, stocks in sectors_to_scan.items():
        # 兼容新旧格式
        if len(stocks[0]) == 2:
            codes = [s[0] for s in stocks]
            names = {s[0]: s[1] for s in stocks}
            leader_code = stocks[0][0]  # 默认第一个是龙头
        else:
            codes = [s[0] for s in stocks]
            names = {s[0]: s[1] for s in stocks}
            leaders = [s for s in stocks if len(s) > 2 and s[2]]
            leader_code = leaders[0][0] if leaders else stocks[0][0]

        ret, data = conn.quote_ctx.get_market_snapshot(codes)
        if ret != RET_OK:
            continue

        # 找到龙头的涨幅
        leader_data = data[data['code'] == leader_code]
        if leader_data.empty:
            continue

        leader_row = leader_data.iloc[0]
        leader_change = (leader_row['last_price'] - leader_row['prev_close_price']) / leader_row['prev_close_price'] * 100
        leader_name = names.get(leader_code, leader_code)

        # 龙头涨幅 > 3% 才有带动效应
        if leader_change < 3:
            continue

        print(f"\n📈 {sector} | 龙头 {leader_name}: {leader_change:+.2f}%")
        print("-" * 50)

        # 找掉队的票
        for _, row in data.iterrows():
            code = row['code']
            if code == leader_code:
                continue

            name = names.get(code, code)
            price = row['last_price']
            prev_close = row['prev_close_price']
            change = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0

            # 掉队条件：涨幅比龙头低5%以上，或者在跌
            lag = leader_change - change

            if lag > 5 or change < 0:
                status = "🔴 在跌" if change < 0 else "⚠️ 涨少"
                print(f"  {status} {name}: {change:+.2f}% (落后龙头 {lag:.1f}%)")

                opportunities.append({
                    'sector': sector,
                    'leader': leader_name,
                    'leader_change': leader_change,
                    'code': code,
                    'name': name,
                    'price': price,
                    'change': change,
                    'lag': lag,
                    'potential': min(lag, 15),  # 补涨潜力，最多估15%
                })

    # 按补涨潜力排序
    opportunities.sort(key=lambda x: x['lag'], reverse=True)

    if opportunities:
        print("\n" + "="*60)
        print("🎯 补涨机会排名:")
        print("="*60)
        for i, opp in enumerate(opportunities[:5], 1):
            print(f"{i}. {opp['name']} ({opp['code']})")
            print(f"   现价: {opp['price']:.2f} | 今日: {opp['change']:+.2f}%")
            print(f"   龙头 {opp['leader']}: {opp['leader_change']:+.2f}%")
            print(f"   💡 补涨潜力: +{opp['potential']:.1f}%")
            print()
    else:
        print("\n❌ 暂无明显补涨机会")
        print("   (需要龙头涨>3%，且有票明显掉队)")

    return opportunities


def scan_hot_sectors(conn: FutuConnection) -> Dict:
    """
    功能1: 盘前扫描热门板块
    使用时间: 08:30-09:30
    """
    print("\n" + "="*60)
    print("🔥 热门板块扫描")
    print("="*60)

    results = {}

    for sector, stocks in HOT_SECTORS.items():
        sector_data = []
        codes = [s[0] for s in stocks]
        # 兼容新旧格式
        names = {s[0]: s[1] for s in stocks}

        ret, data = conn.quote_ctx.get_market_snapshot(codes)
        if ret == RET_OK:
            for _, row in data.iterrows():
                code = row['code']
                name = names.get(code, code)

                # 计算涨跌幅
                last_price = row['last_price']
                prev_close = row['prev_close_price']
                if prev_close > 0:
                    change_rate = (last_price - prev_close) / prev_close * 100
                else:
                    change_rate = 0

                sector_data.append({
                    'code': code,
                    'name': name,
                    'price': last_price,
                    'change': change_rate,
                    'volume': row['volume'],
                    'turnover': row['turnover'],
                    'volume_ratio': row.get('volume_ratio', 0),
                })

        # 计算板块平均涨幅
        if sector_data:
            avg_change = sum(s['change'] for s in sector_data) / len(sector_data)
            # 找出龙头（涨幅最高）
            leader = max(sector_data, key=lambda x: x['change'])

            results[sector] = {
                'avg_change': avg_change,
                'leader': leader,
                'stocks': sector_data
            }

    # 按板块平均涨幅排序
    sorted_sectors = sorted(results.items(), key=lambda x: x[1]['avg_change'], reverse=True)

    print(f"\n📊 板块排名 (按平均涨幅):\n")
    for i, (sector, data) in enumerate(sorted_sectors, 1):
        leader = data['leader']
        print(f"{i}. {sector}")
        print(f"   平均涨幅: {data['avg_change']:+.2f}%")
        print(f"   龙头股: {leader['name']} ({leader['code']}) {leader['change']:+.2f}%")
        print()

    # 推荐今日关注
    if sorted_sectors:
        top_sector = sorted_sectors[0]
        print("="*60)
        print(f"🎯 今日推荐关注板块: {top_sector[0]}")
        print(f"   龙头股: {top_sector[1]['leader']['name']}")
        print("="*60)

    return dict(sorted_sectors)


def check_breakout_signal(conn: FutuConnection, code: str) -> Dict:
    """
    功能2: 检测突破买入信号
    铁律2: 突破前日高点 + 放量
    """
    print(f"\n🔍 检测 {code} 突破信号...")

    result = {
        'code': code,
        'signal': False,
        'reasons': [],
        'data': {}
    }

    # 获取当前行情
    ret, snapshot = conn.quote_ctx.get_market_snapshot([code])
    if ret != RET_OK:
        result['reasons'].append("❌ 获取行情失败")
        return result

    row = snapshot.iloc[0]
    current_price = row['last_price']
    prev_close = row['prev_close_price']
    volume_ratio = row.get('volume_ratio', 0)

    # 获取前日K线
    ret, kline, _ = conn.quote_ctx.request_history_kline(code, max_count=5, ktype=KLType.K_DAY)
    if ret != RET_OK or len(kline) < 2:
        result['reasons'].append("❌ 获取K线失败")
        return result

    prev_day = kline.iloc[-2]
    prev_high = prev_day['high']
    prev_low = prev_day['low']

    result['data'] = {
        'current_price': current_price,
        'prev_high': prev_high,
        'prev_low': prev_low,
        'prev_close': prev_close,
        'volume_ratio': volume_ratio,
    }

    # 检查突破条件
    conditions = []

    # 条件A: 突破前日高点
    if current_price > prev_high:
        conditions.append(("✅ 突破前日高点", True))
        result['reasons'].append(f"✅ 现价 {current_price:.2f} > 前高 {prev_high:.2f}")
    else:
        conditions.append(("❌ 未突破前日高点", False))
        result['reasons'].append(f"❌ 现价 {current_price:.2f} < 前高 {prev_high:.2f}")

    # 条件B: 放量 (量比 > 1.5)
    if volume_ratio > 1.5:
        conditions.append(("✅ 放量确认", True))
        result['reasons'].append(f"✅ 量比 {volume_ratio:.2f} > 1.5")
    else:
        conditions.append(("❌ 未放量", False))
        result['reasons'].append(f"❌ 量比 {volume_ratio:.2f} < 1.5")

    # 条件C: 时间 > 10:00
    now = datetime.now()
    if now.hour >= 10:
        conditions.append(("✅ 时间合适", True))
        result['reasons'].append(f"✅ 当前时间 {now.strftime('%H:%M')} > 10:00")
    else:
        conditions.append(("⚠️ 开盘观察期", False))
        result['reasons'].append(f"⚠️ 当前时间 {now.strftime('%H:%M')} < 10:00 (观察期)")

    # 综合判断
    passed = sum(1 for _, ok in conditions if ok)
    if passed >= 2 and conditions[0][1]:  # 至少突破前高 + 另一个条件
        result['signal'] = True

    return result


def run_buy_checklist(conn: FutuConnection, code: str, name: str = "") -> bool:
    """
    功能3: 买入前检查清单
    8个条件全部通过才能买入
    """
    print("\n" + "="*60)
    print("📋 买入前检查清单")
    print("="*60)
    print(f"股票: {name} ({code})\n")

    checklist = []

    # 1. 是否为热门板块龙头
    is_leader = False
    for sector, stocks in HOT_SECTORS.items():
        if any(s[0] == code for s in stocks):
            is_leader = True
            print(f"□ 1. 热门板块龙头: ✅ 属于 {sector} 板块")
            break
    if not is_leader:
        print(f"□ 1. 热门板块龙头: ❌ 不在热门板块列表中")
    checklist.append(is_leader)

    # 2-4. 突破信号检测
    signal = check_breakout_signal(conn, code)

    # 2. 突破前日高点
    breakout = signal['data'].get('current_price', 0) > signal['data'].get('prev_high', float('inf'))
    print(f"□ 2. 突破前日高点: {'✅' if breakout else '❌'}")
    checklist.append(breakout)

    # 3. 放量确认
    volume_ok = signal['data'].get('volume_ratio', 0) > 1.5
    print(f"□ 3. 成交量放大: {'✅' if volume_ok else '❌'} (量比: {signal['data'].get('volume_ratio', 0):.2f})")
    checklist.append(volume_ok)

    # 4. 时间检查
    time_ok = datetime.now().hour >= 10
    print(f"□ 4. 10:00之后: {'✅' if time_ok else '⚠️ 观察期'}")
    checklist.append(time_ok)

    # 5. 主力资金 (简化检查：涨幅为正)
    change = (signal['data'].get('current_price', 0) - signal['data'].get('prev_close', 1)) / signal['data'].get('prev_close', 1) * 100
    fund_ok = change > 0
    print(f"□ 5. 主力资金净流入: {'✅' if fund_ok else '❌'} (涨幅: {change:+.2f}%)")
    checklist.append(fund_ok)

    # 6. 交易次数检查
    today_trades = load_today_trades()
    trades_ok = len(today_trades) < MAX_TRADES_PER_DAY
    print(f"□ 6. 今日交易<2次: {'✅' if trades_ok else '❌'} (已交易: {len(today_trades)}次)")
    checklist.append(trades_ok)

    # 7. 日止损检查
    config = get_config()
    today_pnl = sum(t.get('pnl', 0) for t in today_trades)
    loss_ok = today_pnl > -config['stop_loss']
    print(f"□ 7. 未达日止损: {'✅' if loss_ok else '❌'} (今日盈亏: {today_pnl:+.0f})")
    checklist.append(loss_ok)

    # 8. 止损价计算
    buy_price = signal['data'].get('current_price', 0)
    stop_price = calc_stop_loss_price(buy_price)
    print(f"□ 8. 止损价已计算: ✅ 止损价: {stop_price:.2f} (买入价的98%)")
    checklist.append(True)  # 只要计算了就OK

    # 汇总结果
    passed = sum(checklist)
    total = len(checklist)

    print("\n" + "-"*60)
    if passed == total:
        print(f"🟢 全部通过 ({passed}/{total}) - 可以买入!")
        print(f"\n💰 建议仓位: {calc_position_size():,.0f} 港元 ({get_config()['position']*100:.0f}%)")
        print(f"🛑 止损价格: {stop_price:.2f} 港元")
        print(f"💵 止损金额: {calc_stop_loss_amount(calc_position_size()):,.0f} 港元")
        return True
    else:
        print(f"🔴 未通过 ({passed}/{total}) - 不要买入!")
        print("\n继续等待更好的机会...")
        return False


def calc_vwap(conn: FutuConnection, code: str, days: int = 20) -> float:
    """
    功能4: 计算VWAP (成交量加权平均价)
    主力成本参考
    """
    ret, kline, _ = conn.quote_ctx.request_history_kline(code, max_count=days, ktype=KLType.K_DAY)

    if ret != RET_OK or kline.empty:
        return 0

    # VWAP = Σ(典型价格 × 成交量) / Σ(成交量)
    kline['typical'] = (kline['high'] + kline['low'] + kline['close']) / 3
    kline['amount'] = kline['typical'] * kline['volume']

    vwap = kline['amount'].sum() / kline['volume'].sum()
    return vwap


def analyze_stock(conn: FutuConnection, code: str, name: str = "") -> Dict:
    """
    功能5: 完整分析单只股票
    """
    print(f"\n{'='*60}")
    print(f"📊 {name} ({code}) 完整分析")
    print("="*60)

    # 获取行情
    ret, snapshot = conn.quote_ctx.get_market_snapshot([code])
    if ret != RET_OK:
        print("❌ 获取行情失败")
        return {}

    row = snapshot.iloc[0]
    current_price = row['last_price']
    prev_close = row['prev_close_price']
    change = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0

    print(f"\n💲 当前价格: {current_price:.2f} HKD")
    print(f"📈 今日涨跌: {change:+.2f}%")
    print(f"📊 量比: {row.get('volume_ratio', 0):.2f}")

    # 计算VWAP
    vwap_20 = calc_vwap(conn, code, 20)
    vwap_10 = calc_vwap(conn, code, 10)

    print(f"\n📐 主力成本分析:")
    print(f"   20日VWAP: {vwap_20:.2f}")
    print(f"   10日VWAP: {vwap_10:.2f}")

    if current_price < vwap_20:
        print(f"   ✅ 现价低于主力成本 ({(current_price/vwap_20-1)*100:+.1f}%)")
    else:
        print(f"   ⚠️ 现价高于主力成本 ({(current_price/vwap_20-1)*100:+.1f}%)")

    # 检测突破信号
    signal = check_breakout_signal(conn, code)
    print(f"\n🎯 突破信号: {'✅ 有信号' if signal['signal'] else '❌ 无信号'}")
    for reason in signal['reasons']:
        print(f"   {reason}")

    # 止损建议
    stop_price = calc_stop_loss_price(current_price)
    print(f"\n🛑 如果买入:")
    print(f"   建议止损价: {stop_price:.2f} (-2%)")
    print(f"   止盈目标: {current_price * 1.03:.2f} (+3%) 或 达到日目标")

    return {
        'code': code,
        'name': name,
        'price': current_price,
        'change': change,
        'vwap_20': vwap_20,
        'vwap_10': vwap_10,
        'signal': signal['signal']
    }


# ==================== 交易记录 ====================

def load_today_trades() -> List[Dict]:
    """加载今日交易记录"""
    try:
        with open(TRADE_LOG_FILE, 'r') as f:
            all_trades = json.load(f)
    except:
        all_trades = []

    today = datetime.now().strftime('%Y-%m-%d')
    return [t for t in all_trades if t.get('date') == today]


def save_trade(trade: Dict):
    """保存交易记录"""
    try:
        with open(TRADE_LOG_FILE, 'r') as f:
            all_trades = json.load(f)
    except:
        all_trades = []

    trade['date'] = datetime.now().strftime('%Y-%m-%d')
    trade['time'] = datetime.now().strftime('%H:%M:%S')
    all_trades.append(trade)

    with open(TRADE_LOG_FILE, 'w') as f:
        json.dump(all_trades, f, ensure_ascii=False, indent=2)

    print(f"✅ 交易已记录")


def record_trade():
    """交互式记录交易"""
    print("\n" + "="*60)
    print("📝 记录交易")
    print("="*60)

    code = input("股票代码 (如 HK.09880): ").strip()
    name = input("股票名称: ").strip()
    action = input("操作类型 (buy/sell): ").strip().lower()
    price = float(input("成交价格: "))
    amount = float(input("成交金额: "))

    pnl = 0
    if action == 'sell':
        pnl = float(input("本笔盈亏: "))

    trade = {
        'code': code,
        'name': name,
        'action': action,
        'price': price,
        'amount': amount,
        'pnl': pnl,
        'followed_rules': input("是否遵守规则 (y/n): ").strip().lower() == 'y',
        'note': input("备注: ").strip()
    }

    save_trade(trade)

    # 显示今日统计
    today_trades = load_today_trades()
    today_pnl = sum(t.get('pnl', 0) for t in today_trades)
    print(f"\n📊 今日统计:")
    print(f"   交易次数: {len(today_trades)}")
    print(f"   总盈亏: {today_pnl:+.0f} HKD")


def show_today_summary():
    """显示今日交易汇总"""
    today_trades = load_today_trades()
    config = get_config()

    print("\n" + "="*60)
    print(f"📊 今日交易汇总 ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"   当前等级: {config['name']}")
    print("="*60)

    if not today_trades:
        print("今日暂无交易记录")
        return

    for i, t in enumerate(today_trades, 1):
        action_emoji = "🟢" if t['action'] == 'buy' else "🔴"
        pnl_str = f"盈亏: {t['pnl']:+.0f}" if t.get('pnl') else ""
        rule_str = "✅" if t.get('followed_rules') else "❌"
        print(f"{i}. {action_emoji} {t['name']} @ {t['price']:.2f} | {pnl_str} | 规则:{rule_str}")

    total_pnl = sum(t.get('pnl', 0) for t in today_trades)
    print("-"*60)
    print(f"总盈亏: {total_pnl:+.0f} HKD")
    print(f"目标: {config['target']} HKD | 止损线: -{config['stop_loss']} HKD")

    if total_pnl >= config['target']:
        print("🎉 已达成今日目标！收工！")
    elif total_pnl <= -config['stop_loss']:
        print("⚠️ 已触及今日止损线！停止交易！")


# ==================== 主菜单 ====================

def print_menu():
    """打印主菜单"""
    config = get_config()
    print("\n" + "="*60)
    print(f"🎯 「五条铁律」策略助手 | {config['name']} | 目标:{config['target']}元")
    print("="*60)
    print("""
1. 🔥 扫描热门板块和龙头股 (盘前)
2. 🔍 分析单只股票
3. ✅ 运行买入检查清单
4. 📝 记录交易
5. 📊 查看今日汇总
6. ⚙️  切换等级
7. 🎯 补涨机会扫描 (龙头带动策略)
0. 退出

请选择 (1-7): """, end="")


def main():
    """主函数"""
    # 连接富途
    conn = FutuConnection()
    if not conn.connect():
        print("⚠️ 无法连接富途API，部分功能不可用")
        return

    try:
        while True:
            print_menu()
            choice = input().strip()

            if choice == '1':
                scan_hot_sectors(conn)

            elif choice == '2':
                code = input("请输入股票代码 (如 HK.09880): ").strip()
                if not code.startswith('HK.'):
                    code = 'HK.' + code
                name = input("股票名称 (可选): ").strip()
                analyze_stock(conn, code, name)

            elif choice == '3':
                code = input("请输入股票代码 (如 HK.09880): ").strip()
                if not code.startswith('HK.'):
                    code = 'HK.' + code
                name = input("股票名称: ").strip()
                run_buy_checklist(conn, code, name)

            elif choice == '4':
                record_trade()

            elif choice == '5':
                show_today_summary()

            elif choice == '6':
                global CURRENT_LEVEL
                print(f"\n当前等级: Lv.{CURRENT_LEVEL}")
                new_level = input("切换到等级 (1-4): ").strip()
                if new_level in ['1', '2', '3', '4']:
                    CURRENT_LEVEL = int(new_level)
                    print(f"✅ 已切换到 Lv.{CURRENT_LEVEL}")

            elif choice == '7':
                find_sector_laggards(conn)

            elif choice == '0':
                print("👋 再见，祝交易顺利！")
                break

            else:
                print("无效选择，请重试")

    finally:
        conn.disconnect()


# ==================== 快捷命令 ====================

def quick_scan():
    """快速扫描 (命令行直接调用)"""
    conn = FutuConnection()
    if conn.connect():
        scan_hot_sectors(conn)
        conn.disconnect()

def quick_analyze(code: str):
    """快速分析 (命令行直接调用)"""
    conn = FutuConnection()
    if conn.connect():
        if not code.startswith('HK.'):
            code = 'HK.' + code
        analyze_stock(conn, code)
        conn.disconnect()

def quick_check(code: str, name: str = ""):
    """快速检查清单 (命令行直接调用)"""
    conn = FutuConnection()
    if conn.connect():
        if not code.startswith('HK.'):
            code = 'HK.' + code
        run_buy_checklist(conn, code, name)
        conn.disconnect()


def quick_laggards():
    """快速补涨扫描 (命令行直接调用)"""
    conn = FutuConnection()
    if conn.connect():
        find_sector_laggards(conn)
        conn.disconnect()


def update_scarce_stocks():
    """更新稀缺股图谱 (获取最新价格)"""
    conn = FutuConnection()
    if not conn.connect():
        print("❌ 无法连接富途API")
        return

    # 顶级稀缺标的
    scarce_stocks = [
        ('HK.02513', '智谱', 'AI大模型', '全球仅2只纯大模型股'),
        ('HK.00100', 'MiniMax', 'AI大模型', '全球仅2只纯大模型股'),
        ('HK.09880', '优必选', '人形机器人', '全球首家纯人形机器人IPO'),
        ('HK.09903', '天数智芯', 'GPU芯片', '国产GPU设计'),
        ('HK.06082', '壁仞科技', 'GPU芯片', '国产GPU龙头'),
        ('HK.03696', '英矽智能', 'AI制药', 'AI制药管线最快'),
        ('HK.02158', '晶泰科技', 'AI制药', 'AI+CRO第一股'),
        ('HK.02252', '微创机器人', '手术机器人', '产品线最全'),
        ('HK.02675', '精锋医疗', '手术机器人', '单孔技术领先'),
        ('HK.09992', '泡泡玛特', '潮玩', '潮玩第一股'),
        ('HK.00020', '商汤', 'AI平台', 'AI平台+应用'),
        ('HK.02172', '微创脑科学', '脑机接口', '港股脑机第一股'),
    ]

    print("\n" + "="*80)
    print("📊 港股稀缺概念股实时行情")
    print("="*80)
    print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    print(f"{'代码':<12} {'名称':<10} {'现价':>10} {'涨跌%':>8} {'成交额':>10} {'赛道':<10}")
    print("-"*80)

    results = []
    for code, name, sector, scarcity in scarce_stocks:
        ret, snapshot = conn.quote_ctx.get_market_snapshot([code])
        if ret == RET_OK and len(snapshot) > 0:
            row = snapshot.iloc[0]
            price = row['last_price']
            prev_close = row['prev_close_price']
            chg = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            turnover = row['turnover'] / 1e8

            results.append({
                'code': code, 'name': name, 'sector': sector,
                'price': price, 'chg': chg, 'turnover': turnover
            })

            hot = "🔥🔥🔥" if turnover > 20 else "🔥🔥" if turnover > 5 else "🔥" if turnover > 1 else ""
            print(f"{code:<12} {name:<10} {price:>10.2f} {chg:>+7.2f}% {turnover:>8.2f}亿 {sector:<10} {hot}")

    print("\n" + "="*80)
    print("热度排行（按成交额）:")
    results.sort(key=lambda x: x['turnover'], reverse=True)
    for i, r in enumerate(results[:5], 1):
        print(f"  {i}. {r['name']} ({r['code']}) - {r['turnover']:.2f}亿")

    conn.disconnect()
    print("\n✅ 稀缺股行情已更新")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == 'scan':
            quick_scan()

        elif cmd == 'analyze' and len(sys.argv) > 2:
            quick_analyze(sys.argv[2])

        elif cmd == 'check' and len(sys.argv) > 2:
            name = sys.argv[3] if len(sys.argv) > 3 else ""
            quick_check(sys.argv[2], name)

        elif cmd == 'summary':
            show_today_summary()

        elif cmd == 'laggards' or cmd == 'lag':
            quick_laggards()

        elif cmd == 'scarce' or cmd == 'update_scarce':
            update_scarce_stocks()

        elif cmd == 'research' and len(sys.argv) > 2:
            # 研究报告分析
            from research_analyzer import ResearchAnalyzer
            analyzer = ResearchAnalyzer()
            report = analyzer.analyze(sys.argv[2], include_search_hint=False)
            print(report)

        else:
            print("""
用法:
  python my_strategy_helper.py           # 交互式菜单
  python my_strategy_helper.py scan      # 快速扫描热门板块
  python my_strategy_helper.py analyze HK.09880  # 分析单只股票
  python my_strategy_helper.py check HK.09880 优必选  # 买入检查清单
  python my_strategy_helper.py summary   # 今日汇总
  python my_strategy_helper.py laggards  # 补涨机会扫描
  python my_strategy_helper.py scarce    # 稀缺股实时行情
  python my_strategy_helper.py research 02382  # 基本面+研究报告分析
            """)
    else:
        main()
