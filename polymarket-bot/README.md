# Polymarket Copy Trading Bot

**High-Win-Rate Automated Copy Trading System for Polymarket**

Follow Sharp traders with 70%+ win rates using Half-Kelly position sizing and multi-layer risk management.

## 🎯 Key Features

### 1. Sharp Trader Identification
- **Data-Driven Selection**: Identifies profitable traders using PolyTrack API
- **Rigorous Criteria**: 70%+ win rate, 50+ trades, $10K+ volume, 20%+ ROI
- **Consistency Filtering**: Only follows traders with stable performance across time
- **Automatic Ranking**: Sharp Score algorithm (0.0-1.0) ranks traders by quality

### 2. Half-Kelly Position Sizing
- **Optimal Bet Sizing**: Kelly Criterion mathematics for maximum long-term growth
- **Conservative Approach**: Half-Kelly (or Quarter-Kelly) reduces variance
- **Edge Detection**: Only trades when edge > 2% (Kelly fraction)
- **Dynamic Sizing**: Adjusts bet size based on Sharp trader win rate and market odds

### 3. Multi-Layer Risk Management
- **Layer 1: Pre-Trade Validation** - Market liquidity, slippage, trade staleness checks
- **Layer 2: Position Limits** - Max 10% per trade, 30% total exposure, 5% per market
- **Layer 3: Circuit Breakers** - Auto-pause on 10% daily loss, 5 consecutive losses
- **Layer 4: Monitoring** - Real-time alerts via Telegram for all risk events

### 4. Built on Open-Source Foundation
- Based on `vladmeer/polymarket-copy-trading-bot` (TypeScript)
- Enhanced with Python for data analysis and ML capabilities
- Integrated with Polymarket API and py-clob-client
- PostgreSQL database for comprehensive trade tracking

---

## 📊 Performance Targets

After 3 months of operation:
- **Win Rate**: 70%+
- **Monthly ROI**: 15%+
- **Max Drawdown**: <20%
- **Sharpe Ratio**: >1.5

**Methodology Source**: skill-from-masters research + expert frameworks from:
- Ed Thorp (Kelly Criterion)
- Larry Williams (Trading systems)
- Polymarket Sharp trader analysis

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15
- Node.js 18+ (for py-clob-client)
- Polygon wallet with USDC
- Infura/Alchemy RPC endpoint

### Installation

```bash
# Clone repository
cd polymarket-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp config.example.yaml config.yaml

# Edit config.yaml with your settings
# - Add wallet private key
# - Add RPC URL
# - Add Telegram bot token (optional)
# - Set paper_trading: true for testing

# Initialize database
python scripts/init_db.py

# Run Sharp trader scanner (find traders to follow)
python src/sharp_trader_identifier.py

# Start bot in paper trading mode
python main.py
```

### Configuration

Edit `config.yaml`:

```yaml
# 1. Set your wallet (KEEP SECURE!)
wallet:
  private_key: "YOUR_PRIVATE_KEY"
  proxy_wallet_address: "YOUR_WALLET_ADDRESS"

# 2. Configure RPC
blockchain:
  rpc_url: "https://polygon-mainnet.infura.io/v3/YOUR_PROJECT_ID"

# 3. Set initial bankroll
paper_trading:
  enabled: true  # Start with paper trading!
  initial_balance: 10000

# 4. Optional: Telegram notifications
notifications:
  telegram:
    enabled: true
    bot_token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
```

---

## 🏗️ Architecture

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
│Identification│     │ (Half-Kelly) │     │   Engine     │
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

### Core Components

**1. Sharp Trader Identifier** (`src/sharp_trader_identifier.py`)
- Scans Polymarket leaderboard for profitable traders
- Calculates Sharp Score using weighted metrics
- Updates every 6 hours to stay within API limits

**2. Kelly Criterion Sizer** (`src/kelly_criterion.py`)
- Calculates optimal bet size using Kelly formula
- Implements Half-Kelly for reduced variance
- Applies maximum bet constraints (10% per trade)

**3. Risk Manager** (`src/risk_manager.py`)
- Pre-trade validation (liquidity, slippage, staleness)
- Position limits enforcement
- Circuit breaker monitoring
- Daily P&L tracking

**4. Trade Executor** (`src/trade_executor.py`)
- Monitors Sharp trader positions every 4 seconds
- Executes copy trades via Polymarket CLOB API
- Handles order placement and fills

**5. Database Models** (`src/models.py`)
- Sharp traders table (profiles, scores)
- Positions table (open, closed)
- Copy trades table (history, P&L)
- Daily performance table (metrics)

---

## 📖 Usage Guide

### Finding Sharp Traders

```bash
# Scan for Sharp traders (requires wallet addresses)
# Get addresses from https://polymarket.com/leaderboard

python src/sharp_trader_identifier.py

# Output:
# === Top Sharp Traders ===
#
# #1 0xABC123...
#    Sharp Score: 0.872
#    Win Rate: 75.3%
#    ROI: 28.5%
#    Volume: $125,430
#    Trades: 87
```

Add top traders to your config:

```yaml
# In config.yaml
sharp_traders:
  wallets:
    - "0xABC123..."  # Rank #1 trader
    - "0xDEF456..."  # Rank #2 trader
```

### Running the Bot

```bash
# Paper trading mode (recommended for first month)
python main.py --mode paper

# Live trading mode (after successful paper trading)
python main.py --mode live

# Backtest mode
python main.py --mode backtest --start 2024-01-01 --end 2024-12-31
```

### Monitoring

```bash
# Check current positions
python scripts/check_positions.py

# View performance
python scripts/performance_report.py --period 7d

# Check risk status
python scripts/risk_report.py
```

---

## ⚙️ Configuration Deep Dive

### Sharp Trader Criteria

The bot identifies "Sharp traders" using these thresholds:

| Metric | Threshold | Why |
|--------|-----------|-----|
| Win Rate | 70%+ | Statistical edge (coin flip = 50%) |
| Min Trades | 50+ | Enough data for significance |
| Min Volume | $10K+ | Serious traders, not hobbyists |
| Max Avg Odds | 90% | Avoids traders who only bet on sure things |
| ROI | 20%+ | Profitable performance |
| Consistency | 60%+ | Stable performance over time |
| Recency | 30 days | Currently active |

**Sharp Score Formula**:
```
Score = 0.35×WinRate + 0.25×ROI + 0.20×Consistency + 0.10×Volume + 0.10×Recency
```

### Kelly Criterion Math

**Full Kelly Formula**:
```
f* = (bp - q) / b

Where:
- f* = fraction of bankroll to bet
- b = odds received (decimal odds - 1)
- p = probability of winning (Sharp trader's win rate)
- q = probability of losing (1 - p)
```

**Half-Kelly** (recommended):
```
f_half = f* × 0.5
```

**Example**:
- Sharp trader: 75% win rate (p = 0.75)
- Market odds: 0.65 (65%)
- Bankroll: $10,000

```python
b = (1 / 0.65) - 1 = 0.538
f* = (0.538 × 0.75 - 0.25) / 0.538 = 0.285  # Full Kelly: 28.5%
f_half = 0.285 × 0.5 = 0.143  # Half Kelly: 14.3%

# But capped at max 10% per trade
Final bet = min(0.143 × 10000, 0.10 × 10000) = $1,000
```

### Risk Management Layers

**Layer 1: Pre-Trade Validation**
```python
# Before executing any trade, check:
- Sharp trader still meets criteria?
- Market has sufficient liquidity (>$10K)?
- Odds haven't moved >5% (slippage check)?
- Trade is recent (<60 seconds old)?
- Account has sufficient balance?
```

**Layer 2: Position Limits**
```python
# Enforce hard limits:
- Max per trade: 10% of bankroll
- Max total exposure: 30% of bankroll
- Max per market: 5% of bankroll
- Max per Sharp trader: 15% of bankroll
```

**Layer 3: Circuit Breakers**
```python
# Auto-pause trading if:
- Daily loss > 10%
- 5 consecutive losses
- Sharp trader drawdown > 30%
- 10 API errors in 1 hour
```

**Layer 4: Monitoring**
```python
# Real-time alerts via Telegram:
- Every trade executed
- Risk limit breaches
- Circuit breaker triggers
- Daily P&L reports
```

---

## 🧪 Testing & Validation

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific module
pytest tests/test_kelly_criterion.py

# Run with coverage
pytest --cov=src tests/
```

### Backtesting

```bash
# Backtest on historical data
python scripts/backtest.py --start 2024-01-01 --end 2024-12-31

# Output:
# === Backtest Results ===
# Period: 2024-01-01 to 2024-12-31
# Initial bankroll: $10,000
# Final bankroll: $14,250
# Total return: +42.5%
# Win rate: 72.3%
# Sharpe ratio: 1.87
# Max drawdown: -12.4%
```

### Paper Trading

**Highly recommended before live trading:**

1. Set `paper_trading: true` in config
2. Run for 1-2 months
3. Monitor performance and risk metrics
4. Only go live if:
   - Win rate > 70%
   - Max drawdown < 20%
   - No circuit breaker triggers
   - Comfortable with trade execution

---

## 🔒 Security Best Practices

### Private Key Management

**❌ NEVER:**
- Commit private keys to git
- Share private keys
- Store in plain text

**✅ DO:**
- Use environment variables
- Use `.env` file (gitignored)
- Consider hardware wallet integration
- Start with small amounts

```bash
# .env file
WALLET_PRIVATE_KEY=your_private_key_here

# config.yaml
wallet:
  private_key: ${WALLET_PRIVATE_KEY}  # Load from env
```

### Network Security

- Use HTTPS RPC endpoints only
- Enable firewall on server
- Use VPN for additional security
- Monitor for unusual activity

---

## 📊 Monitoring Dashboard (Future)

**FastAPI Dashboard** (planned):
- Real-time P&L tracking
- Position visualization
- Sharp trader leaderboard
- Risk metrics charts
- Trade history table
- Circuit breaker status

Access at: `http://localhost:8000/dashboard`

---

## 🛠️ Troubleshooting

### Common Issues

**1. "Insufficient Balance" Error**
```bash
# Check USDC balance
python scripts/check_balance.py

# Check gas (MATIC) balance
python scripts/check_gas.py
```

**2. "API Rate Limit" Error**
```yaml
# In config.yaml, increase polling interval
polling:
  position_check_seconds: 10  # Was 4, now 10
```

**3. "Sharp Trader Not Found"**
- Verify wallet address is correct
- Check trader has recent activity
- Ensure trader meets criteria

**4. "Circuit Breaker Active"**
```bash
# Review reason
python scripts/check_circuit_breaker.py

# Reset manually (if safe)
python scripts/reset_circuit_breaker.py
```

---

## 📈 Performance Optimization

### Recommended Settings by Bankroll

**Small (<$1,000)**:
```yaml
kelly_sizing:
  use_quarter_kelly: true  # More conservative
  max_bet_pct: 0.05  # 5% max
risk_management:
  max_total_exposure_pct: 0.20  # 20% max
```

**Medium ($1,000-$10,000)**:
```yaml
kelly_sizing:
  use_half_kelly: true
  max_bet_pct: 0.10
risk_management:
  max_total_exposure_pct: 0.30
```

**Large (>$10,000)**:
```yaml
kelly_sizing:
  use_half_kelly: true
  max_bet_pct: 0.10
risk_management:
  max_total_exposure_pct: 0.40  # Can increase slightly
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## ⚖️ Legal Disclaimer

**This software is for educational and research purposes.**

- Trading involves significant risk of loss
- Past performance doesn't guarantee future results
- Users are responsible for compliance with local regulations
- Never invest more than you can afford to lose
- The authors are not liable for any losses

**Polymarket Availability:**
- Not available in US, UK, and some other jurisdictions
- Check your local laws before using
- Use VPN at your own risk

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/polymarket-bot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/polymarket-bot/discussions)
- **Email**: your.email@example.com

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

**Methodology Sources:**
- skill-from-masters framework
- Ed Thorp: Kelly Criterion mathematics
- Larry Williams: Trading systems design
- vladmeer: Open-source Polymarket bot foundation
- Polymarket community: Sharp trader research

**Built with:**
- Python 3.11
- py-clob-client (Polymarket trading)
- SQLAlchemy (database ORM)
- FastAPI (dashboard)
- httpx (async HTTP)

---

**⚠️ Remember: Start with paper trading, test thoroughly, and never risk more than you can afford to lose.**

**🚀 Happy Trading!**
