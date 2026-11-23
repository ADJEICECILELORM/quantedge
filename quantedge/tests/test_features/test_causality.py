# tests/test_features/test_causality.py
"""
Pipeline-cleanliness guarantee: FeatureEngineer must be causal.

A causal feature at bar i depends only on bars <= i. Test: computing
features on a truncated history must produce values identical to the
corresponding rows computed on the full history (beyond shared warmup
NaNs). If any future information sneaks into an indicator (a centered
window, a full-sample normalize, a ffill of future data), the truncated
run's values would differ and this test fails.
"""
import numpy as np
import pandas as pd
import pytest

from features.feature_engineer import FeatureEngineer


NON_FEATURE_COLUMNS = {"time", "open", "high", "low", "close", "tick_volume"}


def make_data(n=700, seed=5):
    rng = np.random.default_rng(seed)
    close = 1.1 * np.exp(np.cumsum(rng.normal(0, 0.0008, n)))
    op = np.roll(close, 1)
    op[0] = 1.1
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "open": op,
            "high": np.maximum(op, close) * (1 + 0.0004),
            "low": np.minimum(op, close) * (1 - 0.0004),
            "close": close,
            "tick_volume": rng.integers(100, 1000, n),
        }
    )


class TestFeatureCausality:
    def test_truncated_history_reproduces_full_history_features(self):
        df = make_data()
        split = 500

        full = FeatureEngineer().create_features(df)
        trunc = FeatureEngineer().create_features(df.iloc[:split].copy())

        overlap = set(full["time"]).intersection(set(trunc["time"]))
        assert len(overlap) > 100

        merged = full.merge(trunc, on="time", suffixes=("_full", "_trunc"))
        feature_cols = [
            c for c in full.columns
            if c not in NON_FEATURE_COLUMNS and pd.api.types.is_numeric_dtype(full[c])
        ]

        for col in feature_cols:
            both = merged[[f"{col}_full", f"{col}_trunc"]].dropna()
            both = both.replace([np.inf, -np.inf], np.nan).dropna()
            if len(both) == 0:
                continue
            assert np.allclose(
                both[f"{col}_full"].values,
                both[f"{col}_trunc"].values,
                rtol=1e-9,
                atol=1e-12,
            ), f"Feature '{col}' depends on future data (leakage)"

    def test_last_row_features_equal_when_data_extends(self):
        df = make_data()
        fe = FeatureEngineer()

        trunc = fe.create_features(df.iloc[:400].copy())
        row_from_short = trunc.iloc[[-1]]
        common_time = row_from_short["time"].iloc[0]

        full_table = fe.create_features(df)
        row_from_long = full_table[full_table["time"] == common_time]

        assert len(row_from_long) == 1
        row_from_long = row_from_long.iloc[[-1]]
        for col in set(row_from_long.columns) - NON_FEATURE_COLUMNS:
            if not pd.api.types.is_numeric_dtype(row_from_long[col]):
                continue
            a, b = row_from_long[col].iloc[0], row_from_short[col].iloc[0]
            if pd.isna(a) and pd.isna(b):
                continue
            if not (np.isfinite(a) and np.isfinite(b)):
                continue
            assert a == pytest.approx(b, rel=1e-9, abs=1e-12), (
                f"Feature '{col}' changed when future rows appended - leakage"
            )
