#!/bin/bash
# 一键安装交易系统守护进程

set -e

echo "🚀 开始安装交易系统守护进程..."

# 创建必要目录
mkdir -p ~/hk-trading-bot/scripts
mkdir -p ~/hk-trading-bot/logs
mkdir -p ~/Library/LaunchAgents

# 1. 创建富途启动脚本
echo "📝 创建富途OpenD启动脚本..."
cat > ~/hk-trading-bot/scripts/start_futu.sh <<'EOF'
#!/bin/bash
sleep 30
open "/Users/mantou/Downloads/Futu_OpenD_9.6.5618_Mac 2/Futu_OpenD-GUI_9.6.5618_Mac"
sleep 10
if pgrep -f "Futu_OpenD" > /dev/null; then
    echo "[$(date)] 富途OpenD启动成功" >> ~/hk-trading-bot/logs/futu.log
else
    echo "[$(date)] 富途OpenD启动失败" >> ~/hk-trading-bot/logs/futu.log
fi
EOF
chmod +x ~/hk-trading-bot/scripts/start_futu.sh

# 2. 创建交易监控脚本
echo "📝 创建交易监控脚本..."
cat > ~/hk-trading-bot/scripts/trading_monitor.py <<'EOF'
#!/usr/bin/env python3
"""交易监控守护进程 - 每5分钟扫描市场信号"""
import sys
import time
import subprocess
from datetime import datetime

def is_trading_hours():
    """判断是否交易时间（港股9:30-16:00，工作日）"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:  # 周末
        return False

    # 港股交易时间
    if (hour == 9 and minute >= 30) or (10 <= hour <= 11):
        return True
    if 13 <= hour <= 15:
        return True

    return False

def run_analysis():
    """运行市场分析"""
    try:
        print(f"[{datetime.now()}] 🔍 开始市场扫描...")

        # 运行煤炭分析
        result = subprocess.run([
            'python3',
            '/Users/mantou/hk-trading-bot/coal_etf_analysis.py'
        ], timeout=120, capture_output=True, text=True)

        # 提取关键信息
        for line in result.stdout.split('\n'):
            if '突破评分' in line or '⭐' in line:
                print(line)

        print(f"[{datetime.now()}] ✅ 市场扫描完成\n")

    except subprocess.TimeoutExpired:
        print(f"[{datetime.now()}] ⚠️ 分析超时")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 错误: {e}")

def main():
    print(f"[{datetime.now()}] 🚀 交易监控守护进程启动")
    print("=" * 60)

    while True:
        if is_trading_hours():
            run_analysis()
            time.sleep(300)  # 交易时间：5分钟扫描一次
        else:
            # 非交易时间：显示等待状态
            now = datetime.now()
            print(f"[{now}] 💤 非交易时间，等待中...")
            time.sleep(3600)  # 1小时检查一次

if __name__ == '__main__':
    main()
EOF
chmod +x ~/hk-trading-bot/scripts/trading_monitor.py

# 3. 创建富途launchd配置
echo "📝 创建富途自动启动配置..."
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

# 4. 创建交易监控launchd配置
echo "📝 创建交易监控自动启动配置..."
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

# 5. 加载服务
echo "🔧 加载服务..."
launchctl unload ~/Library/LaunchAgents/com.mantou.futu.plist 2>/dev/null || true
launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist 2>/dev/null || true

launchctl load ~/Library/LaunchAgents/com.mantou.futu.plist
launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist

# 6. 创建管理脚本
cat > ~/hk-trading-bot/scripts/manage_daemon.sh <<'EOF'
#!/bin/bash
# 守护进程管理脚本

case "$1" in
    start)
        echo "🚀 启动服务..."
        launchctl load ~/Library/LaunchAgents/com.mantou.futu.plist
        launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已启动"
        ;;
    stop)
        echo "🛑 停止服务..."
        launchctl unload ~/Library/LaunchAgents/com.mantou.futu.plist
        launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已停止"
        ;;
    restart)
        echo "🔄 重启服务..."
        launchctl unload ~/Library/LaunchAgents/com.mantou.trading.plist 2>/dev/null || true
        launchctl load ~/Library/LaunchAgents/com.mantou.trading.plist
        echo "✅ 服务已重启"
        ;;
    status)
        echo "📊 服务状态："
        echo ""
        echo "富途OpenD："
        launchctl list | grep mantou.futu && echo "  ✅ 运行中" || echo "  ❌ 已停止"
        echo ""
        echo "交易监控："
        launchctl list | grep mantou.trading && echo "  ✅ 运行中" || echo "  ❌ 已停止"
        echo ""
        echo "进程："
        pgrep -f "Futu_OpenD" > /dev/null && echo "  富途: ✅" || echo "  富途: ❌"
        pgrep -f "trading_monitor" > /dev/null && echo "  监控: ✅" || echo "  监控: ❌"
        ;;
    logs)
        echo "📜 最近10条日志："
        echo ""
        echo "=== 交易监控日志 ==="
        tail -10 ~/hk-trading-bot/logs/trading_stdout.log 2>/dev/null || echo "暂无日志"
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOF
chmod +x ~/hk-trading-bot/scripts/manage_daemon.sh

# 7. 防止Mac休眠（需要sudo）
echo ""
echo "⚠️  需要设置Mac防止休眠（需要输入密码）"
read -p "是否设置？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo pmset -c sleep 0
    sudo pmset -c displaysleep 10
    sudo pmset -c disksleep 0
    echo "✅ 已设置Mac不休眠"
fi

echo ""
echo "=" * 60
echo "🎉 安装完成！"
echo ""
echo "管理命令："
echo "  启动: ~/hk-trading-bot/scripts/manage_daemon.sh start"
echo "  停止: ~/hk-trading-bot/scripts/manage_daemon.sh stop"
echo "  重启: ~/hk-trading-bot/scripts/manage_daemon.sh restart"
echo "  状态: ~/hk-trading-bot/scripts/manage_daemon.sh status"
echo "  日志: ~/hk-trading-bot/scripts/manage_daemon.sh logs"
echo ""
echo "快捷方式（添加到 ~/.zshrc）："
echo "  alias trading-start='~/hk-trading-bot/scripts/manage_daemon.sh start'"
echo "  alias trading-stop='~/hk-trading-bot/scripts/manage_daemon.sh stop'"
echo "  alias trading-status='~/hk-trading-bot/scripts/manage_daemon.sh status'"
echo "  alias trading-logs='tail -f ~/hk-trading-bot/logs/trading_stdout.log'"
echo ""
echo "查看实时日志："
echo "  tail -f ~/hk-trading-bot/logs/trading_stdout.log"
echo ""
echo "=" * 60
