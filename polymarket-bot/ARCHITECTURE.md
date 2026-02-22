# Polymarket Copy Trading Bot - System Architecture

## Executive Summary

A high-win-rate (70%+) automated copy trading system that follows Sharp traders on Polymarket using Half-Kelly position sizing.

**Core Strategy**: Smart Money Following (方案B)
**Target Win Rate**: 70%+
**Position Sizing**: Half-Kelly Criterion
**Risk Management**: Multi-layer validation and circuit breakers

---

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Polymarket Copy Bot                      │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Sharp      │     │  Position    │     │   Trade      │
│   Trader     │────▶│  Sizing      │────▶│  Execution   │
│ Identification│     │ (Half-Kelly) │     │   Engine     │
└──────────────┘     └──────────────┘     └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  PolyTrack   │     │   Risk       │     │  Polymarket  │
│     API      │     │ Management   │     │     API      │
└──────────────┘     └──────────────┘     └──────────────┘
        │                                           │
        └───────────────┬───────────────────────────┘
                        ▼
              ┌──────────────────┐
              │   PostgreSQL     │
              │    Database      │
              └──────────────────┘
```

---

## Component Details

### 1. Sharp Trader Identification Module

**Responsibility**: Identify and rank profitable traders to copy

**Data Sources**:
- **Primary**: PolyTrack API (free, 1000 calls/hour)
- **Backup**: Polywhaler, PolymarketAnalytics

**Sharp Trader Criteria** (based on research):
```python
SHARP_TRADER_THRESHOLDS = {
    'win_rate': 0.70,           # 70%+ win rate
    'min_trades': 50,           # At least 50 trades for statistical significance
    'min_volume': 10000,        # $10K+ total volume
    'max_avg_odds': 0.90,       # Don't follow traders who only bet on 0.95+ odds
    'recency_days': 30,         # Active in last 30 days
    'roi': 0.20,                # 20%+ ROI
    'consistency_score': 0.60   # Win rate stable across time windows
}
```

**Ranking Algorithm**:
```
Sharp Score = (
    0.35 * win_rate +
    0.25 * roi +
    0.20 * consistency_score +
    0.10 * volume_percentile +
    0.10 * recency_score
)
```

**Update Frequency**: Every 6 hours (to stay within API limits)

**Output**: Ranked list of top 10 Sharp traders

---

### 2. Position Sizing Module (Half-Kelly Criterion)

**Responsibility**: Calculate optimal bet size based on Sharp trader edge

**Kelly Formula**:
```
f* = (bp - q) / b

Where:
- f* = fraction of bankroll to bet
- b = odds received (decimal odds - 1)
- p = probability of winning (Sharp trader's win rate)
- q = probability of losing (1 - p)
```

**Half-Kelly Implementation**:
```python
def calculate_position_size(
    bankroll: float,
    sharp_trader_win_rate: float,
    market_odds: float,
    max_bet_pct: float = 0.10  # Never bet more than 10% on single trade
) -> float:
    """
    Calculate Half-Kelly position size

    Args:
        bankroll: Current account balance in USD
        sharp_trader_win_rate: Historical win rate of trader (0.70-0.95)
        market_odds: Current market odds (0.50-0.99)
        max_bet_pct: Maximum % of bankroll per trade

    Returns:
        Bet size in USD
    """
    p = sharp_trader_win_rate
    q = 1 - p
    b = (1 / market_odds) - 1  # Convert probability to odds

    # Full Kelly
    kelly_fraction = (b * p - q) / b

    # Half Kelly (more conservative)
    half_kelly = kelly_fraction * 0.5

    # Apply maximum bet constraint
    final_fraction = min(half_kelly, max_bet_pct)

    # Apply minimum bet (don't trade if edge too small)
    if final_fraction < 0.01:
        return 0

    return bankroll * final_fraction
```

**Risk Controls**:
- Maximum 10% of bankroll per trade
- Maximum 30% of bankroll in open positions
- Minimum edge required: Kelly fraction > 2%

---

### 3. Trade Execution Engine

**Responsibility**: Monitor Sharp traders and execute copy trades in real-time

**Polling Strategy** (based on Trust412 implementation):
```python
POLLING_CONFIG = {
    'sharp_trader_positions': 4,     # Check top traders every 4 seconds
    'market_updates': 10,             # Check market odds every 10 seconds
    'api_rate_limit': 1000,           # Polymarket free tier limit
    'max_concurrent_requests': 5      # Avoid rate limiting
}
```

**Execution Logic**:
```
1. Detect Sharp trader new position
2. Validate market still open and odds haven't moved >5%
3. Calculate position size using Half-Kelly
4. Check risk limits (per-trade, total exposure)
5. Execute order via Polymarket API
6. Record trade in database
7. Set exit monitoring
```

**Order Types**:
- Market orders only (for speed)
- Slippage tolerance: 2%
- Timeout: 30 seconds

**Exit Strategy**:
```python
EXIT_CONDITIONS = {
    'copy_trader_exit': True,        # Exit when Sharp trader exits
    'stop_loss_pct': -0.20,          # Stop loss at -20%
    'take_profit_pct': 0.50,         # Take profit at +50%
    'market_close_hours': 1,         # Exit 1 hour before market close
    'odds_reversal_threshold': 0.15  # Exit if odds swing >15%
}
```

---

### 4. Risk Management System

**Multi-Layer Protection**:

**Layer 1: Pre-Trade Validation**
- Sharp trader still meets criteria?
- Market liquidity sufficient (>$10K volume)?
- Odds haven't moved adversely (>5% slippage)?
- Account has sufficient balance?

**Layer 2: Position Limits**
- Max per trade: 10% of bankroll
- Max total exposure: 30% of bankroll
- Max per market: 5% of bankroll
- Max per Sharp trader: 15% of bankroll

**Layer 3: Circuit Breakers**
```python
CIRCUIT_BREAKERS = {
    'daily_loss_limit': -0.10,       # Stop trading if down 10% in a day
    'consecutive_losses': 5,         # Pause after 5 losses in a row
    'sharp_trader_drawdown': -0.30,  # Unfollow if Sharp trader down 30%
    'api_error_threshold': 10,       # Pause if 10 API errors in 1 hour
}
```

**Layer 4: Monitoring & Alerts**
- Telegram notifications for all trades
- Email alerts for risk limit breaches
- Daily P&L reports
- Weekly performance summaries

---

### 5. Data Layer (PostgreSQL)

**Schema Design**:

```sql
-- Sharp Traders
CREATE TABLE sharp_traders (
    wallet_address VARCHAR(42) PRIMARY KEY,
    sharp_score DECIMAL(5,4),
    win_rate DECIMAL(5,4),
    total_volume DECIMAL(15,2),
    total_trades INTEGER,
    roi DECIMAL(6,4),
    consistency_score DECIMAL(5,4),
    last_active TIMESTAMP,
    first_seen TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Positions (both Sharp trader and our copies)
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    wallet_address VARCHAR(42),
    market_id VARCHAR(100),
    outcome VARCHAR(10),  -- YES/NO
    odds DECIMAL(5,4),
    amount DECIMAL(15,2),
    timestamp TIMESTAMP,
    position_type VARCHAR(20),  -- 'sharp_trader' or 'copy_trade'
    status VARCHAR(20),  -- 'open', 'closed', 'expired'
    exit_timestamp TIMESTAMP,
    exit_odds DECIMAL(5,4),
    pnl DECIMAL(15,2)
);

-- Copy Trades
CREATE TABLE copy_trades (
    id SERIAL PRIMARY KEY,
    copied_from VARCHAR(42),  -- Sharp trader wallet
    market_id VARCHAR(100),
    outcome VARCHAR(10),
    entry_odds DECIMAL(5,4),
    amount DECIMAL(15,2),
    kelly_fraction DECIMAL(5,4),
    bankroll_at_entry DECIMAL(15,2),
    timestamp TIMESTAMP,
    exit_timestamp TIMESTAMP,
    exit_odds DECIMAL(5,4),
    pnl DECIMAL(15,2),
    win BOOLEAN
);

-- Performance Metrics
CREATE TABLE daily_performance (
    date DATE PRIMARY KEY,
    trades_count INTEGER,
    wins INTEGER,
    losses INTEGER,
    total_pnl DECIMAL(15,2),
    win_rate DECIMAL(5,4),
    roi DECIMAL(6,4),
    max_drawdown DECIMAL(6,4),
    bankroll_end DECIMAL(15,2)
);
```

---

## Technology Stack

**Backend**:
- **Language**: Python 3.11+
- **Framework**: FastAPI (for API and admin dashboard)
- **Database**: PostgreSQL 15
- **ORM**: SQLAlchemy 2.0
- **Task Queue**: Celery + Redis
- **Caching**: Redis

**External APIs**:
- **Polymarket API**: Market data and trading
- **PolyTrack API**: Sharp trader identification
- **Gamma API** (backup): Market data

**Deployment**:
- **Containerization**: Docker + Docker Compose
- **Cloud**: VPS (Hetzner or DigitalOcean)
- **Monitoring**: Prometheus + Grafana
- **Logging**: Structured logging with Python `logging`

**Development**:
- **Testing**: pytest + pytest-asyncio
- **Code Quality**: ruff, black, mypy
- **CI/CD**: GitHub Actions

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Set up PostgreSQL database
- [ ] Implement PolyTrack API client
- [ ] Build Sharp trader identification module
- [ ] Create database models and migrations

### Phase 2: Core Trading Logic (Week 2)
- [ ] Implement Half-Kelly position sizing
- [ ] Build trade execution engine
- [ ] Integrate Polymarket API
- [ ] Add basic risk management

### Phase 3: Monitoring & Safety (Week 3)
- [ ] Implement circuit breakers
- [ ] Add Telegram notifications
- [ ] Build admin dashboard
- [ ] Create backtesting framework

### Phase 4: Optimization (Week 4)
- [ ] Backtest on historical data
- [ ] Optimize Sharp trader selection criteria
- [ ] Fine-tune Kelly fraction multiplier
- [ ] Load testing and performance optimization

---

## Configuration

**Environment Variables**:
```bash
# Polymarket API
POLYMARKET_API_KEY=your_api_key
POLYMARKET_PRIVATE_KEY=your_wallet_private_key
POLYMARKET_CHAIN_ID=137  # Polygon mainnet

# PolyTrack
POLYTRACK_API_URL=https://polytrack.io/api

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/polymarket_bot

# Redis
REDIS_URL=redis://localhost:6379/0

# Risk Management
INITIAL_BANKROLL=10000
MAX_BET_PCT=0.10
MAX_TOTAL_EXPOSURE_PCT=0.30
DAILY_LOSS_LIMIT_PCT=0.10

# Notifications
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id
```

**Config File** (`config.yaml`):
```yaml
sharp_trader_criteria:
  win_rate: 0.70
  min_trades: 50
  min_volume: 10000
  max_avg_odds: 0.90
  recency_days: 30
  roi: 0.20

kelly_sizing:
  use_half_kelly: true
  max_bet_pct: 0.10
  min_edge_pct: 0.02

polling:
  sharp_traders: 4
  market_updates: 10

risk_management:
  max_per_trade_pct: 0.10
  max_total_exposure_pct: 0.30
  daily_loss_limit_pct: 0.10
  consecutive_loss_limit: 5
```

---

## Open-Source Base

**Selected**: `Trust412/polymarket-copy-trading-bot-version-3`

**Rationale**:
- Most sophisticated implementation (4-second polling)
- Clean TypeScript codebase (will port to Python)
- Already handles real-time position tracking
- Good error handling and retry logic

**Components to Reuse**:
1. Position monitoring logic
2. Market data fetching patterns
3. Order execution flow
4. WebSocket handling (if applicable)

**Components to Replace**:
1. Sharp trader selection (add our scoring algorithm)
2. Position sizing (add Half-Kelly)
3. Risk management (add our multi-layer system)
4. Database (add PostgreSQL with full analytics)

---

## Success Metrics

**Target Performance** (after 3 months):
- Win rate: 70%+
- Monthly ROI: 15%+
- Max drawdown: <20%
- Sharpe ratio: >1.5

**Operational Metrics**:
- API uptime: 99%+
- Trade execution latency: <5 seconds
- Sharp trader update frequency: Every 6 hours
- Zero missed Sharp trader trades (within polling interval)

---

## Risk Disclosure

**Known Risks**:
1. **Smart Money Risk**: Sharp traders can lose money
2. **Slippage Risk**: Odds may move between detection and execution
3. **Liquidity Risk**: Some markets may have low liquidity
4. **API Risk**: PolyTrack or Polymarket API downtime
5. **Regulatory Risk**: Prediction markets legal status varies

**Mitigation**:
- Diversify across multiple Sharp traders
- Use slippage limits and market depth checks
- Implement circuit breakers and stop losses
- Have backup APIs (Polywhaler, direct blockchain querying)
- Monitor regulatory developments

---

## Next Steps

1. Clone Trust412 bot as base implementation
2. Set up PostgreSQL database
3. Implement PolyTrack API client
4. Build Sharp trader scoring system
5. Add Half-Kelly position sizing
6. Integrate with Polymarket API
7. Backtest on historical data
8. Deploy to VPS and start paper trading
9. Run code-review and security-check skills
10. Go live with small bankroll ($1000)

---

**Last Updated**: 2026-01-27
**Author**: Claude Code + skill-from-masters methodology
**Based on**: Research from Polymarket experts, Kelly Criterion literature, and Sharp trader analysis
