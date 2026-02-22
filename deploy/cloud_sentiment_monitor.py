#!/usr/bin/env python3
"""
云端情绪监控服务 - 阿里云7x24小时运行
自动监控港股/美股/韩股情绪变化，推送到Telegram

功能：
1. 定时扫描持仓股情绪
2. 发现异常情绪变化时推送告警
3. 盘前/盘后自动生成报告
"""
import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Telegram配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '7082819163')

# 监控股票列表
WATCHLIST = [
    {'code': '09880', 'name': '优必选', 'market': 'HK'},
    {'code': '02513', 'name': '智谱', 'market': 'HK'},
    {'code': '00100', 'name': 'MiniMax', 'market': 'HK'},
    {'code': '06082', 'name': '壁仞科技', 'market': 'HK'},
    {'code': '02577', 'name': '英诺赛科', 'market': 'HK'},
    {'code': '02432', 'name': '越疆', 'market': 'HK'},
    {'code': '00772', 'name': '阅文集团', 'market': 'HK'},
    {'code': '09988', 'name': '阿里巴巴', 'market': 'HK'},
    {'code': '00700', 'name': '腾讯', 'market': 'HK'},
]

# 上次情绪记录（用于检测变化）
last_sentiments: Dict[str, str] = {}


def send_telegram(message: str) -> bool:
    """发送Telegram消息"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        resp = requests.post(url, data=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram推送失败: {e}")
        return False


def get_xueqiu_quote(stock_code: str) -> Optional[Dict]:
    """从雪球获取行情（移动端API）"""
    try:
        headers = {
            'User-Agent': 'Xueqiu iPhone 14.17',
            'Accept': 'application/json',
        }
        url = 'https://stock.xueqiu.com/v5/stock/quote.json'
        params = {'symbol': stock_code.zfill(5), 'extend': 'detail'}
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            return data.get('data', {}).get('quote', {})
        return None
    except:
        return None


def analyze_sentiment_openai(stock_name: str, stock_code: str) -> Optional[Dict]:
    """使用OpenAI分析情绪"""
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        return None

    try:
        headers = {
            'Authorization': f'Bearer {openai_key}',
            'Content-Type': 'application/json'
        }

        prompt = f"""分析股票 {stock_name}({stock_code}) 的当前市场情绪。

请简洁回答：
1. 情绪：positive/neutral/negative
2. 热度：0-100
3. 一句话总结（20字内）

格式：情绪|热度|总结"""

        data = {
            'model': 'gpt-4o-mini',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 100,
            'temperature': 0.3
        }

        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )

        if resp.status_code == 200:
            content = resp.json()['choices'][0]['message']['content']
            parts = content.strip().split('|')
            if len(parts) >= 3:
                return {
                    'sentiment': parts[0].strip().lower(),
                    'heat': int(parts[1].strip()),
                    'summary': parts[2].strip()
                }
        return None
    except Exception as e:
        print(f"OpenAI分析失败: {e}")
        return None


def is_trading_hours() -> bool:
    """判断是否港股交易时间"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()

    if weekday >= 5:  # 周末
        return False

    # 港股 9:30-12:00, 13:00-16:00
    if (hour == 9 and minute >= 30) or (10 <= hour <= 11):
        return True
    if 13 <= hour <= 15:
        return True

    return False


def is_premarket() -> bool:
    """判断是否盘前（8:00-9:30）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    if now.hour == 8 or (now.hour == 9 and now.minute < 30):
        return True
    return False


def is_postmarket() -> bool:
    """判断是否盘后（16:00-17:00）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    if now.hour == 16:
        return True
    return False


def scan_watchlist() -> str:
    """扫描监控列表"""
    global last_sentiments

    results = []
    alerts = []

    for stock in WATCHLIST:
        code = stock['code']
        name = stock['name']

        # 获取雪球行情
        quote = get_xueqiu_quote(code)

        # 获取情绪分析
        sentiment_data = analyze_sentiment_openai(name, code)

        if quote:
            percent = quote.get('percent', 0) or 0
            current = quote.get('current', 0)

            # 根据涨跌判断情绪
            if percent > 5:
                mood = '🚀'
            elif percent > 2:
                mood = '📈'
            elif percent < -5:
                mood = '💥'
            elif percent < -2:
                mood = '📉'
            else:
                mood = '➖'

            result = f"{mood} {name}: {current} ({percent:+.1f}%)"

            if sentiment_data:
                result += f" | {sentiment_data['summary']}"

            results.append(result)

            # 检测情绪变化
            current_sentiment = sentiment_data['sentiment'] if sentiment_data else 'neutral'
            last_sentiment = last_sentiments.get(code, 'neutral')

            if last_sentiment != current_sentiment:
                if current_sentiment == 'negative' and last_sentiment == 'positive':
                    alerts.append(f"⚠️ {name} 情绪转负！")
                elif current_sentiment == 'positive' and last_sentiment == 'negative':
                    alerts.append(f"🔔 {name} 情绪转正！")

            last_sentiments[code] = current_sentiment

    # 生成报告
    report = f"📊 *持仓情绪扫描*\n"
    report += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report += "\n".join(results)

    if alerts:
        report += "\n\n*⚡ 情绪变化告警*\n"
        report += "\n".join(alerts)

    return report


def generate_daily_report() -> str:
    """生成每日报告"""
    report = f"📋 *每日情绪报告*\n"
    report += f"📅 {datetime.now().strftime('%Y-%m-%d')}\n\n"

    bullish = []
    bearish = []

    for stock in WATCHLIST:
        code = stock['code']
        name = stock['name']

        quote = get_xueqiu_quote(code)
        if quote:
            percent = quote.get('percent', 0) or 0
            if percent > 0:
                bullish.append(f"🟢 {name} +{percent:.1f}%")
            else:
                bearish.append(f"🔴 {name} {percent:.1f}%")

    if bullish:
        report += "*上涨*\n" + "\n".join(bullish) + "\n\n"
    if bearish:
        report += "*下跌*\n" + "\n".join(bearish)

    return report


def main():
    """主循环"""
    print(f"[{datetime.now()}] 🚀 云端情绪监控服务启动")
    print("=" * 60)
    print(f"监控股票数量: {len(WATCHLIST)}")
    print(f"Telegram推送: {TELEGRAM_CHAT_ID}")
    print("=" * 60)

    last_scan = datetime.now() - timedelta(hours=1)
    last_daily_report = None

    while True:
        now = datetime.now()

        try:
            # 盘前报告（每天8:30）
            if is_premarket() and now.hour == 8 and now.minute >= 30:
                if last_daily_report != now.date():
                    print(f"[{now}] 📋 发送盘前报告...")
                    report = "🌅 *盘前提醒*\n\n今日关注：\n"
                    for s in WATCHLIST[:5]:
                        report += f"• {s['name']} ({s['code']})\n"
                    send_telegram(report)
                    last_daily_report = now.date()

            # 交易时间扫描（每30分钟）
            if is_trading_hours():
                if (now - last_scan).seconds >= 1800:  # 30分钟
                    print(f"[{now}] 🔍 扫描持仓情绪...")
                    report = scan_watchlist()
                    print(report)

                    # 如果有告警，推送到Telegram
                    if '⚠️' in report or '🔔' in report:
                        send_telegram(report)

                    last_scan = now

                time.sleep(60)  # 1分钟检查一次

            # 盘后报告（16:30）
            elif is_postmarket() and now.minute >= 30:
                if last_daily_report != now.date() or now.hour == 16:
                    print(f"[{now}] 📋 发送盘后报告...")
                    report = generate_daily_report()
                    send_telegram(report)
                    last_daily_report = now.date()
                    time.sleep(3600)

            else:
                # 非交易时间
                print(f"[{now}] 💤 非交易时间，等待中...")
                time.sleep(1800)  # 30分钟检查一次

        except Exception as e:
            print(f"[{now}] ❌ 错误: {e}")
            time.sleep(60)


if __name__ == '__main__':
    main()
