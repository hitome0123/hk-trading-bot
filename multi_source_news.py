#!/usr/bin/env python3
"""
【方案C】多数据源资讯整合 - 富途公告 + 东方财富快讯
"""
import os
import requests
from datetime import datetime, timedelta

class MultiSourceNews:
    """整合多个专业数据源"""

    def __init__(self, quote_ctx=None):
        """
        参数：
        - quote_ctx: 富途QuoteContext对象（如果有的话）
        """
        self.quote_ctx = quote_ctx

    def fetch_eastmoney_news(self, stock_code):
        """
        从东方财富获取个股快讯

        参数：stock_code - 如 '09880'
        返回：新闻列表
        """
        news_list = []

        try:
            # 东方财富港股快讯API
            url = "https://np-listapi.eastmoney.com/comm/wap/getListInfo"
            params = {
                'cb': 'callback',
                'type': '2',  # 港股
                'keyword': stock_code,
                'pageSize': 10,
                'pageIndex': 1,
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Referer': 'https://wap.eastmoney.com/'
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                # 东方财富返回JSONP，需要提取JSON部分
                text = response.text
                if 'callback(' in text:
                    json_str = text[text.find('(')+1:text.rfind(')')]
                    import json
                    data = json.loads(json_str)

                    if 'data' in data and 'list' in data['data']:
                        for item in data['data']['list'][:3]:
                            title = item.get('title', '').strip()
                            if title and stock_code in title:
                                news_list.append({
                                    'title': f"💼 {title}",
                                    'source': '东方财富',
                                    'time': item.get('showtime', ''),
                                    'confidence': 'high'
                                })

        except Exception as e:
            print(f"⚠️ 东方财富获取失败: {e}")

        return news_list

    def fetch_futu_announcements(self, stock_code):
        """
        从富途获取公司公告（需要富途OpenD支持）

        参数：stock_code - 如 'HK.09880'
        返回：公告列表
        """
        announcements = []

        # 富途API暂时不支持直接获取公告
        # 这里用资金流向等数据推断
        if self.quote_ctx:
            try:
                # 获取资金流向
                ret, data = self.quote_ctx.get_capital_flow([stock_code])

                # RET_OK = 0
                if ret == 0 and not data.empty:
                    main_flow = data.iloc[0].get('main_net_inflow', 0)
                    if abs(main_flow) > 1e7:  # 主力净流入/出 > 1000万
                        direction = "净流入" if main_flow > 0 else "净流出"
                        announcements.append({
                            'title': f"💰 主力资金{direction}{abs(main_flow)/1e8:.2f}亿",
                            'source': '富途资金流',
                            'confidence': 'high'
                        })
            except Exception as e:
                print(f"⚠️ 富途资金流获取失败: {e}")

        return announcements

    def fetch_all_sources(self, stock_name, stock_code, sector_name):
        """
        整合所有数据源

        参数：
        - stock_name: 股票名称
        - stock_code: 股票代码（如 '09880' 或 'HK.09880'）
        - sector_name: 板块名称

        返回：综合新闻列表
        """
        all_news = []

        # 格式化代码
        code_number = stock_code.replace('HK.', '').lstrip('0')
        code_with_hk = stock_code if stock_code.startswith('HK.') else f'HK.{stock_code.zfill(5)}'

        # 1. 东方财富快讯
        print(f"  📡 东方财富: 搜索{stock_name}...")
        eastmoney_news = self.fetch_eastmoney_news(code_number)
        all_news.extend(eastmoney_news)
        if eastmoney_news:
            print(f"    ✅ 找到{len(eastmoney_news)}条")

        # 2. 富途公告/资金流
        if self.quote_ctx:
            print(f"  📡 富途数据: 获取资金流...")
            futu_data = self.fetch_futu_announcements(code_with_hk)
            all_news.extend(futu_data)
            if futu_data:
                print(f"    ✅ 找到{len(futu_data)}条")

        return all_news[:5]  # 最多5条


# 测试
if __name__ == '__main__':
    print("\n" + "="*60)
    print("测试多数据源资讯抓取")
    print("="*60 + "\n")

    fetcher = MultiSourceNews()

    # 测试东方财富
    print("🧪 测试东方财富API...\n")
    news = fetcher.fetch_eastmoney_news('9880')

    if news:
        print(f"✅ 找到 {len(news)} 条新闻:\n")
        for item in news:
            print(f"  {item['title']}")
            print(f"    来源: {item['source']}")
            if 'time' in item:
                print(f"    时间: {item['time']}")
            print()
    else:
        print("❌ 未找到新闻（可能API已变更或股票代码无新闻）\n")

    # 测试综合抓取
    print("\n" + "="*60)
    print("综合抓取优必选资讯")
    print("="*60 + "\n")

    all_news = fetcher.fetch_all_sources("优必选", "09880", "人形机器人")

    print(f"\n✅ 总共找到 {len(all_news)} 条资讯")
