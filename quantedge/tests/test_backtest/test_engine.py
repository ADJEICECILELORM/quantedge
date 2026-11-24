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


class TestMarkToMarket:
    def test_unrealized_pnl_marks_open_position(self, config):
        from backtest.engine import Trade

        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=BuyEveryBar())
        trade = Trade(
            entry_bar=5, exit_bar=None, entry_price=100.0, exit_price=None,
            direction=1, stop_loss=99.0, take_profit=101.0, units=10.0,
        )
        bar = pd.Series({"close": 101.0})

        assert engine._unrealized_pnl(trade, 5, bar) == pytest.approx(10.0)
        assert engine._unrealized_pnl(trade, 4, bar) == 0.0
        assert engine._unrealized_pnl(None, 5, bar) == 0.0
        assert engine._unrealized_pnl(trade, 5, pd.Series({"close": 99.5})) == pytest.approx(-5.0)

    def test_equity_curve_reflects_open_position(self, config):
        data = make_data(n=400, seed=23)
        engine = BacktestEngine(data, symbol="TEST", config=config, inference=BuyEveryBar())
        result = engine.run()

        trades = result.trades
        if len(trades) == 0:
            pytest.skip("no trades generated")
        long_trade = trades[trades["exit_bar"] - trades["entry_bar"] > 1]
        if len(long_trade) == 0:
            pytest.skip("no multi-bar trades generated")

        curve = result.equity_curve.reset_index(drop=True)
        trade = long_trade.iloc[0]
        mid_bars = list(range(int(trade["entry_bar"]) + 1, int(trade["exit_bar"])))
        if not mid_bars:
            pytest.skip("no bars between entry and exit")
        values = curve.iloc[mid_bars].values
        assert not np.allclose(values, values[0]), (
            "equity curve is flat while a position is open - mark-to-market missing"
        )


class SellEveryBar:
    """Stub inference that always signals short with high confidence."""

    def predict(self, row_df):
        return {"direction": -1, "confidence": 0.9, "model_votes": {}}


class TestShortLeg:
    def test_short_entries_recorded_with_direction_minus_one(self, config):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=SellEveryBar())
        result = engine.run()
        assert result.metrics["n_trades"] > 0
        assert (result.trades["direction"] == -1).all()

    def test_short_pnl_sign_is_direction_aware(self, config):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=SellEveryBar())
        result = engine.run()
        # pnl = units * (exit - entry) * direction; a short that exits below its
        # entry must be positive
        shorts = result.trades[
            (result.trades["exit_price"].notna()) & (result.trades["status"].isin(["sl", "tp"]))
        ]
        assert len(shorts) > 0
        tp_trades = shorts[shorts["status"] == "tp"]
        if len(tp_trades) > 0:
            assert (tp_trades["pnl_usd"] > 0).all()

    def test_short_stop_loss_is_above_entry(self, config):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config, inference=SellEveryBar())
        result = engine.run()
        shorts = result.trades[result.trades["direction"] == -1]
        assert len(shorts) > 0
        assert (shorts["stop_loss"] > shorts["entry_price"]).all()
        assert (shorts["take_profit"] < shorts["entry_price"]).all()

    def test_short_entry_fills_at_bid(self, config):
        from features.feature_engineer import FeatureEngineer

        df = make_data()
        features = FeatureEngineer().create_features(df).reset_index(drop=True)
        raw_open = features["open"].to_numpy()
        engine = BacktestEngine(df, symbol="TEST", config=config, inference=SellEveryBar())
        result = engine.run()
        shorts = result.trades[result.trades["direction"] == -1]
        assert len(shorts) > 0
        entry_bars = shorts["entry_bar"].astype(int).to_numpy()
        assert (shorts["entry_price"].to_numpy() <= raw_open[entry_bars]).all()
