# utils/advanced_news_arbitrage.py - Advanced News Arbitrage System
"""
Advanced News Arbitrage with:
- Real-time news API integration
- Pre-news positioning strategy
- Volatility spike detection
- Dynamic risk management
- Post-news momentum trading
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import json


class NewsEvent:
    """Represents a single news event"""
    def __init__(self, time: datetime, currency: str, event_name: str,
                 impact: str, actual: Optional[str] = None,
                 forecast: Optional[str] = None, previous: Optional[str] = None):
        self.time = time
        self.currency = currency
        self.event_name = event_name
        self.impact = impact  # 'low', 'medium', 'high'
        self.actual = actual
        self.forecast = forecast
        self.previous = previous
        self.impact_score = self._calculate_impact_score()

    def _calculate_impact_score(self) -> float:
        """Calculate numerical impact score (0-10)"""
        base_scores = {'low': 2, 'medium': 5, 'high': 8}
        score = base_scores.get(self.impact.lower(), 0)

        # Boost score if we have actual vs forecast deviation
        if self.actual and self.forecast:
            try:
                actual_val = float(self.actual.replace('%', '').replace('K', '000').replace('M', '000000'))
                forecast_val = float(self.forecast.replace('%', '').replace('K', '000').replace('M', '000000'))

                if forecast_val != 0:
                    deviation = abs((actual_val - forecast_val) / forecast_val)
                    # Large deviation = bigger surprise = more volatility
                    if deviation > 0.5:  # 50% deviation
                        score += 2
                    elif deviation > 0.2:  # 20% deviation
                        score += 1
            except:
                pass

        return min(10, score)

    def to_dict(self) -> dict:
        return {
            'time': self.time.isoformat(),
            'currency': self.currency,
            'event': self.event_name,
            'impact': self.impact,
            'impact_score': self.impact_score,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous
        }


class AdvancedNewsArbitrage:
    """Advanced News Arbitrage Trading System"""

    def __init__(self):
        self.events = []
        self.volatility_history = {}  # symbol -> list of volatility readings
        self.news_api_enabled = True

        # Strategy parameters
        self.pre_news_window = 30  # minutes before news
        self.post_news_window = 15  # minutes after news
        self.blackout_before = 5   # stop trading 5 min before news
        self.momentum_window = 30  # trade momentum for 30 min after news

        # Risk management
        self.news_risk_multiplier = 0.5  # Reduce position size by 50% during news
        self.volatility_sl_multiplier = 2.0  # Wider stops during news

    def fetch_forex_factory_events(self, days_ahead: int = 7) -> List[NewsEvent]:
        """
        Scrape ForexFactory economic calendar (fallback method).
        Note: In production, use official APIs or paid data feeds.
        """
        try:
            url = "https://www.forexfactory.com/calendar"
            headers = {'User-Agent': 'Mozilla/5.0'}

            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"⚠️ ForexFactory request failed: {response.status_code}")
                return []

            soup = BeautifulSoup(response.content, 'html.parser')
            events = []

            # Parse calendar rows (simplified - actual parsing is more complex)
            calendar_rows = soup.find_all('tr', class_='calendar__row')

            for row in calendar_rows[:50]:  # Limit to 50 events
                try:
                    # Extract time
                    time_elem = row.find('td', class_='calendar__time')
                    if not time_elem:
                        continue

                    time_str = time_elem.text.strip()
                    if not time_str or time_str == 'All Day':
                        continue

                    # Extract currency
                    currency_elem = row.find('td', class_='calendar__currency')
                    currency = currency_elem.text.strip() if currency_elem else 'USD'

                    # Extract impact
                    impact_elem = row.find('td', class_='calendar__impact')
                    impact_class = impact_elem.find('span')['class'] if impact_elem and impact_elem.find('span') else []

                    if 'icon--ff-impact-red' in impact_class:
                        impact = 'high'
                    elif 'icon--ff-impact-ora' in impact_class:
                        impact = 'medium'
                    else:
                        impact = 'low'

                    # Extract event name
                    event_elem = row.find('td', class_='calendar__event')
                    event_name = event_elem.text.strip() if event_elem else 'Unknown'

                    # Extract actual, forecast, previous
                    actual_elem = row.find('td', class_='calendar__actual')
                    forecast_elem = row.find('td', class_='calendar__forecast')
                    previous_elem = row.find('td', class_='calendar__previous')

                    actual = actual_elem.text.strip() if actual_elem else None
                    forecast = forecast_elem.text.strip() if forecast_elem else None
                    previous = previous_elem.text.strip() if previous_elem else None

                    # Parse time (simplified - you'd need proper date parsing)
                    event_time = self._parse_time_string(time_str)

                    if event_time:
                        news_event = NewsEvent(
                            time=event_time,
                            currency=currency,
                            event_name=event_name,
                            impact=impact,
                            actual=actual,
                            forecast=forecast,
                            previous=previous
                        )
                        events.append(news_event)

                except Exception as e:
                    continue

            print(f"✅ Fetched {len(events)} news events from ForexFactory")
            return events

        except Exception as e:
            print(f"❌ ForexFactory scraping failed: {e}")
            return []

    def fetch_investing_com_events(self) -> List[NewsEvent]:
        """
        Fetch from Investing.com API (requires API key in production).
        This is a placeholder - you'd need actual API integration.
        """
        try:
            # Placeholder for Investing.com API
            # In production: Use official API with authentication
            url = "https://api.investing.com/api/economicCalendar"
            # response = requests.get(url, headers={'Authorization': 'YOUR_API_KEY'})
            # ...
            print("⚠️ Investing.com API integration not configured")
            return []
        except Exception as e:
            print(f"❌ Investing.com API failed: {e}")
            return []

    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """Parse time string to datetime (simplified)"""
        try:
            now = datetime.now()
            # Format: "10:30am" or "2:00pm"
            time_str = time_str.replace('am', 'AM').replace('pm', 'PM')
            parsed_time = datetime.strptime(time_str, '%I:%M%p')

            # Combine with today's date
            event_time = now.replace(
                hour=parsed_time.hour,
                minute=parsed_time.minute,
                second=0,
                microsecond=0
            )

            # If time has passed today, assume it's tomorrow
            if event_time < now:
                event_time += timedelta(days=1)

            return event_time

        except Exception as e:
            return None

    def load_events_from_api(self) -> bool:
        """Load events from available APIs"""
        if not self.news_api_enabled:
            return False

        print(f"\n{'='*60}")
        print(f"📰 FETCHING REAL-TIME NEWS EVENTS")
        print(f"{'='*60}")

        # Try ForexFactory first
        ff_events = self.fetch_forex_factory_events()
        if ff_events:
            self.events.extend(ff_events)

        # Try Investing.com
        # ic_events = self.fetch_investing_com_events()
        # if ic_events:
        #     self.events.extend(ic_events)

        # Remove duplicates and sort by time
        self.events = self._deduplicate_events(self.events)
        self.events.sort(key=lambda x: x.time)

        # Filter to only high-impact events
        high_impact = [e for e in self.events if e.impact == 'high']

        print(f"✅ Loaded {len(self.events)} total events ({len(high_impact)} high-impact)")
        print(f"{'='*60}\n")

        return len(self.events) > 0

    def _deduplicate_events(self, events: List[NewsEvent]) -> List[NewsEvent]:
        """Remove duplicate events"""
        seen = set()
        unique = []

        for event in events:
            key = (event.time, event.currency, event.event_name)
            if key not in seen:
                seen.add(key)
                unique.append(event)

        return unique

    def get_upcoming_events(self, current_time: datetime, minutes_ahead: int = 60) -> List[NewsEvent]:
        """Get events happening in the next N minutes"""
        future_time = current_time + timedelta(minutes=minutes_ahead)

        upcoming = [
            event for event in self.events
            if current_time <= event.time <= future_time
        ]

        return sorted(upcoming, key=lambda x: x.time)

    def get_news_phase(self, current_time: datetime, symbol: str) -> Dict:
        """
        Determine current news phase and strategy.

        Returns:
        {
            'phase': 'pre_news' | 'blackout' | 'during_news' | 'post_news' | 'normal',
            'event': NewsEvent or None,
            'strategy': 'position' | 'avoid' | 'momentum' | 'normal',
            'risk_multiplier': float,
            'sl_multiplier': float
        }
        """
        currency = self._extract_currency_from_symbol(symbol)
        if not currency:
            return self._normal_phase()

        # Find relevant events
        for event in self.events:
            if event.currency != currency:
                continue

            time_diff_minutes = (event.time - current_time).total_seconds() / 60

            # Pre-news positioning window (30-5 min before)
            if self.blackout_before < time_diff_minutes <= self.pre_news_window:
                if event.impact == 'high':
                    return {
                        'phase': 'pre_news',
                        'event': event,
                        'strategy': 'position',
                        'risk_multiplier': 0.7,  # Reduce risk slightly
                        'sl_multiplier': 1.3,    # Slightly wider stops
                        'minutes_to_news': time_diff_minutes
                    }

            # Blackout window (5 min before to 5 min after)
            if -5 <= time_diff_minutes <= self.blackout_before:
                return {
                    'phase': 'blackout',
                    'event': event,
                    'strategy': 'avoid',
                    'risk_multiplier': 0,
                    'sl_multiplier': 999,
                    'minutes_to_news': time_diff_minutes
                }

            # During news (5 min after to 15 min after)
            if -15 <= time_diff_minutes < -5:
                return {
                    'phase': 'during_news',
                    'event': event,
                    'strategy': 'avoid',
                    'risk_multiplier': 0,
                    'sl_multiplier': 999,
                    'minutes_since_news': abs(time_diff_minutes)
                }

            # Post-news momentum window (15-45 min after)
            if -45 <= time_diff_minutes < -15:
                return {
                    'phase': 'post_news',
                    'event': event,
                    'strategy': 'momentum',
                    'risk_multiplier': 1.2,  # Increase risk for momentum
                    'sl_multiplier': 2.0,    # Wider stops for volatility
                    'minutes_since_news': abs(time_diff_minutes)
                }

        return self._normal_phase()

    def _normal_phase(self) -> Dict:
        """Normal trading phase"""
        return {
            'phase': 'normal',
            'event': None,
            'strategy': 'normal',
            'risk_multiplier': 1.0,
            'sl_multiplier': 1.0
        }

    def _extract_currency_from_symbol(self, symbol: str) -> Optional[str]:
        """Extract currency from symbol"""
        symbol_upper = symbol.upper()

        currencies = ['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'NZD', 'CAD', 'CHF']
        for curr in currencies:
            if curr in symbol_upper:
                return curr

        return None

    def detect_volatility_spike(self, df: pd.DataFrame) -> Dict:
        """
        Detect if volatility is spiking (potential news release).

        Returns:
        {
            'spike_detected': bool,
            'spike_strength': float (0-1),
            'current_atr': float,
            'avg_atr': float
        }
        """
        if len(df) < 50:
            return {'spike_detected': False, 'spike_strength': 0}

        # Calculate ATR
        if 'atr_14' not in df.columns:
            high = df['high']
            low = df['low']
            close = df['close']

            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
        else:
            atr = df['atr_14']

        current_atr = atr.iloc[-1]
        recent_atr = atr.iloc[-20:].mean()
        avg_atr = atr.iloc[-50:].mean()

        # Spike detection
        spike_threshold = 1.5  # 50% above average
        spike_detected = current_atr > (avg_atr * spike_threshold)
        spike_strength = min(1.0, (current_atr / avg_atr) / spike_threshold)

        return {
            'spike_detected': spike_detected,
            'spike_strength': spike_strength,
            'current_atr': current_atr,
            'avg_atr': avg_atr,
            'atr_ratio': current_atr / avg_atr if avg_atr > 0 else 1.0
        }

    def get_news_based_sl_tp(self, entry: float, signal: int, base_sl: float,
                             base_tp: float, news_phase: Dict) -> Dict:
        """
        Adjust SL/TP based on news phase.

        Args:
            entry: Entry price
            signal: 1 for buy, -1 for sell
            base_sl: Base stop loss
            base_tp: Base take profit
            news_phase: News phase info from get_news_phase()

        Returns:
        {
            'sl': adjusted stop loss,
            'tp': adjusted take profit,
            'reason': explanation
        }
        """
        sl_multiplier = news_phase['sl_multiplier']

        # Calculate SL distance
        sl_distance = abs(base_sl - entry)
        tp_distance = abs(base_tp - entry)

        # Adjust based on phase
        if news_phase['phase'] == 'pre_news':
            # Tighter TP, normal SL (quick profit before news)
            new_sl = base_sl
            new_tp = entry + (tp_distance * 0.7 * signal)
            reason = "Pre-news: Tighter TP for quick profit"

        elif news_phase['phase'] == 'post_news':
            # Wider SL, wider TP (momentum trade)
            new_sl = entry - (sl_distance * sl_multiplier * signal)
            new_tp = entry + (tp_distance * 1.5 * signal)
            reason = "Post-news: Wider SL/TP for momentum"

        else:
            # Normal
            new_sl = base_sl
            new_tp = base_tp
            reason = "Normal trading"

        return {
            'sl': new_sl,
            'tp': new_tp,
            'reason': reason
        }

    def print_news_calendar(self, current_time: datetime, hours_ahead: int = 4):
        """Print upcoming news events"""
        upcoming = self.get_upcoming_events(current_time, minutes_ahead=hours_ahead*60)

        if not upcoming:
            print("📅 No high-impact news in the next 4 hours")
            return

        print(f"\n{'='*60}")
        print(f"📅 UPCOMING NEWS EVENTS (Next {hours_ahead} hours)")
        print(f"{'='*60}")

        for event in upcoming:
            time_diff = (event.time - current_time).total_seconds() / 60
            impact_emoji = '🔴' if event.impact == 'high' else ('🟡' if event.impact == 'medium' else '🟢')

            print(f"{impact_emoji} {event.time.strftime('%H:%M')} ({int(time_diff)} min) - "
                  f"{event.currency} - {event.event_name}")

        print(f"{'='*60}\n")

    def save_events_to_cache(self, filepath: str = 'data/news_cache.json'):
        """Save events to cache file"""
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            events_data = [event.to_dict() for event in self.events]
            with open(filepath, 'w') as f:
                json.dump(events_data, f, indent=2)

            print(f"💾 News events saved to {filepath}")
        except Exception as e:
            print(f"⚠️ Failed to save news cache: {e}")

    def load_events_from_cache(self, filepath: str = 'data/news_cache.json') -> bool:
        """Load events from cache file"""
        try:
            with open(filepath, 'r') as f:
                events_data = json.load(f)

            self.events = []
            for data in events_data:
                event = NewsEvent(
                    time=datetime.fromisoformat(data['time']),
                    currency=data['currency'],
                    event_name=data['event'],
                    impact=data['impact'],
                    actual=data.get('actual'),
                    forecast=data.get('forecast'),
                    previous=data.get('previous')
                )
                self.events.append(event)

            print(f"✅ Loaded {len(self.events)} events from cache")
            return True

        except Exception as e:
            print(f"⚠️ Failed to load news cache: {e}")
            return False
