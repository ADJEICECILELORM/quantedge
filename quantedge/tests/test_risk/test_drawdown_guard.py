
from risk.drawdown_guard import DrawdownGuard


class TestDrawdownGuard:
    def test_breach_trips_and_clears_on_daily_reset(self):
        guard = DrawdownGuard(10000.0, max_daily_loss_percent=5.0)
        assert guard.check_status(9600.0) is False
        assert guard.check_status(9400.0) is True
        assert guard.is_broken is True

        guard.reset_daily(9400.0)
        assert guard.is_broken is False
        assert guard.start_balance == 9400.0
        assert guard.max_loss == 9400.0 * 0.05

    def test_current_drawdown_fraction(self):
        guard = DrawdownGuard(10000.0)
        guard.observe(11000.0)
        assert guard.current_drawdown == 0.0
        guard.observe(9900.0)
        assert guard.current_drawdown == (11000.0 - 9900.0) / 11000.0

    def test_current_drawdown_clamped(self):
        guard = DrawdownGuard(10000.0)
        guard.peak_equity = 10000.0
        guard.current_equity = 12000.0
        assert guard.current_drawdown == 0.0
        guard.current_equity = 0.0
        assert guard.current_drawdown == 1.0

    def test_check_status_updates_observed_equity(self):
        guard = DrawdownGuard(10000.0)
        guard.check_status(10500.0)
        assert guard.current_equity == 10500.0
        assert guard.peak_equity == 10500.0
