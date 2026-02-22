#!/usr/bin/env python3
"""
n8n港股监控 - 简化稳定版
解决连接超时问题，快速返回结果
"""
import json
import sys
import os

# 关键：先保存stdout，后面直接输出
_stdout_fd = os.dup(1)

def _output_json(data):
    """直接输出JSON"""
    os.dup2(_stdout_fd, 1)
    sys.stdout = os.fdopen(1, 'w', closefd=False)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.stdout.flush()

def main():
    try:
        # 导入富途API
        from futu import OpenQuoteContext, KLType, RET_OK

        ctx = None
        results = []

        try:
            # 连接FutuOpenD
            ctx = OpenQuoteContext(host="127.0.0.1", port=11111)

            # 精选股票池（减少到10只，提高速度）
            candidates = [
                ("HK.09988", "阿里巴巴"),
                ("HK.00700", "腾讯控股"),
                ("HK.03690", "美团"),
                ("HK.01810", "小米集团"),
                ("HK.01024", "快手"),
                ("HK.01211", "比亚迪"),
                ("HK.09618", "京东集团"),
                ("HK.02015", "理想汽车"),
                ("HK.00981", "中芯国际"),
                ("HK.09888", "百度集团"),
            ]

            codes = [c[0] for c in candidates]

            # 批量获取实时行情
            ret, snapshots = ctx.get_market_snapshot(codes)

            if ret != RET_OK:
                _output_json({
                    "error": "获取行情失败",
                    "stocks": [],
                    "count": 0
                })
                return

            snap_map = {}
            if snapshots is not None:
                for _, row in snapshots.iterrows():
                    snap_map[row["code"]] = row

            # 处理每只股票
            for code, name in candidates:
                if code not in snap_map:
                    continue

                s = snap_map[code]
                price = float(s.get("last_price", 0))
                prev_close = float(s.get("prev_close_price", 1))

                if price <= 0 or prev_close <= 0:
                    continue

                change_pct = (price - prev_close) / prev_close * 100
                amplitude = float(s.get("amplitude", 0))
                volume = int(s.get("volume", 0)) / 1_000_000  # 转换为百万

                # 简单评分
                score = 0
                reasons = []

                # 涨幅评分
                if change_pct > 3:
                    score += 30
                    reasons.append("强势上涨")
                elif change_pct > 1:
                    score += 20
                    reasons.append("温和上涨")
                elif change_pct > 0:
                    score += 10

                # 振幅评分
                if amplitude > 4:
                    score += 25
                    reasons.append("振幅大")
                elif amplitude > 2:
                    score += 15

                # 成交量评分
                if volume > 50:
                    score += 15
                    reasons.append("成交活跃")
                elif volume > 20:
                    score += 10

                rating = "strong_buy" if score >= 60 else ("buy" if score >= 40 else "neutral")

                stock = {
                    "code": code.replace("HK.", ""),
                    "name": name,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 2),
                    "amplitude": round(amplitude, 2),
                    "volume": round(volume, 1),
                    "turnover_rate": round(float(s.get("turnover_rate", 0)), 2),
                    "score": score,
                    "rating": rating,
                    "reasons": reasons,
                    "high": float(s.get("high_price", 0)),
                    "low": float(s.get("low_price", 0))
                }

                results.append(stock)

            # 按评分排序
            results.sort(key=lambda x: x['score'], reverse=True)

            # 输出结果
            output = {
                "success": True,
                "stocks": results,
                "count": len(results),
                "timestamp": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            _output_json(output)

        except Exception as e:
            _output_json({
                "error": f"运行错误: {str(e)}",
                "stocks": results,
                "count": len(results)
            })

        finally:
            if ctx:
                ctx.close()

    except ImportError:
        _output_json({
            "error": "futu-api未安装，请运行: pip install futu-api",
            "stocks": [],
            "count": 0
        })
    except Exception as e:
        _output_json({
            "error": f"严重错误: {str(e)}",
            "stocks": [],
            "count": 0
        })

if __name__ == "__main__":
    main()
