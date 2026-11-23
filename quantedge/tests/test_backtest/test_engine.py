# tests/test_backtest/test_engine.py
import numpy as np
import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from utils.config import load_config


def make_data(n=400, seed=7, trend=0.0):
    rng = np.random.default_rng(seed)
    returns = rng.normal(trend, 0.001, n)
    close = 100 * np.exp(np.cumsum(returns))
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    high = np.maximum(open_, close) * (1 + rng.uniform(0, 0.0008, n))
    low = np.minimum(open_, close) * (1 - rng.uniform(0, 0.0008, n))
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": rng.integers(100, 1000, n),
        }
    )


class BuyEveryBar:
    """Stub inference that always signals long with medium confidence."""

    def predict(self, row_df):
        return {"direction": 1, "confidence": 0.9, "model_votes": {}}


class NoTrades:
    def predict(self, row_df):
        return {"direction": 0, "confidence": 0.5, "model_votes": {}}


@pytest.fixture
def config():
    cfg = load_config()
    cfg["backtest"]["warmup_bars"] = 60
    return cfg


class TestBacktestEngine:
    def test_runs_and_produces_metrics(self, config):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=BuyEveryBar())
        result = engine.run()

        assert result.metrics, "metrics should not be empty"
        assert result.metrics["end_equity"] > 0
        assert result.metrics["n_trades"] > 0
        assert len(result.equity_curve) > engine.warmup_bars

    def test_no_trades_without_signals(self, config):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=NoTrades())
        result = engine.run()

        assert result.metrics["n_trades"] == 0
        assert result.metrics["end_equity"] == pytest.approx(result.metrics["start_equity"])

    def test_entries_use_next_bar_open(self, config):
        data = make_data(seed=11)
        engine = BacktestEngine(data, symbol="TEST", config=config, inference=BuyEveryBar())
        result = engine.run()

        if len(result.trades) > 0:
            first_entry = result.trades.iloc[0]["entry_bar"]
            warmup = config["backtest"]["warmup_bars"]
            assert first_entry >= warmup + 1

    def test_confidence_filter_blocks_low_confidence(self, config):
        class LowConfidence:
            def predict(self, row_df):
                return {"direction": 1, "confidence": 0.2, "model_votes": {}}

        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=LowConfidence())
        result = engine.run()
        assert result.metrics["n_trades"] == 0

    def test_insufficient_data_raises(self, config):
        engine = BacktestEngine(make_data(50), symbol="TEST", config=config, inference=BuyEveryBar())
        with pytest.raises(ValueError):
            engine.run()

    def test_equity_curve_is_not_nan_after_warmup(self, config):
        engine = BacktestEngine(make_data(seed=3), symbol="TEST", config=config, inference=BuyEveryBar())
        result = engine.run()
        curve = result.equity_curve
        assert not curve.iloc[: config["backtest"]["warmup_bars"]].isna().any()
        assert not curve.isna().any()
