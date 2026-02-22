#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取Telegram Chat ID的辅助脚本

使用方法:
1. 先向你的bot发送任意消息
2. 运行此脚本: python3 get_chat_id.py YOUR_BOT_TOKEN
"""

import sys
import httpx

def get_chat_id(bot_token):
    """获取chat_id"""
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"

    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get('ok'):
            print(f"❌ API错误: {data}")
            return None

        updates = data.get('result', [])

        if not updates:
            print("❌ 没有找到消息")
            print("请先在Telegram中向你的bot发送一条消息，然后重新运行此脚本")
            return None

        # 获取最新消息
        latest = updates[-1]
        chat_id = latest['message']['chat']['id']
        username = latest['message']['chat'].get('username', 'N/A')
        first_name = latest['message']['chat'].get('first_name', 'N/A')

        print("=" * 60)
        print("✅ 找到你的Telegram信息：")
        print("=" * 60)
        print(f"Chat ID: {chat_id}")
        print(f"用户名: @{username}")
        print(f"名字: {first_name}")
        print("=" * 60)
        print("")
        print("📋 复制下面的配置到 config.yaml：")
        print("")
        print("notifications:")
        print("  telegram:")
        print("    enabled: true")
        print(f'    bot_token: "{bot_token}"')
        print(f'    chat_id: "{chat_id}"')
        print("")

        return chat_id

    except Exception as e:
        print(f"❌ 错误: {e}")
        return None

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法: python3 get_chat_id.py YOUR_BOT_TOKEN")
        print("")
        print("步骤:")
        print("1. 在Telegram中向你的bot发送任意消息（如 /start）")
        print("2. 运行: python3 get_chat_id.py YOUR_BOT_TOKEN")
        sys.exit(1)

    bot_token = sys.argv[1]
    get_chat_id(bot_token)
