# check_connection.py
import MetaTrader5 as mt5

print("🔧 Starting MT5 Diagnosis...")

# 1. Check Connection
if not mt5.initialize():
    print(f"❌ INIT FAILED. Error: {mt5.last_error()}")
    print("❌ FIX: Open MT5 App, Login, then run again.")
else:
    print("✅ MT5 Initialized Successfully.")

# 2. Check Terminal Info
terminal_info = mt5.terminal_info()
if terminal_info:
    print(f"🏢 Terminal Name: {terminal_info.name}")
    print(f"🏢 Connection Path: {terminal_info.path}")
    print(f"🏢 Connected: {terminal_info.connected}")
    print(f"🏢 Trade Allowed: {terminal_info.trade_allowed}")
else:
    print("❌ Could not get Terminal Info.")

# 3. Check Symbols
symbols_to_check = ["EURUSD", "XAUUSD"]
print(f"\n🔭 Checking Market Watch...")

for symbol in symbols_to_check:
    # Check if symbol exists
    info = mt5.symbol_info(symbol)
    if info is None:
        print(f"❌ SYMBOL MISSING: {symbol}")
        print(f"   FIX: Right-click Market Watch -> Show All -> Find {symbol} and add it.")
    else:
        print(f"✅ SYMBOL OK: {symbol}")
        
        # Try to Fetch 10 Bars
        print(f"   Fetching 10 bars...")
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 10)
        
        if rates is None:
            print(f"   ❌ DATA FAILED. Market is likely CLOSED.")
        else:
            print(f"   ✅ DATA OK. Last price: {rates[0]['close']}")

print("\n🔧 Diagnosis Complete.")
mt5.shutdown()