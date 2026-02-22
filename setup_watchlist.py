#!/usr/bin/env python3
"""
堕落天使策略 - 自选股设置脚本
连接富途OpenD，创建自选分组并添加股票
"""

from futu import *
import time

# 富途OpenD连接配置
FUTU_HOST = '127.0.0.1'
FUTU_PORT = 11111

# 堕落天使策略股票池 - 按板块分类
WATCHLIST_STOCKS = {
    "AI核心": [
        "HK.00100",  # MiniMax
        "HK.02513",  # 智谱AI
        "HK.09678",  # 云知声
        "HK.06082",  # 壁仞科技
        "HK.09903",  # 天数智芯
        "HK.09660",  # 地平线机器人
        "HK.06682",  # 第四范式
    ],
    "机器人": [
        "HK.09880",  # 优必选
        "HK.02432",  # 越疆
        "HK.02252",  # 微创机器人
        "HK.02675",  # 精锋医疗
        "HK.02590",  # 极智嘉
    ],
    "AI制药": [
        "HK.02658",  # 英矽智能
        "HK.02259",  # 晶泰科技
        "HK.02506",  # 讯飞医疗
        "HK.02158",  # 医渡科技
    ],
    "低空经济": [
        "HK.09868",  # 小鹏汽车
        "HK.00175",  # 吉利汽车
        "HK.02238",  # 广汽集团
        "HK.01045",  # 亚太卫星
    ],
    "新能源": [
        "HK.01772",  # 赣锋锂业
        "HK.09696",  # 天齐锂业
        "HK.00968",  # 信义光能
        "HK.03868",  # 信义能源
    ],
    "有色金属": [
        "HK.02899",  # 紫金矿业
        "HK.03993",  # 洛阳钼业
        "HK.00358",  # 江西铜业
        "HK.02099",  # 中国黄金国际
        "HK.01818",  # 招金矿业
    ],
    "消费出海": [
        "HK.09992",  # 泡泡玛特
        "HK.09896",  # 名创优品
        "HK.06181",  # 老铺黄金
        "HK.02020",  # 安踏体育
    ],
    "核电铀矿": [
        "HK.01164",  # 中广核矿业
        "HK.01816",  # 中广核电力
        "HK.01811",  # 中广核新能源
    ],
    "军工航天": [
        "HK.02357",  # 中航科工
        # "HK.01185",  # 中国航天万源 - 已退市/无效
    ],
    "电网设备": [
        "HK.01072",  # 东方电气
        "HK.02727",  # 上海电气
        "HK.01133",  # 哈尔滨电气
        "HK.06869",  # 长飞光纤
        "HK.03393",  # 威胜控股
    ],
}


def get_all_stocks():
    """获取所有股票列表"""
    all_stocks = []
    for stocks in WATCHLIST_STOCKS.values():
        all_stocks.extend(stocks)
    return list(set(all_stocks))


def validate_stocks(quote_ctx, stocks):
    """验证股票代码有效性，返回有效代码列表"""
    valid_stocks = []
    invalid_stocks = []

    # 分批验证，每批10只
    batch_size = 10
    for i in range(0, len(stocks), batch_size):
        batch = stocks[i:i+batch_size]
        ret, data = quote_ctx.get_market_snapshot(batch)
        if ret == RET_OK:
            valid_stocks.extend(data['code'].tolist())
        else:
            # 逐个验证这批中的股票
            for code in batch:
                ret2, data2 = quote_ctx.get_market_snapshot([code])
                if ret2 == RET_OK:
                    valid_stocks.append(code)
                else:
                    invalid_stocks.append(code)
        time.sleep(0.1)  # 避免请求过快

    return valid_stocks, invalid_stocks


def setup_watchlist():
    """设置自选股分组"""
    quote_ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)

    try:
        print("="*60)
        print("🚀 堕落天使策略 - 自选股设置")
        print("="*60)

        all_stocks = get_all_stocks()
        print(f"\n📊 共 {len(all_stocks)} 只股票待验证\n")

        # 1. 验证股票代码
        print("🔍 验证股票代码...")
        valid_stocks, invalid_stocks = validate_stocks(quote_ctx, all_stocks)

        if invalid_stocks:
            print(f"\n⚠️ 以下 {len(invalid_stocks)} 只股票代码无效:")
            for code in invalid_stocks:
                print(f"  ❌ {code}")

        print(f"\n✅ {len(valid_stocks)} 只股票代码有效\n")

        # 2. 获取有效股票的行情
        if valid_stocks:
            print("📈 获取实时行情...\n")
            ret, data = quote_ctx.get_market_snapshot(valid_stocks)

            if ret == RET_OK:
                print(f"{'代码':<10} {'名称':<10} {'现价':>8} {'涨跌幅':>8} {'成交额(万)':>10}")
                print("-" * 55)

                # 计算涨跌幅并排序
                data['change_pct'] = 0.0
                for idx, row in data.iterrows():
                    prev = row['prev_close_price']
                    if prev and prev > 0:
                        data.at[idx, 'change_pct'] = (row['last_price'] - prev) / prev * 100

                data_sorted = data.sort_values('change_pct', ascending=False)

                for _, row in data_sorted.iterrows():
                    code = row['code'].replace('HK.', '')
                    name = str(row['name'])[:8]
                    price = row['last_price']
                    change_pct = row['change_pct']
                    turnover = row.get('turnover', 0) / 10000

                    pct_str = f"{change_pct:+.2f}%"
                    print(f"{code:<10} {name:<10} {price:>8.2f} {pct_str:>8} {turnover:>10,.0f}")

                print("-" * 55)

                # 统计
                up = len(data[data['change_pct'] > 0])
                down = len(data[data['change_pct'] < 0])
                flat = len(data[data['change_pct'] == 0])
                print(f"\n📊 上涨: {up} | 下跌: {down} | 平盘: {flat}")

        # 3. 添加到自选
        print("\n" + "-"*55)
        print("📥 添加股票到自选...\n")

        group_name = "自选"
        success_count = 0
        fail_count = 0

        for code in valid_stocks:
            ret, result = quote_ctx.modify_user_security(
                group_name=group_name,
                op=ModifyUserSecurityOp.ADD,
                code_list=[code]
            )
            if ret == RET_OK:
                success_count += 1
                print(f"  ✅ {code}")
            else:
                fail_count += 1
                print(f"  ❌ {code}: {result}")
            time.sleep(0.05)

        print(f"\n📊 添加结果: 成功 {success_count} / 失败 {fail_count}")

        # 4. 显示板块分类
        print("\n" + "="*60)
        print("📋 按板块分类汇总")
        print("="*60)

        for group, stocks in WATCHLIST_STOCKS.items():
            valid_in_group = [s for s in stocks if s in valid_stocks]
            print(f"\n【{group}】({len(valid_in_group)}/{len(stocks)}只)")
            for code in stocks:
                status = "✅" if code in valid_stocks else "❌"
                print(f"  {status} {code}")

        print("\n" + "="*60)
        print("✅ 自选设置完成！请打开富途牛牛APP查看")
        print("="*60)

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        quote_ctx.close()


def show_prices():
    """显示实时行情"""
    quote_ctx = OpenQuoteContext(host=FUTU_HOST, port=FUTU_PORT)

    try:
        all_stocks = get_all_stocks()

        print("\n" + "="*70)
        print("📊 堕落天使策略股票池 - 实时行情")
        print("="*70 + "\n")

        valid_stocks, _ = validate_stocks(quote_ctx, all_stocks)

        ret, data = quote_ctx.get_market_snapshot(valid_stocks)
        if ret == RET_OK:
            # 计算涨跌幅
            data['change_pct'] = 0.0
            for idx, row in data.iterrows():
                prev = row['prev_close_price']
                if prev and prev > 0:
                    data.at[idx, 'change_pct'] = (row['last_price'] - prev) / prev * 100

            data_sorted = data.sort_values('change_pct', ascending=False)

            print(f"{'代码':<10} {'名称':<10} {'现价':>8} {'涨跌幅':>8} {'成交额(万)':>10} {'振幅':>8}")
            print("-" * 70)

            for _, row in data_sorted.iterrows():
                code = row['code'].replace('HK.', '')
                name = str(row['name'])[:8]
                price = row['last_price']
                change_pct = row['change_pct']
                turnover = row.get('turnover', 0) / 10000
                high = row.get('high_price', price)
                low = row.get('low_price', price)
                prev = row.get('prev_close_price', price)
                amplitude = (high - low) / prev * 100 if prev > 0 else 0

                pct_str = f"{change_pct:+.2f}%"
                amp_str = f"{amplitude:.2f}%"

                print(f"{code:<10} {name:<10} {price:>8.2f} {pct_str:>8} {turnover:>10,.0f} {amp_str:>8}")

            print("-" * 70)

            up = len(data[data['change_pct'] > 0])
            down = len(data[data['change_pct'] < 0])
            flat = len(data[data['change_pct'] == 0])
            print(f"\n共 {len(data)} 只股票 | 上涨: {up} | 下跌: {down} | 平盘: {flat}")
        else:
            print(f"❌ 获取行情失败: {data}")

    finally:
        quote_ctx.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "prices":
        show_prices()
    else:
        setup_watchlist()
