import json
import os

import numpy as np
import pandas as pd
import pytest

from models.registry import load_metadata, save_metadata
from utils.drift_monitor import FeatureDriftMonitor, compute_psi, summarize_feature_distribution


def make_frame(mean=0.0, seed=1, n=300, col="feat_a"):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({col: rng.normal(mean, 1.0, n)})


class TestPSI:
    def test_identical_distributions_near_zero(self):
        e = make_frame(seed=1)["feat_a"].to_numpy()
        a = make_frame(seed=1, n=150)["feat_a"].to_numpy()
        assert compute_psi(e, a) < 0.05

    def test_shifted_distribution_flags(self):
        e = make_frame(mean=0.0, seed=1)["feat_a"].to_numpy()
        a = make_frame(mean=1.5, seed=2)["feat_a"].to_numpy()
        assert compute_psi(e, a) > 0.25

    def test_empty_inputs_nan(self):
        assert np.isnan(compute_psi([], []))

    def test_explicit_bin_edges(self):
        e = make_frame(seed=1)["feat_a"].to_numpy()
        a = make_frame(mean=3.0, seed=2)["feat_a"].to_numpy()
        edges = np.quantile(e, np.linspace(0, 1, 11))
        edge_psi = compute_psi(e, a, bin_edges=edges)
        assert edge_psi > 0.25


class TestFeatureDriftMonitor:
    def _make_model_dir(self, tmp_path, ref):
        model_dir = str(tmp_path / "models" / "saved")
        os.makedirs(model_dir, exist_ok=True)
        save_metadata(model_dir, feature_cols=list(ref.keys()), feature_stats=ref)
        return model_dir

    def test_disabled_without_stats(self, tmp_path):
        model_dir = str(tmp_path / "empty")
        os.makedirs(model_dir, exist_ok=True)
        save_metadata(model_dir, feature_cols=["x"])
        monitor = FeatureDriftMonitor(model_dir)
        assert monitor.enabled is False
        assert monitor.check()["status"] == "not_enabled"

    def test_stable_window_is_ok(self, tmp_path):
        ref_df = make_frame(seed=1, n=1000)
        ref = summarize_feature_distribution(ref_df, ["feat_a"])
        monitor = FeatureDriftMonitor(self._make_model_dir(tmp_path, ref), min_samples=20)
        for _ in range(3):
            monitor.push(make_frame(seed=5, n=10))
        assert monitor.check()["status"] == "ok"

    def test_shifted_window_violates(self, tmp_path):
        ref_df = make_frame(seed=1, n=1000)
        ref = summarize_feature_distribution(ref_df, ["feat_a"])
        monitor = FeatureDriftMonitor(self._make_model_dir(tmp_path, ref), min_samples=20)
        for _ in range(3):
            monitor.push(make_frame(mean=2.0, seed=9, n=10))
        result = monitor.check()
        assert result["status"] == "violation"
        assert result["psi"][0][0] == "feat_a"

    def test_insufficient_samples(self, tmp_path):
        ref = summarize_feature_distribution(make_frame(seed=1, n=100), ["feat_a"])
        monitor = FeatureDriftMonitor(self._make_model_dir(tmp_path, ref), min_samples=20)
        monitor.push(make_frame(seed=5, n=5))
        assert monitor.check()["status"] == "insufficient_samples"

    def test_metadata_roundtrip_with_stats(self, tmp_path):
        ref = summarize_feature_distribution(make_frame(seed=1, n=100), ["feat_a"])
        model_dir = self._make_model_dir(tmp_path, ref)
        loaded = load_metadata(model_dir)
        assert "feat_a" in loaded["feature_stats"]
        assert len(loaded["feature_stats"]["feat_a"]["bin_edges"]) >= 2
