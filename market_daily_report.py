#!/usr/bin/env python3
"""
市场动态日报 - 一键采集 + 推送
整合新闻、热点、BTC、恐惧贪婪指数
"""

import requests
import json
from datetime import datetime
from typing import Dict, List, Optional


class MarketDailyReport:
    """市场日报生成器"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

    def get_hk_hot_stocks(self, limit: int = 10) -> List[Dict]:
        """获取港股热门股票"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1, 'pz': limit, 'po': 1,
                'np': 1, 'fltt': 2, 'invt': 2,
                'fid': 'f3',
                'fs': 'm:128+t:3,m:128+t:4,m:128+t:1,m:128+t:2',  # 港股
                'fields': 'f12,f14,f2,f3,f5,f6'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            stocks = []
            if data and 'data' in data and data['data'] and 'diff' in data['data']:
                for item in data['data']['diff']:
                    stocks.append({
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'price': item.get('f2', 0),
                        'change_pct': item.get('f3', 0),
                        'volume': item.get('f5', 0),
                        'amount': item.get('f6', 0)
                    })
            return stocks
        except Exception as e:
            print(f"获取港股热门失败: {e}")
            return []

    def get_concept_hot(self, limit: int = 10) -> List[Dict]:
        """获取热门概念板块"""
        try:
            url = "http://push2.eastmoney.com/api/qt/clist/get"
            params = {
                'pn': 1, 'pz': limit, 'po': 1,
                'np': 1, 'fltt': 2, 'invt': 2,
                'fid': 'f3',
                'fs': 'm:90+t:3',  # 概念板块
                'fields': 'f12,f14,f2,f3,f104,f105'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            concepts = []
            if data and 'data' in data and data['data'] and 'diff' in data['data']:
                for item in data['data']['diff']:
                    concepts.append({
                        'code': item.get('f12', ''),
                        'name': item.get('f14', ''),
                        'change_pct': item.get('f3', 0),
                        'up_count': item.get('f104', 0),
                        'down_count': item.get('f105', 0)
                    })
            return concepts
        except Exception as e:
            print(f"获取概念板块失败: {e}")
            return []

    def get_btc_price(self) -> Optional[Dict]:
        """获取BTC价格"""
        try:
            # CoinGecko
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                'ids': 'bitcoin',
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if 'bitcoin' in data:
                return {
                    'price': data['bitcoin'].get('usd', 0),
                    'change_24h': data['bitcoin'].get('usd_24h_change', 0)
                }
        except:
            pass

        # 备用 Binance
        try:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {'symbol': 'BTCUSDT'}
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()
            return {
                'price': float(data.get('lastPrice', 0)),
                'change_24h': float(data.get('priceChangePercent', 0))
            }
        except Exception as e:
            print(f"获取BTC失败: {e}")
            return None

    def get_fear_greed_index(self) -> Optional[Dict]:
        """获取恐惧贪婪指数"""
        try:
            url = "https://api.alternative.me/fng/"
            resp = requests.get(url, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'data' in data:
                latest = data['data'][0]
                return {
                    'value': int(latest.get('value', 50)),
                    'classification': latest.get('value_classification', '')
                }
        except Exception as e:
            print(f"获取恐惧贪婪指数失败: {e}")
            return None

    def get_sina_news(self, limit: int = 5) -> List[Dict]:
        """获取新浪财经快讯"""
        news = []
        try:
            url = "https://zhibo.sina.com.cn/api/zhibo/feed"
            params = {
                'page': 1, 'page_size': 20,
                'zhibo_id': 152, 'tag_id': 0,
                'dire': 'f', 'dpc': 1
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            data = resp.json()

            if data and 'result' in data and 'data' in data['result']:
                feed = data['result']['data'].get('feed', {})
                import re
                for item in feed.get('list', [])[:limit]:
                    rich_text = item.get('rich_text', '')
                    text = re.sub(r'<[^>]+>', '', rich_text)
                    if text:
                        news.append({
                            'content': text[:80],
                            'time': item.get('create_time', '')[-8:-3]
                        })
        except Exception as e:
            print(f"获取新闻失败: {e}")
        return news

    def generate_report(self) -> str:
        """生成市场日报"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M')

        report = f"""
📊 **市场动态日报**
⏰ {now}
{'=' * 40}
"""

        # 1. BTC + 恐惧贪婪
        btc = self.get_btc_price()
        fgi = self.get_fear_greed_index()

        if btc:
            icon = '🟢' if btc['change_24h'] > 0 else '🔴'
            report += f"\n**🪙 BTC**: ${btc['price']:,.0f} {icon}{btc['change_24h']:+.2f}%"

        if fgi:
            emotion = '😱' if fgi['value'] < 30 else '😐' if fgi['value'] < 60 else '🤑'
            report += f"\n**{emotion} 恐惧贪婪**: {fgi['value']} ({fgi['classification']})"

        # 2. 热门概念
        concepts = self.get_concept_hot(5)
        if concepts:
            report += f"\n\n**🔥 热门概念板块**"
            for c in concepts:
                icon = '🔺' if c['change_pct'] > 0 else '🔻'
                report += f"\n  {icon} {c['name']}: {c['change_pct']:+.2f}%"

        # 3. 港股热门
        hk_stocks = self.get_hk_hot_stocks(5)
        if hk_stocks:
            report += f"\n\n**📈 港股热门**"
            for s in hk_stocks:
                icon = '🔺' if s['change_pct'] > 0 else '🔻'
                report += f"\n  {icon} {s['code']} {s['name']}: {s['change_pct']:+.2f}%"

        # 4. 财经快讯
        news = self.get_sina_news(3)
        if news:
            report += f"\n\n**📰 财经快讯**"
            for n in news:
                report += f"\n  • [{n['time']}] {n['content']}"

        report += f"\n\n{'=' * 40}"
        report += f"\n💡 数据来源: 东方财富/CoinGecko/新浪财经"

        return report

    def send_to_dingtalk(self, webhook_url: str, secret: str = None) -> bool:
        """发送到钉钉"""
        import hashlib, hmac, base64, urllib.parse

        report = self.generate_report()

        url = webhook_url
        if secret:
            timestamp = str(round(datetime.now().timestamp() * 1000))
            string_to_sign = f'{timestamp}\n{secret}'
            hmac_code = hmac.new(
                secret.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
            url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": "市场动态日报",
                "text": report
            }
        }

        try:
            resp = requests.post(url, json=data, timeout=10)
            result = resp.json()
            if result.get('errcode') == 0:
                print("✅ 钉钉推送成功")
                return True
            else:
                print(f"❌ 钉钉推送失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 推送异常: {e}")
            return False

    def send_to_feishu(self, webhook_url: str) -> bool:
        """发送到飞书"""
        report = self.generate_report()

        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": "📊 市场动态日报"},
                    "template": "blue"
                },
                "elements": [
                    {"tag": "markdown", "content": report}
                ]
            }
        }

        try:
            resp = requests.post(webhook_url, json=data, timeout=10)
            result = resp.json()
            if result.get('code') == 0 or result.get('StatusCode') == 0:
                print("✅ 飞书推送成功")
                return True
            else:
                print(f"❌ 飞书推送失败: {result}")
                return False
        except Exception as e:
            print(f"❌ 推送异常: {e}")
            return False


def main():
    """主程序"""
    import sys

    reporter = MarketDailyReport()

    if len(sys.argv) < 2:
        # 仅生成报告，打印到终端
        print(reporter.generate_report())
        print("\n用法:")
        print("  python market_daily_report.py              # 仅查看报告")
        print("  python market_daily_report.py dingtalk     # 推送到钉钉")
        print("  python market_daily_report.py feishu       # 推送到飞书")
        return

    action = sys.argv[1].lower()

    if action == 'dingtalk':
        # 从配置文件读取钉钉配置
        import os
        config_file = os.path.expanduser('~/.dingtalk_config.json')
        if os.path.exists(config_file):
            with open(config_file) as f:
                config = json.load(f)
            webhook = config.get('webhook_url', '')
            secret = config.get('secret', '')
            if webhook:
                reporter.send_to_dingtalk(webhook, secret)
            else:
                print("❌ 请先配置钉钉 Webhook")
        else:
            print("❌ 未找到钉钉配置文件，请先配置")
            print("   python dingtalk_notifier.py setup")

    elif action == 'feishu':
        # 飞书 webhook
        webhook = sys.argv[2] if len(sys.argv) > 2 else ''
        if webhook:
            reporter.send_to_feishu(webhook)
        else:
            print("❌ 请提供飞书 Webhook URL")
            print("   python market_daily_report.py feishu <webhook_url>")

    else:
        print(reporter.generate_report())


if __name__ == "__main__":
    main()
