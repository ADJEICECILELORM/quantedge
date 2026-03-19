# tests/conftest.py - pytest configuration and fixtures
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing"""
    np.random.seed(42)
    n_bars = 200

    # Generate realistic price data
    base_price = 1.1000
    returns = np.random.randn(n_bars) * 0.0005  # 5 pip std deviation
    prices = base_price * np.exp(np.cumsum(returns))

    df = pd.DataFrame({
        'time': pd.date_range(end=datetime.now(), periods=n_bars, freq='5min'),
        'open': prices + np.random.randn(n_bars) * 0.00005,
        'high': prices + np.abs(np.random.randn(n_bars)) * 0.0001,
        'low': prices - np.abs(np.random.randn(n_bars)) * 0.0001,
        'close': prices,
        'tick_volume': np.random.randint(100, 1000, n_bars)
    })

    # Ensure high/low are correct
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    return df


@pytest.fixture
def sample_features_data(sample_ohlcv_data):
    """Generate sample features DataFrame"""
    from features.feature_engineer import FeatureEngineer

    fe = FeatureEngineer()
    return fe.create_features(sample_ohlcv_data)


@pytest.fixture
def mock_mt5_connector():
    """Mock MT5 connector for testing"""
    from tests.fixtures.mock_mt5 import MockMT5Connector
    return MockMT5Connector()


@pytest.fixture
def sample_trade_history():
    """Sample trade history for Kelly Criterion testing"""
    return [
        {'pnl': 100, 'outcome': 'win'},
        {'pnl': -50, 'outcome': 'loss'},
        {'pnl': 150, 'outcome': 'win'},
        {'pnl': -50, 'outcome': 'loss'},
        {'pnl': 200, 'outcome': 'win'},
        {'pnl': -75, 'outcome': 'loss'},
        {'pnl': 100, 'outcome': 'win'},
        {'pnl': -50, 'outcome': 'loss'},
        {'pnl': 125, 'outcome': 'win'},
        {'pnl': -60, 'outcome': 'loss'},
    ]


@pytest.fixture
def sample_correlation_data():
    """Sample correlation matrix"""
    symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD']
    n = len(symbols)

    # Create realistic correlations
    corr_matrix = np.eye(n)
    corr_matrix[0, 1] = corr_matrix[1, 0] = 0.75  # EUR/GBP high correlation
    corr_matrix[0, 2] = corr_matrix[2, 0] = -0.30  # EUR/JPY negative
    corr_matrix[1, 2] = corr_matrix[2, 1] = -0.25  # GBP/JPY negative

    return pd.DataFrame(corr_matrix, index=symbols, columns=symbols)
