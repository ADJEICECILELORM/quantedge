# create_connector.py
# Simple script to recreate mt5_connector.py

file_content = """# utils/mt5_connector.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta

class MT5Connector:
    def __init__(self):
        self.connected = False

    def connect(self):
        \"\"\"Initialize and login to MT5\"\"\"
        if not mt5.initialize():
            print(f\"MT5 initialize() failed, error code = {mt5.last_error()}\")
            return False
        self.connected = True
        print(\"MT5 Connected\")
        return True

    def get_historical_data(self, symbol, timeframe, bars=5000):
        if not self.connected:
            self.connect()
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
        if rates is None:
            print(f\"No data found for {symbol}\")
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_latest_bars(self, symbol, timeframe, count=200):
        \"\"\"
        Robust fetcher with Auto-Reconnect logic.
        \"\"\"
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        
        if rates is None:
            print(f\"⚠️  Data fetch failed for {symbol}. Attempting Reconnect...\")
            self.connected = False
            if self.connect():
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            else:
                print(\"❌ Reconnect failed.\")
                return None

        if rates is None: return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def shutdown(self):
        mt5.shutdown()
"""

# Write the file
try:
    with open("utils/mt5_connector.py", "w", encoding="utf-8") as f:
        f.write(file_content)
    print("✅ utils/mt5_connector.py created successfully.")
except Exception as e:
    print(f"❌ Error creating file: {e}")