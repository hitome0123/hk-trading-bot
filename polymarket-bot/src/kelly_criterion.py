#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kelly Criterion Position Sizing Module

Implements Half-Kelly criterion for optimal bet sizing on Polymarket.

Based on methodology from skill-from-masters research:
- Kelly formula: f* = (bp - q) / b
- Half-Kelly for conservative approach (reduces variance)
- Maximum bet constraints (10% per trade, 30% total exposure)
- Minimum edge requirements (2% Kelly fraction)

References:
- Ed Thorp: "Beat the Dealer" - Kelly Criterion for blackjack
- William Poundstone: "Fortune's Formula"
- Larry Williams: Position sizing for trading
"""

from dataclasses import dataclass
from typing import Optional, Dict
import structlog

logger = structlog.get_logger()


@dataclass
class KellyCalculation:
    """Result of Kelly criterion calculation"""

    # Inputs
    bankroll: float
    win_probability: float  # Sharp trader's win rate
    market_odds: float  # Current market price (0.0-1.0)

    # Kelly calculations
    full_kelly_fraction: float
    half_kelly_fraction: float
    quarter_kelly_fraction: float

    # Final bet size
    recommended_bet: float
    recommended_fraction: str  # 'half' or 'quarter' or 'none'

    # Constraints applied
    capped_by_max_per_trade: bool
    capped_by_max_total_exposure: bool
    below_min_edge: bool

    # Reasoning
    reasoning: str


class KellyCriterion:
    """
    Kelly Criterion position sizer for Polymarket copy trading

    Conservative approach:
    - Uses Half-Kelly by default (more stable returns)
    - Option for Quarter-Kelly (even more conservative)
    - Never bet more than 10% per trade
    - Never have more than 30% total exposure
    - Minimum 2% Kelly edge required
    """

    def __init__(
        self,
        max_bet_pct: float = 0.10,  # Max 10% per trade
        max_total_exposure_pct: float = 0.30,  # Max 30% total exposure
        min_edge_pct: float = 0.02,  # Min 2% Kelly fraction
        use_quarter_kelly: bool = False,  # Use 1/4 Kelly instead of 1/2
    ):
        self.max_bet_pct = max_bet_pct
        self.max_total_exposure_pct = max_total_exposure_pct
        self.min_edge_pct = min_edge_pct
        self.use_quarter_kelly = use_quarter_kelly

    def calculate_position_size(
        self,
        bankroll: float,
        sharp_trader_win_rate: float,
        market_odds: float,
        current_total_exposure: float = 0.0,
    ) -> KellyCalculation:
        """
        Calculate optimal position size using Kelly Criterion

        Args:
            bankroll: Current account balance in USD
            sharp_trader_win_rate: Historical win rate of Sharp trader (0.70-0.95)
            market_odds: Current market price/probability (0.50-0.99)
            current_total_exposure: Current total open positions in USD

        Returns:
            KellyCalculation with recommended bet size and reasoning

        Example:
            >>> kc = KellyCriterion()
            >>> calc = kc.calculate_position_size(
            ...     bankroll=10000,
            ...     sharp_trader_win_rate=0.75,  # 75% win rate
            ...     market_odds=0.65,  # Market at 65%
            ... )
            >>> print(f"Bet: ${calc.recommended_bet:.2f}")
            Bet: $500.00
        """
        # 输入验证
        if not (0.5 <= sharp_trader_win_rate <= 1.0):
            raise ValueError(
                f"Sharp交易员胜率必须在0.5-1.0之间，当前: {sharp_trader_win_rate}. "
                f"胜率<50%意味着没有优势"
            )

        # 严格的赔率验证（防止除零和极端值）
        if market_odds <= 0.0:
            raise ValueError(
                f"市场赔率必须为正数，当前: {market_odds}. "
                f"零赔率会导致凯利公式除零错误"
            )

        if market_odds < 0.01 or market_odds > 0.99:
            raise ValueError(
                f"市场赔率必须在0.01-0.99之间，当前: {market_odds}. "
                f"极端赔率(<0.01或>0.99)会导致凯利计算不可靠。"
                f"凯利准则假设中等概率范围"
            )

        if bankroll <= 0:
            raise ValueError(f"资金必须为正数，当前: {bankroll}")

        # Kelly formula: f* = (bp - q) / b
        # Where:
        #   p = probability of winning (Sharp trader's win rate)
        #   q = probability of losing (1 - p)
        #   b = odds received (decimal odds - 1) = (1/market_odds - 1)

        p = sharp_trader_win_rate
        q = 1 - p

        # Convert probability to decimal odds
        # If market price is 0.65, fair odds are 1/0.65 = 1.538
        # Net odds (b) = 1.538 - 1 = 0.538
        b = (1 / market_odds) - 1

        # 全凯利分数
        full_kelly = (b * p - q) / b

        # 检查负边缘（市场赔率高于胜率）
        if full_kelly < 0:
            logger.warning(
                "负凯利分数 - 市场赔率超过胜率概率",
                kelly_fraction=full_kelly,
                win_rate=p,
                market_odds=market_odds,
                recommendation="跳过此交易，无优势"
            )
            # 返回零下注
            return KellyCalculation(
                bankroll=bankroll,
                win_probability=p,
                market_odds=market_odds,
                full_kelly_fraction=full_kelly,
                half_kelly_fraction=0.0,
                quarter_kelly_fraction=0.0,
                recommended_bet=0.0,
                recommended_fraction="none",
                capped_by_max_per_trade=False,
                capped_by_max_total_exposure=False,
                below_min_edge=True,
                reasoning=f"负凯利分数({full_kelly:.3f}) - 无边缘优势，跳过交易"
            )

        # 半凯利（推荐，大多数交易员使用）
        half_kelly = full_kelly * 0.5

        # 四分之一凯利（非常保守）
        quarter_kelly = full_kelly * 0.25

        # Choose fraction
        if self.use_quarter_kelly:
            kelly_fraction = quarter_kelly
            fraction_type = "quarter"
        else:
            kelly_fraction = half_kelly
            fraction_type = "half"

        # Calculate raw bet size
        raw_bet = bankroll * kelly_fraction

        # Initialize constraint flags
        capped_by_max_per_trade = False
        capped_by_max_total_exposure = False
        below_min_edge = False

        # Build reasoning
        reasoning_parts = []
        reasoning_parts.append(
            f"Sharp trader win rate: {p:.1%}, Market odds: {market_odds:.1%}"
        )
        reasoning_parts.append(
            f"Full Kelly: {full_kelly:.3f}, Half Kelly: {half_kelly:.3f}"
        )

        # Check minimum edge requirement
        if kelly_fraction < self.min_edge_pct:
            below_min_edge = True
            reasoning_parts.append(
                f"Edge too small ({kelly_fraction:.3f} < {self.min_edge_pct}) - SKIP"
            )
            final_bet = 0.0
        else:
            final_bet = raw_bet
            reasoning_parts.append(
                f"{fraction_type.capitalize()} Kelly bet: ${raw_bet:,.2f} ({kelly_fraction:.1%} of bankroll)"
            )

            # Apply max bet per trade constraint
            max_bet_allowed = bankroll * self.max_bet_pct
            if final_bet > max_bet_allowed:
                final_bet = max_bet_allowed
                capped_by_max_per_trade = True
                reasoning_parts.append(
                    f"Capped by max bet per trade: ${max_bet_allowed:,.2f} ({self.max_bet_pct:.0%})"
                )

            # Apply total exposure constraint
            new_total_exposure = current_total_exposure + final_bet
            max_total_allowed = bankroll * self.max_total_exposure_pct

            if new_total_exposure > max_total_allowed:
                # Reduce bet to fit within total exposure limit
                available_room = max(0, max_total_allowed - current_total_exposure)

                if available_room > 0:
                    final_bet = available_room
                    capped_by_max_total_exposure = True
                    reasoning_parts.append(
                        f"Reduced to fit max total exposure: ${final_bet:,.2f} "
                        f"(total exposure: ${new_total_exposure:,.2f}/{max_total_allowed:,.2f})"
                    )
                else:
                    final_bet = 0.0
                    capped_by_max_total_exposure = True
                    reasoning_parts.append(
                        f"Max total exposure reached ({current_total_exposure:,.2f}/{max_total_allowed:,.2f}) - SKIP"
                    )

        reasoning = " | ".join(reasoning_parts)

        return KellyCalculation(
            bankroll=bankroll,
            win_probability=p,
            market_odds=market_odds,
            full_kelly_fraction=full_kelly,
            half_kelly_fraction=half_kelly,
            quarter_kelly_fraction=quarter_kelly,
            recommended_bet=final_bet,
            recommended_fraction=fraction_type,
            capped_by_max_per_trade=capped_by_max_per_trade,
            capped_by_max_total_exposure=capped_by_max_total_exposure,
            below_min_edge=below_min_edge,
            reasoning=reasoning,
        )

    def backtest_kelly_performance(
        self,
        initial_bankroll: float,
        win_rate: float,
        avg_odds: float,
        num_bets: int = 100,
    ) -> Dict[str, float]:
        """
        Backtest Kelly performance vs other strategies

        Compares:
        - Full Kelly
        - Half Kelly
        - Quarter Kelly
        - Fixed 5% per bet
        - Fixed $100 per bet

        Args:
            initial_bankroll: Starting capital
            win_rate: Win rate to simulate
            avg_odds: Average market odds
            num_bets: Number of bets to simulate

        Returns:
            Dictionary with final bankrolls for each strategy
        """
        import random

        results = {}

        for strategy_name, kelly_multiplier in [
            ("Full Kelly", 1.0),
            ("Half Kelly", 0.5),
            ("Quarter Kelly", 0.25),
            ("Fixed 5%", None),
            ("Fixed $100", None),
        ]:
            bankroll = initial_bankroll
            max_drawdown = 0.0
            peak = initial_bankroll

            for _ in range(num_bets):
                # Determine bet size
                if kelly_multiplier is not None:
                    p = win_rate
                    q = 1 - p
                    b = (1 / avg_odds) - 1
                    kelly_fraction = ((b * p - q) / b) * kelly_multiplier
                    bet_size = bankroll * min(kelly_fraction, self.max_bet_pct)
                elif strategy_name == "Fixed 5%":
                    bet_size = bankroll * 0.05
                else:  # Fixed $100
                    bet_size = min(100, bankroll * 0.10)  # Cap at 10%

                # Simulate outcome
                win = random.random() < win_rate

                if win:
                    # Win: get back bet + profit
                    profit = bet_size * b
                    bankroll += profit
                else:
                    # Lose: lose the bet
                    bankroll -= bet_size

                # Track drawdown
                if bankroll > peak:
                    peak = bankroll
                drawdown = (peak - bankroll) / peak
                max_drawdown = max(max_drawdown, drawdown)

                # Bankruptcy check
                if bankroll <= 0:
                    bankroll = 0
                    break

            results[strategy_name] = {
                "final_bankroll": bankroll,
                "return_pct": ((bankroll - initial_bankroll) / initial_bankroll) * 100,
                "max_drawdown_pct": max_drawdown * 100,
            }

        return results


def main():
    """Test Kelly Criterion calculator"""
    kc = KellyCriterion(use_quarter_kelly=False)

    print("=== Kelly Criterion Position Sizing ===\n")

    # Test scenarios
    scenarios = [
        {
            "name": "Strong Edge (75% win rate, 65% market odds)",
            "bankroll": 10000,
            "win_rate": 0.75,
            "market_odds": 0.65,
        },
        {
            "name": "Moderate Edge (70% win rate, 60% market odds)",
            "bankroll": 10000,
            "win_rate": 0.70,
            "market_odds": 0.60,
        },
        {
            "name": "Weak Edge (72% win rate, 70% market odds)",
            "bankroll": 10000,
            "win_rate": 0.72,
            "market_odds": 0.70,
        },
        {
            "name": "No Edge (50% win rate, 50% market odds)",
            "bankroll": 10000,
            "win_rate": 0.50,
            "market_odds": 0.50,
        },
    ]

    for scenario in scenarios:
        print(f"{scenario['name']}")
        calc = kc.calculate_position_size(
            bankroll=scenario["bankroll"],
            sharp_trader_win_rate=scenario["win_rate"],
            market_odds=scenario["market_odds"],
        )

        print(f"  Full Kelly: {calc.full_kelly_fraction:.3f}")
        print(f"  Half Kelly: {calc.half_kelly_fraction:.3f}")
        print(f"  Recommended bet: ${calc.recommended_bet:,.2f}")
        print(f"  Reasoning: {calc.reasoning}")
        print()

    # Backtest
    print("\n=== Backtest: 100 bets at 70% win rate, 0.60 avg odds ===\n")
    backtest_results = kc.backtest_kelly_performance(
        initial_bankroll=10000, win_rate=0.70, avg_odds=0.60, num_bets=100
    )

    for strategy, result in backtest_results.items():
        print(f"{strategy}:")
        print(f"  Final bankroll: ${result['final_bankroll']:,.2f}")
        print(f"  Return: {result['return_pct']:+.1f}%")
        print(f"  Max drawdown: {result['max_drawdown_pct']:.1f}%")
        print()


if __name__ == "__main__":
    main()
