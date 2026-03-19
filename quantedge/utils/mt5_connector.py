# utils/mt5_connector.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Optional, List, Dict

class MT5Connector:
    def __init__(self):
        self.connected = False
        # FORCE the path that worked for you earlier
        self.terminal_path = r"C:\quantedge\terminal64.exe"
        self.symbol_cache = {}  # Cache resolved symbols

        # Common broker suffixes
        self.common_suffixes = [
            "",      # No suffix (standard)
            ".i",    # ICMarkets
            ".a",    # Alpari
            ".raw",  # Raw spread
            ".pro",  # Professional
            ".m",    # Mini
            ".c",    # Classic
            "_",     # Underscore variant
            "m",     # Lowercase m
            "pro",   # Lowercase pro
        ]

    def connect(self):
        """Initialize and login to MT5"""
        # 1. Check if file exists first (Safety)
        if not os.path.exists(self.terminal_path):
            print(f"❌ File not found: {self.terminal_path}")
            return False

        # 2. Initialize with EXPLICIT path
        if not mt5.initialize(path=self.terminal_path):
            print(f"❌ Init Failed (Path: {self.terminal_path}). Error: {mt5.last_error()}")
            return False

        self.connected = True
        print("✅ MT5 Connected")
        return True

    def resolve_symbol(self, base_symbol: str) -> Optional[str]:
        """
        Smart symbol resolver - tries multiple variations to find the actual MT5 symbol.

        Args:
            base_symbol: Base symbol name (e.g., "EURUSD", "BTCUSD", "XAUUSD")

        Returns:
            Actual MT5 symbol name if found, None otherwise
        """
        # Check cache first
        if base_symbol in self.symbol_cache:
            return self.symbol_cache[base_symbol]

        if not self.connected:
            self.connect()

        # Try the base symbol first
        if mt5.symbol_info(base_symbol) is not None:
            self.symbol_cache[base_symbol] = base_symbol
            print(f"✅ Symbol found: {base_symbol}")
            return base_symbol

        # Try with common suffixes
        for suffix in self.common_suffixes:
            test_symbol = f"{base_symbol}{suffix}"
            if mt5.symbol_info(test_symbol) is not None:
                self.symbol_cache[base_symbol] = test_symbol
                print(f"✅ Symbol found: {base_symbol} -> {test_symbol}")
                return test_symbol

        # Try alternative names for crypto
        if "BTC" in base_symbol or "ETH" in base_symbol:
            alternatives = []

            if "BTCUSD" in base_symbol:
                alternatives = ["Bitcoin", "BTCUSD", "BTC/USD", "XBTUSD", "BTC"]
            elif "ETHUSD" in base_symbol:
                alternatives = ["Ethereum", "ETHUSD", "ETH/USD", "ETHUSD", "ETH"]

            for alt in alternatives:
                # Try alternative with suffixes
                for suffix in self.common_suffixes:
                    test_symbol = f"{alt}{suffix}"
                    if mt5.symbol_info(test_symbol) is not None:
                        self.symbol_cache[base_symbol] = test_symbol
                        print(f"✅ Symbol found: {base_symbol} -> {test_symbol}")
                        return test_symbol

        # Try alternative names for metals
        if "XAU" in base_symbol:
            alternatives = ["XAUUSD", "GOLD", "Gold"]
            for alt in alternatives:
                for suffix in self.common_suffixes:
                    test_symbol = f"{alt}{suffix}"
                    if mt5.symbol_info(test_symbol) is not None:
                        self.symbol_cache[base_symbol] = test_symbol
                        print(f"✅ Symbol found: {base_symbol} -> {test_symbol}")
                        return test_symbol

        if "XAG" in base_symbol:
            alternatives = ["XAGUSD", "SILVER", "Silver"]
            for alt in alternatives:
                for suffix in self.common_suffixes:
                    test_symbol = f"{alt}{suffix}"
                    if mt5.symbol_info(test_symbol) is not None:
                        self.symbol_cache[base_symbol] = test_symbol
                        print(f"✅ Symbol found: {base_symbol} -> {test_symbol}")
                        return test_symbol

        print(f"❌ Symbol not found: {base_symbol} (tried {len(self.common_suffixes)} variations)")
        return None

    def enable_symbol(self, symbol: str) -> bool:
        """
        Enable symbol in Market Watch (make it visible and tradeable).

        Args:
            symbol: MT5 symbol name

        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            self.connect()

        # Resolve the symbol first
        resolved_symbol = self.resolve_symbol(symbol)
        if resolved_symbol is None:
            return False

        # Enable the symbol in Market Watch
        if not mt5.symbol_select(resolved_symbol, True):
            print(f"⚠️ Failed to enable {resolved_symbol} in Market Watch")
            return False

        print(f"✅ Symbol {resolved_symbol} enabled in Market Watch")
        return True

    def enable_multiple_symbols(self, symbols: List[str]) -> Dict[str, Optional[str]]:
        """
        Enable multiple symbols in Market Watch at once.

        Args:
            symbols: List of base symbol names

        Returns:
            Dictionary mapping base symbol to resolved symbol (or None if failed)
        """
        results = {}

        print(f"\n{'='*60}")
        print(f"🔍 AUTO-ENABLING {len(symbols)} SYMBOLS IN MT5 MARKET WATCH")
        print(f"{'='*60}")

        for symbol in symbols:
            resolved = self.resolve_symbol(symbol)
            if resolved:
                self.enable_symbol(resolved)
            results[symbol] = resolved

        # Summary
        successful = sum(1 for v in results.values() if v is not None)
        print(f"\n✅ Successfully enabled {successful}/{len(symbols)} symbols")
        print(f"{'='*60}\n")

        return results

    def get_historical_data(self, symbol, timeframe, bars=5000):
        if not self.connected:
            self.connect()

        # Resolve symbol
        resolved_symbol = self.resolve_symbol(symbol)
        if resolved_symbol is None:
            print(f"❌ Symbol not found: {symbol}")
            return None

        rates = mt5.copy_rates_from_pos(resolved_symbol, timeframe, 0, bars)
        if rates is None:
            print(f"No data found for {resolved_symbol}")
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_latest_bars(self, symbol, timeframe, count=200):
        """
        Robust fetcher with Explicit Path Check and Smart Symbol Resolution
        """
        if not self.connected:
            self.connect()

        # Explicit Path Check
        if not os.path.exists(self.terminal_path):
            print(f"❌ Terminal file missing. Path: {self.terminal_path}")
            return None

        # Resolve symbol first
        resolved_symbol = self.resolve_symbol(symbol)
        if resolved_symbol is None:
            print(f"❌ Symbol not found: {symbol}")
            return None

        # Use Explicit Path with resolved symbol
        try:
            rates = mt5.copy_rates_from_pos(resolved_symbol, timeframe, 0, count)
        except Exception as e:
            print(f"⚠️ Fetch Exception for {resolved_symbol}: {e}")
            return None

        if rates is None:
            print(f"❌ No data fetched for {resolved_symbol}")
            return None
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_available_symbols(self) -> List[str]:
        """Get all available symbols in MT5."""
        if not self.connected:
            self.connect()

        symbols = mt5.symbols_get()
        if symbols is None:
            return []

        return [s.name for s in symbols]

    def shutdown(self):
        mt5.shutdown()