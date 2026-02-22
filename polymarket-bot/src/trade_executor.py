#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易执行引擎

监控Sharp交易员仓位并自动跟单

核心功能：
- 4秒轮询Sharp交易员仓位
- 检测新交易
- 计算跟单规模（凯利准则）
- 执行Polymarket订单
- 追踪仓位状态
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import structlog

from utils import validate_wallet_address, truncate_wallet, APIRateLimiter
from kelly_criterion import KellyCriterion, KellyCalculation
from risk_manager import RiskManager, TradeValidation
from config import BotConfig

logger = structlog.get_logger()


@dataclass
class SharpTraderPosition:
    """Sharp交易员的仓位"""
    wallet_address: str
    market_id: str
    condition_id: str
    outcome: str  # YES or NO
    size: float  # 持仓大小（份额数）
    avg_price: float  # 平均价格
    current_price: float  # 当前价格
    initial_value: float  # 初始投入（USDC）
    current_value: float  # 当前价值（USDC）
    timestamp: datetime  # 检测时间
    market_title: str = ''  # 市场标题（直接从API获取）
    event_slug: str = ''  # 事件slug（用于构建链接）


@dataclass
class CopyTrade:
    """跟单交易"""
    sharp_trader: str  # Sharp交易员地址
    market_id: str
    condition_id: str
    outcome: str
    sharp_trader_size: float  # Sharp交易员仓位大小
    our_size: float  # 我们的跟单大小
    entry_price: float  # 入场价格
    entry_time: datetime
    status: str  # 'pending', 'filled', 'failed'
    order_id: Optional[str] = None


class TradeExecutor:
    """
    交易执行引擎

    职责：
    1. 监控Sharp交易员仓位变化
    2. 检测新开仓
    3. 计算跟单规模
    4. 执行Polymarket订单
    5. 管理仓位生命周期
    """

    def __init__(
        self,
        config: BotConfig,
        kelly_calculator: KellyCriterion,
        risk_manager: RiskManager,
        sharp_trader_addresses: List[str],
        telegram_notifier=None
    ):
        self.config = config
        self.kelly = kelly_calculator
        self.risk_manager = risk_manager
        self.sharp_traders = sharp_trader_addresses
        self.telegram = telegram_notifier

        # HTTP客户端
        self.client = httpx.AsyncClient(timeout=30.0)

        # API限流器
        self.rate_limiter = APIRateLimiter(
            max_calls=900,
            window_seconds=3600
        )

        # 状态追踪
        self.known_positions: Dict[str, Set[str]] = {}  # wallet -> set of position_ids
        self.our_positions: Dict[str, CopyTrade] = {}  # position_id -> CopyTrade
        self.copy_history: List[CopyTrade] = []

        # 初始化已知仓位
        for trader in self.sharp_traders:
            self.known_positions[trader] = set()

        # 模拟交易模式
        self.paper_trading = config.paper_trading
        self.paper_balance = config.initial_balance if self.paper_trading else 0.0

        logger.info(
            "交易执行引擎初始化",
            mode="模拟交易" if self.paper_trading else "真实交易",
            sharp_traders=len(self.sharp_traders),
            initial_balance=f"${self.paper_balance:,.0f}" if self.paper_trading else "链上查询"
        )

    async def start(self):
        """启动执行引擎"""
        logger.info("🚀 交易执行引擎启动")

        # 初次加载：标记所有现有仓位为已知（避免首次运行跟单历史仓位）
        await self._initialize_known_positions()

        logger.info("✓ 初始化完成，开始监控...")

        # 主循环
        while True:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(self.config.polling.position_check_seconds)
            except KeyboardInterrupt:
                logger.info("接收到停止信号")
                break
            except Exception as e:
                logger.error(
                    "监控循环错误",
                    error_type=type(e).__name__,
                    error_msg=str(e)[:200]
                )
                await asyncio.sleep(10)  # 错误后等10秒再重试

    async def _initialize_known_positions(self):
        """初始化已知仓位（首次运行时避免跟单历史）"""
        logger.info("初始化已知仓位...")

        for trader in self.sharp_traders:
            try:
                positions = await self._fetch_trader_positions(trader)

                for pos in positions:
                    position_id = self._get_position_id(
                        trader,
                        pos.market_id,
                        pos.outcome
                    )
                    self.known_positions[trader].add(position_id)

                logger.info(
                    "标记已知仓位",
                    trader=truncate_wallet(trader),
                    positions=len(positions)
                )

            except Exception as e:
                logger.error(
                    "初始化仓位失败",
                    trader=truncate_wallet(trader),
                    error=str(e)[:100]
                )

        logger.info(f"✓ 初始化完成，已标记{sum(len(p) for p in self.known_positions.values())}个历史仓位")

    async def _monitoring_cycle(self):
        """一个监控周期"""
        # 获取所有Sharp交易员的最新仓位
        all_positions: List[SharpTraderPosition] = []

        for trader in self.sharp_traders:
            try:
                positions = await self._fetch_trader_positions(trader)
                all_positions.extend(positions)
            except Exception as e:
                logger.error(
                    "获取仓位失败",
                    trader=truncate_wallet(trader),
                    error=str(e)[:100]
                )
                self.risk_manager.record_api_error()

        # 检测新仓位
        new_positions = self._detect_new_positions(all_positions)

        if new_positions:
            logger.info(
                f"检测到{len(new_positions)}个新仓位",
                positions=len(new_positions)
            )

            # 获取所有仓位的市场信息并按结算日期排序（优先处理即将结算的）
            positions_with_dates = []
            for pos in new_positions:
                market_info = await self._get_market_info(pos.condition_id, pos.market_title)
                days_until_close = market_info.get('days_until_close', 999)
                is_closed = market_info.get('is_closed', False)

                # 跳过已关闭的市场
                if is_closed or days_until_close < 0:
                    logger.debug(
                        "跳过已关闭市场",
                        market=pos.market_title[:40],
                        trader=truncate_wallet(pos.wallet_address)
                    )
                    continue

                positions_with_dates.append((pos, days_until_close))

            # 按结算日期排序（天数少的在前）
            positions_with_dates.sort(key=lambda x: x[1])

            logger.info(
                f"按结算日期排序完成，优先处理近期结算的市场",
                shortest_days=positions_with_dates[0][1] if positions_with_dates else 'N/A'
            )

            # 处理每个新仓位（按结算日期从近到远）
            for pos, days in positions_with_dates:
                await self._process_new_position(pos)

    async def _fetch_trader_positions(self, wallet_address: str) -> List[SharpTraderPosition]:
        """
        获取交易员的当前仓位

        Args:
            wallet_address: 交易员地址

        Returns:
            仓位列表
        """
        # 检查限流
        if not self.rate_limiter.can_call():
            wait_time = self.rate_limiter.wait_time()
            await asyncio.sleep(wait_time + 1)

        self.rate_limiter.record_call()

        # 调用Polymarket API
        url = f"{self.config.api.polymarket_api_url}/positions?user={wallet_address}"
        response = await self.client.get(url)
        response.raise_for_status()
        positions_data = response.json()

        # 转换为SharpTraderPosition对象
        positions = []
        for pos_data in positions_data:
            # 只关注有持仓的（size > 0）
            if float(pos_data.get('size', 0)) <= 0:
                continue

            position = SharpTraderPosition(
                wallet_address=wallet_address,
                market_id=pos_data.get('slug', ''),
                condition_id=pos_data.get('conditionId', ''),
                outcome=pos_data.get('outcome', ''),
                size=float(pos_data.get('size', 0)),
                avg_price=float(pos_data.get('avgPrice', 0)),
                current_price=float(pos_data.get('curPrice', 0)),
                initial_value=float(pos_data.get('initialValue', 0)),
                current_value=float(pos_data.get('currentValue', 0)),
                timestamp=datetime.now(),
                market_title=pos_data.get('title', 'Unknown Market'),
                event_slug=pos_data.get('eventSlug', '')
            )
            positions.append(position)

        return positions

    def _detect_new_positions(
        self,
        current_positions: List[SharpTraderPosition]
    ) -> List[SharpTraderPosition]:
        """
        检测新仓位（与已知仓位对比）

        Args:
            current_positions: 当前所有仓位

        Returns:
            新仓位列表
        """
        new_positions = []

        for pos in current_positions:
            position_id = self._get_position_id(
                pos.wallet_address,
                pos.market_id,
                pos.outcome
            )

            # 检查是否为新仓位
            if position_id not in self.known_positions[pos.wallet_address]:
                new_positions.append(pos)
                # 标记为已知
                self.known_positions[pos.wallet_address].add(position_id)

        return new_positions

    def _get_position_id(self, wallet: str, market_id: str, outcome: str) -> str:
        """生成仓位唯一ID"""
        return f"{wallet}:{market_id}:{outcome}"

    async def _get_market_info(self, condition_id: str, existing_title: str = '') -> dict:
        """
        获取市场详细信息（标题、结算日期、slug等）

        Args:
            condition_id: 市场条件ID
            existing_title: 已有的市场标题（从positions API获取）

        Returns:
            包含market_title, market_slug, end_date_iso, days_until_close的字典
        """
        try:
            # 调用Polymarket Gamma API - 使用condition_id查询
            url = f"https://gamma-api.polymarket.com/markets?condition_id={condition_id}"
            response = await self.client.get(url)
            response.raise_for_status()

            data = response.json()

            if data and len(data) > 0:
                market = data[0]

                # 检查市场是否已关闭
                is_closed = market.get('closed', False)
                is_active = market.get('active', True)

                # 如果市场已关闭或不活跃，标记为无效
                if is_closed or not is_active:
                    logger.debug(
                        "市场已关闭，跳过",
                        market=existing_title[:40] if existing_title else condition_id[:20],
                        closed=is_closed,
                        active=is_active
                    )
                    return {
                        'market_title': existing_title if existing_title else 'Closed Market',
                        'market_slug': condition_id[:20],
                        'end_date_iso': 'N/A',
                        'days_until_close': -1,  # -1表示市场已关闭
                        'is_closed': True
                    }

                # 优先使用已有的title（从positions API获取的），因为更准确
                market_title = existing_title if existing_title else market.get('question', market.get('title', 'Unknown Market'))
                market_slug = market.get('market_slug', market.get('slug', condition_id))
                end_date_iso = market.get('end_date_iso', market.get('endDate', 'N/A'))

                # 计算距离结算天数
                days_until_close = 999
                if end_date_iso and end_date_iso != 'N/A':
                    try:
                        from datetime import datetime as dt
                        # 处理ISO格式日期
                        date_str = end_date_iso.replace('Z', '+00:00')
                        end_date = dt.fromisoformat(date_str)
                        now = dt.now(end_date.tzinfo)
                        delta = end_date - now
                        days_until_close = max(0, delta.days)
                    except Exception as date_err:
                        logger.debug(f"日期解析失败: {end_date_iso}, error: {date_err}")
                        pass

                return {
                    'market_title': market_title,
                    'market_slug': market_slug,
                    'end_date_iso': end_date_iso[:10] if end_date_iso and end_date_iso != 'N/A' else 'N/A',
                    'days_until_close': days_until_close,
                    'is_closed': False
                }

        except Exception as e:
            logger.debug(
                "获取市场信息失败（将使用默认值）",
                condition_id=condition_id[:20],
                error=str(e)[:80]
            )

        # 返回默认值（不影响核心功能）
        return {
            'market_title': existing_title if existing_title else 'Unknown Market',
            'market_slug': condition_id[:20],  # 截取前20字符作为slug
            'end_date_iso': 'N/A',
            'days_until_close': 999,
            'is_closed': False
        }

    async def _process_new_position(self, position: SharpTraderPosition):
        """
        处理新检测到的仓位

        流程：
        1. 获取当前余额
        2. 计算凯利仓位
        3. 风险验证
        4. 执行订单
        """
        # 跳过价格为0的仓位（已结算市场或无效市场）
        if position.current_price <= 0:
            logger.debug(
                "跳过：价格为0的市场（可能已结算）",
                market=position.market_title[:40],
                trader=truncate_wallet(position.wallet_address)
            )
            return

        logger.info(
            "🔔 新仓位检测",
            trader=truncate_wallet(position.wallet_address),
            market=position.market_id[:30] + "..." if len(position.market_id) > 30 else position.market_id,
            outcome=position.outcome,
            price=f"{position.current_price:.3f}",
            size_usd=f"${position.initial_value:,.0f}"
        )

        try:
            # 1. 获取当前余额和敞口
            current_balance = await self._get_current_balance()
            current_exposure = self._calculate_current_exposure()

            # 2. 获取Sharp交易员信息（胜率）
            # TODO: 从数据库查询或缓存获取
            sharp_trader_win_rate = 0.75  # 临时：假设75%胜率

            # 3. 计算凯利仓位
            kelly_calc = self.kelly.calculate_position_size(
                bankroll=current_balance,
                sharp_trader_win_rate=sharp_trader_win_rate,
                market_odds=position.current_price,
                current_total_exposure=current_exposure
            )

            logger.info(
                "凯利计算",
                recommended_bet=f"${kelly_calc.recommended_bet:,.2f}",
                kelly_fraction=f"{kelly_calc.half_kelly_fraction:.3f}",
                reasoning=kelly_calc.reasoning[:100]
            )

            # 如果凯利推荐为0，跳过
            if kelly_calc.recommended_bet == 0:
                logger.info("跳过：凯利推荐不下注")
                return

            # 4. 风险验证
            validation = self.risk_manager.validate_trade(
                trade_size_usd=kelly_calc.recommended_bet,
                current_bankroll=current_balance,
                current_total_exposure=current_exposure,
                market_id=position.market_id,
                trader_address=position.wallet_address,
                market_liquidity=100000,  # TODO: 获取真实流动性
                current_odds=position.current_price,
                sharp_trader_entry_odds=position.avg_price,
                trade_timestamp=position.timestamp
            )

            # 计算预估收益
            potential_profit = kelly_calc.recommended_bet * (1.0 / position.current_price - 1.0)

            # 获取市场详情（标题、结算日期、链接等）
            market_info = await self._get_market_info(position.condition_id, position.market_title)
            market_title = market_info.get('market_title', position.market_title)  # 优先用position自带的title
            end_date_str = market_info.get('end_date_iso', 'N/A')
            days_until_close = market_info.get('days_until_close', 999)
            market_slug = market_info.get('market_slug', position.market_id)

            # 发送Telegram通知（无论通过与否）
            if self.telegram and self.telegram.enabled:
                await self.telegram.notify_trade_recommendation({
                    'market_title': market_title,  # 使用API获取的真实标题
                    'market_slug': market_slug,  # 用于生成链接
                    'condition_id': position.condition_id,  # 备用
                    'outcome': position.outcome,
                    'current_price': position.current_price,
                    'sharp_trader': position.wallet_address,
                    'sharp_win_rate': sharp_trader_win_rate,
                    'kelly_bet': kelly_calc.recommended_bet,
                    'kelly_fraction': kelly_calc.half_kelly_fraction,
                    'reasoning': kelly_calc.reasoning,
                    'potential_profit': potential_profit,
                    'end_date': end_date_str,
                    'days_until_close': days_until_close,
                    'approved': validation.approved,
                    'rejection_reasons': validation.reasons if not validation.approved else []
                })

            if not validation.approved:
                logger.warning(
                    "❌ 风险验证失败",
                    reasons=validation.reasons
                )
                return

            # 5. 执行订单
            await self._execute_order(
                position=position,
                size_usd=kelly_calc.recommended_bet,
                kelly_calc=kelly_calc
            )

        except Exception as e:
            logger.error(
                "处理新仓位错误",
                error_type=type(e).__name__,
                error_msg=str(e)[:200]
            )

    async def _get_current_balance(self) -> float:
        """
        获取当前余额

        Returns:
            USDC余额
        """
        if self.paper_trading:
            return self.paper_balance
        else:
            # TODO: 查询链上USDC余额
            # 使用web3.py查询ERC20余额
            return 10000.0  # 临时

    def _calculate_current_exposure(self) -> float:
        """
        计算当前总敞口（所有开仓仓位的价值）

        Returns:
            总敞口（USDC）
        """
        total = sum(
            trade.our_size * trade.entry_price
            for trade in self.our_positions.values()
            if trade.status == 'filled'
        )
        return total

    async def _execute_order(
        self,
        position: SharpTraderPosition,
        size_usd: float,
        kelly_calc: KellyCalculation
    ):
        """
        执行订单

        Args:
            position: Sharp交易员仓位
            size_usd: 下注金额（USDC）
            kelly_calc: 凯利计算结果
        """
        logger.info(
            "📤 准备下单",
            market=position.market_id[:30] + "...",
            outcome=position.outcome,
            size_usd=f"${size_usd:,.2f}",
            price=f"{position.current_price:.3f}"
        )

        # 计算份额数量
        shares = size_usd / position.current_price

        # 创建跟单记录
        copy_trade = CopyTrade(
            sharp_trader=position.wallet_address,
            market_id=position.market_id,
            condition_id=position.condition_id,
            outcome=position.outcome,
            sharp_trader_size=position.size,
            our_size=shares,
            entry_price=position.current_price,
            entry_time=datetime.now(),
            status='pending'
        )

        if self.paper_trading:
            # 模拟交易：直接标记为成功
            copy_trade.status = 'filled'
            copy_trade.order_id = f"PAPER_{datetime.now().timestamp()}"

            # 扣除余额
            self.paper_balance -= size_usd

            # 记录仓位
            position_id = self._get_position_id(
                position.wallet_address,
                position.market_id,
                position.outcome
            )
            self.our_positions[position_id] = copy_trade
            self.copy_history.append(copy_trade)

            # 记录到风险管理器（假设成功）
            self.risk_manager.record_trade_result(
                trade_size=size_usd,
                pnl=0.0,  # 开仓时P&L为0
                trader_address=position.wallet_address,
                market_id=position.market_id
            )

            logger.info(
                "✅ 模拟订单成功",
                order_id=copy_trade.order_id,
                shares=f"{shares:.2f}",
                spent=f"${size_usd:,.2f}",
                remaining_balance=f"${self.paper_balance:,.2f}"
            )

        else:
            # 真实交易：调用Polymarket CLOB API
            # TODO: 实现真实订单逻辑
            logger.warning("真实交易暂未实现，跳过")
            copy_trade.status = 'failed'

    async def get_status(self) -> Dict:
        """获取执行器状态"""
        return {
            'mode': '模拟交易' if self.paper_trading else '真实交易',
            'balance': self.paper_balance if self.paper_trading else 'N/A',
            'open_positions': len([p for p in self.our_positions.values() if p.status == 'filled']),
            'total_trades': len(self.copy_history),
            'sharp_traders_monitored': len(self.sharp_traders),
            'api_usage': self.rate_limiter.get_usage()
        }

    async def close(self):
        """关闭资源"""
        await self.client.aclose()
        logger.info("交易执行引擎已关闭")


# 测试函数
async def main():
    """测试交易执行器"""
    from config import get_config
    import os

    # 设置测试环境变量
    os.environ['WALLET_PRIVATE_KEY'] = '0x' + '1' * 64

    # 加载配置
    config = get_config()

    # 创建执行器
    kelly = KellyCriterion()
    risk_manager = RiskManager()

    # 测试Sharp交易员地址（示例）
    test_traders = [
        "0x0000000000000000000000000000000000000001"  # 替换为真实地址
    ]

    executor = TradeExecutor(
        config=config,
        kelly_calculator=kelly,
        risk_manager=risk_manager,
        sharp_trader_addresses=test_traders
    )

    try:
        # 获取状态
        status = await executor.get_status()
        print("\n=== 执行器状态 ===")
        for key, value in status.items():
            print(f"  {key}: {value}")

    finally:
        await executor.close()


if __name__ == '__main__':
    asyncio.run(main())
