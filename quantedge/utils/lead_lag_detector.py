# utils/lead_lag_detector.py - Lead-Lag Market Detection System
"""
Detects lead-lag relationships between assets using cross-correlation analysis.
Examples:
- S&P 500 futures often lead EURUSD
- BTC often leads ETH
- Gold futures lead spot gold
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import MetaTrader5 as mt5


class LeadLagDetector:
    """
    Analyzes cross-correlation between asset pairs to identify leading/lagging relationships.
    """

    def __init__(self, max_lag_periods: int = 20, lookback_periods: int = 200):
        """
        Args:
            max_lag_periods: Maximum number of periods to check for lag
            lookback_periods: Number of historical periods to use for analysis
        """
        self.max_lag_periods = max_lag_periods
        self.lookback_periods = lookback_periods

        # Cache of lead-lag relationships
        self.relationships = {}  # {(leader, follower): {'lag': int, 'correlation': float, 'last_update': datetime}}

        # Pre-defined common relationships (based on market knowledge)
        self.known_pairs = [
            # (leader, follower)
            ('BTCUSD', 'ETHUSD'),       # BTC leads ETH
            ('XAUUSD', 'EURUSD'),       # Gold affects EUR
            ('EURUSD', 'GBPUSD'),       # EUR leads GBP (sometimes)
        ]

    def calculate_returns(self, prices: pd.Series) -> pd.Series:
        """Calculate log returns"""
        return np.log(prices / prices.shift(1)).dropna()

    def calculate_cross_correlation(self, series1: pd.Series, series2: pd.Series,
                                    max_lag: int) -> Tuple[int, float]:
        """
        Calculate cross-correlation between two series at different lags.

        Returns:
            (optimal_lag, max_correlation)
            - positive lag means series1 leads series2
            - negative lag means series2 leads series1
        """
        if len(series1) != len(series2) or len(series1) < 50:
            return (0, 0.0)

        # Ensure same length and no NaN
        series1 = series1.dropna()
        series2 = series2.dropna()

        # Align indices
        common_index = series1.index.intersection(series2.index)
        series1 = series1.loc[common_index]
        series2 = series2.loc[common_index]

        if len(series1) < 50:
            return (0, 0.0)

        correlations = []
        lags = range(-max_lag, max_lag + 1)

        for lag in lags:
            if lag == 0:
                corr = series1.corr(series2)
            elif lag > 0:
                # Positive lag: series1 leads series2
                corr = series1.iloc[:-lag].corr(series2.iloc[lag:])
            else:
                # Negative lag: series2 leads series1
                corr = series1.iloc[-lag:].corr(series2.iloc[:lag])

            correlations.append(abs(corr) if not np.isnan(corr) else 0)

        # Find lag with maximum correlation
        max_corr_idx = np.argmax(correlations)
        optimal_lag = lags[max_corr_idx]
        max_correlation = correlations[max_corr_idx]

        return (optimal_lag, max_correlation)

    def detect_lead_lag(self, df1: pd.DataFrame, df2: pd.DataFrame,
                       symbol1: str, symbol2: str) -> Dict:
        """
        Detect lead-lag relationship between two assets.

        Args:
            df1, df2: DataFrames with OHLCV data
            symbol1, symbol2: Asset symbols

        Returns:
        {
            'leader': str,
            'follower': str,
            'lag_periods': int,
            'correlation': float,
            'strength': str ('strong', 'moderate', 'weak'),
            'confidence': float (0-1)
        }
        """
        if df1 is None or df2 is None or len(df1) < 50 or len(df2) < 50:
            return self._no_relationship(symbol1, symbol2)

        # Calculate returns
        returns1 = self.calculate_returns(df1['close'])
        returns2 = self.calculate_returns(df2['close'])

        # Calculate cross-correlation
        optimal_lag, max_correlation = self.calculate_cross_correlation(
            returns1, returns2, self.max_lag_periods
        )

        # Determine leader and follower
        if optimal_lag > 0:
            leader = symbol1
            follower = symbol2
            lag_periods = optimal_lag
        elif optimal_lag < 0:
            leader = symbol2
            follower = symbol1
            lag_periods = abs(optimal_lag)
        else:
            # No clear lead-lag (simultaneous)
            return {
                'leader': None,
                'follower': None,
                'lag_periods': 0,
                'correlation': max_correlation,
                'strength': 'simultaneous',
                'confidence': max_correlation
            }

        # Determine strength
        if max_correlation >= 0.7:
            strength = 'strong'
        elif max_correlation >= 0.5:
            strength = 'moderate'
        else:
            strength = 'weak'

        return {
            'leader': leader,
            'follower': follower,
            'lag_periods': lag_periods,
            'correlation': max_correlation,
            'strength': strength,
            'confidence': max_correlation
        }

    def _no_relationship(self, symbol1: str, symbol2: str) -> Dict:
        """Return structure for no relationship"""
        return {
            'leader': None,
            'follower': None,
            'lag_periods': 0,
            'correlation': 0.0,
            'strength': 'none',
            'confidence': 0.0
        }

    def get_leading_signal(self, leader_df: pd.DataFrame, follower_symbol: str,
                          lag_periods: int) -> Optional[Dict]:
        """
        Generate predictive signal for follower based on leader's recent movement.

        Args:
            leader_df: Recent price data for the leading asset
            follower_symbol: Symbol of the follower asset
            lag_periods: Number of periods the leader is ahead

        Returns:
        {
            'signal': 1/-1/0,
            'confidence': float,
            'reason': str
        }
        """
        if leader_df is None or len(leader_df) < lag_periods + 5:
            return None

        # Get leader's recent movement
        recent_returns = self.calculate_returns(leader_df['close'])

        if len(recent_returns) < lag_periods:
            return None

        # Look at leader's movement over the lag period
        lag_return = recent_returns.iloc[-lag_periods:].sum()

        # Threshold for signal generation (0.5% movement)
        threshold = 0.005

        if lag_return > threshold:
            return {
                'signal': 1,  # Expect follower to go up
                'confidence': min(1.0, abs(lag_return) / (threshold * 3)),
                'reason': f'Leader moved +{lag_return*100:.2f}% over {lag_periods} periods'
            }
        elif lag_return < -threshold:
            return {
                'signal': -1,  # Expect follower to go down
                'confidence': min(1.0, abs(lag_return) / (threshold * 3)),
                'reason': f'Leader moved {lag_return*100:.2f}% over {lag_periods} periods'
            }
        else:
            return {
                'signal': 0,
                'confidence': 0.0,
                'reason': 'No significant movement in leader'
            }

    def update_relationships(self, mt5_connector, symbols: List[str]) -> Dict[str, Dict]:
        """
        Update lead-lag relationships for all symbol pairs.

        Args:
            mt5_connector: MT5Connector instance
            symbols: List of symbols to analyze

        Returns:
            Dictionary of relationships: {(leader, follower): relationship_info}
        """
        print(f"\n{'='*60}")
        print("🔗 UPDATING LEAD-LAG RELATIONSHIPS")
        print(f"{'='*60}")

        timeframe = mt5.TIMEFRAME_M5
        updated = 0

        # Analyze all pairs
        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i+1:]:
                # Fetch data
                df1 = mt5_connector.get_latest_bars(symbol1, timeframe, self.lookback_periods)
                df2 = mt5_connector.get_latest_bars(symbol2, timeframe, self.lookback_periods)

                if df1 is None or df2 is None:
                    continue

                # Detect relationship
                relationship = self.detect_lead_lag(df1, df2, symbol1, symbol2)

                if relationship['leader'] is not None:
                    key = (relationship['leader'], relationship['follower'])
                    self.relationships[key] = {
                        **relationship,
                        'last_update': datetime.now()
                    }

                    print(f"✅ {relationship['leader']} leads {relationship['follower']} "
                          f"by {relationship['lag_periods']} periods "
                          f"(corr: {relationship['correlation']:.2f}, {relationship['strength']})")

                    updated += 1

        print(f"{'='*60}")
        print(f"✅ Updated {updated} lead-lag relationships")
        print(f"{'='*60}\n")

        return self.relationships

    def get_lead_lag_score(self, symbol: str, mt5_connector) -> Dict:
        """
        Get lead-lag predictive score for a symbol.

        Args:
            symbol: Symbol to analyze
            mt5_connector: MT5Connector instance

        Returns:
        {
            'has_leading_signal': bool,
            'signal': 1/-1/0,
            'confidence': float,
            'leader': str or None,
            'reason': str
        }
        """
        # Check if this symbol is a follower in any relationship
        for (leader, follower), rel_info in self.relationships.items():
            if follower == symbol and rel_info['confidence'] >= 0.5:
                # Get leader's data
                leader_df = mt5_connector.get_latest_bars(
                    leader,
                    mt5.TIMEFRAME_M5,
                    self.lookback_periods
                )

                if leader_df is not None:
                    # Generate signal based on leader
                    signal_info = self.get_leading_signal(
                        leader_df,
                        follower,
                        rel_info['lag_periods']
                    )

                    if signal_info and signal_info['signal'] != 0:
                        return {
                            'has_leading_signal': True,
                            'signal': signal_info['signal'],
                            'confidence': signal_info['confidence'] * rel_info['confidence'],
                            'leader': leader,
                            'lag_periods': rel_info['lag_periods'],
                            'reason': f"{leader} (leads by {rel_info['lag_periods']}): {signal_info['reason']}"
                        }

        return {
            'has_leading_signal': False,
            'signal': 0,
            'confidence': 0.0,
            'leader': None,
            'reason': 'No leading signal detected'
        }

    def print_relationships_summary(self):
        """Print summary of detected relationships"""
        if not self.relationships:
            print("No lead-lag relationships detected yet")
            return

        print(f"\n{'='*60}")
        print("🔗 LEAD-LAG RELATIONSHIPS SUMMARY")
        print(f"{'='*60}")

        for (leader, follower), info in self.relationships.items():
            print(f"📊 {leader} → {follower}")
            print(f"   Lag: {info['lag_periods']} periods")
            print(f"   Correlation: {info['correlation']:.3f}")
            print(f"   Strength: {info['strength'].upper()}")
            print(f"   Last Updated: {info['last_update'].strftime('%Y-%m-%d %H:%M')}")
            print()

        print(f"{'='*60}\n")

    def get_confidence_multiplier(self, lead_lag_score: Dict) -> float:
        """
        Get confidence multiplier based on lead-lag signal.

        Returns:
            Multiplier (0.8 - 1.3)
            - 1.0 = no effect
            - >1.0 = boost confidence (leading signal agrees)
            - <1.0 = reduce confidence (leading signal disagrees or weak)
        """
        if not lead_lag_score['has_leading_signal']:
            return 1.0

        # Strong leading signal boosts confidence
        if lead_lag_score['confidence'] >= 0.7:
            return 1.3
        elif lead_lag_score['confidence'] >= 0.5:
            return 1.15
        elif lead_lag_score['confidence'] >= 0.3:
            return 1.05
        else:
            return 1.0

    def should_boost_signal(self, symbol: str, ml_signal: int,
                           lead_lag_score: Dict) -> Tuple[bool, float]:
        """
        Determine if lead-lag analysis agrees with ML signal.

        Args:
            symbol: Trading symbol
            ml_signal: ML model signal (1/-1/0)
            lead_lag_score: Lead-lag score from get_lead_lag_score()

        Returns:
            (should_boost, multiplier)
        """
        if not lead_lag_score['has_leading_signal']:
            return (False, 1.0)

        lead_signal = lead_lag_score['signal']

        # Check agreement
        if ml_signal == lead_signal:
            # Signals agree - boost confidence
            multiplier = self.get_confidence_multiplier(lead_lag_score)
            return (True, multiplier)
        elif ml_signal == -lead_signal:
            # Signals disagree - reduce confidence
            return (False, 0.85)
        else:
            # Neutral
            return (False, 1.0)
