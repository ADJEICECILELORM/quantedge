# utils/drift_monitor.py
"""
Feature drift monitoring: compares live inference feature distributions
against the training-time reference stored in model metadata.json.

Raw PSI on small windows is noisy (E[PSI] ~ chi2/(bins-1) / n under the
null), so check() reports an adjusted PSI with the chi-square 95% noise
floor subtracted. Conventional interpretation applies to the adjusted
value:

PSI < 0.10    -> no significant change
PSI 0.10-0.25 -> warning: model inputs have shifted, validate
PSI > 0.25    -> violation: the model is trading a regime it never saw
"""
import math
from collections import deque
from statistics import NormalDist

import numpy as np
import pandas as pd

from models.registry import load_metadata


def compute_psi(expected, actual, n_bins: int = 10, bin_edges=None, alpha: float = 0.5) -> float:
    """
    Population Stability Index between two samples, with Jeffreys
    smoothing (alpha pseudo-counts per bin) so empty bins do not explode
    the score on small windows. If bin_edges is given (e.g. training
    deciles from metadata), actual is binned against the reference
    edges; otherwise both are binned on expected's quantiles.
    """
    a = np.asarray(actual, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return float("nan")

    if bin_edges is None:
        e = np.asarray(expected, dtype=float)
        e = e[np.isfinite(e)]
        if len(e) == 0:
            return float("nan")
        bin_edges = np.quantile(e, np.linspace(0, 1, n_bins + 1))
        bin_edges = np.unique(bin_edges)

    edges = np.concatenate(([-np.inf], bin_edges[1:-1], [np.inf]))
    k = len(edges) - 1
    if len(expected) > 0:
        e_counts = np.histogram(expected, bins=edges)[0]
    else:
        e_counts = np.full(k, len(a) / k)
    a_counts = np.histogram(a, bins=edges)[0]

    e_props = (e_counts + alpha) / (e_counts.sum() + alpha * k)
    a_props = (a_counts + alpha) / (a_counts.sum() + alpha * k)
    return float(np.sum((a_props - e_props) * np.log(a_props / e_props)))


def _chi2_crit(df: int, prob: float = 0.95) -> float:
    """95th percentile of chi-square(df) via the Wilson-Hilferty transform."""
    z = NormalDist().inv_cdf(prob)
    return df * (1 - 2 / (9 * df) + z * math.sqrt(2 / (9 * df))) ** 3


def summarize_feature_distribution(df: pd.DataFrame, feature_cols, n_bins: int = 10) -> dict:
    """
    Per-feature training-time statistics (mean/std/quantile bin edges)
    stored in model metadata so drift can be measured without the full
    training dataset.
    """
    stats = {}
    for col in feature_cols:
        if col not in df.columns:
            continue
        s = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
        if len(s) == 0:
            continue
        edges = np.unique(np.quantile(s.values, np.linspace(0, 1, n_bins + 1)))
        if len(edges) < 2:
            edges = np.array([edges[0] - 1e-12, edges[0] + 1e-12])
        stats[col] = {
            "mean": float(s.mean()),
            "std": float(s.std()) if len(s) > 1 else 0.0,
            "bin_edges": [float(x) for x in edges],
        }
    return stats


class FeatureDriftMonitor:
    """
    Rolling-window drift check at inference time. Push every feature row
    you predict on; every check() compares the accumulated window against
    training reference distributions.
    """

    def __init__(
        self,
        model_dir: str,
        psi_warn: float = 0.10,
        psi_fail: float = 0.25,
        window: int = 200,
        min_samples: int = 20,
        n_bins: int = 10,
    ):
        metadata = load_metadata(model_dir) or {}
        self.reference = metadata.get("feature_stats") or {}
        self.reference_cols = sorted(self.reference.keys())
        self.enabled = bool(self.reference)
        self.psi_warn = psi_warn
        self.psi_fail = psi_fail
        self.min_samples = min_samples
        self.n_bins = n_bins
        self.window = deque(maxlen=window)

    def push(self, features_df: pd.DataFrame) -> None:
        if not self.enabled or features_df is None or len(features_df) == 0:
            return
        grid = features_df.reindex(columns=self.reference_cols)
        numeric = grid.apply(pd.to_numeric, errors="coerce")
        self.window.extend(numeric.to_numpy(dtype=float))

    def check(self) -> dict:
        if not self.enabled:
            return {"status": "not_enabled", "n_samples": len(self.window)}
        if len(self.window) < self.min_samples:
            return {"status": "insufficient_samples", "n_samples": len(self.window)}

        matrix = np.array(self.window, dtype=float)
        n = matrix.shape[0]

        per_feature = {}
        for idx, col in enumerate(self.reference_cols):
            ref = self.reference[col]
            edges = np.asarray(ref.get("bin_edges", []), dtype=float)
            if len(edges) < 2 or idx >= matrix.shape[1]:
                continue
            actual = matrix[:, idx][np.isfinite(matrix[:, idx])]
            if len(actual) == 0:
                continue
            raw_psi = compute_psi(
                np.asarray(ref.get("values", [])),
                actual,
                n_bins=self.n_bins,
                bin_edges=edges,
            )
            if raw_psi != raw_psi:
                continue
            noise_floor = _chi2_crit(len(edges) - 1) / n
            per_feature[col] = (raw_psi, max(0.0, raw_psi - noise_floor))

        if not per_feature:
            return {"status": "insufficient_samples", "n_samples": n}

        max_adj = max(adj for _, adj in per_feature.values())
        worst = sorted(per_feature.items(), key=lambda kv: -kv[1][0])[:10]
        if max_adj >= self.psi_fail:
            status = "violation"
        elif max_adj >= self.psi_warn:
            status = "warning"
        else:
            status = "ok"

        return {
            "status": status,
            "max_psi_adjusted": float(max_adj),
            "psi": [(col, round(raw, 4)) for col, (raw, _) in worst],
            "n_samples": n,
        }
