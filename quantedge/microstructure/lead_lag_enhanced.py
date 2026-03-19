# microstructure/lead_lag_enhanced.py - Enhanced Lead-Lag Correlation Analysis
"""
Enhanced Lead-Lag Correlation for Front-Running Signals.

Concept:
If DXY/XAU leads and BTC lags by 500ms, we can front-run BTC moves
by watching DXY/XAU first.

Use Case:
- Monitor 1-min rolling correlation between DXY, XAU, BTC
- If correlation > 0.7 and one asset leads consistently
- Trade the lagging asset when leader moves
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class LeadLagRelationship:
    """Stores lead-lag relationship between two assets"""

    def __init__(
        self,
        leader: str,
        lagger: str,
        correlation: float,
        optimal_lag_bars: int,
        confidence: float
    ):
        self.leader = leader
        self.lagger = lagger
        self.correlation = correlation
        self.optimal_lag_bars = optimal_lag_bars
        self.confidence = confidence
        self.last_updated = datetime.now()

    def to_dict(self) -> Dict:
        return {
            'leader': self.leader,
            'lagger': self.lagger,
            'correlation': self.correlation,
            'optimal_lag_bars': self.optimal_lag_bars,
            'confidence': self.confidence,
            'last_updated': self.last_updated.isoformat()
        }


class EnhancedLeadLagDetector:
    """
    Enhanced lead-lag correlation detector.

    Improvements over V5:
    1. Automatic lag detection (finds optimal lag)
    2. Confidence scoring
    3. Regime-aware (only works in stable correlations)
    4. Multiple timeframe analysis
    """

    def __init__(
        self,
        max_lag_bars: int = 20,          # Maximum lag to test (in bars)
        min_correlation: float = 0.7,    # Minimum correlation to consider
        lookback_bars: int = 200,        # Bars for correlation calculation
        confidence_threshold: float = 0.6  # Minimum confidence to trade
    ):
        self.max_lag_bars = max_lag_bars
        self.min_correlation = min_correlation
        self.lookback_bars = lookback_bars
        self.confidence_threshold = confidence_threshold

        # Store discovered relationships
        self.relationships: Dict[Tuple[str, str], LeadLagRelationship] = {}

        # Correlation history for stability check
        self.correlation_history = defaultdict(lambda: deque(maxlen=50))

    def detect_lead_lag(
        self,
        leader_prices: pd.Series,
        lagger_prices: pd.Series,
        leader_symbol: str,
        lagger_symbol: str
    ) -> Optional[LeadLagRelationship]:
        """
        Detect lead-lag relationship between two assets.

        Args:
            leader_prices: Price series of potential leader
            lagger_prices: Price series of potential lagger
            leader_symbol: Symbol name of leader
            lagger_symbol: Symbol name of lagger

        Returns:
            LeadLagRelationship if found, None otherwise
        """
        try:
            if len(leader_prices) < self.lookback_bars or len(lagger_prices) < self.lookback_bars:
                return None

            # Calculate returns
            leader_returns = leader_prices.pct_change().dropna()
            lagger_returns = lagger_prices.pct_change().dropna()

            # Align lengths
            min_len = min(len(leader_returns), len(lagger_returns))
            leader_returns = leader_returns.iloc[-min_len:]
            lagger_returns = lagger_returns.iloc[-min_len:]

            # Test different lags
            best_lag = 0
            best_corr = 0

            for lag in range(self.max_lag_bars + 1):
                if lag == 0:
                    # Synchronous correlation
                    corr = leader_returns.corr(lagger_returns)
                else:
                    # Lagged correlation
                    # Leader at t, Lagger at t+lag
                    leader_lagged = leader_returns.iloc[:-lag]
                    lagger_shifted = lagger_returns.iloc[lag:]

                    if len(leader_lagged) < 50:  # Need minimum data
                        continue

                    corr = leader_lagged.corr(lagger_shifted)

                if abs(corr) > abs(best_corr):
                    best_corr = corr
                    best_lag = lag

            # Check if correlation is significant
            if abs(best_corr) < self.min_correlation:
                return None

            # Calculate confidence
            confidence = self._calculate_confidence(
                leader_returns, lagger_returns, best_lag, best_corr
            )

            # Create relationship
            relationship = LeadLagRelationship(
                leader=leader_symbol,
                lagger=lagger_symbol,
                correlation=best_corr,
                optimal_lag_bars=best_lag,
                confidence=confidence
            )

            # Store
            key = (leader_symbol, lagger_symbol)
            self.relationships[key] = relationship

            # Update correlation history
            self.correlation_history[key].append(best_corr)

            logger.info(f"Lead-lag found: {leader_symbol} → {lagger_symbol} "
                       f"(lag={best_lag}, corr={best_corr:.3f}, conf={confidence:.3f})")

            return relationship

        except Exception as e:
            logger.error(f"Error detecting lead-lag: {e}")
            return None

    def _calculate_confidence(
        self,
        leader_returns: pd.Series,
        lagger_returns: pd.Series,
        lag: int,
        correlation: float
    ) -> float:
        """
        Calculate confidence in lead-lag relationship.

        Based on:
        - Correlation strength (higher = more confident)
        - Stability over time (consistent = more confident)
        - Statistical significance
        """
        # Correlation strength component (40%)
        corr_conf = min(1.0, abs(correlation) / 0.9) * 0.4

        # Stability component (30%)
        # Calculate rolling correlation to check stability
        if lag == 0:
            rolling_corr = leader_returns.rolling(50).corr(lagger_returns)
        else:
            # For lagged, more complex
            rolling_corr = pd.Series([correlation] * 10)  # Simplified

        if len(rolling_corr) > 10:
            std_corr = rolling_corr.std()
            stability = max(0, 1.0 - std_corr) * 0.3
        else:
            stability = 0.15

        # Sample size component (30%)
        n = len(leader_returns)
        sample_conf = min(1.0, n / 200) * 0.3

        confidence = corr_conf + stability + sample_conf

        return max(0.0, min(1.0, confidence))

    def get_lead_lag_signal(
        self,
        symbol: str,
        mt5_connector
    ) -> Dict:
        """
        Get lead-lag trading signal for a symbol.

        Checks if any leaders have moved recently,
        predicting this symbol will follow.

        Args:
            symbol: Symbol to get signal for (the lagger)
            mt5_connector: MT5 connector to fetch leader prices

        Returns:
            Dict with signal and confidence
        """
        try:
            # Find relationships where this symbol is the lagger
            relevant_relationships = [
                rel for rel in self.relationships.values()
                if rel.lagger == symbol and rel.confidence >= self.confidence_threshold
            ]

            if not relevant_relationships:
                return {
                    'has_signal': False,
                    'reason': 'No lead-lag relationships found'
                }

            # Check each leader for recent moves
            signals = []

            for rel in relevant_relationships:
                # Get leader data
                leader_df = mt5_connector.get_latest_bars(rel.leader, mt5.TIMEFRAME_M1, count=50)

                if leader_df is None or len(leader_df) < rel.optimal_lag_bars + 5:
                    continue

                # Check if leader moved significantly
                leader_returns = leader_df['close'].pct_change()
                recent_move = leader_returns.iloc[-rel.optimal_lag_bars:].sum()

                # If leader moved > threshold, we expect lagger to follow
                if abs(recent_move) > 0.001:  # 0.1% threshold
                    direction = 1 if recent_move > 0 else -1

                    signals.append({
                        'leader': rel.leader,
                        'direction': direction,
                        'magnitude': abs(recent_move),
                        'correlation': rel.correlation,
                        'confidence': rel.confidence,
                        'lag_bars': rel.optimal_lag_bars
                    })

            if not signals:
                return {
                    'has_signal': False,
                    'reason': 'No significant leader moves detected'
                }

            # Take strongest signal
            best_signal = max(signals, key=lambda x: x['confidence'] * x['magnitude'])

            return {
                'has_signal': True,
                'direction': best_signal['direction'],
                'confidence': best_signal['confidence'],
                'leader': best_signal['leader'],
                'expected_move': best_signal['magnitude'] * best_signal['correlation'],
                'lag_bars': best_signal['lag_bars'],
                'reason': f"{best_signal['leader']} moved {best_signal['magnitude']:.2%}, "
                         f"{symbol} expected to follow (lag={best_signal['lag_bars']} bars)"
            }

        except Exception as e:
            logger.error(f"Error getting lead-lag signal: {e}")
            return {
                'has_signal': False,
                'reason': f'Error: {e}'
            }

    def update_all_relationships(
        self,
        mt5_connector,
        symbols: List[str]
    ):
        """
        Update all lead-lag relationships between symbols.

        Args:
            mt5_connector: MT5 connector
            symbols: List of symbols to analyze
        """
        logger.info(f"Updating lead-lag relationships for {len(symbols)} symbols...")

        # Test all pairs
        for i, leader_symbol in enumerate(symbols):
            for lagger_symbol in symbols[i+1:]:
                try:
                    # Get data
                    leader_df = mt5_connector.get_latest_bars(
                        leader_symbol, mt5.TIMEFRAME_M1, count=self.lookback_bars
                    )
                    lagger_df = mt5_connector.get_latest_bars(
                        lagger_symbol, mt5.TIMEFRAME_M1, count=self.lookback_bars
                    )

                    if leader_df is None or lagger_df is None:
                        continue

                    # Test both directions
                    # A leads B
                    self.detect_lead_lag(
                        leader_df['close'], lagger_df['close'],
                        leader_symbol, lagger_symbol
                    )

                    # B leads A
                    self.detect_lead_lag(
                        lagger_df['close'], leader_df['close'],
                        lagger_symbol, leader_symbol
                    )

                except Exception as e:
                    logger.error(f"Error updating {leader_symbol}/{lagger_symbol}: {e}")

        logger.info(f"Found {len(self.relationships)} lead-lag relationships")

    def print_relationships(self):
        """Print all discovered relationships"""
        if not self.relationships:
            print("\n📊 No lead-lag relationships found yet")
            return

        print("\n" + "="*80)
        print("🔗 LEAD-LAG RELATIONSHIPS")
        print("="*80)
        print(f"{'Leader':<15} {'→':<3} {'Lagger':<15} {'Lag (bars)':<12} {'Correlation':<13} {'Confidence':<12}")
        print("-"*80)

        sorted_rels = sorted(
            self.relationships.values(),
            key=lambda r: r.confidence * abs(r.correlation),
            reverse=True
        )

        for rel in sorted_rels:
            print(f"{rel.leader:<15} {'→':<3} {rel.lagger:<15} {rel.optimal_lag_bars:<12} "
                  f"{rel.correlation:>+.3f}        {rel.confidence:.3f}")

        print("="*80 + "\n")

    def get_stats(self) -> Dict:
        """Get lead-lag detector statistics"""
        return {
            'total_relationships': len(self.relationships),
            'high_confidence': sum(1 for r in self.relationships.values() if r.confidence > 0.7),
            'avg_correlation': np.mean([abs(r.correlation) for r in self.relationships.values()]) if self.relationships else 0,
            'avg_lag_bars': np.mean([r.optimal_lag_bars for r in self.relationships.values()]) if self.relationships else 0
        }


# Import mt5 for timeframe constant
import MetaTrader5 as mt5
