# backtest/strategies.py
"""
Transparent rule-based strategies that plug into BacktestEngine through
the same predict() contract the ML ensemble uses.

Unlike the ML path, these rules are fixed a priori - nothing is fitted
to the data - so any history run through the engine is genuine held-out
evidence. They serve both as standalone strategies and as honest
baselines the ML ensemble must beat to justify its complexity.
"""
import numpy as np


class FeatureSignMomentum:
    """
    Time-series momentum proxy: trade in the direction of a single
    signed trend feature (e.g. 'price_vs_sma50' as a ~2-3 month
    momentum signal, 'sma_cross' as an EMA/SMA regime switch).

    deadband keeps flat whatever sits inside +- the threshold, so the
    strategy stands aside near the crossover boundary.
    """

    def __init__(self, feature: str = "price_vs_sma50", confidence: float = 0.9,
                 deadband: float = 0.0):
        self.feature = feature
        self.confidence = float(confidence)
        self.deadband = float(deadband)

    def predict(self, row_df) -> dict:
        value = row_df.iloc[-1].get(self.feature, np.nan)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = np.nan

        if not np.isfinite(value):
            return {'direction': 0, 'confidence': 0.5, 'model_votes': {}}

        if abs(value) < self.deadband:
            direction = 0
        else:
            direction = 1 if value > 0 else -1

        return {
            'direction': direction,
            'confidence': self.confidence,
            'model_votes': {self.feature: value},
        }
