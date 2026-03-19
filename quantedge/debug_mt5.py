# debug_mt5.py
import MetaTrader5 as mt5

print("🔧 Starting Diagnostic...")

# 1. Check Connection
if not mt5.initialize(path=r"C:\quantedge\terminal64.exe"):
    print(f"❌ Init Failed: {mt5.last_error()}")
    exit()
print("✅ MT5 Initialized.")

# 2. Check Symbols (The most common issue)
print("\n--- Checking Symbol Names ---")
symbols = ["EURUSD", "XAUUSD", "XAUUSDm", "XAUUSDd", "EURUSDm", "EURUSDd"]
found = []

for s in symbols:
    info = mt5.symbol_info(s)
    if info is not None:
        print(f"✅ FOUND: {s}")
        found.append(s)
    else:
        print(f"❌ NOT FOUND: {s}")

# 3. Try Fetching (If found)
print("\n--- Attempting Fetch (Last 100 bars) ---")
if found:
    rates = mt5.copy_rates_from_pos(found[0], mt5.TIMEFRAME_M5, 0, 100)
    if rates is None:
        print(f"❌ Fetch Failed for {found[0]}. Error: {mt5.last_error()}")
    else:
        print(f"✅ Success! Fetched {len(rates)} bars. Last close: {rates[-1][4]}")

mt5.shutdown()