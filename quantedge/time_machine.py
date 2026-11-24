# time_machine.py - Session Filter (The Time Machine)
from datetime import datetime, timedelta


class TimeMachine:
    """
    Filters out low-liquidity hours and weekends.

    By default only London + New York hours (07:00-17:00 UTC) are allowed.
    Pass `allowed_utc_ranges` as a list of (start_hour, end_hour) tuples to
    override, e.g. [(0, 24)] for 24/5 trading.
    """

    def __init__(self, allowed_utc_ranges=None):
        if allowed_utc_ranges is None:
            allowed_utc_ranges = [(7, 17)]
        self.allowed_utc_ranges = [
            (int(start), int(end)) for start, end in allowed_utc_ranges
        ]

    def is_trading_allowed(self, current_time: datetime) -> bool:
        if current_time.weekday() >= 5:
            return False

        current_hour = current_time.hour

        for start, end in self.allowed_utc_ranges:
            if end == 24:
                if current_hour >= start:
                    return True
            elif start <= current_hour < end:
                return True

        return False

    def next_window_open(self, current_time: datetime) -> datetime:
        start_hour = self.allowed_utc_ranges[0][0]
        for day_offset in range(1, 8):
            candidate = (current_time + timedelta(days=day_offset)).replace(
                hour=start_hour, minute=0, second=0, microsecond=0,
            )
            if candidate.weekday() < 5:
                return candidate
        return current_time
