#!/usr/bin/env python3
# test_mt5_connection.py - Quick MT5 Connection Test
"""
Quick diagnostic tool to check MT5 connection and available symbols.

Run this BEFORE starting the bot to verify everything works.
"""

import MetaTrader5 as mt5
from datetime import datetime

print("=" * 70)
print("MT5 CONNECTION DIAGNOSTIC TEST")
print("=" * 70)
print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Test 1: MT5 Installation
print("[1/5] Checking MT5 Installation...")
try:
    version = mt5.__version__
    print(f"   [OK] MT5 Python package version: {version}")
except Exception as e:
    print(f"   [FAIL] MT5 package error: {e}")
    exit(1)

# Test 2: Initialize MT5
print("\n[2/5] Initializing MT5...")
if not mt5.initialize():
    error = mt5.last_error()
    print(f"   [FAIL] MT5 initialization failed")
    print(f"   Error: {error}")
    print("\n   Solutions:")
    print("   - Make sure MetaTrader 5 is installed")
    print("   - Open MT5 application")
    print("   - Try running as administrator")
    exit(1)
else:
    print("   [OK] MT5 initialized successfully")

# Test 3: Check Terminal Info
print("\n[3/5] Checking Terminal Info...")
terminal_info = mt5.terminal_info()
if terminal_info:
    print(f"   [OK] MT5 Terminal: {terminal_info.name}")
    print(f"   [OK] Company: {terminal_info.company}")
    print(f"   [OK] Connected: {terminal_info.connected}")

    if not terminal_info.connected:
        print("\n   [WARNING] Not connected to trading server!")
        print("   Please login to your account in MT5")
else:
    print("   [FAIL] Could not get terminal info")

# Test 4: Check Account Info
print("\n[4/5] Checking Account Info...")
account_info = mt5.account_info()
if account_info:
    print(f"   [OK] Login: {account_info.login}")
    print(f"   [OK] Server: {account_info.server}")
    print(f"   [OK] Balance: ${account_info.balance:.2f}")
    print(f"   [OK] Equity: ${account_info.equity:.2f}")
    print(f"   [OK] Trade Allowed: {account_info.trade_allowed}")

    if not account_info.trade_allowed:
        print("\n   [WARNING] Trading not allowed on this account!")
else:
    print("   [FAIL] Not logged in to any account")
    print("   Please login to MT5")

# Test 5: Test Symbol Availability
print("\n[5/5] Testing Symbol Availability...")

test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "XAUUSD"]
available_symbols = []
unavailable_symbols = []

for symbol in test_symbols:
    # Try to get symbol info
    info = mt5.symbol_info(symbol)

    if info is None:
        # Try with common suffixes
        for suffix in ["", ".raw", ".a", ".pro", ".m", ".e", ".i", ".c"]:
            test_name = symbol + suffix
            info = mt5.symbol_info(test_name)
            if info:
                print(f"   [OK] {symbol} found as '{test_name}'")
                available_symbols.append(test_name)

                # Try to enable it
                if not info.visible:
                    if mt5.symbol_select(test_name, True):
                        print(f"        Enabled in Market Watch")
                    else:
                        print(f"        Warning: Could not enable in Market Watch")
                break
        else:
            print(f"   [FAIL] {symbol} - NOT FOUND")
            unavailable_symbols.append(symbol)
    else:
        print(f"   [OK] {symbol} - Available")
        available_symbols.append(symbol)

        # Try to enable it
        if not info.visible:
            if mt5.symbol_select(symbol, True):
                print(f"        Enabled in Market Watch")

# Summary
print("\n" + "=" * 70)
print("DIAGNOSTIC SUMMARY")
print("=" * 70)
print(f"Available Symbols: {len(available_symbols)}/{len(test_symbols)}")
print(f"Symbol List: {', '.join(available_symbols) if available_symbols else 'NONE'}")

if unavailable_symbols:
    print(f"\nUnavailable Symbols: {', '.join(unavailable_symbols)}")
    print("\nNote: Your broker may use different symbol names.")
    print("Check MT5 Market Watch for exact symbol names.")

# Final verdict
print("\n" + "=" * 70)
if available_symbols and account_info and terminal_info.connected:
    print("STATUS: READY TO TRADE")
    print("=" * 70)
    print("\nYour system is ready! You can now run:")
    print("  python bot_v6_ultimate.py")
else:
    print("STATUS: NOT READY")
    print("=" * 70)
    print("\nPlease fix the issues above before running the bot.")

    if not account_info:
        print("\n[ACTION REQUIRED] Login to MT5:")
        print("  1. Open MetaTrader 5")
        print("  2. Click File > Login to Trade Account")
        print("  3. Enter your credentials")

    if not terminal_info.connected:
        print("\n[ACTION REQUIRED] Connect to server:")
        print("  1. Make sure you're logged in")
        print("  2. Check internet connection")
        print("  3. Restart MT5 if needed")

    if not available_symbols:
        print("\n[ACTION REQUIRED] Add symbols:")
        print("  1. Open MT5")
        print("  2. Go to View > Market Watch")
        print("  3. Right-click > Show All")
        print("  4. Find EURUSD, GBPUSD, etc.")

print("=" * 70)

# Cleanup
mt5.shutdown()
