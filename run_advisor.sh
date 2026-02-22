#!/bin/bash
# 板块交易顾问 - 定时运行脚本

# 设置环境变量
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export GEMINI_API_KEY="AIzaSyAKEu9CUAnfLU_BQGgQdBjA0oxBrNkc8M0"
export PATH="/Users/mantou/miniconda3/bin:$PATH"

# 进入工作目录
cd /Users/mantou/hk-trading-bot

# 记录开始时间
echo "========================================" >> logs/advisor_cron.log
date >> logs/advisor_cron.log

# 运行板块交易顾问
/Users/mantou/miniconda3/bin/python3 sector_trading_advisor.py >> logs/advisor_cron.log 2>&1

# 记录结束时间
echo "完成于:" >> logs/advisor_cron.log
date >> logs/advisor_cron.log
echo "" >> logs/advisor_cron.log
