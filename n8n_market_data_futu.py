#!/usr/bin/env python3
"""
港股市场数据获取（使用Futu API）
替代东财API，避免连接超时问题
"""
import json
import sys
import os

_stdout_fd = os.dup(1)
_devnull = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull, 1)
os.close(_devnull)

try:
    from futu import OpenQuoteContext, Market, RET_OK, SortField, StockField
    FUTU_AVAILABLE = True
except ImportError:
    FUTU_AVAILABLE = False


def _output_json(data):
    """输出JSON"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False))
    sys.stdout.flush()


def main():
    if not FUTU_AVAILABLE:
        _output_json({"rc": -1, "rt": -1, "data": None, "message": "futu-api not installed"})
        return

    ctx = None
    try:
        ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

        # 获取港股股票列表
        ret, data = ctx.get_stock_basicinfo(market=Market.HK, stock_type='STOCK')

        if ret != RET_OK:
            _output_json({"rc": -1, "rt": -1, "data": None, "message": "Failed to get stock list"})
            return

        # 精选活跃股票
        codes = []
        for _, row in data.head(300).iterrows():  # 取前300只
            codes.append(row['code'])

        # 批量获取快照
        ret, snapshots = ctx.get_market_snapshot(codes[:100])  # 限制100只，避免超时

        if ret != RET_OK:
            _output_json({"rc": -1, "rt": -1, "data": None, "message": "Failed to get snapshots"})
            return

        stocks = []
        for _, s in snapshots.iterrows():
            code_num = s['code'].replace('HK.', '')
            stocks.append({
                'f12': code_num,  # 股票代码
                'f14': s.get('name', ''),  # 股票名称
                'f2': float(s.get('last_price', 0)),  # 最新价
                'f3': float(s.get('change_rate', 0)),  # 涨跌幅%
                'f4': float(s.get('change_val', 0)),  # 涨跌额
                'f5': int(s.get('volume', 0)),  # 成交量
                'f6': float(s.get('turnover', 0)),  # 成交额
                'f7': float(s.get('amplitude', 0)),  # 振幅%
                'f15': float(s.get('high_price', 0)),  # 最高
                'f16': float(s.get('low_price', 0)),  # 最低
                'f17': float(s.get('open_price', 0)),  # 今开
                'f18': float(s.get('prev_close_price', 0)),  # 昨收
            })

        # 模拟东财API格式
        output = {
            "rc": 0,
            "rt": 4,
            "svr": 182479632,
            "lt": 1,
            "full": 1,
            "dlmkts": "",
            "data": {
                "total": len(stocks),
                "diff": stocks
            }
        }

        _output_json(output)

    except Exception as e:
        _output_json({
            "rc": -1,
            "rt": -1,
            "data": None,
            "message": str(e)
        })
    finally:
        if ctx:
            ctx.close()


if __name__ == "__main__":
    main()
