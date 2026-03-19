# 🚀 START HERE - Quick Setup Guide

## ⚡ **3-Step Quick Start**

### **Step 1: Test MT5 Connection**
```bash
python test_mt5_connection.py
```

**This will check:**
- ✅ MT5 is installed
- ✅ MT5 is connected
- ✅ You're logged in
- ✅ Symbols are available

**Expected Output:** "STATUS: READY TO TRADE"

---

### **Step 2: Start the Bot (Shadow Mode)**
```bash
python bot_v6_ultimate.py
```

**You should see:**
```
✅ EURUSD enabled
✅ GBPUSD enabled
✅ USDJPY enabled
✅ AUDUSD enabled
✅ XAUUSD enabled

Total Symbols: 5
```

**Bot will run in SHADOW MODE** (no real trades)

---

### **Step 3: Go Live When Ready**
```bash
python bot_v6_ultimate.py --live --balance 10000
```

**Replace 10000 with your actual balance!**

---

## ❌ **If You See "NO SYMBOLS" or "0 symbols"**

### Quick Fix:

1. **Open MetaTrader 5**
2. **Login** to your account
3. Click **"Algo Trading"** button (top toolbar - should turn GREEN)
4. **Check Market Watch** (View > Market Watch)
   - Right-click > "Show All"
   - Make sure EURUSD, GBPUSD, etc. are visible
5. **Restart the bot**

---

## 🔧 **Troubleshooting**

### Problem: "MT5 not initialized"
**Solution:**
- Close and reopen MT5
- Make sure you're logged in
- Run as administrator

### Problem: "Trading not allowed"
**Solution:**
- Check if your account allows algo trading
- Contact your broker
- Make sure account is funded

### Problem: Symbols not found
**Solution:**
- Your broker may use different names (e.g., "EURUSD.raw" or "EURUSD.a")
- Run `python test_mt5_connection.py` to see exact names
- Check MT5 Market Watch for available symbols

---

## 📊 **What the Bot Does**

### Shadow Mode (Default):
- Scans 5 symbols every 30 seconds
- Analyzes news and market conditions
- Applies V6 intelligence (RAG, Quant, Microstructure)
- **LOGS trades** to `data/shadow_trades.json`
- **Does NOT execute** real trades

### Live Mode (--live):
- Same as shadow mode BUT
- **EXECUTES REAL TRADES** on MT5
- ⚠️ **REAL MONEY AT RISK**

---

## 🛡️ **Safety Features**

- **Shadow Mode Default** - Must explicitly use `--live` to trade real money
- **5% Kill Switch** - Auto-stops if daily loss reaches 5%
- **10% Max Per Trade** - Cannot risk more than 10% on single trade
- **Max 5 Open Trades** - Position limits
- **VPIN Filter** - Blocks toxic order flow
- **Correlation Filter** - Prevents overexposure

---

## 📈 **Symbols Traded**

**Forex (4 pairs):**
- EURUSD
- GBPUSD
- USDJPY
- AUDUSD

**Metals (1):**
- XAUUSD (Gold)

**Total: 5 symbols**

*(Simplified from 40+ to ensure compatibility with all brokers)*

---

## ⏹️ **How to Stop the Bot**

**Press `Ctrl + C`** in the terminal

Or just close the terminal window.

Bot will finish current cycle and exit safely.

---

## 📊 **Monitoring**

### Every Cycle You'll See:
```
📊 CYCLE #5 - 2026-03-01 14:30:00
🔍 Scanning 5 symbols...
   Found 2 opportunities

💡 Opportunity: EURUSD
   Signal: BUY
   Jump Prob: 25.3%

🔮 SHADOW TRADE LOGGED: EURUSD BUY
   Size: $250.00 (0.02 lots)
```

### Every 20 Cycles (Performance Summary):
```
🛡️ RISK GATES STATUS
   Account Balance: $10,000.00
   Daily Loss: +0.50% / 5.0% max
   Kill Switch: ✅ OK

🔮 SHADOW MODE PERFORMANCE
   Total Trades: 15
   Wins: 9
   Win Rate: 60.0%
   Total P&L: +2.5%
```

---

## ✅ **Quick Checklist Before Going Live**

- [ ] Ran `python test_mt5_connection.py` - Status: READY
- [ ] Shadow mode tested for 24+ hours
- [ ] Win rate > 55% in shadow mode
- [ ] Positive P&L in shadow mode
- [ ] MT5 "Algo Trading" button is GREEN
- [ ] Starting with small balance ($100-500)
- [ ] Know how to stop bot (Ctrl+C)

---

## 🎯 **Commands Reference**

```bash
# Test MT5 connection
python test_mt5_connection.py

# Validate system
python FINAL_CHECK.py

# Run shadow mode
python bot_v6_ultimate.py

# Run live trading
python bot_v6_ultimate.py --live --balance 10000
```

---

## 📁 **Important Files**

- `bot_v6_ultimate.py` - Main trading bot
- `test_mt5_connection.py` - Connection diagnostic tool
- `FINAL_CHECK.py` - System validation
- `data/shadow_trades.json` - Shadow trade logs
- `START_HERE.md` - This file

---

## 🆘 **Need Help?**

1. Run `python test_mt5_connection.py` to diagnose
2. Check `FINAL_REVIEW.md` for detailed info
3. Read `QUICKSTART_V6.md` for more details

---

**🚀 You're ready! Start with `python test_mt5_connection.py` 🚀**
