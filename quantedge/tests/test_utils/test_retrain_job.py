# tests/test_utils/test_retrain_job.py
import os

import numpy as np
import pandas as pd
import pytest

from pipeline import inference_pipeline as ip
from utils.retrain_job import (
    _drift_psi,
    _verdict,
    format_retrain_report,
    retrain_pair,
)


def make_daily(n=900, seed=7):
    rng = np.random.default_rng(seed)
    close = 1.0 * np.exp(np.cumsum(rng.normal(0, 0.005, n)))
    open_ = np.roll(close, 1)
    open_[0] = 1.0
    highs = np.maximum(open_, close) * 1.001
    lows = np.minimum(open_, close) * 0.999
    return pd.DataFrame(
        {
            "time": pd.date_range("2022-01-01", periods=n, freq="D"),
            "open": open_,
            "high": highs,
            "low": lows,
            "close": close,
            "tick_volume": rng.integers(1000, 5000, n),
        }
    )


@pytest.fixture
def restore_inference():
    env = dict(os.environ)
    yield
    if "QUANTEDGE_MODEL_DIR" in os.environ:
        del os.environ["QUANTEDGE_MODEL_DIR"]
    for k, v in env.items():
        os.environ[k] = v
    ip.InferencePipeline._instance = None
    ip.InferencePipeline._models_loaded = False


def test_drift_psi_detects_and_skips():
    rng = np.random.default_rng(1)
    train = pd.DataFrame(
        {
            "feat_a": rng.normal(0, 1, 200),
            "feat_b": rng.normal(0, 1, 200),
            "time": pd.date_range("2022-01-01", periods=200, freq="D"),
            "target": [0] * 200,
        }
    )
    oos = pd.DataFrame(
        {
            "feat_a": rng.normal(3, 1, 150),
            "feat_b": rng.normal(0, 1, 150),
            "time": pd.date_range("2023-01-01", periods=150, freq="D"),
            "target": [1] * 150,
        }
    )
    res = _drift_psi(train, oos)
    assert res["features_checked"] == 2
    assert res["worst_feature"] == "feat_a"
    assert res["max_psi"] > 1.0


def test_verdict_thresholds():
    assert _verdict(0.96) == "validated - championship review"
    assert _verdict(0.7) == "noise-adjacent - review manually"
    assert _verdict(0.2) == "below chance - do not deploy"


def test_retrain_pair_end_to_end(tmp_path, restore_inference, monkeypatch):
    df = make_daily()
    monkeypatch.setattr(
        "utils.retrain_job.fetch_yahoo_ohlcv",
        lambda symbol, interval, range_: df.copy(),
    )
    artifact_root = tmp_path / "artifacts"

    res = retrain_pair("TEST", "TEST=X", artifact_root=str(artifact_root),
                       optimize=False, oos_days=180)

    assert res["symbol"] == "TEST"
    assert res["last_data_date"] == str(df["time"].iloc[-1].date())
    assert res["oos"]["bars"] > 0
    artifact_dir = artifact_root / "TEST"
    for name in ("scaler.pkl", "rf_model.pkl", "xgb_model.pkl",
                 "lr_model.pkl", "model_metadata.json"):
        assert (artifact_dir / name).exists(), f"missing {name}"

    report = format_retrain_report([res], "2026-01-01T00:00:00+00:00")
    assert "# Model retrain report" in report
    assert "TEST" in report
    assert "championship" in report
