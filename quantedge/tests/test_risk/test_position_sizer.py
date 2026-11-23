import numpy as np
import pytest

from risk.position_sizer import vol_target_scalar


class TestVolTargetScalar:
    def test_at_target_returns_one(self):
        assert vol_target_scalar(0.00015, 0.1, target_vol_per_bar=0.0015) == pytest.approx(1.0)

    def test_low_vol_scales_up(self):
        assert vol_target_scalar(0.0001, 1.0, target_vol_per_bar=0.00015) == pytest.approx(1.5)

    def test_high_vol_scales_down(self):
        assert vol_target_scalar(0.003, 1.0, target_vol_per_bar=0.0015) == pytest.approx(0.5)

    def test_clamped_to_ceiling(self):
        assert vol_target_scalar(1e-9, 1.0, target_vol_per_bar=0.0015) == pytest.approx(2.0)

    def test_invalid_inputs_return_neutral(self):
        assert vol_target_scalar(np.nan, 1.0) == 1.0
        assert vol_target_scalar(0.0, 1.0) == 1.0
        assert vol_target_scalar("bad", 1.0) == 1.0
        assert vol_target_scalar(0.001, 0.0) == 1.0
