# tests/test_features/test_leakage_detector.py
"""
Leakage detector: on a random walk there is no learnable signal, so a
causal pipeline must fail to predict the target (accuracy ~ chance). If
even an intentionally-leaked feature blows accuracy up while the causal
feature set stays flat, the detector catches leaks introduced by future
pipeline changes.

We train the real ModelTrainer both ways:
  - clean:   features are strictly lagged/rolling (no future info)
  - leaky:   one feature peeks one bar into the future

The test asserts leaky accuracy is far above chance AND far above clean.
A pipeline refactor that accidentally leaks will push the *clean* run's
accuracy up and fail this test.
"""
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from models.model_trainer import ModelTrainer


def make_synthetic_data(n=900, seed=42):
    rng = np.random.default_rng(seed)
    returns = rng.normal(0, 0.002, n)
    close = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "time": pd.date_range("2023-01-01", periods=n, freq="5min"),
            "open": np.roll(close, 1),
            "high": close * (1 + 0.0005),
            "low": close * (1 - 0.0005),
            "close": close,
            "tick_volume": rng.integers(100, 1000, n),
        }
    )
    df.loc[0, "open"] = 100.0
    return df


def prepare(df, leak=False):
    df = df.copy()
    df["return_lag_1"] = df["close"].pct_change(1).shift(1)
    df["return_lag_2"] = df["close"].pct_change(1).shift(2)
    df["ma_5_lag"] = df["close"].rolling(5).mean().shift(1)
    df["vol_10_lag"] = df["close"].pct_change(1).rolling(10).std().shift(1)
    if leak:
        df["future_gap"] = df["close"].shift(-1) - df["close"]
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.dropna().reset_index(drop=True)
    return df


def train_and_score(df):
    trainer = ModelTrainer(df)
    X_train, X_test, y_train, y_test, feature_cols = trainer.prepare_data()
    rf = RandomForestClassifier(n_estimators=50, max_depth=6, random_state=42)
    rf.fit(X_train, y_train)
    return float(accuracy_score(y_test, rf.predict(X_test)))


class TestLeakageDetector:
    def test_causal_features_cannot_predict_random_walk(self):
        accuracy = train_and_score(prepare(make_synthetic_data(), leak=False))
        assert accuracy < 0.70, (
            f"Clean causal features scored {accuracy:.3f} on a random walk. "
            "Something in the pipeline is leaking future information."
        )

    def test_leaky_feature_is_detected(self):
        clean = train_and_score(prepare(make_synthetic_data(), leak=False))
        leaky = train_and_score(prepare(make_synthetic_data(), leak=True))
        assert leaky > 0.85, "Detector data is broken: leaky feature should be near-perfect"
        assert leaky > clean + 0.15, (
            "Leaked feature did not stand out from causal features - fix detector data"
        )
