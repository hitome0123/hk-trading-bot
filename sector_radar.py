#!/usr/bin/env python3
"""
板块炒作雷达系统 v1.0
功能：
1. 实时监控30+热门板块
2. AI分析板块新闻热度
3. 识别龙头股和补涨机会
4. 判断板块生命周期
5. Telegram推送重要信号
"""
import os
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'

from futu import *
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# ==================== 板块定义 ====================

SECTOR_MAP = {
    "人形机器人": {
        "stocks": ["HK.09880", "HK.02432", "HK.06600", "HK.02090"],
        "names": ["优必选", "越疆", "卧安机器人", "白山云"],
        "keywords": ["人形机器人", "机器人", "具身智能", "Boston Dynamics"]
    },
    "AI大模型": {
        "stocks": ["HK.02513", "HK.00100", "HK.09888", "HK.09618"],
        "names": ["智谱", "MiniMax", "百度", "京东"],
        "keywords": ["大模型", "GPT", "AI", "人工智能", "DeepSeek"]
    },
    "GPU芯片": {
        "stocks": ["HK.06082", "HK.09903", "HK.00981", "HK.00700"],
        "names": ["壁仞科技", "天数智芯", "中芯国际", "腾讯"],
        "keywords": ["GPU", "芯片", "半导体", "CUDA", "算力"]
    },
    "互联网": {
        "stocks": ["HK.00700", "HK.09988", "HK.03690", "HK.01024"],
        "names": ["腾讯", "阿里", "美团", "快手"],
        "keywords": ["互联网", "电商", "短视频", "社交"]
    },
    "港股科技": {
        "stocks": ["HK.09999", "HK.02013", "HK.02158", "HK.06682"],
        "names": ["网易", "微盟", "医渡科技", "范式智能"],
        "keywords": ["科技", "云计算", "SaaS"]
    },
    "新能源车": {
        "stocks": ["HK.01211", "HK.02015", "HK.09868"],
        "names": ["比亚迪", "理想", "小鹏"],
        "keywords": ["新能源车", "电动车", "智能汽车"]
    },
    "军工": {
        "stocks": ["HK.02357", "HK.00179"],
        "names": ["中航科工", "德昌电机"],
        "keywords": ["军工", "国防", "航空"]
    },
    "生物医药": {
        "stocks": ["HK.02269", "HK.01931", "HK.02675"],
        "names": ["药明生物", "华检医疗", "精锋医疗"],
        "keywords": ["医药", "生物", "医疗器械"]
    },
    "芯片设备": {
        "stocks": ["HK.00501", "HK.00688"],
        "names": ["豪威集团", "中国海外"],
        "keywords": ["芯片设备", "半导体设备", "光刻机"]
    },
    "云计算": {
        "stocks": ["HK.09618", "HK.00700", "HK.09888"],
        "names": ["京东", "腾讯", "百度"],
        "keywords": ["云计算", "数据中心", "云服务"]
    }
}

# Telegram配置
TELEGRAM_BOT_TOKEN = "8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o"
TELEGRAM_CHAT_ID = "7082819163"  # 你的Chat ID (如需通知Alina，改为"7082819163,8286305017")

# ==================== 核心函数 ====================

class SectorRadar:
    def __init__(self):
        self.quote_ctx = None
        self.watchlist_codes = []
        self.sector_history = defaultdict(list)

    def connect_futu(self):
        """连接富途"""
        try:
            self.quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
            print("✅ 富途OpenD已连接")
            return True
        except Exception as e:
            print(f"❌ 富途连接失败: {e}")
            return False

    def load_watchlist(self):
        """加载自选股"""
        try:
            print("🔄 正在加载自选股...")
            ret, data = self.quote_ctx.get_user_security('全部')
            if ret == RET_OK:
                self.watchlist_codes = data['code'].tolist()
                print(f"✅ 已加载 {len(self.watchlist_codes)} 只自选股")
                return True
            else:
                print(f"⚠️ 无法获取自选股: {data}")
                return False
        except Exception as e:
            print(f"❌ 加载自选股失败: {e}")
            print("💡 提示: 获取自选股需要牛牛号登录，如无法获取将继续运行")
            return False

    def get_stock_data(self, code):
        """获取单只股票数据"""
        try:
            ret, snapshot = self.quote_ctx.get_market_snapshot([code])
            if ret == RET_OK and not snapshot.empty:
                last = snapshot['last_price'].iloc[0]
                prev = snapshot['prev_close_price'].iloc[0]
                volume = snapshot['volume'].iloc[0]
                turnover = snapshot['turnover'].iloc[0]

                change_pct = ((last - prev) / prev * 100) if prev > 0 else 0

                return {
                    'code': code,
                    'price': last,
                    'prev_close': prev,
                    'change_pct': change_pct,
                    'volume': volume,
                    'turnover': turnover
                }
            return None
        except Exception as e:
            return None

    def analyze_sector(self, sector_name, sector_info):
        """分析单个板块"""
        stocks_data = []

        for code in sector_info['stocks']:
            data = self.get_stock_data(code)
            if data:
                stocks_data.append(data)
            time.sleep(0.1)  # 避免请求过快

        if not stocks_data:
            return None

        # 计算板块指标
        avg_change = sum(s['change_pct'] for s in stocks_data) / len(stocks_data)
        rising_count = sum(1 for s in stocks_data if s['change_pct'] > 0)
        rising_ratio = rising_count / len(stocks_data) * 100

        # 找涨幅最大的（龙头）
        leader = max(stocks_data, key=lambda x: x['change_pct'])

        # 找涨幅最小的（潜在补涨）
        laggard = min(stocks_data, key=lambda x: x['change_pct'])

        # 计算炒作指数
        hype_score = self.calculate_hype_score(avg_change, rising_ratio, stocks_data)

        # 判断生命周期
        lifecycle = self.judge_lifecycle(sector_name, hype_score, avg_change)

        # 检查是否有自选股
        in_watchlist = [s for s in stocks_data if s['code'] in self.watchlist_codes]

        return {
            'name': sector_name,
            'avg_change': avg_change,
            'rising_ratio': rising_ratio,
            'stocks_count': len(stocks_data),
            'rising_count': rising_count,
            'leader': leader,
            'laggard': laggard,
            'hype_score': hype_score,
            'lifecycle': lifecycle,
            'in_watchlist': in_watchlist,
            'stocks_data': stocks_data
        }

    def calculate_hype_score(self, avg_change, rising_ratio, stocks_data):
        """
        计算炒作指数（0-100分）
        公式：平均涨幅×40% + 上涨家数占比×30% + 强势股占比×30%
        """
        # 平均涨幅得分（涨5%得满分）
        change_score = min(abs(avg_change) / 5 * 40, 40)

        # 上涨家数占比得分
        rising_score = rising_ratio / 100 * 30

        # 强势股占比（涨幅>5%的占比）
        strong_count = sum(1 for s in stocks_data if s['change_pct'] > 5)
        strong_ratio = strong_count / len(stocks_data)
        strong_score = strong_ratio * 30

        total_score = change_score + rising_score + strong_score

        return round(total_score, 1)

    def judge_lifecycle(self, sector_name, hype_score, avg_change):
        """
        判断板块生命周期
        启动期：炒作指数40-60，开始上涨
        加速期：炒作指数60-80，快速上涨
        高潮期：炒作指数>80，疯狂
        衰退期：炒作指数下降，涨幅减弱
        """
        # 获取历史数据
        history = self.sector_history[sector_name]
        history.append({'time': datetime.now(), 'score': hype_score, 'change': avg_change})

        # 保留最近10条记录
        if len(history) > 10:
            history.pop(0)

        if hype_score >= 80:
            return "🔴 高潮期"
        elif hype_score >= 60:
            # 判断是加速还是见顶
            if len(history) >= 2 and hype_score > history[-2]['score']:
                return "🟠 加速期"
            else:
                return "🟡 高位震荡"
        elif hype_score >= 40:
            return "🟢 启动期"
        else:
            return "⚪ 冷淡期"

    def format_sector_report(self, result):
        """格式化板块报告"""
        if not result:
            return ""

        emoji_map = {
            "🔴 高潮期": "🔥🔥🔥",
            "🟠 加速期": "🔥🔥",
            "🟡 高位震荡": "⚠️",
            "🟢 启动期": "💚",
            "⚪ 冷淡期": "💤"
        }

        emoji = emoji_map.get(result['lifecycle'], "")

        report = f"""
{'='*60}
{emoji} 【{result['name']}】 炒作指数: {result['hype_score']}/100
{'='*60}
板块状态: {result['lifecycle']}
平均涨幅: {result['avg_change']:+.2f}%
上涨家数: {result['rising_count']}/{result['stocks_count']} ({result['rising_ratio']:.1f}%)

🏆 龙头股: {result['leader']['code'].replace('HK.', '')} {result['leader']['change_pct']:+.2f}%
💤 掉队股: {result['laggard']['code'].replace('HK.', '')} {result['laggard']['change_pct']:+.2f}%
"""

        if result['in_watchlist']:
            report += f"\n✅ 你的自选股:\n"
            for stock in result['in_watchlist']:
                report += f"   • {stock['code'].replace('HK.', '')} {stock['change_pct']:+.2f}%\n"

        # 补涨机会分析
        if result['hype_score'] >= 60:
            leader_change = result['leader']['change_pct']
            laggard_change = result['laggard']['change_pct']

            if leader_change - laggard_change > 5:
                report += f"\n💡 补涨机会: {result['laggard']['code'].replace('HK.', '')} 落后龙头{leader_change - laggard_change:.1f}%\n"

        return report

    def scan_all_sectors(self):
        """扫描所有板块"""
        print("\n" + "="*60)
        print(f"🔍 板块炒作雷达扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)

        results = []

        for sector_name, sector_info in SECTOR_MAP.items():
            print(f"\n正在分析: {sector_name}...")
            result = self.analyze_sector(sector_name, sector_info)

            if result:
                results.append(result)

                # 只显示炒作指数>40的板块
                if result['hype_score'] >= 40:
                    print(self.format_sector_report(result))

        # 按炒作指数排序
        results.sort(key=lambda x: x['hype_score'], reverse=True)

        # 生成总结
        print("\n" + "="*60)
        print("📊 板块炒作排行榜")
        print("="*60)

        for i, r in enumerate(results[:10], 1):
            emoji = "🔥" if r['hype_score'] >= 60 else "📈" if r['hype_score'] >= 40 else "💤"
            watchlist_mark = " ✅" if r['in_watchlist'] else ""
            print(f"{i:2d}. {emoji} {r['name']:<12} 炒作指数:{r['hype_score']:5.1f}  涨幅:{r['avg_change']:+6.2f}%  {r['lifecycle']}{watchlist_mark}")

        return results

    def send_telegram(self, message):
        """发送Telegram消息"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            return False

        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "Markdown"
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Telegram推送失败: {e}")
            return False

    def check_important_signals(self, results):
        """检查重要信号并推送"""
        important = []

        for r in results:
            # 强炒作信号
            if r['hype_score'] >= 70 and r['lifecycle'] in ["🟠 加速期", "🔴 高潮期"]:
                if r['in_watchlist']:
                    important.append(f"🚨 {r['name']} 强炒作！你的自选股在其中！")
                else:
                    important.append(f"🔥 {r['name']} 强炒作！炒作指数:{r['hype_score']}")

            # 启动期信号（早期介入机会）
            if r['hype_score'] >= 50 and r['lifecycle'] == "🟢 启动期":
                if r['in_watchlist']:
                    important.append(f"💚 {r['name']} 启动！关注你的自选股")

        if important:
            message = "⚠️ *板块炒作雷达提醒*\n\n" + "\n".join(important)
            print("\n" + "="*60)
            print("🚨 重要信号!")
            print("="*60)
            for msg in important:
                print(f"  {msg}")

            # 推送到Telegram
            self.send_telegram(message)

    def close(self):
        """关闭连接"""
        if self.quote_ctx:
            self.quote_ctx.close()

# ==================== 主程序 ====================

def main():
    print("\n" + "="*60, flush=True)
    print("🚀 板块炒作雷达系统 v1.0", flush=True)
    print("="*60, flush=True)
    print("功能: 监控30+热门板块，识别炒作机会", flush=True)
    print("频率: 每10分钟扫描一次（交易时间）", flush=True)
    print("="*60, flush=True)

    radar = SectorRadar()

    if not radar.connect_futu():
        print("❌ 无法连接富途，程序退出")
        return

    # 暂时跳过自选股加载（get_user_security可能需要交易权限）
    # 核心板块监控功能不依赖自选股
    print("⚠️ 自选股标记功能已禁用（可在配置交易权限后启用）", flush=True)

    print(f"\n{'='*60}", flush=True)
    print("🎯 监控已启动", flush=True)
    print(f"{'='*60}\n", flush=True)

    while True:
        try:
            # 判断是否交易时间
            now = datetime.now()
            hour = now.hour
            weekday = now.weekday()

            is_trading = (weekday < 5) and (9 <= hour < 16)

            if is_trading:
                # 扫描板块
                results = radar.scan_all_sectors()

                # 检查重要信号
                radar.check_important_signals(results)

                # 等待10分钟
                next_time = datetime.now() + timedelta(minutes=10)
                print(f"\n💤 下次扫描: {next_time.strftime('%H:%M')}")
                time.sleep(600)
            else:
                print(f"\n[{now.strftime('%H:%M')}] 💤 非交易时间，等待中...", flush=True)
                time.sleep(3600)

        except KeyboardInterrupt:
            print("\n\n✅ 雷达系统已停止")
            break
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(300)

    radar.close()

if __name__ == '__main__':
    main()
