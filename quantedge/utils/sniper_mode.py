# utils/sniper_mode.py - High Volatility Sniping + News Arbitrage
import pandas as pd
from datetime import datetime
from typing import Dict

class SniperMode:
    """
    High Volatility Breakout Detection + News Event Trading.
    Identifies compression patterns and explosive breakouts.
    """
    def __init__(self, lookback=50, squeeze_threshold=0.8):
        self.lookback = lookback
        self.squeeze_threshold = squeeze_threshold
        self.news_events = []  # Will store upcoming news events

    def detect_compression(self, df: pd.DataFrame) -> bool:
        """
        Detects Bollinger Band squeeze / Triangle pattern.
        Returns True if market is compressed (ready to explode).
        """
        if len(df) < self.lookback:
            return False

        # Calculate Bollinger Bands
        close = df['close'].iloc[-self.lookback:]
        sma = close.rolling(20).mean()
        std = close.rolling(20).std()

        bb_upper = sma + (2 * std)
        bb_lower = sma - (2 * std)
        bb_width = (bb_upper - bb_lower) / sma

        current_width = bb_width.iloc[-1]
        avg_width = bb_width.mean()

        # Squeeze: Current width is smaller than threshold * average
        is_squeezed = current_width < (avg_width * self.squeeze_threshold)

        return is_squeezed

    def detect_breakout(self, df: pd.DataFrame) -> Dict:
        """
        Detects if price has broken out of compression.
        Returns: {'signal': 1/-1/0, 'strength': 0-1}
        """
        if len(df) < self.lookback:
            return {'signal': 0, 'strength': 0}

        recent_data = df.iloc[-self.lookback:]
        current_close = df['close'].iloc[-1]
        current_volume = df['tick_volume'].iloc[-1]

        # Calculate recent high/low
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()

        # Calculate average volume
        avg_volume = recent_data['tick_volume'].mean()
        volume_surge = current_volume / avg_volume if avg_volume > 0 else 1.0

        # Breakout conditions
        breakout_up = current_close > recent_high * 1.0005  # 0.05% above high
        breakout_down = current_close < recent_low * 0.9995  # 0.05% below low

        # Require volume confirmation
        volume_confirmed = volume_surge > 1.5

        if breakout_up and volume_confirmed:
            strength = min(1.0, volume_surge / 3.0)  # Cap at 1.0
            return {'signal': 1, 'strength': strength, 'type': 'breakout_up'}

        if breakout_down and volume_confirmed:
            strength = min(1.0, volume_surge / 3.0)
            return {'signal': -1, 'strength': strength, 'type': 'breakout_down'}

        return {'signal': 0, 'strength': 0, 'type': 'no_breakout'}

    def add_news_event(self, time: datetime, currency: str, impact: str):
        """
        Add upcoming news event.
        impact: 'high', 'medium', 'low'
        """
        self.news_events.append({
            'time': time,
            'currency': currency,
            'impact': impact
        })

    def is_news_imminent(self, current_time: datetime, minutes_before=30) -> Dict:
        """
        Check if high-impact news is coming soon.
        Returns: {'imminent': bool, 'event': dict or None}
        """
        for event in self.news_events:
            time_diff = (event['time'] - current_time).total_seconds() / 60

            # Check if news is within the window
            if -5 <= time_diff <= minutes_before and event['impact'] == 'high':
                return {'imminent': True, 'event': event, 'minutes_away': time_diff}

        return {'imminent': False, 'event': None}

    def should_avoid_trading(self, current_time: datetime) -> bool:
        """
        Avoid trading during high-impact news (30 min before, 15 min after).
        """
        for event in self.news_events:
            time_diff = (current_time - event['time']).total_seconds() / 60

            # Avoid 30 min before and 15 min after
            if -30 <= time_diff <= 15 and event['impact'] == 'high':
                return True

        return False

    def calculate_sniper_score(self, df: pd.DataFrame, current_time: datetime) -> float:
        """
        Calculate overall "sniper opportunity" score (0-100).
        Higher score = better opportunity.
        """
        score = 0

        # 1. Compression (40 points)
        if self.detect_compression(df):
            score += 40

        # 2. Breakout (30 points)
        breakout = self.detect_breakout(df)
        if breakout['signal'] != 0:
            score += 30 * breakout['strength']

        # 3. News proximity (30 points)
        news_check = self.is_news_imminent(current_time, minutes_before=15)
        if news_check['imminent']:
            # Trade right before news can be risky but profitable
            score += 30

        return score

    def get_sniper_signal(self, df: pd.DataFrame, current_time: datetime) -> Dict:
        """
        Main function: Get sniper trading signal.
        Returns: {'should_trade': bool, 'signal': 1/-1/0, 'confidence': 0-1, 'reason': str}
        """
        # Check if we should avoid
        if self.should_avoid_trading(current_time):
            return {
                'should_trade': False,
                'signal': 0,
                'confidence': 0,
                'reason': 'News event too close - avoiding'
            }

        # Calculate score
        score = self.calculate_sniper_score(df, current_time)

        # Get breakout signal
        breakout = self.detect_breakout(df)

        # Decision
        if score >= 60 and breakout['signal'] != 0:
            return {
                'should_trade': True,
                'signal': breakout['signal'],
                'confidence': score / 100,
                'reason': f"Sniper opportunity detected: {breakout['type']}"
            }

        return {
            'should_trade': False,
            'signal': 0,
            'confidence': score / 100,
            'reason': f"Score too low: {score}/100"
        }
