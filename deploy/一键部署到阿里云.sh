#!/bin/bash
# 一键部署交易系统到阿里云服务器
# 使用方法: ./一键部署到阿里云.sh

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 服务器配置
SERVER_IP="121.40.66.34"
SERVER_USER="root"

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    交易系统一键部署到阿里云${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# 检查SSH密码
echo -e "${YELLOW}步骤1: 测试SSH连接${NC}"
echo "服务器IP: $SERVER_IP"
echo ""
echo "请确保你已经在阿里云控制台重置了密码，并且重启了实例。"
echo ""
read -p "按回车继续..."

# 测试连接
echo ""
echo "测试SSH连接..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no $SERVER_USER@$SERVER_IP "echo '✅ 连接成功'" 2>/dev/null; then
    echo -e "${GREEN}✅ SSH连接成功！${NC}"
else
    echo -e "${RED}❌ SSH连接失败${NC}"
    echo ""
    echo "请检查："
    echo "1. 是否已在阿里云控制台重置密码？"
    echo "2. 是否已重启实例？"
    echo "3. 输入密码时是否正确？"
    exit 1
fi

echo ""
echo -e "${YELLOW}步骤2: 安装Python环境${NC}"
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

echo "更新系统..."
yum update -y 2>&1 | grep -v "^Reading\|^Downloading\|^Running" || true

echo "安装Python3..."
yum install -y python3 python3-pip python3-devel 2>&1 | grep -v "^Reading\|^Downloading\|^Running" || true

echo "验证Python版本..."
python3 --version

echo "✅ Python环境安装完成"
ENDSSH

echo ""
echo -e "${YELLOW}步骤3: 打包并上传项目${NC}"

# 打包项目
cd ~/hk-trading-bot
echo "打包项目文件..."
tar -czf /tmp/hk-trading-bot.tar.gz \
    coal_etf_analysis.py \
    my_strategy_helper.py \
    requirements.txt \
    港股交易完整策略手册_v2.0.md \
    主力成本分析策略.md \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='.git' \
    2>/dev/null || true

echo "上传到服务器..."
scp /tmp/hk-trading-bot.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

echo ""
echo -e "${YELLOW}步骤4: 解压并安装依赖${NC}"
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

echo "创建目录..."
mkdir -p /opt/trading-bot
cd /opt/trading-bot

echo "解压项目..."
tar -xzf /tmp/hk-trading-bot.tar.gz

echo "创建虚拟环境..."
python3 -m venv venv

echo "激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install akshare -q

echo "✅ 依赖安装完成"
ENDSSH

echo ""
echo -e "${YELLOW}步骤5: 创建监控服务${NC}"
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

cat > /opt/trading-bot/monitor_service.py <<'EOF'
#!/usr/bin/env python3
"""
交易监控服务 - 运行在阿里云服务器
每5分钟扫描一次市场（仅交易时间）
"""
import sys
import time
import subprocess
from datetime import datetime

def is_trading_hours():
    """判断是否交易时间（港股9:30-16:00，工作日）"""
    now = datetime.now()
    hour = now.hour
    weekday = now.weekday()

    if weekday >= 5:  # 周末
        return False

    # 港股交易时间
    if 9 <= hour <= 15:
        return True

    return False

def run_coal_analysis():
    """运行煤炭分析"""
    try:
        print(f"[{datetime.now()}] 🔍 运行煤炭ETF分析...")
        result = subprocess.run([
            '/opt/trading-bot/venv/bin/python3',
            '/opt/trading-bot/coal_etf_analysis.py'
        ], timeout=120, capture_output=True, text=True)

        # 只输出关键信息
        for line in result.stdout.split('\n'):
            if '突破评分' in line or '⭐' in line or '最优标的' in line:
                print(line)

        print(f"[{datetime.now()}] ✅ 分析完成\n")

    except subprocess.TimeoutExpired:
        print(f"[{datetime.now()}] ⚠️ 分析超时")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ 错误: {e}")

def main():
    print(f"[{datetime.now()}] 🚀 交易监控服务启动")
    print("=" * 60)
    print("服务器: 阿里云 121.40.66.34")
    print("运行模式: 7x24小时")
    print("扫描频率: 交易时间每5分钟")
    print("=" * 60)

    while True:
        if is_trading_hours():
            run_coal_analysis()
            time.sleep(300)  # 5分钟
        else:
            now = datetime.now()
            print(f"[{now}] 💤 非交易时间，等待中...")
            time.sleep(3600)  # 1小时

if __name__ == '__main__':
    main()
EOF

chmod +x /opt/trading-bot/monitor_service.py

echo "✅ 监控服务创建完成"
ENDSSH

echo ""
echo -e "${YELLOW}步骤6: 配置systemd开机自启${NC}"
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

cat > /etc/systemd/system/trading-monitor.service <<'EOF'
[Unit]
Description=Trading Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/trading-bot
ExecStart=/opt/trading-bot/venv/bin/python3 /opt/trading-bot/monitor_service.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trading-monitor.service

echo "✅ 开机自启配置完成"
ENDSSH

echo ""
echo -e "${YELLOW}步骤7: 启动服务${NC}"
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

systemctl start trading-monitor.service
sleep 2
systemctl status trading-monitor.service --no-pager

echo ""
echo "✅ 服务已启动"
ENDSSH

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}    🎉 部署完成！${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "服务器信息:"
echo "  IP: $SERVER_IP"
echo "  位置: /opt/trading-bot"
echo ""
echo "管理命令（在服务器上执行）:"
echo "  ssh root@$SERVER_IP"
echo "  systemctl status trading-monitor   # 查看状态"
echo "  systemctl restart trading-monitor  # 重启服务"
echo "  journalctl -u trading-monitor -f   # 查看日志"
echo ""
echo "⚠️  注意：富途OpenD仍需在本地Mac运行"
echo ""
read -p "按回车查看实时日志..."

echo ""
echo "正在连接服务器查看日志（按Ctrl+C退出）..."
ssh $SERVER_USER@$SERVER_IP "journalctl -u trading-monitor -f"
