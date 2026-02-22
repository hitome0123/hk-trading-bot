#!/bin/bash
# 更新阿里云情绪监控服务
# 使用方法: ./update_cloud_service.sh

set -e

SERVER_IP="121.40.66.34"
SERVER_USER="root"

echo "🚀 更新阿里云情绪监控服务"
echo "服务器: $SERVER_IP"
echo ""

# 1. 上传新文件
echo "📤 上传文件..."
scp ~/hk-trading-bot/deploy/cloud_sentiment_monitor.py $SERVER_USER@$SERVER_IP:/opt/trading-bot/
scp ~/hk-trading-bot/sentiment_hub.py $SERVER_USER@$SERVER_IP:/opt/trading-bot/
scp ~/hk-trading-bot/gemini_deep_research.py $SERVER_USER@$SERVER_IP:/opt/trading-bot/

# 2. 上传环境变量
echo "📤 上传环境变量..."
scp ~/hk-trading-bot/.env $SERVER_USER@$SERVER_IP:/opt/trading-bot/

# 3. 安装依赖并更新服务
echo "🔧 更新服务..."
ssh $SERVER_USER@$SERVER_IP <<'ENDSSH'
set -e

cd /opt/trading-bot
source venv/bin/activate

# 安装新依赖
pip install python-dotenv openai requests -q

# 更新systemd服务
cat > /etc/systemd/system/sentiment-monitor.service <<'EOF'
[Unit]
Description=Sentiment Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/trading-bot
EnvironmentFile=/opt/trading-bot/.env
ExecStart=/opt/trading-bot/venv/bin/python3 /opt/trading-bot/cloud_sentiment_monitor.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sentiment-monitor.service
systemctl restart sentiment-monitor.service

echo "✅ 服务已更新"
systemctl status sentiment-monitor.service --no-pager
ENDSSH

echo ""
echo "✅ 更新完成！"
echo ""
echo "管理命令："
echo "  ssh root@$SERVER_IP"
echo "  systemctl status sentiment-monitor   # 查看状态"
echo "  journalctl -u sentiment-monitor -f   # 查看日志"
echo ""
echo "📱 Telegram会收到："
echo "  - 盘前提醒 (8:30)"
echo "  - 情绪变化告警 (实时)"
echo "  - 盘后报告 (16:30)"
