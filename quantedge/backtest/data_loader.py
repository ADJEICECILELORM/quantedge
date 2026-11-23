# backtest/data_loader.py
import os
import pandas as pd


REQUIRED_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume"]


def _validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Data is missing required columns: {missing}")
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").drop_duplicates(subset="time").reset_index(drop=True)
    return df


def load_csv_history(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV data not found: {path}")
    df = pd.read_csv(path)
    return _validate_ohlcv(df)


def load_mt5_history(connector, symbol: str, timeframe, start, end, bars: int = 20000) -> pd.DataFrame:
    """
    Fetch historical candles through the live connector.

    Args:
        connector: utils.mt5_connector.MT5Connector (must be connected).
        symbol: Resolved MT5 symbol name.
        timeframe: MT5 timeframe constant.
        start: datetime (broker time) of the first bar wanted.
        end: datetime of the last bar wanted.
        bars: Max bars to request if the range is empty.

    Returns:
        DataFrame with time/open/high/low/close/tick_volume/spread.
    """
    import MetaTrader5 as mt5

    rates = mt5.copy_rates_range(symbol, timeframe, start, end)
    if rates is None or len(rates) == 0:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No historical data returned for {symbol} ({mt5.last_error()})")

    df = pd.DataFrame(rates)
    if "spread" not in df.columns:
        df["spread"] = 0
    return _validate_ohlcv(df)
