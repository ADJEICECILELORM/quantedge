# tests/test_backtest/test_engine_inference.py
import numpy as np
import pandas as pd
import pytest

import pipeline.inference_pipeline as ip
from backtest.engine import BacktestEngine
from utils.config import load_config


def make_data(n=400, seed=7):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.001, n)))
    open_ = np.roll(close, 1)
    open_[0] = 100.0
    return pd.DataFrame(
        {
            "time": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "open": open_,
            "high": np.maximum(open_, close) * (1 + rng.uniform(0, 0.0008, n)),
            "low": np.minimum(open_, close) * (1 - rng.uniform(0, 0.0008, n)),
            "close": close,
            "tick_volume": rng.integers(100, 1000, n),
        }
    )


@pytest.fixture
def config():
    cfg = load_config()
    cfg["backtest"]["warmup_bars"] = 60
    return cfg


@pytest.fixture
def no_models(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ip.InferencePipeline, "_models_loaded", False, raising=False)


class TestInferenceLoading:
    def test_falls_back_to_stub_when_model_files_missing(self, config, no_models):
        engine = BacktestEngine(make_data(), symbol="TEST", config=config)
        assert engine._get_inference() is None

    def test_missing_models_backtest_runs_without_trades(self, config, no_models):
        engine = BacktestEngine(make_data(400), symbol="TEST", config=config)
        result = engine.run()
        assert len(result.trades) == 0

    def test_get_inference_tries_to_load_models(self, config):
        import os

        if not os.path.exists("models/saved/rf_model.pkl"):
            pytest.skip("no local trained models")
        engine = BacktestEngine(make_data(), symbol="TEST", config=config)
        inference = engine._get_inference()
        assert inference is not None
        assert hasattr(inference, "predict")


class AlwaysLongStrongADX:
    def predict(self, row_df):
        return {'direction': 1, 'confidence': 0.9, 'model_votes': {}}


class TestAdxGate:
    def test_min_adx_gates_entries(self, config):
        cfg = load_config()
        cfg["backtest"]["warmup_bars"] = 60
        data = make_data(400, seed=11)
        from features.feature_engineer import FeatureEngineer
        feats = FeatureEngineer().create_features(data)
        assert feats["adx"].notna().any()

        cfg["backtest"]["min_adx"] = 0.0
        base = BacktestEngine(data, symbol="T", config=cfg, inference=AlwaysLongStrongADX()).run()

        cfg["backtest"]["min_adx"] = 1e9
        gated = BacktestEngine(data, symbol="T", config=cfg, inference=AlwaysLongStrongADX()).run()
        assert len(base.trades) > 0
        assert len(gated.trades) == 0
