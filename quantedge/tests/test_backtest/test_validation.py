import numpy as np
import pandas as pd
import pytest

from backtest.validation import (
    bootstrap_trade_outcomes,
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    robustness_report,
)


def make_returns(n=2000, mean=0.0005, std=0.001, seed=11):
    rng = np.random.default_rng(seed)
    return rng.normal(mean, std, n)


def make_trades(pnls):
    return pd.DataFrame({"pnl_usd": pnls})


class TestProbabilisticSharpeRatio:
    def test_strong_edge_is_confident(self):
        r = make_returns(mean=0.0008, std=0.001, n=2000)
        psr = probabilistic_sharpe_ratio(r, 0.0)
        assert psr > 0.99

    def test_zero_mean_returns_is_coin_flip(self):
        r = make_returns(mean=0.0, std=0.001, n=2000)
        psr = probabilistic_sharpe_ratio(r, 0.0)
        assert 0.3 < psr < 0.7

    def test_bounded_unit_interval(self):
        r = make_returns()
        assert 0.0 <= probabilistic_sharpe_ratio(r, 0.0) <= 1.0

    def test_short_series_is_nan(self):
        assert np.isnan(probabilistic_sharpe_ratio([0.1, 0.2]))


class TestDeflatedSharpeRatio:
    def test_multiple_trials_lower_confidence_than_psr(self):
        r = make_returns(mean=0.00002, std=0.001, n=2000)
        psr = probabilistic_sharpe_ratio(r, 0.0)
        dsr = deflated_sharpe_ratio(r, sr_trials=[0.5, 0.2, 0.6, 0.1, 0.4])
        assert dsr < psr

    def test_accepts_trials_std_directly(self):
        r = make_returns(mean=0.00002, std=0.001, n=2000)
        dsr = deflated_sharpe_ratio(r, n_trials=50, sr_std=0.2)
        assert 0.0 <= dsr <= 1.0

    def test_multiple_trials_lower_benchmark_than_single(self):
        assert expected_max_sharpe(50, 0.2) > 0.0

    def test_single_trial_falls_back_to_zero_benchmark(self):
        r = make_returns()
        assert deflated_sharpe_ratio(r, n_trials=1) == probabilistic_sharpe_ratio(r, 0.0)

    def test_requires_trial_information(self):
        with pytest.raises(ValueError):
            deflated_sharpe_ratio(make_returns())


class TestBootstrapTradeOutcomes:
    def test_negative_expectancy_busts_most_paths(self):
        pnls = [-100.0] * 70 + [150.0] * 30
        report = bootstrap_trade_outcomes(
            make_trades(pnls), 10000, n_paths=2000, ruin_drawdown_pct=20.0, seed=3
        )
        assert report["prob_profit"] < 0.5
        assert report["prob_ruin"] > 0.1

    def test_positive_expectancy_mostly_survives(self):
        pnls = [200.0] * 55 + [-100.0] * 45
        report = bootstrap_trade_outcomes(make_trades(pnls), 10000, n_paths=2000, seed=3)
        assert report["prob_profit"] > 0.8

    def test_drawdown_percentiles_are_ordered(self):
        pnls = [-50.0, 80.0, -120.0, 200.0, -30.0, 60.0]
        report = bootstrap_trade_outcomes(make_trades(pnls), 10000, n_paths=1000, seed=5)
        assert 0 <= report["max_dd_p50"] <= report["max_dd_p90"] <= report["max_dd_p95"] <= report["max_dd_p99"]

    def test_seed_reproducibility(self):
        pnls = [-50.0, 80.0, -120.0, 200.0, -30.0, 60.0]
        a = bootstrap_trade_outcomes(make_trades(pnls), 10000, n_paths=500, seed=1)
        b = bootstrap_trade_outcomes(make_trades(pnls), 10000, n_paths=500, seed=1)
        assert a["end_equity_p50"] == b["end_equity_p50"]

    def test_empty_trades_returns_empty(self):
        assert bootstrap_trade_outcomes(make_trades([]), 10000) == {}


class TestRobustnessReport:
    def test_report_includes_mc_and_psr(self):
        pnls = [-50.0, 80.0, -120.0, 200.0, -30.0, 60.0] * 10
        equity = pd.Series(np.cumsum([0] + list(np.pad(pnls, (0, 1)))[:600]) + 10000.0)
        returns = equity.pct_change().dropna()
        report = robustness_report(make_trades(pnls), 10000, returns=returns, n_paths=500, seed=1)
        assert "prob_ruin" in report and "psr" in report
