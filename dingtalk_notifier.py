#!/usr/bin/env python3
"""
钉钉机器人推送
用于港股异动、板块预警、选股推荐的实时通知
"""
import requests
import json
import hashlib
import hmac
import base64
import time
import urllib.parse
from datetime import datetime
from typing import Optional


class DingTalkNotifier:
    """钉钉机器人推送"""

    def __init__(self, webhook_url: str = None, secret: str = None):
        """
        初始化钉钉推送

        Args:
            webhook_url: 钉钉机器人Webhook地址
            secret: 加签密钥（如果设置了安全设置）
        """
        self.webhook_url = webhook_url or self._load_config().get('webhook_url', '')
        self.secret = secret or self._load_config().get('secret', '')

    def _load_config(self) -> dict:
        """从配置文件加载"""
        import os
        config_file = os.path.expanduser('~/.dingtalk_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self, webhook_url: str, secret: str = ''):
        """保存配置"""
        import os
        config_file = os.path.expanduser('~/.dingtalk_config.json')
        with open(config_file, 'w') as f:
            json.dump({'webhook_url': webhook_url, 'secret': secret}, f)
        print(f"✅ 配置已保存到 {config_file}")

    def _get_sign(self) -> tuple:
        """生成签名（如果设置了加签）"""
        if not self.secret:
            return '', ''

        timestamp = str(round(time.time() * 1000))
        secret_enc = self.secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign

    def _build_url(self) -> str:
        """构建请求URL"""
        url = self.webhook_url
        if self.secret:
            timestamp, sign = self._get_sign()
            url = f"{url}&timestamp={timestamp}&sign={sign}"
        return url

    def send_text(self, content: str, at_all: bool = False) -> bool:
        """
        发送文本消息
        """
        if not self.webhook_url:
            print("❌ 未配置钉钉Webhook，请先运行: python dingtalk_notifier.py setup")
            return False

        data = {
            "msgtype": "text",
            "text": {
                "content": content
            },
            "at": {
                "isAtAll": at_all
            }
        }

        return self._send(data)

    def send_markdown(self, title: str, content: str, at_all: bool = False) -> bool:
        """
        发送Markdown消息（更美观）
        """
        if not self.webhook_url:
            print("❌ 未配置钉钉Webhook")
            return False

        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            },
            "at": {
                "isAtAll": at_all
            }
        }

        return self._send(data)

    def _send(self, data: dict) -> bool:
        """发送请求"""
        try:
            url = self._build_url()
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, json=data, timeout=10)
            result = response.json()

            if result.get('errcode') == 0:
                return True
            else:
                print(f"❌ 钉钉推送失败: {result.get('errmsg')}")
                return False

        except Exception as e:
            print(f"❌ 钉钉推送异常: {e}")
            return False

    # ========== 业务推送方法 ==========

    def notify_stock_alert(self, stock_name: str, code: str, price: float,
                           change_pct: float, alert_type: str):
        """个股异动提醒"""
        icon = "🟢" if change_pct > 0 else "🔴"
        title = f"{icon} 个股异动: {stock_name}"

        content = f"""### {icon} 个股异动提醒

**{stock_name}** ({code})

- 现价: **{price:.2f}**
- 涨跌: **{change_pct:+.2f}%**
- 类型: {alert_type}
- 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_markdown(title, content)

    def notify_sector_alert(self, sector_name: str, change_pct: float,
                            leader_name: str, leader_change: float, is_hot: bool = False):
        """板块异动提醒"""
        hot = "🌟" if is_hot else ""
        title = f"🔥 板块暴涨: {sector_name}"

        content = f"""### 🔥 板块暴涨预警 {hot}

**{sector_name}** 板块涨幅: **+{change_pct:.2f}%**

**领涨股:** {leader_name} +{leader_change:.2f}%

时间: {datetime.now().strftime('%H:%M:%S')}

> 建议关注板块内龙头股
"""
        return self.send_markdown(title, content)

    def notify_stock_pick(self, sector_name: str, picks: list):
        """智能选股推荐"""
        title = f"🎯 选股推荐: {sector_name}"

        content = f"""### 🎯 智能选股推荐

**板块:** {sector_name}

**推荐股票:**

"""
        for i, p in enumerate(picks, 1):
            stars = "⭐" * min(int(p.get('score', 0) / 25) + 1, 3)
            content += f"""**{i}. {p['name']}** ({p['code']})
- 现价: {p['price']:.2f} | 涨幅: {p['change_pct']:+.1f}%
- 评分: {p['score']:.0f}/100 {stars}
- 热度: {p.get('heat_level', 'N/A')}

"""

        content += f"""---
时间: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_markdown(title, content)

    def notify_news_alert(self, title: str, source: str, sectors: list, stocks: list):
        """新闻热点提醒"""
        msg_title = f"📰 新闻热点: {title[:20]}"

        content = f"""### 📰 新闻热点预警

**{title}**

- 来源: {source}
- 相关板块: {', '.join(sectors[:3])}
- 关注股票: {', '.join(stocks[:4])}
- 时间: {datetime.now().strftime('%H:%M:%S')}
"""
        return self.send_markdown(msg_title, content)

    def notify_morning_report(self, hot_sectors: list, picks: list):
        """早盘快报"""
        title = "📊 早盘快报"

        content = f"""### 📊 港股早盘快报

**日期:** {datetime.now().strftime('%Y-%m-%d')}

#### 🔥 热门板块
"""
        for i, s in enumerate(hot_sectors[:5], 1):
            icon = "🌟" if s.get('is_hot') else ""
            content += f"{i}. **{s['name']}** +{s['change']:.2f}% {icon}\n"

        content += "\n#### 🎯 今日推荐\n"
        for p in picks[:3]:
            content += f"- **{p['name']}** ({p['code']}) 评分:{p['score']:.0f}\n"

        content += f"\n---\n*祝您投资顺利！*"

        return self.send_markdown(title, content)


def setup_dingtalk():
    """交互式配置钉钉"""
    print("=" * 50)
    print("🔔 钉钉机器人配置向导")
    print("=" * 50)
    print("""
配置步骤：
1. 打开钉钉，创建一个群（可以只有你自己）
2. 群设置 → 智能群助手 → 添加机器人
3. 选择「自定义」机器人
4. 安全设置选择「加签」，复制密钥
5. 复制 Webhook 地址
""")

    webhook = input("\n请粘贴 Webhook 地址: ").strip()
    secret = input("请粘贴加签密钥 (没有则直接回车): ").strip()

    if not webhook:
        print("❌ Webhook 地址不能为空")
        return

    notifier = DingTalkNotifier(webhook, secret)

    # 测试发送
    print("\n📤 发送测试消息...")
    success = notifier.send_text("🎉 钉钉推送配置成功！\n\n港股监控系统已连接。")

    if success:
        notifier.save_config(webhook, secret)
        print("✅ 配置完成！测试消息已发送到钉钉群。")
    else:
        print("❌ 配置失败，请检查 Webhook 地址和密钥是否正确。")


def test_notifications():
    """测试各种通知"""
    notifier = DingTalkNotifier()

    print("测试个股异动...")
    notifier.notify_stock_alert("亚太卫星", "01045.HK", 4.50, 9.8, "涨幅异动")

    print("测试板块预警...")
    notifier.notify_sector_alert("商业航天", 5.2, "亚太卫星", 9.8, True)

    print("测试选股推荐...")
    notifier.notify_stock_pick("商业航天", [
        {'name': '亚太卫星', 'code': '01045.HK', 'price': 4.50, 'change_pct': 9.8, 'score': 78, 'heat_level': '🔥爆热'},
        {'name': '钧达股份', 'code': '02865.HK', 'price': 12.30, 'change_pct': 7.2, 'score': 65, 'heat_level': '🔶较热'},
    ])

    print("✅ 测试完成，请查看钉钉群消息")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "setup":
            setup_dingtalk()
        elif cmd == "test":
            test_notifications()
        else:
            print("用法:")
            print("  python dingtalk_notifier.py setup  - 配置钉钉机器人")
            print("  python dingtalk_notifier.py test   - 测试推送")
    else:
        print("用法:")
        print("  python dingtalk_notifier.py setup  - 配置钉钉机器人")
        print("  python dingtalk_notifier.py test   - 测试推送")
