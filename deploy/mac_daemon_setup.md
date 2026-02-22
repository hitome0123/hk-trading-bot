# Mac本地7x24小时运行交易系统

## 方案：Mac + launchd守护进程

适合你现在的Mac（不用买Mac mini），让程序持续运行。

---

## 1️⃣ 让富途OpenD开机自启

### 创建启动脚本

```bash
# 创建富途启动脚本
cat > ~/hk-trading-bot/scripts/start_futu.sh <<'EOF'
#!/bin/bash
# 等待系统完全启动
sleep 30

# 启动富途OpenD
open "/Users/mantou/Downloads/Futu_OpenD_9.6.5618_Mac 2/Futu_OpenD-GUI_9.6.5618_Mac"

# 等待富途启动完成
sleep 10

# 检查富途是否启动成功
if pgrep -f "Futu_OpenD" > /dev/null; then
    echo "[$(date)] 富途OpenD启动成功" >> ~/hk-trading-bot/logs/futu.log
else
    echo "[$(date)] 富途OpenD启动失败" >> ~/hk-trading-bot/logs/futu.log
fi
EOF

chmod +x ~/hk-trading-bot/scripts/start_futu.sh
```

### 创建launchd配置

```bash
# 创建开机自启配置
cat > ~/Library/LaunchAgents/com.mantou.futu.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mantou.futu</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/mantou/hk-trading-bot/scripts/start_futu.sh</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>Crashed</key>
        <true/>
    </dict>

    <key>StandardOutPath</key>
    <string>/Users/mantou/hk-trading-bot/logs/futu_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/mantou/hk-trading-bot/logs/futu_stderr.log</string>
</dict>
</plist>
EOF

# 加载配置
launchctl load ~/Library/LaunchAgents/com.mantou.futu.plist
```

---

## 2️⃣ 让交易监控脚本持续运行

### 创建主监控脚本

```bash
cat > ~/hk-trading-bot/scripts/trading_monitor.py <<'EOF'
#!/usr/bin/env python3
"""
交易监控守护进程
每5分钟扫描一次市场信号
"""
import sys
import time
import subprocess
from datetime import datetime

def is_trading_hours():
    """判断是否交易时间"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    # 周末不运行
    if weekday >= 5:
        return False

    # 港股交易时间：9:30-12:00, 13:00-16:00
    if (hour == 9 and minute >= 30) or (10 <= hour <= 11):
        return True
    if 13 <= hour <= 15:
        return True

    return False

def run_analysis():
    """运行市场分析"""
    try:
        print(f"[{datetime.now()}] 开始市场扫描...")

        # 运行煤炭分析
        subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/coal_etf_analysis.py'
        ], timeout=120)

        # 运行你的主策略
        subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/my_strategy_helper.py',
            'scan'
        ], timeout=120)

        print(f"[{datetime.now()}] 市场扫描完成")

    except Exception as e:
        print(f"[{datetime.now()}] 错误: {e}")

def main():
    print(f"[{datetime.now()}] 交易监控守护进程启动")

    while True:
        if is_trading_hours():
            run_analysis()
            # 交易时间：每5分钟扫描一次
            time.sleep(300)
        else:
            # 非交易时间：每小时检查一次
            time.sleep(3600)

if __name__ == '__main__':
    main()
EOF

chmod +x ~/hk-trading-bot/scripts/trading_monitor.py
```

### 创建守护进程配置

```bash
cat > ~/Library/LaunchAgents/com.mantou.trading.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mantou.trading</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/mantou/hk-trading-bot/scripts/trading_monitor.py</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/Users/mantou/hk-trading-bot/logs/trading_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>/Users/mantou/hk-trading-bot/logs/trading_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

# 加载配置
launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
```

---

## 3️⃣ 管理命令

### 启动服务
```bash
# 启动富途
launchctl load ~/Library/LaunchAgents/com.mantou.futu.plist

# 启动交易监控
launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
```

### 停止服务
```bash
# 停止富途
launchctl unload ~/Library/LaunchAgents/com.mantou.futu.plist

# 停止交易监控
launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist
```

### 重启服务
```bash
# 重启交易监控
launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist
launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
```

### 查看运行状态
```bash
# 查看进程
launchctl list | grep mantou

# 查看日志
tail -f ~/hk-trading-bot/logs/trading_stdout.log
tail -f ~/hk-trading-bot/logs/futu.log
```

---

## 4️⃣ Mac省电设置（重要）

### 防止Mac休眠
```bash
# 系统偏好设置 > 电池 > 电源适配器
# - 关闭"显示器关闭时，防止Mac自动进入睡眠"
# - 设置"关闭显示器"为"永不"

# 或用命令行（推荐）
sudo pmset -c sleep 0
sudo pmset -c displaysleep 10
sudo pmset -c disksleep 0
```

### 防止网络断开
```bash
# 系统偏好设置 > 网络 > Wi-Fi > 高级
# - 取消勾选"自动加入此网络"
# 建议用网线，更稳定
```

---

## 5️⃣ 监控和报警

### 配合Telegram推送（可选）

```bash
# 在 trading_monitor.py 中添加
import requests

def send_telegram(message):
    """发送Telegram通知"""
    bot_token = "YOUR_BOT_TOKEN"
    chat_id = "YOUR_CHAT_ID"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=data, timeout=10)
    except:
        pass

# 在关键位置调用
send_telegram(f"🚨 兖州煤业突破买入价！当前价：17.35")
```

---

## 6️⃣ 定时任务示例

### 每天收盘后发送总结报告

```bash
cat > ~/Library/LaunchAgents/com.mantou.daily-report.plist <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mantou.daily-report</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/mantou/hk-trading-bot/scripts/daily_report.py</string>
    </array>

    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>16</integer>
        <key>Minute</key>
        <integer>30</integer>
    </dict>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.mantou.daily-report.plist
```

---

## 7️⃣ 故障恢复

### 自动重启机制

launchd已经内置：
- `KeepAlive: true` - 进程崩溃自动重启
- `Crashed: true` - 异常退出自动重启

### 日志滚动（防止日志文件过大）

```bash
# 添加到 crontab
crontab -e

# 每周日凌晨3点清理旧日志
0 3 * * 0 find ~/hk-trading-bot/logs -name "*.log" -mtime +7 -delete
```

---

## ✅ 最终检查清单

- [ ] 富途OpenD自动启动
- [ ] 交易监控脚本运行
- [ ] Mac不休眠
- [ ] 日志正常写入
- [ ] Telegram通知测试
- [ ] 重启Mac测试自动恢复

---

## 💡 成本对比

| 方案 | 首年成本 | 年度成本 | 稳定性 |
|------|---------|---------|--------|
| 现有Mac | ¥0 | ¥120电费 | ⭐⭐⭐ |
| 买Mac mini | ¥4000 | ¥53电费 | ⭐⭐⭐⭐⭐ |
| 云服务器 | ¥318 | ¥318 | ⭐⭐⭐⭐ |

推荐：**先用现有Mac测试1-2个月，稳定后再决定是否买Mac mini**
