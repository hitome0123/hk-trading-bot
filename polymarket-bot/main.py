#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Polymarket Copy Trading Bot - 主程序

高胜率自动跟单机器人
- 识别Sharp交易员（70%+胜率）
- 半凯利仓位计算
- 多层风险管理
- 自动执行跟单

作者：Claude Code + skill-from-masters
日期：2026-01-27
"""

import asyncio
import sys
import signal
from pathlib import Path
from typing import Optional
import structlog

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import get_config, BotConfig
from sharp_trader_identifier import SharpTraderIdentifier
from kelly_criterion import KellyCriterion
from risk_manager import RiskManager, RiskLimits
from trade_executor import TradeExecutor
from telegram_notifier import TelegramNotifier

logger = structlog.get_logger()


class PolymarketCopyBot:
    """Polymarket跟单机器人主类"""

    def __init__(self, config: BotConfig):
        self.config = config
        self.running = False

        # 组件
        self.sharp_identifier: Optional[SharpTraderIdentifier] = None
        self.kelly_calculator: Optional[KellyCriterion] = None
        self.risk_manager: Optional[RiskManager] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.telegram: Optional[TelegramNotifier] = None

        # Sharp交易员列表
        self.sharp_traders: list = []

        logger.info(
            "Polymarket跟单机器人初始化",
            mode="🎮 模拟交易" if config.paper_trading else "💰 真实交易",
            initial_balance=f"${config.initial_balance:,.0f}" if config.paper_trading else "链上查询"
        )

    async def initialize(self):
        """初始化所有组件"""
        logger.info("初始化组件...")

        # 1. Sharp交易员识别器
        self.sharp_identifier = SharpTraderIdentifier(
            polytrack_api_url=self.config.api.polytrack_api_url,
            polymarket_api_url=self.config.api.polymarket_api_url
        )
        logger.info("✓ Sharp交易员识别器")

        # 2. 凯利准则计算器
        self.kelly_calculator = KellyCriterion(
            max_bet_pct=self.config.kelly_sizing.max_bet_pct,
            max_total_exposure_pct=self.config.kelly_sizing.max_total_exposure_pct,
            min_edge_pct=self.config.kelly_sizing.min_edge_pct,
            use_quarter_kelly=self.config.kelly_sizing.use_quarter_kelly
        )
        logger.info("✓ 凯利准则计算器")

        # 3. 风险管理器
        risk_limits = RiskLimits(
            max_per_trade_pct=self.config.risk_management.max_per_trade_pct,
            max_per_trade_usd=self.config.risk_management.max_per_trade_usd,
            max_total_exposure_pct=self.config.risk_management.max_total_exposure_pct,
            max_per_market_pct=self.config.risk_management.max_per_market_pct,
            max_per_trader_pct=self.config.risk_management.max_per_trader_pct,
            daily_loss_limit_pct=self.config.risk_management.daily_loss_limit_pct,
            consecutive_loss_limit=self.config.risk_management.consecutive_loss_limit,
            sharp_trader_drawdown_pct=self.config.risk_management.sharp_trader_drawdown_pct,
            api_error_threshold=self.config.risk_management.api_error_threshold,
            min_market_liquidity_usd=self.config.risk_management.min_market_liquidity_usd,
            max_slippage_pct=self.config.risk_management.max_slippage_pct,
            max_trade_age_seconds=self.config.risk_management.max_trade_age_seconds
        )
        self.risk_manager = RiskManager(limits=risk_limits)
        logger.info("✓ 风险管理器")

        # 4. Telegram通知器
        self.telegram = TelegramNotifier(
            bot_token=self.config.telegram.bot_token,
            chat_id=self.config.telegram.chat_id,
            enabled=self.config.telegram.enabled
        )
        logger.info("✓ Telegram通知器")

        # 5. 扫描Sharp交易员（可选：从配置或API获取）
        # TODO: 从配置文件或数据库加载已识别的Sharp交易员
        # 这里演示手动指定
        logger.info("加载Sharp交易员列表...")
        # self.sharp_traders = await self._scan_sharp_traders()

        # Sharp交易员地址列表
        self.sharp_traders = [
            "0xc6587b11a2209e46dfe3928b31c5514a8e33b784",  # Erasmus - 政治+宏观专家，$1.3M+利润
            # 可以添加更多Sharp交易员：
            # "0x2728d99b2405a52db60160837e130b3ba3c1a83c",  # WindWalk3 - 大赌注专家
        ]

        if not self.sharp_traders:
            logger.warning(
                "⚠️ 未配置Sharp交易员！\n"
                "请添加交易员地址到sharp_traders列表"
            )
            return False

        logger.info(f"✓ 已加载{len(self.sharp_traders)}个Sharp交易员")

        # 6. 交易执行器
        self.trade_executor = TradeExecutor(
            config=self.config,
            kelly_calculator=self.kelly_calculator,
            risk_manager=self.risk_manager,
            sharp_trader_addresses=self.sharp_traders,
            telegram_notifier=self.telegram
        )
        logger.info("✓ 交易执行引擎")

        logger.info("🎉 所有组件初始化完成！")
        return True

    async def _scan_sharp_traders(self, top_n: int = 5):
        """
        扫描Polymarket寻找Sharp交易员

        注意：需要手动提供交易员地址列表，因为Polymarket不公开排行榜API
        """
        logger.info("扫描Sharp交易员（需要手动提供地址列表）...")

        # 示例地址列表（需要用户从polymarket.com/leaderboard手动获取）
        candidate_addresses = [
            # "0x...",  # 从排行榜复制地址
        ]

        if not candidate_addresses:
            logger.warning(
                "没有候选交易员地址。\n"
                "请访问 https://polymarket.com/leaderboard 获取地址"
            )
            return []

        # 分析候选交易员
        sharp_traders = await self.sharp_identifier.find_sharp_traders(
            wallet_addresses=candidate_addresses,
            top_n=top_n
        )

        return [trader.wallet_address for trader in sharp_traders]

    async def start(self):
        """启动机器人"""
        if not await self.initialize():
            logger.error("初始化失败，退出")
            return

        self.running = True

        logger.info("=" * 80)
        logger.info(" 🚀 Polymarket跟单机器人启动！")
        logger.info("=" * 80)
        logger.info(f" 模式: {'🎮 模拟交易' if self.config.paper_trading else '💰 真实交易'}")
        logger.info(f" Sharp交易员: {len(self.sharp_traders)}个")
        logger.info(f" 轮询间隔: {self.config.polling.position_check_seconds}秒")
        logger.info(f" 凯利模式: {'半凯利' if self.config.kelly_sizing.use_half_kelly else '四分之一凯利'}")
        logger.info(f" 单笔上限: {self.config.kelly_sizing.max_bet_pct:.0%}")
        logger.info(f" 总敞口上限: {self.config.risk_management.max_total_exposure_pct:.0%}")
        logger.info("=" * 80)

        if self.config.paper_trading:
            logger.warning("⚠️  当前为模拟交易模式，不会执行真实订单")
        else:
            logger.warning("⚠️  真实交易模式 - 将执行真实订单！")

        # 发送Telegram启动通知
        if self.telegram and self.telegram.enabled:
            await self.telegram.notify_bot_start({
                'mode': '🎮 模拟交易' if self.config.paper_trading else '💰 真实交易',
                'sharp_traders': len(self.sharp_traders),
                'balance': self.config.initial_balance if self.config.paper_trading else 0,
                'polling_seconds': self.config.polling.position_check_seconds
            })

        # 启动执行器
        try:
            await self.trade_executor.start()
        except KeyboardInterrupt:
            logger.info("\n接收到停止信号...")
        except Exception as e:
            logger.error(
                "执行器错误",
                error_type=type(e).__name__,
                error_msg=str(e)
            )
        finally:
            await self.shutdown()

    async def shutdown(self):
        """关闭机器人"""
        logger.info("正在关闭...")
        self.running = False

        if self.trade_executor:
            await self.trade_executor.close()

        if self.sharp_identifier:
            await self.sharp_identifier.close()

        logger.info("✅ 机器人已安全关闭")

    async def get_status(self):
        """获取机器人状态"""
        if not self.trade_executor:
            return {"status": "未初始化"}

        executor_status = await self.trade_executor.get_status()
        risk_summary = self.risk_manager.get_risk_summary(
            current_bankroll=executor_status.get('balance', 10000)
        )

        return {
            "执行器": executor_status,
            "风险": risk_summary
        }


def setup_signal_handlers(bot):
    """设置信号处理器（优雅退出）"""
    def signal_handler(sig, frame):
        logger.info(f"\n接收到信号: {sig}")
        if bot.running:
            # 触发shutdown
            asyncio.create_task(bot.shutdown())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """主函数"""
    # 显示欢迎信息
    print("\n" + "=" * 80)
    print("  🎯 Polymarket高胜率跟单机器人")
    print("  📊 基于Sharp交易员识别 + 凯利准则 + 多层风险管理")
    print("  🔬 方法论来源: skill-from-masters (Ed Thorp, Larry Williams)")
    print("=" * 80 + "\n")

    # 检查配置文件
    config_path = Path("config.yaml")
    if not config_path.exists():
        print("❌ 错误：找不到config.yaml")
        print("请复制 config.example.yaml 为 config.yaml 并配置\n")
        print("关键配置：")
        print("  1. 设置环境变量: export WALLET_PRIVATE_KEY='your_key'")
        print("  2. 配置RPC URL")
        print("  3. 添加Sharp交易员地址")
        print("  4. 设置 paper_trading: true (首次运行)")
        return

    # 检查环境变量
    if not os.environ.get('WALLET_PRIVATE_KEY'):
        print("❌ 错误：未设置 WALLET_PRIVATE_KEY 环境变量")
        print("请设置：export WALLET_PRIVATE_KEY='your_private_key'")
        print("或在.env文件中添加\n")
        return

    try:
        # 加载配置
        config = get_config()

        # 创建机器人
        bot = PolymarketCopyBot(config)

        # 设置信号处理
        setup_signal_handlers(bot)

        # 启动
        await bot.start()

    except FileNotFoundError as e:
        logger.error(f"配置文件错误: {e}")
    except RuntimeError as e:
        logger.error(f"运行时错误: {e}")
    except Exception as e:
        logger.error(
            "未预期错误",
            error_type=type(e).__name__,
            error_msg=str(e)
        )


if __name__ == '__main__':
    import os

    # 加载.env文件（如果存在）
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    # 配置日志
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # 运行
    asyncio.run(main())
