#!/usr/bin/env python3
"""调试雪球API"""
import requests
import json

# 你的cookie
COOKIE = "acw_tc=2f3478b417717377539325780e71f7cd4abe784caab2a9bf6b834db2d9491e; cookiesu=901771737755125; device_id=8fc5b1eaa2f27255f3a57e733348dad7; Hm_lvt_1db88642e346389874251b5a1eded6e3=1771737759; HMACCOUNT=04D111D07F536FA6; smidV2=20260222132239047867fc4a0778a522cffa9fff37977200d489202c2959c50; remember=1; xq_a_token=1f8d3500f5859d5b08602d4349175a673d8df866; xqat=1f8d3500f5859d5b08602d4349175a673d8df866; xq_id_token=eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOjI1NDQ3MTE2NTIsImlzcyI6InVjIiwiZXhwIjoxNzc0MzI5Nzk5LCJjdG0iOjE3NzE3Mzc3OTkwOTksImNpZCI6ImQ5ZDBuNEFadXAifQ.GAJGUgkqmkViZuc20uULA0uKYiNwfzOU8TWdoJXFIG8CC76ee-7DtaQWHnhZBYBuzy-UJzBUeub5DnTtAujQN8egrmAVzPyWpX5C8MmYDkRa--EvGEGlANY06rPlybzk46G5OvcxvEaxy5nBPu5u2xvRrShYn7SzEnrzB27r5d7RRIvYo-oewF0O5SZUth_w9ELmrqH8U_quQqXiyBMdESeWnH8QO3wPSbkb8BjOLmOnCWwFJhSBR2E0WvFdXp5lIM9qDrx-WSgfU8EBF3gae1AFxo-_6muYcAFFoEiCZJEZtJGz7tYQJ6TixqsJTNYi7pHcgL1dh4L3Ce2BoeRdzA; xq_r_token=a4cb09d22ccaafbec60cf56320e8262df7df236f; xq_is_login=1; u=2544711652; Hm_lpvt_1db88642e346389874251b5a1eded6e3=1771737873"

def test_xueqiu_api():
    symbol = "09880.HK"

    print(f"测试雪球API - 股票代码: {symbol}\n")

    # 方法1: timeline API
    print("="*60)
    print("方法1: Timeline API")
    print("="*60)

    url1 = "https://stock.xueqiu.com/v5/stock/timeline/status.json"
    params1 = {
        'symbol': symbol,
        'count': 5,
        'source': 'all',
        'page': 1
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': f'https://xueqiu.com/S/{symbol}',
        'Cookie': COOKIE
    }

    try:
        response = requests.get(url1, params=params1, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        print(f"\n响应内容（前500字符）:")
        print(response.text[:500])

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\nJSON解析成功！")
                print(f"数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
            except:
                print(f"\nJSON解析失败，返回的是HTML或其他格式")
    except Exception as e:
        print(f"请求失败: {e}")

    print("\n" + "="*60)
    print("方法2: 热门讨论API")
    print("="*60)

    # 方法2: 热门讨论
    url2 = "https://xueqiu.com/statuses/stock_timeline.json"
    params2 = {
        'symbol_id': symbol,
        'count': 5,
        'source': 'all'
    }

    try:
        response = requests.get(url2, params=params2, headers=headers, timeout=10)
        print(f"状态码: {response.status_code}")
        print(f"\n响应内容（前500字符）:")
        print(response.text[:500])

        if response.status_code == 200:
            try:
                data = response.json()
                print(f"\nJSON解析成功！")
                print(f"数据结构: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
            except:
                print(f"\nJSON解析失败")
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == '__main__':
    test_xueqiu_api()
