# utils/probability_window.py - Time-Based Probability Analysis
"""
Analyzes historical performance by time of day, day of week, and trading session
to identify high-probability trading windows.
"""

import pandas as pd
from datetime import datetime, time
from typing import Dict, List, Optional
import json
import os


class TradingSession:
    """Represents a trading session"""
    SYDNEY = {'start': time(22, 0), 'end': time(7, 0), 'name': 'Sydney'}
    TOKYO = {'start': time(0, 0), 'end': time(9, 0), 'name': 'Tokyo'}
    LONDON = {'start': time(8, 0), 'end': time(17, 0), 'name': 'London'}
    NEW_YORK = {'start': time(13, 0), 'end': time(22, 0), 'name': 'New York'}
    OVERLAP_LONDON_NY = {'start': time(13, 0), 'end': time(17, 0), 'name': 'London-NY Overlap'}


class ProbabilityWindow:
    """
    Time-based probability analysis for identifying optimal trading periods.
    """

    def __init__(self, lookback_days: int = 90):
        """
        Args:
            lookback_days: Number of days of history to analyze
        """
        self.lookback_days = lookback_days
        self.trade_history = []  # List of historical trades

        # Performance by time dimensions
        self.hourly_stats = {}      # Hour of day (0-23) -> {wins, losses, total, win_rate}
        self.daily_stats = {}       # Day of week (0-6) -> {wins, losses, total, win_rate}
        self.session_stats = {}     # Session name -> {wins, losses, total, win_rate}
        self.symbol_time_stats = {} # (symbol, hour) -> {wins, losses, total, win_rate}

        # Probability matrices
        self.probability_matrix = None  # (day_of_week, hour) -> probability
        self.session_probabilities = {}

    def add_trade(self, trade: Dict):
        """
        Add a completed trade to history.

        Args:
            trade: {
                'time': datetime,
                'symbol': str,
                'signal': 1/-1,
                'entry': float,
                'exit': float,
                'profit': float,
                'won': bool
            }
        """
        if 'time' not in trade:
            trade['time'] = datetime.now()

        # Ensure 'won' field exists
        if 'won' not in trade and 'profit' in trade:
            trade['won'] = trade['profit'] > 0

        self.trade_history.append(trade)

        # Update stats
        self._update_stats(trade)

    def _update_stats(self, trade: Dict):
        """Update probability statistics with new trade"""
        trade_time = trade['time']
        hour = trade_time.hour
        day_of_week = trade_time.weekday()  # 0=Monday, 6=Sunday
        symbol = trade['symbol']
        won = trade['won']

        # Update hourly stats
        if hour not in self.hourly_stats:
            self.hourly_stats[hour] = {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0.0}

        self.hourly_stats[hour]['total'] += 1
        if won:
            self.hourly_stats[hour]['wins'] += 1
        else:
            self.hourly_stats[hour]['losses'] += 1

        self.hourly_stats[hour]['win_rate'] = (
            self.hourly_stats[hour]['wins'] / self.hourly_stats[hour]['total']
        )

        # Update daily stats
        if day_of_week not in self.daily_stats:
            self.daily_stats[day_of_week] = {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0.0}

        self.daily_stats[day_of_week]['total'] += 1
        if won:
            self.daily_stats[day_of_week]['wins'] += 1
        else:
            self.daily_stats[day_of_week]['losses'] += 1

        self.daily_stats[day_of_week]['win_rate'] = (
            self.daily_stats[day_of_week]['wins'] / self.daily_stats[day_of_week]['total']
        )

        # Update session stats
        session = self._get_trading_session(trade_time)
        if session:
            if session not in self.session_stats:
                self.session_stats[session] = {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0.0}

            self.session_stats[session]['total'] += 1
            if won:
                self.session_stats[session]['wins'] += 1
            else:
                self.session_stats[session]['losses'] += 1

            self.session_stats[session]['win_rate'] = (
                self.session_stats[session]['wins'] / self.session_stats[session]['total']
            )

        # Update symbol-time stats
        key = (symbol, hour)
        if key not in self.symbol_time_stats:
            self.symbol_time_stats[key] = {'wins': 0, 'losses': 0, 'total': 0, 'win_rate': 0.0}

        self.symbol_time_stats[key]['total'] += 1
        if won:
            self.symbol_time_stats[key]['wins'] += 1
        else:
            self.symbol_time_stats[key]['losses'] += 1

        self.symbol_time_stats[key]['win_rate'] = (
            self.symbol_time_stats[key]['wins'] / self.symbol_time_stats[key]['total']
        )

    def _get_trading_session(self, dt: datetime) -> Optional[str]:
        """Determine which trading session a datetime falls into"""
        t = dt.time()

        if TradingSession.OVERLAP_LONDON_NY['start'] <= t <= TradingSession.OVERLAP_LONDON_NY['end']:
            return TradingSession.OVERLAP_LONDON_NY['name']
        elif TradingSession.LONDON['start'] <= t < TradingSession.LONDON['end']:
            return TradingSession.LONDON['name']
        elif TradingSession.NEW_YORK['start'] <= t <= TradingSession.NEW_YORK['end']:
            return TradingSession.NEW_YORK['name']
        elif TradingSession.TOKYO['start'] <= t < TradingSession.TOKYO['end']:
            return TradingSession.TOKYO['name']
        elif t >= TradingSession.SYDNEY['start'] or t < TradingSession.SYDNEY['end']:
            return TradingSession.SYDNEY['name']

        return None

    def get_probability_score(self, current_time: datetime, symbol: str) -> Dict:
        """
        Get probability score for trading at a specific time.

        Returns:
        {
            'overall_probability': float (0-1),
            'hourly_win_rate': float,
            'daily_win_rate': float,
            'session_win_rate': float,
            'symbol_time_win_rate': float,
            'confidence_multiplier': float (0.8-1.2),
            'recommendation': str
        }
        """
        if not self.trade_history or len(self.trade_history) < 20:
            return self._default_probability()

        hour = current_time.hour
        day_of_week = current_time.weekday()
        session = self._get_trading_session(current_time)

        # Get individual probabilities
        hourly_wr = self.hourly_stats.get(hour, {}).get('win_rate', 0.5)
        daily_wr = self.daily_stats.get(day_of_week, {}).get('win_rate', 0.5)
        session_wr = self.session_stats.get(session, {}).get('win_rate', 0.5) if session else 0.5
        symbol_time_wr = self.symbol_time_stats.get((symbol, hour), {}).get('win_rate', 0.5)

        # Calculate weighted overall probability
        weights = {
            'hourly': 0.25,
            'daily': 0.20,
            'session': 0.30,
            'symbol_time': 0.25
        }

        overall_prob = (
            hourly_wr * weights['hourly'] +
            daily_wr * weights['daily'] +
            session_wr * weights['session'] +
            symbol_time_wr * weights['symbol_time']
        )

        # Calculate confidence multiplier
        if overall_prob >= 0.60:
            multiplier = 1.2  # High probability window
            recommendation = "EXCELLENT time to trade"
        elif overall_prob >= 0.55:
            multiplier = 1.1  # Good probability
            recommendation = "GOOD time to trade"
        elif overall_prob >= 0.50:
            multiplier = 1.0  # Average probability
            recommendation = "AVERAGE time to trade"
        elif overall_prob >= 0.45:
            multiplier = 0.95  # Below average
            recommendation = "Below average time"
        else:
            multiplier = 0.85  # Poor probability window
            recommendation = "POOR time to trade - consider waiting"

        return {
            'overall_probability': overall_prob,
            'hourly_win_rate': hourly_wr,
            'daily_win_rate': daily_wr,
            'session_win_rate': session_wr,
            'symbol_time_win_rate': symbol_time_wr,
            'session': session,
            'confidence_multiplier': multiplier,
            'recommendation': recommendation,
            'sample_size': len(self.trade_history)
        }

    def _default_probability(self) -> Dict:
        """Default probability when insufficient data"""
        return {
            'overall_probability': 0.50,
            'hourly_win_rate': 0.50,
            'daily_win_rate': 0.50,
            'session_win_rate': 0.50,
            'symbol_time_win_rate': 0.50,
            'session': None,
            'confidence_multiplier': 1.0,
            'recommendation': 'Insufficient data - building history',
            'sample_size': len(self.trade_history)
        }

    def get_best_trading_hours(self, top_n: int = 5) -> List[Dict]:
        """
        Get the best hours of the day for trading.

        Returns:
            List of {hour, win_rate, total_trades}
        """
        if not self.hourly_stats:
            return []

        # Filter hours with at least 5 trades
        valid_hours = [
            {'hour': hour, 'win_rate': stats['win_rate'], 'total_trades': stats['total']}
            for hour, stats in self.hourly_stats.items()
            if stats['total'] >= 5
        ]

        # Sort by win rate
        valid_hours.sort(key=lambda x: x['win_rate'], reverse=True)

        return valid_hours[:top_n]

    def get_best_trading_days(self) -> List[Dict]:
        """
        Get the best days of the week for trading.

        Returns:
            List of {day, day_name, win_rate, total_trades}
        """
        if not self.daily_stats:
            return []

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        days = [
            {
                'day': day,
                'day_name': day_names[day],
                'win_rate': stats['win_rate'],
                'total_trades': stats['total']
            }
            for day, stats in self.daily_stats.items()
            if stats['total'] >= 3
        ]

        # Sort by win rate
        days.sort(key=lambda x: x['win_rate'], reverse=True)

        return days

    def get_best_sessions(self) -> List[Dict]:
        """Get the best trading sessions"""
        if not self.session_stats:
            return []

        sessions = [
            {
                'session': session,
                'win_rate': stats['win_rate'],
                'total_trades': stats['total']
            }
            for session, stats in self.session_stats.items()
            if stats['total'] >= 5
        ]

        sessions.sort(key=lambda x: x['win_rate'], reverse=True)

        return sessions

    def generate_heatmap_data(self) -> pd.DataFrame:
        """
        Generate a probability heatmap (day x hour).

        Returns:
            DataFrame with days as rows, hours as columns, win rates as values
        """
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        hours = list(range(24))

        heatmap = pd.DataFrame(index=day_names, columns=hours, data=0.5)

        for (day, hour), stats in self.symbol_time_stats.items():
            if stats['total'] >= 3:  # Minimum sample size
                heatmap.loc[day_names[day % 7], hour] = stats['win_rate']

        return heatmap

    def print_probability_report(self, current_time: datetime = None):
        """Print detailed probability analysis report"""
        if current_time is None:
            current_time = datetime.now()

        print(f"\n{'='*60}")
        print("⏰ PROBABILITY WINDOW ANALYSIS")
        print(f"{'='*60}")
        print(f"Sample Size: {len(self.trade_history)} trades")

        # Best hours
        best_hours = self.get_best_trading_hours(top_n=5)
        if best_hours:
            print("\n🕐 BEST TRADING HOURS:")
            for h in best_hours:
                print(f"   {h['hour']:02d}:00 - Win Rate: {h['win_rate']*100:.1f}% "
                      f"({h['total_trades']} trades)")

        # Best days
        best_days = self.get_best_trading_days()
        if best_days:
            print("\n📅 BEST TRADING DAYS:")
            for d in best_days:
                print(f"   {d['day_name']}: {d['win_rate']*100:.1f}% ({d['total_trades']} trades)")

        # Best sessions
        best_sessions = self.get_best_sessions()
        if best_sessions:
            print("\n🌍 BEST TRADING SESSIONS:")
            for s in best_sessions:
                print(f"   {s['session']}: {s['win_rate']*100:.1f}% ({s['total_trades']} trades)")

        print(f"{'='*60}\n")

    def save_to_file(self, filepath: str = 'data/probability_window.json'):
        """Save probability data to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            data = {
                'trade_history': [
                    {**trade, 'time': trade['time'].isoformat()}
                    for trade in self.trade_history
                ],
                'hourly_stats': self.hourly_stats,
                'daily_stats': self.daily_stats,
                'session_stats': self.session_stats
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            print(f"💾 Probability data saved to {filepath}")
        except Exception as e:
            print(f"⚠️ Failed to save probability data: {e}")

    def load_from_file(self, filepath: str = 'data/probability_window.json') -> bool:
        """Load probability data from file"""
        try:
            if not os.path.exists(filepath):
                return False

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Load trade history
            self.trade_history = []
            for trade in data.get('trade_history', []):
                trade['time'] = datetime.fromisoformat(trade['time'])
                self.trade_history.append(trade)

            # Load stats
            self.hourly_stats = {int(k): v for k, v in data.get('hourly_stats', {}).items()}
            self.daily_stats = {int(k): v for k, v in data.get('daily_stats', {}).items()}
            self.session_stats = data.get('session_stats', {})

            print(f"✅ Loaded {len(self.trade_history)} trades from probability cache")
            return True

        except Exception as e:
            print(f"⚠️ Failed to load probability data: {e}")
            return False

    def record_closed_trade(self, trade_data: Dict):
        """
        Convenience method to record a closed trade.

        Args:
            trade_data: Should contain time, symbol, entry, exit, profit
        """
        trade = {
            'time': trade_data.get('time', datetime.now()),
            'symbol': trade_data['symbol'],
            'signal': trade_data.get('signal', 1),
            'entry': trade_data['entry'],
            'exit': trade_data.get('exit', trade_data['entry']),
            'profit': trade_data['profit'],
            'won': trade_data['profit'] > 0
        }

        self.add_trade(trade)
        self.save_to_file()
