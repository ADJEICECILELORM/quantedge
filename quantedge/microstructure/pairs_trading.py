# microstructure/pairs_trading.py - Pairs Trading for Delta-Neutral Hedging
"""
Pairs Trading: Delta-Neutral Hedging Strategy.

Concept:
Trade two correlated assets simultaneously to neutralize market risk.

Example:
- Long Gold / Short Bitcoin
- For medium-confidence news
- Neutralizes USD exposure
- Profits from spread movement

Use Case:
When news confidence is medium (50-70%), use pairs trading
to reduce directional risk while still capturing alpha.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PairCandidate:
    """Pair trading candidate"""
    symbol_a: str
    symbol_b: str
    correlation: float
    hedge_ratio: float           # Units of B per unit of A
    spread_mean: float
    spread_std: float
    z_score: float              # Current spread z-score
    confidence: float


class PairsTradingStrategy:
    """
    Pairs trading for delta-neutral hedging.

    Strategy:
    1. Find correlated pairs (correlation > 0.7)
    2. Calculate hedge ratio (beta)
    3. Monitor spread (price_A - beta * price_B)
    4. Trade when spread deviates from mean
    """

    def __init__(
        self,
        min_correlation: float = 0.7,
        entry_z_score: float = 2.0,      # Enter when |z| > 2
        exit_z_score: float = 0.5,       # Exit when |z| < 0.5
        lookback_bars: int = 200
    ):
        self.min_correlation = min_correlation
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.lookback_bars = lookback_bars

        # Store active pairs
        self.active_pairs: Dict[Tuple[str, str], PairCandidate] = {}

    def find_pairs(
        self,
        mt5_connector,
        symbols: List[str]
    ) -> List[PairCandidate]:
        """
        Find valid trading pairs from symbol list.

        Args:
            mt5_connector: MT5 connector
            symbols: List of symbols to analyze

        Returns:
            List of valid pair candidates
        """
        candidates = []

        logger.info(f"Searching for pairs among {len(symbols)} symbols...")

        # Test all combinations
        for i, symbol_a in enumerate(symbols):
            for symbol_b in symbols[i+1:]:
                try:
                    pair = self._analyze_pair(mt5_connector, symbol_a, symbol_b)
                    if pair and abs(pair.correlation) >= self.min_correlation:
                        candidates.append(pair)
                        logger.info(f"Found pair: {symbol_a}/{symbol_b} "
                                   f"(corr={pair.correlation:.3f}, z={pair.z_score:.2f})")

                except Exception as e:
                    logger.error(f"Error analyzing {symbol_a}/{symbol_b}: {e}")

        # Sort by trading opportunity (high z-score + high correlation)
        candidates.sort(
            key=lambda p: abs(p.z_score) * abs(p.correlation) * p.confidence,
            reverse=True
        )

        logger.info(f"Found {len(candidates)} valid pairs")

        return candidates

    def _analyze_pair(
        self,
        mt5_connector,
        symbol_a: str,
        symbol_b: str
    ) -> Optional[PairCandidate]:
        """Analyze if two symbols make a good pair"""
        try:
            # Get historical data
            df_a = mt5_connector.get_latest_bars(symbol_a, mt5.TIMEFRAME_M5, count=self.lookback_bars)
            df_b = mt5_connector.get_latest_bars(symbol_b, mt5.TIMEFRAME_M5, count=self.lookback_bars)

            if df_a is None or df_b is None:
                return None

            if len(df_a) < 100 or len(df_b) < 100:
                return None

            # Align data
            min_len = min(len(df_a), len(df_b))
            prices_a = df_a['close'].iloc[-min_len:].values
            prices_b = df_b['close'].iloc[-min_len:].values

            # Calculate correlation
            correlation = np.corrcoef(prices_a, prices_b)[0, 1]

            if abs(correlation) < self.min_correlation:
                return None

            # Calculate hedge ratio (beta)
            # Using linear regression: price_a = alpha + beta * price_b
            beta = np.cov(prices_a, prices_b)[0, 1] / np.var(prices_b)

            # Calculate spread
            spread = prices_a - beta * prices_b

            # Spread statistics
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)

            # Current spread z-score
            current_spread = spread[-1]
            z_score = (current_spread - spread_mean) / spread_std if spread_std > 0 else 0

            # Confidence (based on correlation strength and spread stationarity)
            # Higher correlation + lower spread std = higher confidence
            corr_conf = abs(correlation)
            spread_conf = 1.0 / (1.0 + spread_std / abs(spread_mean)) if spread_mean != 0 else 0.5
            confidence = (corr_conf * 0.7 + spread_conf * 0.3)

            return PairCandidate(
                symbol_a=symbol_a,
                symbol_b=symbol_b,
                correlation=correlation,
                hedge_ratio=beta,
                spread_mean=spread_mean,
                spread_std=spread_std,
                z_score=z_score,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"Error in pair analysis: {e}")
            return None

    def get_trade_signal(
        self,
        pair: PairCandidate
    ) -> Dict:
        """
        Get trading signal for a pair.

        Args:
            pair: Pair candidate

        Returns:
            Dict with trade signal
        """
        z = pair.z_score

        # Entry signals
        if abs(z) >= self.entry_z_score:
            if z > 0:
                # Spread too high → short spread
                # Short A, Long B
                signal = {
                    'action': 'ENTER',
                    'position_a': 'SELL',
                    'position_b': 'BUY',
                    'hedge_ratio': pair.hedge_ratio,
                    'z_score': z,
                    'confidence': pair.confidence,
                    'reason': f"Spread {z:.2f} std above mean → Short {pair.symbol_a}, Long {pair.symbol_b}"
                }
            else:
                # Spread too low → long spread
                # Long A, Short B
                signal = {
                    'action': 'ENTER',
                    'position_a': 'BUY',
                    'position_b': 'SELL',
                    'hedge_ratio': pair.hedge_ratio,
                    'z_score': z,
                    'confidence': pair.confidence,
                    'reason': f"Spread {z:.2f} std below mean → Long {pair.symbol_a}, Short {pair.symbol_b}"
                }

            return signal

        # Exit signals
        elif abs(z) <= self.exit_z_score:
            signal = {
                'action': 'EXIT',
                'z_score': z,
                'reason': f"Spread reverted to mean (z={z:.2f})"
            }
            return signal

        # Hold
        else:
            signal = {
                'action': 'HOLD',
                'z_score': z,
                'reason': f"Spread at z={z:.2f}, waiting for entry/exit threshold"
            }
            return signal

    def calculate_position_sizes(
        self,
        pair: PairCandidate,
        risk_amount: float,
        price_a: float,
        price_b: float
    ) -> Dict:
        """
        Calculate position sizes for delta-neutral hedge.

        Args:
            pair: Pair candidate
            risk_amount: Dollar amount to risk
            price_a: Current price of asset A
            price_b: Current price of asset B

        Returns:
            Dict with lot sizes
        """
        try:
            # Hedge ratio tells us units of B per unit of A
            # For delta neutrality: value_a = hedge_ratio * value_b

            # Allocate risk equally to both sides
            risk_per_side = risk_amount / 2

            # Calculate units
            units_a = risk_per_side / price_a
            units_b = units_a * pair.hedge_ratio

            # Value check (should be approximately equal)
            value_a = units_a * price_a
            value_b = units_b * price_b

            return {
                'symbol_a': pair.symbol_a,
                'symbol_b': pair.symbol_b,
                'units_a': units_a,
                'units_b': units_b,
                'value_a': value_a,
                'value_b': value_b,
                'hedge_ratio': pair.hedge_ratio,
                'delta_neutral': abs(value_a - value_b) < (risk_amount * 0.1)  # Within 10%
            }

        except Exception as e:
            logger.error(f"Error calculating position sizes: {e}")
            return {}

    def get_pairs_for_news(
        self,
        news_confidence: float,
        news_direction: int,
        available_pairs: List[PairCandidate]
    ) -> Optional[PairCandidate]:
        """
        Select best pair for news-driven trade.

        Args:
            news_confidence: News confidence (0-1)
            news_direction: Trade direction (1=long, -1=short)
            available_pairs: List of available pairs

        Returns:
            Best pair for this news, or None
        """
        # Pairs trading works best for medium confidence (50-70%)
        # High confidence → directional trade
        # Low confidence → skip
        if news_confidence < 0.4 or news_confidence > 0.8:
            return None

        if not available_pairs:
            return None

        # Filter pairs with good z-scores
        tradeable_pairs = [
            p for p in available_pairs
            if abs(p.z_score) >= self.entry_z_score
        ]

        if not tradeable_pairs:
            return None

        # Select best pair (highest confidence * correlation)
        best_pair = max(tradeable_pairs, key=lambda p: p.confidence * abs(p.correlation))

        return best_pair

    def print_pairs(self, pairs: List[PairCandidate]):
        """Print pairs analysis"""
        if not pairs:
            print("\n📊 No valid pairs found")
            return

        print("\n" + "="*100)
        print("🔗 PAIRS TRADING CANDIDATES")
        print("="*100)
        print(f"{'Pair':<25} {'Correlation':<13} {'Hedge Ratio':<13} {'Z-Score':<10} {'Confidence':<12} {'Signal':<10}")
        print("-"*100)

        for pair in pairs[:10]:  # Top 10
            signal = 'ENTER' if abs(pair.z_score) >= self.entry_z_score else 'HOLD'
            print(f"{pair.symbol_a}/{pair.symbol_b:<20} {pair.correlation:>+.3f}        "
                  f"{pair.hedge_ratio:>8.4f}       {pair.z_score:>+6.2f}     "
                  f"{pair.confidence:>6.3f}       {signal:<10}")

        print("="*100 + "\n")

    def get_stats(self) -> Dict:
        """Get pairs trading statistics"""
        return {
            'active_pairs': len(self.active_pairs),
            'min_correlation': self.min_correlation,
            'entry_z_score': self.entry_z_score,
            'exit_z_score': self.exit_z_score
        }


# Import mt5 for timeframe
import MetaTrader5 as mt5
