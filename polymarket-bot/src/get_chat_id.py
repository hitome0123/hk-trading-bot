#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取Telegram Chat ID工具

使用方法：
1. 让朋友给bot发送 /start
2. 运行此脚本获取所有chat_id
"""

import requests
import sys
from pathlib import Path

# 从配置读取bot_token
sys.path.insert(0, str(Path(__file__).parent))
from config import get_config

def get_all_chat_ids():
    """获取所有给bot发过消息的chat_id"""
    try:
        config = get_config()
        bot_token = config.telegram.bot_token

        if not bot_token:
            print("❌ 错误：未配置bot_token")
            return

        # 调用Telegram API
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        data = response.json()

        if not data.get('ok'):
            print(f"❌ API错误: {data}")
            return

        updates = data.get('result', [])

        if not updates:
            print("⚠️  没有找到任何消息")
            print("请确保朋友已经给bot发送了 /start")
            return

        # 提取所有唯一的chat_id
        chat_ids = set()
        chat_info = {}

        for update in updates:
            if 'message' in update:
                msg = update['message']
                chat = msg.get('chat', {})
                chat_id = chat.get('id')
                if chat_id:
                    chat_ids.add(str(chat_id))
                    chat_info[str(chat_id)] = {
                        'first_name': chat.get('first_name', ''),
                        'last_name': chat.get('last_name', ''),
                        'username': chat.get('username', ''),
                        'type': chat.get('type', '')
                    }

        if not chat_ids:
            print("⚠️  没有找到chat_id")
            return

        print(f"\n✅ 找到 {len(chat_ids)} 个对话\n")
        print("=" * 60)

        for idx, chat_id in enumerate(sorted(chat_ids), 1):
            info = chat_info.get(chat_id, {})
            name = f"{info.get('first_name', '')} {info.get('last_name', '')}".strip()
            username = info.get('username', '')

            print(f"\n用户 {idx}:")
            print(f"  Chat ID: {chat_id}")
            if name:
                print(f"  姓名: {name}")
            if username:
                print(f"  用户名: @{username}")
            print(f"  类型: {info.get('type', 'unknown')}")

        print("\n" + "=" * 60)
        print("\n📋 复制下面这行到 config.yaml 的 chat_id 字段：")
        print(f"\nchat_id: \"{','.join(sorted(chat_ids))}\"")
        print("\n")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_all_chat_ids()
