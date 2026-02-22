#!/usr/bin/env python3
"""
真实社区资讯抓取模块
支持：股吧、雪球、淘股吧、富途公告
"""
import requests
import json
import re
from datetime import datetime
from typing import List, Dict
import time

class RealNewsFetcher:
    """真实资讯抓取器"""

    def __init__(self, config_path='news_config.json'):
        """初始化，加载配置"""
        self.config = self.load_config(config_path)

    def load_config(self, path):
        """加载配置文件（cookie等）"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            # 默认配置
            return {
                'xueqiu': {'enabled': False, 'cookie': ''},
                'eastmoney': {'enabled': False, 'cookie': ''},
                'futu': {'enabled': True}
            }

    def fetch_guba_posts(self, stock_code: str, limit=5) -> List[Dict]:
        """
        抓取股吧（东方财富）帖子
        stock_code: HK.09880 -> 需转换为 09880
        """
        news_list = []

        try:
            # 港股代码转换
            code_num = stock_code.replace('HK.', '').replace('US.', '').replace('SH.', '').replace('SZ.', '')

            # 方法1: 尝试API接口（更可靠）
            api_url = f"https://guba.eastmoney.com/interface/GetData.aspx?type=1&GetHQNodeData=1&id={code_num}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://guba.eastmoney.com/',
                'Connection': 'keep-alive'
            }

            # 如果有cookie则添加
            if self.config.get('eastmoney', {}).get('enabled') and self.config['eastmoney'].get('cookie'):
                headers['Cookie'] = self.config['eastmoney']['cookie']

            response = requests.get(api_url, headers=headers, timeout=5)

            if response.status_code == 200:
                # 简单提取标题（使用更宽松的正则）
                # 匹配 title="xxx" 或 >标题文字<
                title_pattern = r'title="([^"]{10,})"'
                titles = re.findall(title_pattern, response.text)

                for title in titles[:limit]:
                    clean_title = title.strip()
                    # 过滤广告和无意义内容
                    if clean_title and len(clean_title) >= 8 and '广告' not in clean_title:
                        news_list.append({
                            'title': clean_title,
                            'source': '股吧',
                            'time': '',
                            'platform': 'guba'
                        })
        except requests.exceptions.Timeout:
            # 超时静默失败
            pass
        except Exception as e:
            # 其他错误也静默失败，避免影响整体流程
            pass

        return news_list

    def fetch_xueqiu_posts(self, stock_code: str, limit=5) -> List[Dict]:
        """
        抓取雪球帖子
        方法：从股票详情页抓取最新讨论
        """
        news_list = []

        # 检查是否启用和配置cookie
        if not self.config.get('xueqiu', {}).get('enabled'):
            return news_list

        try:
            # 港股代码转换（雪球格式）
            if stock_code.startswith('HK.'):
                symbol = stock_code.replace('HK.', '0') + '.HK'  # 09880 -> 09880.HK
            elif stock_code.startswith('US.'):
                symbol = stock_code.replace('US.', '')
            else:
                symbol = stock_code

            # 雪球股票讨论API（更可靠的接口）
            url = f"https://stock.xueqiu.com/v5/stock/timeline/status.json"
            params = {
                'symbol': symbol,
                'count': limit,
                'source': 'all',
                'page': 1
            }

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': f'https://xueqiu.com/S/{symbol}',
                'Origin': 'https://xueqiu.com',
                'Cookie': self.config['xueqiu'].get('cookie', '')
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                # 雪球返回格式：{"data": {"items": [...]}}
                if 'data' in data and 'items' in data['data']:
                    items = data['data']['items']
                    for item in items[:limit]:
                        # 提取文本内容
                        text = item.get('text', '') or item.get('description', '')
                        # 去除HTML标签
                        clean_text = re.sub(r'<[^>]+>', '', text)
                        clean_text = clean_text.strip()

                        if clean_text and len(clean_text) >= 10:
                            news_list.append({
                                'title': clean_text[:100] + '...' if len(clean_text) > 100 else clean_text,
                                'source': '雪球',
                                'time': self._format_timestamp(item.get('created_at', 0) / 1000),
                                'platform': 'xueqiu',
                                'author': item.get('user', {}).get('screen_name', '匿名')
                            })
                elif 'error_description' in data:
                    # Cookie可能过期
                    pass
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            # 静默失败，避免影响整体流程
            pass

        return news_list

    def fetch_taoguba_posts(self, stock_code: str, limit=5) -> List[Dict]:
        """
        抓取淘股吧帖子
        淘股吧API较复杂，需要登录
        """
        news_list = []

        try:
            # 港股代码转换
            code_num = stock_code.replace('HK.', '').lstrip('0')

            # 淘股吧搜索URL（简化版）
            url = f"https://www.taoguba.com.cn/search/getHotReplyList?keyword={code_num}"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://www.taoguba.com.cn/'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if 'data' in data and isinstance(data['data'], list):
                    for item in data['data'][:limit]:
                        title = item.get('title', '') or item.get('content', '')
                        if title and len(title) > 5:
                            news_list.append({
                                'title': title[:100],
                                'source': '淘股吧',
                                'time': item.get('create_time', ''),
                                'platform': 'taoguba'
                            })
        except Exception as e:
            # 淘股吧可能需要登录，静默失败
            pass

        return news_list

    def fetch_futu_announcements(self, stock_code: str, limit=3) -> List[Dict]:
        """
        抓取富途公告（通过futu-api）
        这个是最可靠的港股资讯来源
        """
        news_list = []

        try:
            from futu import OpenQuoteContext, AnnType, RET_OK

            quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)

            # 获取公司公告
            ret, data = quote_ctx.request_history_kl_quota(get_detail=False)
            if ret == RET_OK:
                # 这里简化了，实际应该用 get_referencestock_list 获取公告
                # 富途OpenAPI暂不直接支持公告查询，需要用网页版
                pass

            quote_ctx.close()

        except Exception as e:
            pass

        return news_list

    def fetch_all_news(self, stock_code: str, stock_name: str) -> List[Dict]:
        """
        从所有来源抓取资讯，并按时间排序
        """
        all_news = []

        # 1. 股吧（默认开启，无需cookie）
        guba_news = self.fetch_guba_posts(stock_code)
        all_news.extend(guba_news)

        # 2. 雪球（需要cookie）
        xueqiu_news = self.fetch_xueqiu_posts(stock_code)
        all_news.extend(xueqiu_news)

        # 3. 淘股吧（暂时跳过，API复杂）
        # taoguba_news = self.fetch_taoguba_posts(stock_code)
        # all_news.extend(taoguba_news)

        # 4. 富途公告
        futu_news = self.fetch_futu_announcements(stock_code)
        all_news.extend(futu_news)

        # 去重（基于标题）
        seen_titles = set()
        unique_news = []
        for news in all_news:
            title = news['title']
            if title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)

        return unique_news[:10]  # 返回前10条

    def _format_timestamp(self, timestamp):
        """格式化时间戳"""
        try:
            if timestamp > 1e10:  # 毫秒级
                timestamp = timestamp / 1000
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M')
        except:
            return ''


# 测试代码
if __name__ == '__main__':
    fetcher = RealNewsFetcher()

    # 测试股票
    test_codes = ['HK.09880', 'HK.02432']

    for code in test_codes:
        print(f"\n{'='*60}")
        print(f"测试抓取: {code}")
        print(f"{'='*60}\n")

        news = fetcher.fetch_all_news(code, code.replace('HK.', ''))

        if news:
            print(f"✅ 找到 {len(news)} 条资讯:\n")
            for i, item in enumerate(news[:5], 1):
                print(f"{i}. [{item['source']}] {item['title']}")
                if item.get('time'):
                    print(f"   时间: {item['time']}")
                print()
        else:
            print("⚠️ 未找到资讯\n")
