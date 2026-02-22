#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sharp Trader Identification Module

Identifies and ranks profitable traders on Polymarket using PolyTrack API.

Based on methodology from skill-from-masters research:
- Win rate > 70%
- Minimum 50 trades for statistical significance
- Volume > $10,000
- ROI > 20%
- Consistency score > 60%
"""

import httpx
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import structlog
from utils import (
    validate_wallet_address,
    truncate_wallet,
    APIRateLimiter,
    enforce_https
)

logger = structlog.get_logger()


@dataclass
class SharpTraderCriteria:
    """Criteria for identifying Sharp traders"""
    win_rate: float = 0.70  # 70%+ win rate
    min_trades: int = 50  # At least 50 trades
    min_volume: float = 10000.0  # $10K+ total volume
    max_avg_odds: float = 0.90  # Don't follow traders who only bet on 0.95+ odds
    recency_days: int = 30  # Active in last 30 days
    roi: float = 0.20  # 20%+ ROI
    consistency_score: float = 0.60  # Win rate stable across time windows


@dataclass
class TraderProfile:
    """Profile of a trader with performance metrics"""
    wallet_address: str
    win_rate: float
    total_trades: int
    total_volume: float
    roi: float
    avg_odds: float
    last_active: datetime
    consistency_score: float
    sharp_score: float
    markets_traded: List[str]
    best_categories: List[str]


class SharpTraderIdentifier:
    """
    Identifies Sharp traders on Polymarket using multiple data sources.

    Primary: PolyTrack API (free)
    Backup: Polymarket Data API, Polywhaler
    """

    def __init__(
        self,
        polytrack_api_url: str = "https://polytrack.io/api",
        polymarket_api_url: str = "https://data-api.polymarket.com",
        criteria: Optional[SharpTraderCriteria] = None,
    ):
        # 强制HTTPS
        self.polytrack_api_url = enforce_https(polytrack_api_url)
        self.polymarket_api_url = enforce_https(polymarket_api_url)
        self.criteria = criteria or SharpTraderCriteria()

        # HTTP客户端配置
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,    # 5秒建立连接
                read=30.0,      # 30秒读取响应
                write=5.0,      # 5秒发送请求
                pool=5.0        # 5秒从连接池获取
            )
        )

        # API限流器 - Polymarket免费版: 1000次/小时
        # 设为900次/小时（90%）留安全余量
        self.rate_limiter = APIRateLimiter(
            max_calls=900,
            window_seconds=3600,
            warn_threshold=0.85  # 85%时警告
        )

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

    async def get_trader_profile(self, wallet_address: str) -> Optional[TraderProfile]:
        """
        从Polymarket数据API获取交易员档案

        Args:
            wallet_address: 交易员的以太坊钱包地址

        Returns:
            TraderProfile对象，如果不符合标准则返回None
        """
        # 验证钱包地址格式
        if not validate_wallet_address(wallet_address):
            logger.error(
                "无效的钱包地址格式",
                wallet=truncate_wallet(wallet_address),
            )
            raise ValueError(
                f"无效的以太坊钱包地址: {wallet_address}. "
                f"必须是0x开头+40位十六进制字符"
            )

        try:
            # 检查API限流
            if not self.rate_limiter.can_call():
                wait_time = self.rate_limiter.wait_time()
                logger.warning(
                    "API限流 - 等待中",
                    wait_seconds=f"{wait_time:.1f}",
                    wallet=truncate_wallet(wallet_address)
                )
                await asyncio.sleep(wait_time + 1)  # 多等1秒确保安全

            # 记录API调用
            self.rate_limiter.record_call()

            # 获取交易员活动记录
            url = f"{self.polymarket_api_url}/activity?user={wallet_address}&type=TRADE"
            response = await self.client.get(url)
            response.raise_for_status()
            activities = response.json()

            if not activities or len(activities) == 0:
                logger.info(
                    "未找到交易活动",
                    wallet=truncate_wallet(wallet_address),
                )
                return None

            # 再次检查限流（第二次API调用）
            if not self.rate_limiter.can_call():
                wait_time = self.rate_limiter.wait_time()
                await asyncio.sleep(wait_time + 1)

            self.rate_limiter.record_call()

            # 获取交易员持仓
            positions_url = f"{self.polymarket_api_url}/positions?user={wallet_address}"
            positions_response = await self.client.get(positions_url)
            positions_response.raise_for_status()
            positions = positions_response.json()

            # Calculate metrics
            metrics = self._calculate_trader_metrics(activities, positions)

            # Check if trader meets criteria
            if not self._meets_criteria(metrics):
                logger.debug(
                    "交易员不符合Sharp标准",
                    wallet=truncate_wallet(wallet_address),
                    win_rate=f"{metrics.get('win_rate', 0):.1%}",
                    total_trades=metrics.get("total_trades", 0),
                )
                return None

            # Calculate Sharp score
            sharp_score = self._calculate_sharp_score(metrics)

            return TraderProfile(
                wallet_address=wallet_address,
                win_rate=metrics["win_rate"],
                total_trades=metrics["total_trades"],
                total_volume=metrics["total_volume"],
                roi=metrics["roi"],
                avg_odds=metrics["avg_odds"],
                last_active=metrics["last_active"],
                consistency_score=metrics["consistency_score"],
                sharp_score=sharp_score,
                markets_traded=metrics["markets_traded"],
                best_categories=metrics["best_categories"],
            )

        except httpx.HTTPError as e:
            logger.error(
                "HTTP错误：获取交易员档案失败",
                wallet=truncate_wallet(wallet_address),
                error_type=type(e).__name__,
                status_code=getattr(e.response, 'status_code', None),
            )
            return None
        except Exception as e:
            logger.error(
                "获取交易员档案失败",
                wallet=truncate_wallet(wallet_address),
                error_type=type(e).__name__,
                error_msg=str(e)[:100],  # 截断错误消息
            )
            return None

    def _calculate_trader_metrics(
        self, activities: List[Dict], positions: List[Dict]
    ) -> Dict:
        """
        Calculate trader performance metrics

        Args:
            activities: List of trading activities
            positions: List of current/past positions

        Returns:
            Dictionary of metrics
        """
        # Filter for recent activity (last 90 days for consistency check)
        now = datetime.now()
        recent_cutoff = now - timedelta(days=90)

        recent_activities = [
            a
            for a in activities
            if datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00"))
            > recent_cutoff
        ]

        # Calculate basic metrics
        total_trades = len(recent_activities)
        total_volume = sum(float(a.get("usdcSize", 0)) for a in recent_activities)

        # Calculate win rate from closed positions
        closed_positions = [p for p in positions if p.get("redeemable", False)]
        wins = sum(1 for p in closed_positions if float(p.get("cashPnl", 0)) > 0)
        win_rate = wins / len(closed_positions) if closed_positions else 0

        # Calculate ROI
        total_invested = sum(
            float(p.get("initialValue", 0)) for p in closed_positions
        )
        total_pnl = sum(float(p.get("cashPnl", 0)) for p in closed_positions)
        roi = total_pnl / total_invested if total_invested > 0 else 0

        # Calculate average odds (from activities)
        odds_sum = 0
        odds_count = 0
        for a in recent_activities:
            if a.get("side") == "BUY" and "price" in a:
                price = float(a["price"])
                odds = price if price <= 1.0 else 1.0
                odds_sum += odds
                odds_count += 1

        avg_odds = odds_sum / odds_count if odds_count > 0 else 0.5

        # Last active
        last_active = max(
            (datetime.fromisoformat(a["timestamp"].replace("Z", "+00:00")) for a in activities),
            default=now,
        )

        # Consistency score: compare win rate across time windows
        consistency_score = self._calculate_consistency(closed_positions)

        # Markets traded
        markets_traded = list(
            set(a.get("conditionId", "") for a in recent_activities)
        )

        # Best categories (simplified - would need market metadata)
        best_categories = []

        return {
            "win_rate": win_rate,
            "total_trades": total_trades,
            "total_volume": total_volume,
            "roi": roi,
            "avg_odds": avg_odds,
            "last_active": last_active,
            "consistency_score": consistency_score,
            "markets_traded": markets_traded,
            "best_categories": best_categories,
        }

    def _calculate_consistency(self, closed_positions: List[Dict]) -> float:
        """
        Calculate consistency score by comparing win rates across time windows

        Higher score = more consistent performance
        Lower score = erratic performance (could be luck)

        Returns:
            Consistency score (0.0 - 1.0)
        """
        if len(closed_positions) < 10:
            return 0.0

        # Sort positions by end date
        sorted_positions = sorted(
            [
                p
                for p in closed_positions
                if p.get("endDate")
            ],
            key=lambda x: x["endDate"],
        )

        # Split into 3 time windows
        window_size = len(sorted_positions) // 3
        if window_size < 3:
            return 0.0

        win_rates = []
        for i in range(3):
            start_idx = i * window_size
            end_idx = start_idx + window_size if i < 2 else len(sorted_positions)
            window = sorted_positions[start_idx:end_idx]

            wins = sum(1 for p in window if float(p.get("cashPnl", 0)) > 0)
            wr = wins / len(window) if window else 0
            win_rates.append(wr)

        # Calculate standard deviation
        mean_wr = sum(win_rates) / len(win_rates)
        variance = sum((wr - mean_wr) ** 2 for wr in win_rates) / len(win_rates)
        std_dev = variance**0.5

        # Consistency score: inverse of std dev (normalized to 0-1)
        # Low std dev = high consistency
        consistency = 1.0 - min(std_dev * 2, 1.0)

        return consistency

    def _meets_criteria(self, metrics: Dict) -> bool:
        """
        Check if trader meets Sharp trader criteria

        Args:
            metrics: Dictionary of trader metrics

        Returns:
            True if trader meets all criteria
        """
        if metrics["win_rate"] < self.criteria.win_rate:
            return False

        if metrics["total_trades"] < self.criteria.min_trades:
            return False

        if metrics["total_volume"] < self.criteria.min_volume:
            return False

        if metrics["avg_odds"] > self.criteria.max_avg_odds:
            return False

        if metrics["roi"] < self.criteria.roi:
            return False

        if metrics["consistency_score"] < self.criteria.consistency_score:
            return False

        # Check recency
        days_since_active = (datetime.now() - metrics["last_active"]).days
        if days_since_active > self.criteria.recency_days:
            return False

        return True

    def _calculate_sharp_score(self, metrics: Dict) -> float:
        """
        Calculate Sharp score (0.0 - 1.0)

        Weighted combination of metrics:
        - 35% win rate
        - 25% ROI
        - 20% consistency
        - 10% volume percentile
        - 10% recency

        Args:
            metrics: Dictionary of trader metrics

        Returns:
            Sharp score (0.0 - 1.0)
        """
        # Normalize metrics to 0-1 scale
        win_rate_score = min(metrics["win_rate"], 1.0)

        # ROI score: 0.20 ROI = 0.5, 1.0 ROI = 1.0
        roi_score = min(metrics["roi"] / 2.0 + 0.5, 1.0)

        consistency_score = metrics["consistency_score"]

        # Volume score: $10K = 0.0, $100K = 0.5, $1M+ = 1.0
        volume_score = min((metrics["total_volume"] - 10000) / 990000, 1.0)

        # Recency score: Active today = 1.0, 30 days ago = 0.0
        days_since = (datetime.now() - metrics["last_active"]).days
        recency_score = max(1.0 - (days_since / 30), 0.0)

        # Weighted sum
        sharp_score = (
            0.35 * win_rate_score
            + 0.25 * roi_score
            + 0.20 * consistency_score
            + 0.10 * volume_score
            + 0.10 * recency_score
        )

        return sharp_score

    async def find_sharp_traders(
        self, wallet_addresses: List[str], top_n: int = 10
    ) -> List[TraderProfile]:
        """
        Find and rank Sharp traders from a list of wallet addresses

        Args:
            wallet_addresses: List of wallet addresses to evaluate
            top_n: Number of top traders to return

        Returns:
            List of top N Sharp traders sorted by Sharp score
        """
        logger.info(
            "Scanning traders for Sharp profiles",
            total_wallets=len(wallet_addresses),
        )

        # Fetch profiles concurrently
        tasks = [self.get_trader_profile(addr) for addr in wallet_addresses]
        profiles = await asyncio.gather(*tasks)

        # Filter out None and sort by Sharp score
        sharp_traders = [p for p in profiles if p is not None]
        sharp_traders.sort(key=lambda x: x.sharp_score, reverse=True)

        top_traders = sharp_traders[:top_n]

        logger.info(
            "Sharp trader identification complete",
            total_scanned=len(wallet_addresses),
            sharp_traders_found=len(sharp_traders),
            top_n=len(top_traders),
        )

        for i, trader in enumerate(top_traders, 1):
            logger.info(
                f"#{i} Sharp Trader",
                wallet=trader.wallet_address[:8],
                sharp_score=f"{trader.sharp_score:.3f}",
                win_rate=f"{trader.win_rate:.1%}",
                roi=f"{trader.roi:.1%}",
                volume=f"${trader.total_volume:,.0f}",
            )

        return top_traders

    async def scan_leaderboard(self, limit: int = 100) -> List[str]:
        """
        Scan Polymarket leaderboard for top traders

        Args:
            limit: Number of top traders to fetch

        Returns:
            List of wallet addresses
        """
        # Note: This would need actual leaderboard API endpoint
        # Polymarket doesn't publicly expose this via API currently
        # Would need to scrape or use third-party tools like Predictfolio

        logger.warning(
            "Leaderboard scanning not implemented - Polymarket API limitation. "
            "Please manually provide wallet addresses from polymarket.com/leaderboard"
        )
        return []


async def main():
    """Test Sharp trader identification"""
    identifier = SharpTraderIdentifier()

    # Example: Test with known good trader (Axios)
    test_wallets = [
        # Add wallet addresses here from Polymarket leaderboard
    ]

    try:
        sharp_traders = await identifier.find_sharp_traders(test_wallets, top_n=5)

        print("\n=== Top Sharp Traders ===\n")
        for i, trader in enumerate(sharp_traders, 1):
            print(f"#{i} {trader.wallet_address}")
            print(f"   Sharp Score: {trader.sharp_score:.3f}")
            print(f"   Win Rate: {trader.win_rate:.1%}")
            print(f"   ROI: {trader.roi:.1%}")
            print(f"   Volume: ${trader.total_volume:,.0f}")
            print(f"   Trades: {trader.total_trades}")
            print(f"   Consistency: {trader.consistency_score:.2f}")
            print()

    finally:
        await identifier.close()


if __name__ == "__main__":
    asyncio.run(main())
