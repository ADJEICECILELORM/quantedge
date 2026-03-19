# time_machine.py - Session Filter (The Time Machine)
import pandas as pd
from datetime import datetime, time as dt_time

class TimeMachine:
    """
    Advanced Session Filter: Only trades during optimal market conditions.
    Filters out low-liquidity hours and weekends.
    """
    def __init__(self):
        # Define high-liquidity sessions (UTC time)
        self.sessions = {
            'asian': {'start': dt_time(0, 0), 'end': dt_time(7, 0)},
            'london_open': {'start': dt_time(7, 0), 'end': dt_time(9, 0)},
            'london_main': {'start': dt_time(9, 0), 'end': dt_time(12, 0)},
            'overlap': {'start': dt_time(12, 0), 'end': dt_time(13, 0)},
            'ny_open': {'start': dt_time(13, 0), 'end': dt_time(15, 0)},
            'ny_main': {'start': dt_time(15, 0), 'end': dt_time(18, 0)},
            'evening': {'start': dt_time(18, 0), 'end': dt_time(23, 59)},
        }

        # Trading allowed sessions (ALL sessions - 24/5 trading)
        self.allowed_sessions = ['asian', 'london_open', 'london_main', 'overlap', 'ny_open', 'ny_main', 'evening']

    def is_trading_allowed(self, current_time: datetime) -> bool:
        """
        Check if current time is within allowed trading sessions.
        """
        # Check if weekend
        if current_time.weekday() >= 5:
            return False

        # Check if within any allowed session
        current_time_only = current_time.time()

        for session_name in self.allowed_sessions:
            session = self.sessions[session_name]
            if session['start'] <= current_time_only <= session['end']:
                return True

        return False

    def get_current_session(self, current_time: datetime) -> str:
        """Get the name of current trading session"""
        if current_time.weekday() >= 5:
            return 'weekend'

        current_time_only = current_time.time()

        for session_name, session in self.sessions.items():
            if session['start'] <= current_time_only <= session['end']:
                return session_name

        return 'off_hours'

    def get_session_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze historical performance by session.
        df should have 'time' and 'returns' columns.
        """
        if 'time' not in df.columns:
            print("Error: 'time' column not found")
            return None

        df['session'] = df['time'].apply(self.get_current_session)

        stats = df.groupby('session').agg({
            'returns_1': ['mean', 'std', 'count']
        })

        return stats

    def is_high_volatility_period(self, current_time: datetime) -> bool:
        """
        Check if current time is during high-volatility periods.
        """
        session = self.get_current_session(current_time)
        return session in ['london_open', 'ny_open', 'overlap']

    def avoid_rollover(self, current_time: datetime) -> bool:
        """
        Avoid trading during rollover period (5pm EST = 22:00 UTC)
        """
        rollover_start = dt_time(21, 45)
        rollover_end = dt_time(22, 15)

        current_time_only = current_time.time()

        if rollover_start <= current_time_only <= rollover_end:
            return True

        return False

    def print_status(self, current_time: datetime):
        """Print current session status"""
        session = self.get_current_session(current_time)
        allowed = self.is_trading_allowed(current_time)
        high_vol = self.is_high_volatility_period(current_time)

        print(f"Time Machine Status:")
        print(f"   Current Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"   Session: {session.upper()}")
        print(f"   Trading Allowed: {'YES' if allowed else 'NO'}")
        print(f"   High Volatility Period: {'YES' if high_vol else 'NO'}")
