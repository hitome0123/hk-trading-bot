#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Multi-Layer Risk Management System

Implements 4-layer risk protection for Polymarket copy trading:
1. Pre-trade validation
2. Position limits
3. Circuit breakers
4. Monitoring & alerts

Based on best practices from:
- Larry Williams: "Long-Term Secrets to Short-Term Trading"
- Van Tharp: "Trade Your Way to Financial Freedom"
- Risk management principles from skill-from-masters research
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
import structlog

logger = structlog.get_logger()


class RiskLevel(Enum):
    """Risk level classification"""

    GREEN = "green"  # Normal operation
    YELLOW = "yellow"  # Warning - approaching limits
    RED = "red"  # Danger - limits breached
    BLACK = "black"  # Circuit breaker - trading halted


@dataclass
class RiskLimits:
    """Risk management configuration limits"""

    # Per-trade limits
    max_per_trade_pct: float = 0.10  # 10% max per trade
    max_per_trade_usd: Optional[float] = None

    # Total exposure limits
    max_total_exposure_pct: float = 0.30  # 30% max total exposure
    max_total_exposure_usd: Optional[float] = None

    # Per-market limits
    max_per_market_pct: float = 0.05  # 5% max per market
    max_per_trader_pct: float = 0.15  # 15% max following one trader

    # Circuit breaker thresholds
    daily_loss_limit_pct: float = 0.10  # Stop if down 10% in a day
    consecutive_loss_limit: int = 5  # Pause after 5 losses in a row
    sharp_trader_drawdown_pct: float = 0.30  # Unfollow if trader down 30%
    api_error_threshold: int = 10  # Pause if 10 API errors in 1 hour

    # Pre-trade validation
    min_market_liquidity_usd: float = 10000  # $10K minimum liquidity
    max_slippage_pct: float = 0.05  # 5% max acceptable slippage
    max_trade_age_seconds: int = 60  # Don't copy trades older than 60s


@dataclass
class TradeValidation:
    """Result of pre-trade validation"""

    approved: bool
    risk_level: RiskLevel
    reasons: List[str]
    warnings: List[str]


@dataclass
class CircuitBreakerStatus:
    """Circuit breaker status"""

    triggered: bool
    reason: str
    triggered_at: Optional[datetime]
    can_reset: bool
    reset_condition: str


class RiskManager:
    """
    Multi-layer risk management system for Polymarket copy trading

    Responsibilities:
    - Pre-trade validation
    - Position limit enforcement
    - Circuit breaker monitoring
    - Performance tracking
    - Alert generation
    """

    def __init__(self, limits: Optional[RiskLimits] = None):
        self.limits = limits or RiskLimits()

        # State tracking
        self.daily_trades: List[Dict] = []
        self.daily_pnl: float = 0.0
        self.consecutive_losses: int = 0
        self.api_errors: List[datetime] = []
        self.circuit_breaker: Optional[CircuitBreakerStatus] = None

        # Sharp trader tracking
        self.trader_performance: Dict[str, Dict] = {}

    def validate_trade(
        self,
        trade_size_usd: float,
        current_bankroll: float,
        current_total_exposure: float,
        market_id: str,
        trader_address: str,
        market_liquidity: float,
        current_odds: float,
        sharp_trader_entry_odds: float,
        trade_timestamp: datetime,
    ) -> TradeValidation:
        """
        Layer 1: Pre-trade validation

        Validates trade against all risk criteria before execution.

        Args:
            trade_size_usd: Proposed trade size
            current_bankroll: Current account balance
            current_total_exposure: Current open positions value
            market_id: Polymarket market ID
            trader_address: Sharp trader wallet address
            market_liquidity: Market's total liquidity
            current_odds: Current market odds
            sharp_trader_entry_odds: Odds Sharp trader got
            trade_timestamp: When Sharp trader made the trade

        Returns:
            TradeValidation with approval status and reasons
        """
        approved = True
        risk_level = RiskLevel.GREEN
        reasons = []
        warnings = []

        # Check circuit breaker first
        if self.circuit_breaker and self.circuit_breaker.triggered:
            return TradeValidation(
                approved=False,
                risk_level=RiskLevel.BLACK,
                reasons=[
                    f"Circuit breaker active: {self.circuit_breaker.reason}",
                    f"Reset condition: {self.circuit_breaker.reset_condition}",
                ],
                warnings=[],
            )

        # 1. Check per-trade limit
        max_per_trade = current_bankroll * self.limits.max_per_trade_pct
        if self.limits.max_per_trade_usd:
            max_per_trade = min(max_per_trade, self.limits.max_per_trade_usd)

        if trade_size_usd > max_per_trade:
            approved = False
            risk_level = RiskLevel.RED
            reasons.append(
                f"Exceeds max per-trade limit: ${trade_size_usd:,.2f} > ${max_per_trade:,.2f}"
            )

        # 2. Check total exposure limit
        new_total_exposure = current_total_exposure + trade_size_usd
        max_total = current_bankroll * self.limits.max_total_exposure_pct
        if self.limits.max_total_exposure_usd:
            max_total = min(max_total, self.limits.max_total_exposure_usd)

        if new_total_exposure > max_total:
            approved = False
            risk_level = RiskLevel.RED
            reasons.append(
                f"Exceeds max total exposure: ${new_total_exposure:,.2f} > ${max_total:,.2f}"
            )
        elif new_total_exposure > max_total * 0.8:
            risk_level = max(risk_level, RiskLevel.YELLOW)
            warnings.append(
                f"Approaching max total exposure: ${new_total_exposure:,.2f} / ${max_total:,.2f}"
            )

        # 3. Check market liquidity
        if market_liquidity < self.limits.min_market_liquidity_usd:
            approved = False
            risk_level = RiskLevel.RED
            reasons.append(
                f"Insufficient market liquidity: ${market_liquidity:,.2f} < ${self.limits.min_market_liquidity_usd:,.2f}"
            )

        # 4. Check slippage
        slippage = abs(current_odds - sharp_trader_entry_odds) / sharp_trader_entry_odds
        if slippage > self.limits.max_slippage_pct:
            approved = False
            risk_level = RiskLevel.RED
            reasons.append(
                f"Excessive slippage: {slippage:.1%} > {self.limits.max_slippage_pct:.1%} "
                f"(Sharp trader: {sharp_trader_entry_odds:.3f}, Current: {current_odds:.3f})"
            )

        # 5. Check trade age (staleness)
        trade_age = (datetime.now() - trade_timestamp).total_seconds()
        if trade_age > self.limits.max_trade_age_seconds:
            approved = False
            risk_level = RiskLevel.RED
            reasons.append(
                f"Trade too old: {trade_age:.0f}s > {self.limits.max_trade_age_seconds}s"
            )

        # 6. Check Sharp trader recent performance
        if trader_address in self.trader_performance:
            trader_stats = self.trader_performance[trader_address]
            if trader_stats.get("recent_drawdown", 0) > self.limits.sharp_trader_drawdown_pct:
                approved = False
                risk_level = RiskLevel.RED
                reasons.append(
                    f"Sharp trader in drawdown: {trader_stats['recent_drawdown']:.1%} > {self.limits.sharp_trader_drawdown_pct:.1%}"
                )

        if approved:
            reasons.append("✓ All validation checks passed")

        return TradeValidation(
            approved=approved,
            risk_level=risk_level,
            reasons=reasons,
            warnings=warnings,
        )

    def record_trade_result(
        self,
        trade_size: float,
        pnl: float,
        trader_address: str,
        market_id: str,
    ):
        """
        Record trade result and update circuit breaker monitoring

        Args:
            trade_size: Trade size in USD
            pnl: Profit/loss in USD
            trader_address: Sharp trader address
            market_id: Market ID
        """
        # Record trade
        trade_record = {
            "timestamp": datetime.now(),
            "size": trade_size,
            "pnl": pnl,
            "trader": trader_address,
            "market": market_id,
        }
        self.daily_trades.append(trade_record)
        self.daily_pnl += pnl

        # Update consecutive losses
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        # Update trader performance
        if trader_address not in self.trader_performance:
            self.trader_performance[trader_address] = {
                "trades": [],
                "recent_drawdown": 0.0,
            }

        self.trader_performance[trader_address]["trades"].append(trade_record)

        # Calculate trader recent drawdown (last 10 trades)
        recent_trades = self.trader_performance[trader_address]["trades"][-10:]
        if recent_trades:
            total_pnl = sum(t["pnl"] for t in recent_trades)
            total_invested = sum(t["size"] for t in recent_trades)
            if total_invested > 0:
                self.trader_performance[trader_address]["recent_drawdown"] = (
                    -total_pnl / total_invested if total_pnl < 0 else 0.0
                )

        # Check circuit breakers
        self._check_circuit_breakers()

    def _check_circuit_breakers(self):
        """
        Layer 3: Check circuit breaker conditions

        Triggers circuit breaker if:
        - Daily loss exceeds limit
        - Too many consecutive losses
        - Too many API errors
        """
        # Check daily loss limit
        if self.daily_pnl < 0:
            # Calculate loss as percentage of starting balance
            # (Note: would need actual starting balance tracking)
            logger.warning(
                "Daily P&L negative",
                daily_pnl=self.daily_pnl,
            )

        # Check consecutive losses
        if self.consecutive_losses >= self.limits.consecutive_loss_limit:
            self._trigger_circuit_breaker(
                reason=f"Consecutive loss limit reached: {self.consecutive_losses} losses",
                reset_condition="Manual reset required after reviewing strategy",
            )
            return

        # Check API errors
        recent_errors = [
            e
            for e in self.api_errors
            if e > datetime.now() - timedelta(hours=1)
        ]
        if len(recent_errors) >= self.limits.api_error_threshold:
            self._trigger_circuit_breaker(
                reason=f"API error threshold reached: {len(recent_errors)} errors in 1 hour",
                reset_condition="Wait 1 hour and verify API connectivity",
            )
            return

    def _trigger_circuit_breaker(self, reason: str, reset_condition: str):
        """
        Trigger circuit breaker - halt all trading

        Args:
            reason: Why circuit breaker was triggered
            reset_condition: What needs to happen to reset
        """
        self.circuit_breaker = CircuitBreakerStatus(
            triggered=True,
            reason=reason,
            triggered_at=datetime.now(),
            can_reset=False,
            reset_condition=reset_condition,
        )

        logger.critical(
            "🚨 CIRCUIT BREAKER TRIGGERED 🚨",
            reason=reason,
            reset_condition=reset_condition,
        )

    def reset_circuit_breaker(self):
        """Manually reset circuit breaker"""
        if self.circuit_breaker:
            logger.warning(
                "Circuit breaker reset",
                previous_reason=self.circuit_breaker.reason,
            )
            self.circuit_breaker = None

    def record_api_error(self):
        """Record an API error for circuit breaker monitoring"""
        self.api_errors.append(datetime.now())

    def reset_daily_stats(self):
        """Reset daily statistics (call at start of each day)"""
        self.daily_trades = []
        self.daily_pnl = 0.0
        # Don't reset consecutive losses - those carry over

    def get_risk_summary(self, current_bankroll: float) -> Dict:
        """
        Get current risk status summary

        Args:
            current_bankroll: Current account balance

        Returns:
            Dictionary with risk metrics
        """
        return {
            "circuit_breaker_active": self.circuit_breaker is not None,
            "circuit_breaker_reason": (
                self.circuit_breaker.reason if self.circuit_breaker else None
            ),
            "daily_trades": len(self.daily_trades),
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / current_bankroll * 100)
            if current_bankroll > 0
            else 0,
            "consecutive_losses": self.consecutive_losses,
            "api_errors_last_hour": len(
                [e for e in self.api_errors if e > datetime.now() - timedelta(hours=1)]
            ),
            "tracked_traders": len(self.trader_performance),
        }


def main():
    """Test risk manager"""
    rm = RiskManager()

    print("=== Risk Manager Test ===\n")

    # Test scenario: Validate a trade
    validation = rm.validate_trade(
        trade_size_usd=500,
        current_bankroll=10000,
        current_total_exposure=2000,
        market_id="test-market-123",
        trader_address="0xabc123",
        market_liquidity=50000,
        current_odds=0.65,
        sharp_trader_entry_odds=0.63,
        trade_timestamp=datetime.now() - timedelta(seconds=10),
    )

    print(f"Trade Validation:")
    print(f"  Approved: {validation.approved}")
    print(f"  Risk Level: {validation.risk_level.value}")
    print(f"  Reasons:")
    for reason in validation.reasons:
        print(f"    - {reason}")
    if validation.warnings:
        print(f"  Warnings:")
        for warning in validation.warnings:
            print(f"    - {warning}")

    # Simulate some trades
    print("\n=== Simulating Trades ===\n")
    for i in range(6):
        pnl = -50 if i < 5 else 100  # 5 losses, then 1 win
        rm.record_trade_result(
            trade_size=100,
            pnl=pnl,
            trader_address="0xabc123",
            market_id="market-1",
        )
        print(f"Trade {i+1}: P&L ${pnl:+.0f}, Consecutive losses: {rm.consecutive_losses}")

    # Check circuit breaker
    summary = rm.get_risk_summary(current_bankroll=10000)
    print(f"\n=== Risk Summary ===")
    print(f"Circuit breaker active: {summary['circuit_breaker_active']}")
    if summary["circuit_breaker_active"]:
        print(f"Reason: {summary['circuit_breaker_reason']}")
    print(f"Daily P&L: ${summary['daily_pnl']:+,.2f}")
    print(f"Consecutive losses: {summary['consecutive_losses']}")


if __name__ == "__main__":
    main()
