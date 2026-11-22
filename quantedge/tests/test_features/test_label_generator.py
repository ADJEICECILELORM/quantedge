# tests/test_features/test_label_generator.py
import numpy as np
import pandas as pd
import pytest

from features.label_generator import LabelGenerator


def make_df(closes, atr=2.0):
    n = len(closes)
    return pd.DataFrame(
        {
            'close': np.asarray(closes, dtype=float),
            'atr_14': np.full(n, atr, dtype=float),
        }
    )


class TestLabelGenerator:
    def test_trailing_rows_without_future_are_dropped(self):
        gen = LabelGenerator(forward_bars=2, vol_multiple=0.5)
        df = make_df([100, 100, 100, 103, 100])

        result = gen.create_labels(df)

        assert len(result) == 3
        assert result['target'].tolist() == [0, 1, 0]

    def test_no_nan_targets_in_output(self):
        gen = LabelGenerator(forward_bars=5, vol_multiple=0.5)
        n = 12
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            {
                'close': 100 + np.cumsum(rng.normal(0, 1, n)),
                'atr_14': np.full(n, 2.0),
            }
        )

        result = gen.create_labels(df)

        assert result['target'].isna().sum() == 0
        assert set(result['target'].unique()).issubset({0, 1})
        assert len(result) == n - 5

    def test_does_not_mutate_input(self):
        gen = LabelGenerator(forward_bars=1, vol_multiple=0.5)
        df = make_df([100, 101, 100])
        original = df.copy()

        gen.create_labels(df)

        pd.testing.assert_frame_equal(df, original)
