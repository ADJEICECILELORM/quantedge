# tests/test_utils/test_time_machine.py
from datetime import datetime

from time_machine import TimeMachine


class TestTimeMachine:
    def setup_method(self):
        self.tm = TimeMachine()

    def test_defaults_cover_liquid_hours_only(self):
        assert self.tm.is_trading_allowed(datetime(2024, 1, 2, 8, 0)) is True
        assert self.tm.is_trading_allowed(datetime(2024, 1, 2, 16, 0)) is True
        assert self.tm.is_trading_allowed(datetime(2024, 1, 2, 3, 0)) is False
        assert self.tm.is_trading_allowed(datetime(2024, 1, 2, 20, 0)) is False

    def test_weekend_is_never_allowed(self):
        for hour in (0, 8, 12, 23):
            assert self.tm.is_trading_allowed(datetime(2024, 1, 6, hour, 0)) is False

    def test_custom_ranges_are_respected(self):
        tm = TimeMachine(allowed_utc_ranges=[(0, 24)])
        assert tm.is_trading_allowed(datetime(2024, 1, 2, 3, 0)) is True

    def test_range_end_24_covers_rest_of_day(self):
        tm = TimeMachine(allowed_utc_ranges=[(21, 24)])
        assert tm.is_trading_allowed(datetime(2024, 1, 2, 22, 30)) is True
        assert tm.is_trading_allowed(datetime(2024, 1, 2, 20, 0)) is False

    def test_next_window_open_skips_weekend(self):
        result = self.tm.next_window_open(datetime(2024, 1, 5, 20, 0))
        assert result.weekday() < 5
        assert result.hour == 7
