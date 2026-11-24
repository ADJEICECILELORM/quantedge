import numpy as np
import pandas as pd

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
    def test_three_class_labels(self):
        gen = LabelGenerator(forward_bars=2, vol_multiple=0.5)
        # atr=2, threshold=1
        # bar0: 100 -> 100 flat; bar1: 100 -> 103 (+3 up); bar2: 100 -> 100 flat
        df = make_df([100, 100, 100, 103, 100])

        result = gen.create_labels(df)

        assert len(result) == 3
        assert result['target'].tolist() == [0, 1, 0]

    def test_short_label_below_negative_threshold(self):
        gen = LabelGenerator(forward_bars=2, vol_multiple=0.5)
        # bar2: 100 -> 95 (-5) short
        df = make_df([100, 100, 100, 103, 95])

        result = gen.create_labels(df)

        assert result['target'].tolist() == [0, 1, -1]

    def test_within_deadband_is_flat(self):
        gen = LabelGenerator(forward_bars=2, vol_multiple=0.5)
        # moves of +/-0.5 stay flat (threshold=1.0)
        df = make_df([100, 100, 100, 100.5, 99.5])

        result = gen.create_labels(df)

        assert result['target'].tolist() == [0, 0, 0]

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
        assert set(result['target'].unique()).issubset({-1, 0, 1})
        assert len(result) == n - 5

    def test_does_not_mutate_input(self):
        gen = LabelGenerator(forward_bars=1, vol_multiple=0.5)
        df = make_df([100, 101, 100])
        original = df.copy()

        gen.create_labels(df)

        pd.testing.assert_frame_equal(df, original)

    def test_asymmetric_plateau_not_persistently_long(self):
        gen = LabelGenerator(forward_bars=3, vol_multiple=0.5)
        n = 20
        closes = [100] * 5 + [102] * 10 + [100] * 5
        df = make_df(closes)
        df['atr_14'] = np.full(n, 1.0)

        result = gen.create_labels(df)

        assert (result['target'] == 1).sum() > 0
        assert result['target'].isna().sum() == 0
        assert (result['target'] == -1).sum() >= 1, "repricing back down must produce short labels"
