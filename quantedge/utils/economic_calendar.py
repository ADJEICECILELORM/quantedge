# utils/economic_calendar.py - Economic Calendar Integration
from datetime import datetime, timedelta
from typing import List, Dict

class EconomicCalendar:
    """
    Economic Calendar for high-impact news events.
    In production, this would fetch from an API (ForexFactory, Investing.com, etc.)
    For now, we'll use a simple manual system.
    """
    def __init__(self):
        self.events = []
        self.impact_levels = {'low': 1, 'medium': 2, 'high': 3}

    def add_event(self, time: datetime, currency: str, event_name: str, impact: str):
        """
        Add a news event manually.
        impact: 'low', 'medium', 'high'
        """
        self.events.append({
            'time': time,
            'currency': currency,
            'event': event_name,
            'impact': impact,
            'impact_level': self.impact_levels.get(impact, 1)
        })

    def load_weekly_events(self):
        """
        Load common weekly events (can be customized).
        In production, fetch from API.
        """
        now = datetime.now()

        # Example: NFP (first Friday of month at 13:30 UTC)
        # This is just a placeholder - in production, use real API
        pass

    def get_upcoming_events(self, minutes_ahead: int = 60) -> List[Dict]:
        """
        Get events happening in the next N minutes.
        """
        now = datetime.now()
        future_time = now + timedelta(minutes=minutes_ahead)

        upcoming = [
            event for event in self.events
            if now <= event['time'] <= future_time
        ]

        return sorted(upcoming, key=lambda x: x['time'])

    def is_news_imminent(self, current_time: datetime, currency: str, minutes_before: int = 30) -> Dict:
        """
        Check if high-impact news is coming soon for a currency.
        """
        future_time = current_time + timedelta(minutes=minutes_before)

        for event in self.events:
            if event['currency'] == currency and event['impact'] == 'high':
                if current_time <= event['time'] <= future_time:
                    minutes_away = (event['time'] - current_time).total_seconds() / 60
                    return {
                        'imminent': True,
                        'event': event,
                        'minutes_away': minutes_away
                    }

        return {'imminent': False, 'event': None}

    def should_avoid_trading(self, current_time: datetime, currency: str,
                            minutes_before: int = 30, minutes_after: int = 15) -> bool:
        """
        Avoid trading during news blackout period.
        """
        for event in self.events:
            if event['currency'] != currency:
                continue

            if event['impact'] != 'high':
                continue

            # Check if we're in the blackout window
            blackout_start = event['time'] - timedelta(minutes=minutes_before)
            blackout_end = event['time'] + timedelta(minutes=minutes_after)

            if blackout_start <= current_time <= blackout_end:
                return True

        return False

    def get_news_for_symbol(self, symbol: str) -> str:
        """
        Extract currency from symbol (e.g., EURUSD -> EUR, USD)
        """
        # Common patterns
        if 'EUR' in symbol:
            return 'EUR'
        elif 'USD' in symbol:
            return 'USD'
        elif 'GBP' in symbol:
            return 'GBP'
        elif 'JPY' in symbol:
            return 'JPY'
        elif 'AUD' in symbol:
            return 'AUD'
        elif 'NZD' in symbol:
            return 'NZD'
        elif 'CAD' in symbol:
            return 'CAD'
        elif 'CHF' in symbol:
            return 'CHF'
        elif 'BTC' in symbol:
            return 'BTC'
        elif 'ETH' in symbol:
            return 'ETH'
        else:
            return 'UNKNOWN'
