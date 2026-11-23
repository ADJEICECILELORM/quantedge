import numpy as np
import pandas as pd
import pytest

from backtest.portfolio_backtest import PortfolioBacktest, format_portfolio_report
from utils.config import load_config


class BuyEveryBar:
    def predict(self, row_df):
        return {"direction": 1, "confidence": 0.9, "model_votes": {}}


def make_data(n=400, seed=7):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0.0002, 0.001, n)
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


@pytest.fixture
def config():
    cfg = load_config()
    cfg["backtest"]["warmup_bars"] = 60
    cfg["backtest"]["mc_paths"] = 500
    return cfg


class TestPortfolioBacktest:
    def test_two_symbols_produce_combined_view(self, config):
        dfs = {"AAAUSD": make_data(seed=7), "BBBUSD": make_data(seed=11)}
        result = PortfolioBacktest(dfs, config=config, inference_map={s: BuyEveryBar() for s in dfs}).run()
        assert set(result.per_symbol.keys()) == {"AAAUSD", "BBBUSD"}
        assert len(result.combined_equity) > 100
        assert len(result.combined_trades) > 0
        assert result.metrics["n_trades"] == len(result.combined_trades)
        assert result.robustness.get("prob_ruin") is not None

    def test_identical_sources_flag_correlation_gate(self, config):
        shared = make_data(seed=3)
        dfs = {"AAAUSD": shared, "BBBUSD": shared.copy()}
        result = PortfolioBacktest(dfs, config=config, inference_map={s: BuyEveryBar() for s in dfs}).run()
        assert result.correlation_violations, "identical price series must violate the correlation gate"
        a, b, c = result.correlation_violations[0]
        assert abs(c) > 0.7

    def test_unrelated_sources_pass_correlation_gate(self, config):
        dfs = {"AAAUSD": make_data(seed=7), "BBBUSD": make_data(seed=42)}
        result = PortfolioBacktest(dfs, config=config, inference_map={s: BuyEveryBar() for s in dfs}).run()
        for a, b, c in result.correlation_violations:
            assert abs(c) <= 0.7

    def test_exposure_violations_surfaced_when_cap_low(self, config):
        dfs = {"AAAUSD": make_data(seed=7), "BBBUSD": make_data(seed=11)}
        config["risk"]["max_gross_exposure_usd"] = 100.0
        result = PortfolioBacktest(dfs, config=config, inference_map={s: BuyEveryBar() for s in dfs}).run()
        assert result.exposure_violations, "tiny cap must be reported as breached"

    def test_requires_data(self):
        with pytest.raises(ValueError):
            PortfolioBacktest({})

    def test_format_report_renders(self, config):
        dfs = {"AAAUSD": make_data(seed=7)}
        result = PortfolioBacktest(dfs, config=config, inference_map={s: BuyEveryBar() for s in dfs}).run()
        text = format_portfolio_report(result)
        assert "PORTFOLIO BACKTEST REPORT" in text
        assert "PORTFOLIO" in text
