# QuantEdge V6 - QUICK START ⚡

## 🚀 Run in 3 Steps

### 1. Install Dependencies (One-Time)
```bash
pip install qdrant-client fastembed numpy pandas scikit-learn
```

### 2. Start MT5
- Open MetaTrader 5
- Enable "Algo Trading" (top toolbar)
- Login to your account

### 3. Run the Bot
```bash
cd "C:\Users\ADJEI CECIL ELORM\OneDrive\quantedge"
python bot_v6_ultimate.py
```

**That's it!** 🎉

---

## 📊 What You'll See

```
🚀 QUANTEDGE V6.0 - RAG INTELLIGENCE SYSTEM
================================================
🔮 SHADOW MODE ENABLED
   All trades will be LOGGED, not EXECUTED
   This is SAFE for testing new strategies
================================================

📦 Loading V5 Core Systems...
🧠 Loading V6 RAG Intelligence...
📊 Loading V6 Quant Models...
🏛️ Loading V6 Microstructure Filters...
🛡️ Loading V6 Safety Systems...

🌍 Configuring Expanded Symbol Universe...
🔍 AUTO-DETECTING SYMBOLS...

FOREX MAJORS:
✅ EURUSD enabled
✅ GBPUSD enabled
✅ USDJPY enabled
...

✅ SYMBOL DETECTION COMPLETE
   Total Symbols: 40+

📈 Initializing Market Analysis...
🔗 Finding Trading Pairs...
   Found 15 viable pairs

📰 Fetching Recent News...
   Fetched 25 news events
   Stored 25 events in vector DB

✅ QUANTEDGE V6.0 INITIALIZED SUCCESSFULLY
Mode: 🔮 SHADOW MODE (Safe - Logging Only)
Symbols: 42
Trading Pairs: 15

🤖 QUANTEDGE V6 TRADING LOOP STARTED
```

---

## 💡 Understanding the Output

### Each Cycle (~30s):
```
📊 CYCLE #1 - 2025-01-20 14:30:00
================================================
🔍 Scanning 42 symbols...
   Found 3 opportunities

💡 Opportunity: EURUSD
   Regime: Trend Following
   Signal: BUY
   Jump Prob: 25.3%

🔮 SHADOW TRADE LOGGED: EURUSD BUY
   Size: $250.00 (0.02 lots)
   Entry: 1.08450
   SL: 1.08200 | TP: 1.08950
```

**Shadow trades are LOGGED ONLY - no real money at risk!**

---

## 📈 View Performance (Every 20 Cycles)

```
📈 PERFORMANCE SUMMARY
================================================
🛡️ RISK GATES STATUS
   Account Balance: $10,000.00
   Daily Loss: +0.00% / 5.0% max
   Kill Switch: ✅ OK
   Open Trades: 0 / 5 max
   GA Updates This Month: 0 / 4 max
   Human Override: ✅ Disabled

🔮 SHADOW MODE PERFORMANCE
   Total Trades: 12
   Wins: 7
   Losses: 5
   Win Rate: 58.3%
   Total P&L: +4.25%
   Avg per Trade: +0.35%
```

---

## ⚡ Go Live (After Testing)

### When Shadow Performance Looks Good:
```bash
python bot_v6_ultimate.py --live --balance 10000
```

**⚠️ WARNING: This uses REAL MONEY!**

### Recommended:
1. Test shadow mode 24 hours minimum
2. Win rate > 55%
3. Start with small balance ($100-500)
4. Scale up gradually

---

## 🛑 Stop the Bot

Press `Ctrl + C` in the terminal

---

## 📊 Trading Stats

### Symbols Traded:
- **40+ symbols** across forex, indices, metals, crypto, commodities
- Auto-detects what your broker supports
- Correlation-filtered to avoid overexposure

### Position Sizing:
- Max 10% per trade (hard limit)
- Enhanced Kelly Criterion with news/regime adjustments
- Automatically reduced in high-volatility regimes

### Risk Management:
- 5% daily loss = automatic shutdown
- VPIN filter blocks toxic order flow
- Correlation filter prevents clustered risk
- Max 20 trades per day

---

## 🧠 Intelligence Features

### RAG System:
- Fetches news every 5 minutes
- Scores source credibility
- Semantic search for relevant context
- Structured feature extraction

### Quant Models:
- **Jump-Diffusion**: Predicts news-driven jumps
- **Info Decay**: Optimal holding periods
- **Enhanced Kelly**: Dynamic position sizing

### Microstructure:
- **VPIN**: Detects informed trading
- **Lead-Lag**: Front-runs correlations
- **Pairs**: Delta-neutral strategies

---

## 📁 Important Files

### Logs:
- `data/shadow_trades.json` - Shadow trade history
- Console output - Real-time logs

### Config:
- `bot_v6_ultimate.py` - Main settings (line 120 for symbols)
- `safety/risk_gates.py` - Risk limits
- `data/config_ga.json` - GA-optimized parameters

### Docs:
- `V6_INTEGRATION_COMPLETE.md` - Full reference
- `V6_FINAL_SUMMARY.md` - Technical details
- `QUANTEDGE_V6_ARCHITECTURE.md` - System design

---

## 🆘 Common Issues

### "Module not found"
```bash
pip install qdrant-client fastembed numpy pandas scikit-learn tensorflow
```

### "MT5 not connected"
- Open MT5
- Enable "Algo Trading"
- Restart bot

### "No symbols enabled"
- Check broker supports these symbols
- Try standard pairs: EURUSD, GBPUSD, XAUUSD
- Reduce symbol list in code

### "Qdrant error"
- Will auto-use in-memory mode
- No action needed

---

## 🎯 Next Actions

### Today:
- [x] Run bot in shadow mode
- [ ] Let it run 2-4 hours
- [ ] Check performance stats

### This Week:
- [ ] Run shadow mode 24+ hours
- [ ] Review win rate and P&L
- [ ] If good, go live with $100-500

### This Month:
- [ ] Monitor live performance
- [ ] Scale up gradually
- [ ] Add more symbols if needed

---

## 💪 What Makes This Special

✅ **40+ symbols** - More opportunities
✅ **RAG intelligence** - Context-aware decisions
✅ **Regime adaptation** - Works in all markets
✅ **Multi-layer safety** - Can't blow up account
✅ **Shadow mode** - Risk-free testing
✅ **Institutional models** - Hedge fund techniques

---

## 🏆 You're Ready!

```bash
python bot_v6_ultimate.py
```

**Watch it trade, learn the patterns, go live when ready!**

📈 **Happy Trading!** 💰
