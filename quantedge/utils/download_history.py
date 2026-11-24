# utils/download_history.py
"""
Fetch OHLCV history from Yahoo Finance's public chart API into the
same CSV schema the backtest loaders expect (time/open/high/low/close/
tick_volume), so backtests can run without a Windows MT5 terminal.

Usage:
    python utils/download_history.py --symbol EURUSD=X --interval 5m \
        --range 60d --out data/EURUSD_M5.csv
"""
import argparse
import json
import sys
import urllib.request

import pandas as pd


def fetch_yahoo_ohlcv(symbol: str = "EURUSD=X", interval: str = "5m", range_: str = "60d") -> pd.DataFrame:
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval={interval}&range={range_}"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)

    result = data["chart"]["result"]
    if not result:
        raise ValueError(f"Yahoo returned no data for {symbol}: {data['chart'].get('error')}")

    result = result[0]
    ts = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(ts, unit="s", utc=True).tz_localize(None),
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        }
    )
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    df = df.drop_duplicates(subset="time").sort_values("time").reset_index(drop=True)
    df = df.rename(columns={"volume": "tick_volume"})
    df["tick_volume"] = df["tick_volume"].fillna(0).astype(int)
    return df


def main():
    parser = argparse.ArgumentParser(description="Download OHLCV history from Yahoo Finance")
    parser.add_argument("--symbol", default="EURUSD=X")
    parser.add_argument("--interval", default="5m", choices=["1m", "2m", "5m", "15m", "30m", "60m", "1d"])
    parser.add_argument("--range", dest="range_", default="60d")
    parser.add_argument("--out", default="data/history.csv")
    args = parser.parse_args()

    df = fetch_yahoo_ohlcv(args.symbol, args.interval, args.range_)
    if df.empty:
        sys.exit(f"No data returned for {args.symbol}")

    import os
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} bars ({df['time'].iloc[0]} .. {df['time'].iloc[-1]}) to {args.out}")


if __name__ == "__main__":
    main()
