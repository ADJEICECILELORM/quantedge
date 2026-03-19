# tests/fixtures/mock_mt5.py - Mock MT5 Connector for Testing
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import MetaTrader5 as mt5


class MockMT5Connector:
    """Mock MT5 connector for testing without live connection"""

    def __init__(self):
        self.connected = True
        self.symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'BTCUSD', 'ETHUSD']

    def connect(self):
        """Mock connection"""
        self.connected = True
        return True

    def disconnect(self):
        """Mock disconnection"""
        self.connected = False

    def get_latest_bars(self, symbol: str, timeframe, count: int = 100):
        """Generate mock OHLCV data"""
        if not self.connected or symbol not in self.symbols:
            return None

        # Generate realistic price data
        np.random.seed(hash(symbol) % 2**32)  # Consistent data per symbol

        base_prices = {
            'EURUSD': 1.1000,
            'GBPUSD': 1.3000,
            'USDJPY': 110.00,
            'XAUUSD': 1800.00,
            'BTCUSD': 40000.00,
            'ETHUSD': 2500.00
        }

        base_price = base_prices.get(symbol, 1.0)
        returns = np.random.randn(count) * 0.0005
        prices = base_price * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            'time': pd.date_range(end=datetime.now(), periods=count, freq='5min'),
            'open': prices + np.random.randn(count) * base_price * 0.00005,
            'high': prices + np.abs(np.random.randn(count)) * base_price * 0.0001,
            'low': prices - np.abs(np.random.randn(count)) * base_price * 0.0001,
            'close': prices,
            'tick_volume': np.random.randint(100, 1000, count)
        })

        # Ensure high/low are correct
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)

        return df

    def enable_multiple_symbols(self, symbols: list):
        """Mock symbol enabling"""
        result = {}
        for symbol in symbols:
            if symbol in self.symbols:
                result[symbol] = symbol
            else:
                result[symbol] = None
        return result
