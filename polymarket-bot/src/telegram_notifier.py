#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram通知模块

发送Polymarket bot的实时通知到Telegram
"""

import httpx
import asyncio
from datetime import datetime
from typing import Optional
import structlog

logger = structlog.get_logger()


class TelegramNotifier:
    """Telegram通知发送器"""

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        self.bot_token = bot_token
        # 支持单个chat_id或多个chat_id（用逗号分隔）
        if isinstance(chat_id, str):
            self.chat_ids = [cid.strip() for cid in chat_id.split(',')]
        else:
            self.chat_ids = chat_id
        self.enabled = enabled
        self.client = httpx.AsyncClient(timeout=10.0)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        if self.enabled:
            logger.info("Telegram通知已启用", users=len(self.chat_ids))

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """发送消息到Telegram（支持多个用户）"""
        if not self.enabled:
            return False

        success_count = 0
        url = f"{self.base_url}/sendMessage"

        # 发送给所有chat_id
        for chat_id in self.chat_ids:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                }

                response = await self.client.post(url, json=payload)
                response.raise_for_status()
                success_count += 1

            except Exception as e:
                logger.error("Telegram发送失败", chat_id=chat_id[:10], error=str(e)[:100])

        if success_count > 0:
            logger.debug("Telegram消息已发送", users=success_count, message_length=len(text))
            return True
        return False

    async def notify_bot_start(self, config_summary: dict):
        """Bot启动通知"""
        text = f"""
🚀 <b>Polymarket Bot 已启动</b>

📊 <b>配置信息</b>
━━━━━━━━━━━━━━━━━━━━
• 模式: {config_summary.get('mode', 'N/A')}
• Sharp交易员: {config_summary.get('sharp_traders', 0)}个
• 初始余额: ${config_summary.get('balance', 0):,.0f}
• 轮询间隔: {config_summary.get('polling_seconds', 0)}秒

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def notify_new_position(self, trader: str, market: str, outcome: str,
                                  size_usd: float, price: float):
        """新仓位检测通知"""
        text = f"""
🔔 <b>新仓位检测</b>

👤 <b>交易员</b>
{trader[:10]}...{trader[-8:]}

📊 <b>市场</b>
{market[:50]}

📈 <b>详情</b>
━━━━━━━━━━━━━━━━━━━━
• 方向: <b>{outcome}</b>
• 价格: ${price:.3f}
• 规模: ${size_usd:,.0f}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def notify_trade_recommendation(self, details: dict):
        """
        超详细交易推荐通知

        Args:
            details: 包含以下字段的字典
                - market_title: 市场标题
                - market_id: 市场ID（用于生成链接）
                - outcome: YES/NO
                - current_price: 当前价格
                - sharp_trader: Sharp交易员地址
                - sharp_win_rate: Sharp交易员胜率
                - kelly_bet: 凯利推荐金额
                - kelly_fraction: 凯利分数
                - reasoning: 推荐原因
                - potential_profit: 预估收益
                - end_date: 结算日期
                - days_until_close: 距离结算天数
                - approved: 是否通过风险验证
                - rejection_reasons: 拒绝原因（如果有）
        """
        approved = details.get('approved', False)

        if approved:
            emoji = "✅"
            title = "交易推荐"
            color = "🟢"
        else:
            emoji = "❌"
            title = "风险拒绝"
            color = "🔴"

        # 市场信息
        market_full = details.get('market_title', 'Unknown')
        market = market_full[:60]  # 显示用的短标题
        market_slug = details.get('market_slug', '')
        condition_id = details.get('condition_id', '')
        outcome = details.get('outcome', 'N/A')
        price = details.get('current_price', 0)

        # Sharp trader信息
        trader = details.get('sharp_trader', '')

        # 生成链接 - 直接链接到Sharp trader的仓位页面
        trader_profile_link = f"https://polymarket.com/profile/{trader}"

        link_info = f"""
🔗 <b>查看盘口</b>
👉 <a href="{trader_profile_link}">打开Sharp交易员的仓位</a>
   （滚动找到这个市场，点 <b>{outcome}</b> 下单）

💡 或者手动搜索:
   标题: <code>{market_full[:80]}</code>
   买的位置: <b>{outcome}</b>"""

        # 结算日期和紧急程度
        end_date = details.get('end_date', 'N/A')
        days_until_close = details.get('days_until_close')

        # 紧急程度标识
        urgency = ""
        if days_until_close is not None:
            if days_until_close <= 3:
                urgency = "🔥 紧急 "
            elif days_until_close <= 7:
                urgency = "⚡ 短期 "
            elif days_until_close <= 30:
                urgency = "📅 中期 "
            else:
                urgency = "📆 长期 "

        # Sharp交易员信息（从上面移下来，因为上面已经用了）
        win_rate = details.get('sharp_win_rate', 0) * 100

        # 凯利计算
        kelly_bet = details.get('kelly_bet', 0)
        kelly_frac = details.get('kelly_fraction', 0)

        # 收益预估
        profit_if_win = details.get('potential_profit', 0)
        roi = (profit_if_win / kelly_bet * 100) if kelly_bet > 0 else 0

        # 原因
        reasoning = details.get('reasoning', '')[:150]

        text = f"""
{emoji} <b>{urgency}{title}</b>
{color}━━━━━━━━━━━━━━━━━━━━

{link_info}

📈 <b>交易详情</b>
• 买的位置: <b>{outcome}</b> ← 重要！
• 当前价格: ${price:.3f}
• 隐含概率: {price*100:.1f}%

⏰ <b>结算时间</b>
• 结算日期: {end_date}
• 剩余天数: {days_until_close}天 {urgency}

👤 <b>Sharp交易员</b>
{trader[:10]}...{trader[-8:]}
• 历史胜率: <b>{win_rate:.1f}%</b>

💰 <b>凯利推荐</b>
• 下注金额: <b>${kelly_bet:,.2f}</b>
• 凯利分数: {kelly_frac:.3f}
• 账户比例: {kelly_bet/10000*100:.1f}%

📊 <b>赔率分析</b>
• 市场赔率: {price:.3f}
• Sharp胜率: {win_rate:.1f}%
• Edge优势: {win_rate - price*100:+.1f}%

💵 <b>预估收益</b>
• 赢时收益: ${profit_if_win:,.2f}
• ROI: {roi:.1f}%
• 输时损失: -${kelly_bet:,.2f}

💡 <b>逻辑</b>
{reasoning}
"""

        if not approved:
            reasons = details.get('rejection_reasons', [])
            reasons_text = "\n".join([f"  • {r}" for r in reasons[:3]])
            text += f"""

⚠️ <b>拒绝原因</b>
{reasons_text}
"""

        text += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"

        await self.send_message(text.strip())

    async def notify_risk_rejection(self, market: str, reasons: list):
        """风险拒绝通知"""
        reasons_text = "\n".join([f"• {r}" for r in reasons[:3]])

        text = f"""
❌ <b>风险验证失败</b>

📊 {market[:40]}

⚠️ <b>拒绝原因</b>
━━━━━━━━━━━━━━━━━━━━
{reasons_text}

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def notify_trade_executed(self, market: str, outcome: str,
                                    size_usd: float, price: float, order_id: str):
        """交易执行通知"""
        text = f"""
✅ <b>模拟订单执行</b>

📊 {market[:40]}

📈 <b>交易详情</b>
━━━━━━━━━━━━━━━━━━━━
• 方向: <b>{outcome}</b>
• 价格: ${price:.3f}
• 金额: ${size_usd:,.2f}
• 订单号: {order_id[:20]}...

⏰ {datetime.now().strftime('%H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def notify_circuit_breaker(self, reason: str, details: str):
        """熔断器触发通知"""
        text = f"""
🚨 <b>熔断器触发！</b>

⚠️ <b>原因</b>
{reason}

📋 <b>详情</b>
{details[:150]}

🛑 Bot已暂停交易

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def notify_daily_summary(self, stats: dict):
        """每日总结通知"""
        text = f"""
📊 <b>每日总结</b>

💰 <b>今日数据</b>
━━━━━━━━━━━━━━━━━━━━
• 检测仓位: {stats.get('positions_detected', 0)}个
• 凯利推荐: {stats.get('kelly_approved', 0)}笔
• 风险拒绝: {stats.get('risk_rejected', 0)}笔
• 执行交易: {stats.get('trades_executed', 0)}笔

📈 <b>当前状态</b>
• 余额: ${stats.get('balance', 0):,.2f}
• 持仓: {stats.get('open_positions', 0)}个
• P&L: {stats.get('pnl', 0):+.2f}%

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        await self.send_message(text.strip())

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 测试函数
async def test_telegram():
    """测试Telegram通知"""
    # 从配置加载
    import sys
    sys.path.insert(0, 'src')
    from config import get_config

    config = get_config()

    notifier = TelegramNotifier(
        bot_token=config.telegram.bot_token,
        chat_id=config.telegram.chat_id,
        enabled=config.telegram.enabled
    )

    # 测试启动通知
    await notifier.notify_bot_start({
        'mode': '🎮 模拟交易',
        'sharp_traders': 1,
        'balance': 10000,
        'polling_seconds': 4
    })

    print("✅ 测试消息已发送！检查你的Telegram")

    await notifier.close()


if __name__ == '__main__':
    asyncio.run(test_telegram())
