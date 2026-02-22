# HK Trading Bot - Claude Code Instructions

## Project Overview

港股智能交易系统 - 板块交易顾问

**核心功能**：
- 扫描富途发现涨的板块
- 四重数据源分析（量价+新闻+资金+情绪）
- AI分析炒作周期和进场时机
- Telegram推送交易建议

**技术栈**：
- 富途OpenD API (行情数据)
- Gemini 2.5 Flash (AI分析)
- Grok API (社区情绪)
- Telegram Bot (推送)

**重要限制**：
- 富途仅允许只读操作（查询行情、持仓、资金）
- 禁止任何交易操作（place_order等）

---

## Workflow Orchestration

### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## Task Management

1. **Plan First**: Write plan to `tasks/todo.md` with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to `tasks/todo.md`
6. **Capture Lessons**: Update `tasks/lessons.md` after corrections

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Project-Specific Guidelines

### Data Source Priority
1. **量价信号** (Price/Volume) - Most reliable, always available
2. **Gemini搜索** (News) - Real news, quota limited (20/day)
3. **富途资金流** (Capital Flow) - Institutional data, reliable
4. **Grok社区** (Sentiment) - X/Twitter, optional (requires API key)

### Error Handling
- **Graceful Degradation**: Any data source failure should not stop the system
- **Clear Logging**: Print status for each data source attempt
- **Auto-Fallback**: Gemini quota exceeded → rule-based analysis

### Code Style
- Use Chinese for user-facing messages
- Use English for code comments
- Keep functions focused and testable
- Avoid hardcoded values - use config/env vars

### Testing Protocol
- Test with real Futu OpenD connection
- Verify Telegram push before marking complete
- Check quota usage for paid APIs (Gemini, Grok)
- Validate output format matches user expectations

### File Organization
```
hk-trading-bot/
├── sector_trading_advisor.py      # Main entry
├── gemini_analyzer.py              # AI analysis
├── gemini_news_search.py           # News search
├── grok_sentiment_analyzer.py      # Sentiment analysis
├── multi_source_news.py            # Multi-source integration
├── run_advisor.sh                  # Cron script
├── logs/                           # Runtime logs
├── docs/                           # Documentation
└── tasks/                          # Task tracking
    ├── todo.md                     # Current tasks
    └── lessons.md                  # Lessons learned
```

---

## API Keys and Configuration

**Environment Variables** (set in ~/.zshrc):
```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export GEMINI_API_KEY="AIzaSyAKEu9CUAnfLU_BQGgQdBjA0oxBrNkc8M0"
export GROK_API_KEY="your-grok-key"  # Optional
```

**Telegram**:
- Bot Token: `8590123130:AAGu-7p7AUDmZm90M8-svKpTSLUC-VCs80o`
- Chat ID: `7082819163`

**Futu OpenD**:
- Host: `127.0.0.1:11111`
- Read-only access

---

## Common Commands

```bash
# Run advisor manually
cd ~/hk-trading-bot && python3 sector_trading_advisor.py

# Test Gemini analyzer
python3 gemini_analyzer.py

# Test Grok sentiment
python3 grok_sentiment_analyzer.py

# View logs
tail -f logs/advisor_cron.log

# Check cron status
crontab -l
```

---

## Recent Updates

**2026-02-22**:
- ✅ Added Grok social sentiment analysis (方案D)
- ✅ Integrated 4 data sources (price, news, capital, sentiment)
- ✅ Transparent source attribution in reports
- ✅ Auto-degradation for API failures
- ✅ Cron scheduling setup

**Pending**:
- [ ] Get Grok API key from user
- [ ] Enable cron timer (manual setup required)
- [ ] Monitor accuracy for 1 week

---

**Remember**: This is a trading advisor system. Accuracy matters more than speed. Verify all data sources before marking tasks complete.
