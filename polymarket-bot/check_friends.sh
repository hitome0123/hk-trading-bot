#!/bin/bash
echo "检查是否有新用户..."
export $(cat .env | grep -v '^#' | xargs)
python3 src/get_chat_id.py
