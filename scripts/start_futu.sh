#!/bin/bash
sleep 30
open "/Users/mantou/Downloads/Futu_OpenD_9.6.5618_Mac 2/Futu_OpenD-GUI_9.6.5618_Mac"
sleep 10
if pgrep -f "Futu_OpenD" > /dev/null; then
    echo "[$(date)] 富途OpenD启动成功" >> ~/hk-trading-bot/logs/futu.log
else
    echo "[$(date)] 富途OpenD启动失败" >> ~/hk-trading-bot/logs/futu.log
fi
