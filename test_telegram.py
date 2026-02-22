#!/usr/bin/env python3
"""测试Telegram推送"""
import requests

TELEGRAM_BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
TELEGRAM_CHAT_ID = "7082819163"

def send_test_message():
    """发送测试消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        message = """🧪 *板块炒作雷达系统测试*

✅ Telegram推送配置成功！

📊 系统状态:
• 富途OpenD: 已连接
• 监控板块: 10个
• 推送功能: 正常

🔥 下周一开盘后，如检测到以下信号会自动推送:
• 炒作指数≥70 + 加速期/高潮期
• 炒作指数≥50 + 启动期

_测试消息 - 2026-02-22_"""

        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            print("✅ Telegram测试消息发送成功!")
            print(f"   Chat ID: {TELEGRAM_CHAT_ID}")
            return True
        else:
            print(f"❌ 发送失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 推送出错: {e}")
        return False

if __name__ == '__main__':
    print("🔔 测试Telegram推送...")
    print("")
    send_test_message()
