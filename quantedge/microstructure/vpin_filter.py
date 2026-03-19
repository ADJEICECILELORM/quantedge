# microstructure/vpin_filter.py - VPIN (Volume-Synchronized Probability of Informed Trading)
"""
VPIN: Toxicity Filter for Detecting Informed Trading.

What is VPIN?
- Measures order flow toxicity (insider/informed trading)
- When VPIN > 90th percentile → High toxicity → DON'T TRADE
- Prevents trading against informed traders who know more

How it works:
1. Classify volume into buy/sell based on price direction
2. Calculate imbalance in buckets
3. High imbalance = informed trading = toxic

Reference: Easley, Lopez de Prado, O'Hara (2011)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List
from collections import deque

logger = logging.getLogger(__name__)


class VPINFilter:
    """
    VPIN (Volume-Synchronized Probability of Informed Trading).

    Blocks trades when order flow toxicity is high (insider trading detected).
    """

    def __init__(
        self,
        bucket_size: int = 50,           # Volume per bucket
        num_buckets: int = 50,           # Number of buckets for VPIN calculation
        toxicity_threshold_pct: float = 90.0,  # Block if VPIN > 90th percentile
        lookback: int = 100              # Historical lookback for percentiles
    ):
        self.bucket_size = bucket_size
        self.num_buckets = num_buckets
        self.toxicity_threshold_pct = toxicity_threshold_pct
        self.lookback = lookback

        # Historical VPIN values for percentile calculation
        self.vpin_history = deque(maxlen=lookback)

        # Current volume bucket accumulator
        self.current_bucket = {
            'buy_volume': 0,
            'sell_volume': 0,
            'total_volume': 0
        }

        # Completed buckets
        self.buckets = deque(maxlen=num_buckets)

    def update_volume(
        self,
        df: pd.DataFrame,
        tick_rule: str = 'price_change'
    ):
        """
        Update volume buckets from OHLCV data.

        Args:
            df: DataFrame with OHLCV data
            tick_rule: How to classify buy/sell ('price_change' or 'tick')
        """
        try:
            if len(df) < 2:
                return

            # Classify volume into buy/sell
            if tick_rule == 'price_change':
                # Price increase = buy, decrease = sell
                price_changes = df['close'].diff()

                for i in range(1, len(df)):
                    volume = df['tick_volume'].iloc[i]
                    price_change = price_changes.iloc[i]

                    if price_change > 0:
                        # Uptick = buy
                        self._add_volume(volume, direction='buy')
                    elif price_change < 0:
                        # Downtick = sell
                        self._add_volume(volume, direction='sell')
                    else:
                        # No change = split evenly
                        self._add_volume(volume / 2, direction='buy')
                        self._add_volume(volume / 2, direction='sell')

        except Exception as e:
            logger.error(f"Error updating VPIN volume: {e}")

    def _add_volume(self, volume: float, direction: str):
        """Add volume to current bucket"""
        if direction == 'buy':
            self.current_bucket['buy_volume'] += volume
        else:
            self.current_bucket['sell_volume'] += volume

        self.current_bucket['total_volume'] += volume

        # Check if bucket is full
        if self.current_bucket['total_volume'] >= self.bucket_size:
            # Save bucket
            self.buckets.append({
                'buy_volume': self.current_bucket['buy_volume'],
                'sell_volume': self.current_bucket['sell_volume'],
                'total_volume': self.current_bucket['total_volume']
            })

            # Reset current bucket
            self.current_bucket = {
                'buy_volume': 0,
                'sell_volume': 0,
                'total_volume': 0
            }

    def calculate_vpin(self) -> float:
        """
        Calculate current VPIN value.

        VPIN = (1 / n) * Σ |V_buy - V_sell| / V_total

        Returns:
            VPIN value (0-1), higher = more toxic
        """
        try:
            if len(self.buckets) < self.num_buckets:
                logger.warning(f"Insufficient buckets for VPIN: {len(self.buckets)}/{self.num_buckets}")
                return 0.5  # Default neutral

            # Calculate order imbalance for each bucket
            imbalances = []
            for bucket in list(self.buckets)[-self.num_buckets:]:
                buy_vol = bucket['buy_volume']
                sell_vol = bucket['sell_volume']
                total_vol = bucket['total_volume']

                if total_vol > 0:
                    imbalance = abs(buy_vol - sell_vol) / total_vol
                    imbalances.append(imbalance)

            # VPIN = average imbalance
            vpin = np.mean(imbalances) if imbalances else 0.5

            # Store in history
            self.vpin_history.append(vpin)

            return min(1.0, max(0.0, vpin))

        except Exception as e:
            logger.error(f"Error calculating VPIN: {e}")
            return 0.5

    def get_vpin_percentile(self, vpin: float) -> float:
        """
        Get percentile of current VPIN relative to history.

        Args:
            vpin: Current VPIN value

        Returns:
            Percentile (0-100)
        """
        if len(self.vpin_history) < 10:
            return 50.0  # Not enough history

        # Calculate percentile
        below = sum(1 for v in self.vpin_history if v < vpin)
        percentile = (below / len(self.vpin_history)) * 100

        return percentile

    def is_toxic(
        self,
        vpin: Optional[float] = None,
        threshold_percentile: Optional[float] = None
    ) -> bool:
        """
        Check if order flow is toxic (should avoid trading).

        Args:
            vpin: VPIN value (if None, calculates current)
            threshold_percentile: Percentile threshold (if None, uses default)

        Returns:
            True if toxic (don't trade)
        """
        if vpin is None:
            vpin = self.calculate_vpin()

        threshold = threshold_percentile or self.toxicity_threshold_pct
        percentile = self.get_vpin_percentile(vpin)

        return percentile >= threshold

    def should_block_trade(
        self,
        df: pd.DataFrame,
        update: bool = True
    ) -> Dict:
        """
        Main decision function: should we block this trade?

        Args:
            df: Latest OHLCV data
            update: Whether to update volume buckets first

        Returns:
            Dict with decision and details
        """
        # Input validation
        if df is None or not isinstance(df, pd.DataFrame):
            logger.error(f"Invalid DataFrame provided: {type(df)}")
            return {
                'should_block': True,  # Conservative: block on invalid input
                'vpin': 0.5,
                'reason': "Invalid input data"
            }

        if df.empty or len(df) < 1:
            logger.warning("Empty DataFrame provided to VPIN filter")
            return {
                'should_block': True,
                'vpin': 0.5,
                'reason': "No data available"
            }

        required_columns = ['close', 'tick_volume']
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return {
                'should_block': True,
                'vpin': 0.5,
                'reason': f"Missing data columns: {missing_cols}"
            }

        try:
            # Update volume if requested
            if update:
                self.update_volume(df)

            # Calculate VPIN
            vpin = self.calculate_vpin()
            percentile = self.get_vpin_percentile(vpin)
            is_toxic = self.is_toxic(vpin)

            # Get toxicity level
            if percentile >= 95:
                toxicity_level = "CRITICAL"
            elif percentile >= 90:
                toxicity_level = "HIGH"
            elif percentile >= 75:
                toxicity_level = "MEDIUM"
            elif percentile >= 50:
                toxicity_level = "LOW"
            else:
                toxicity_level = "VERY LOW"

            return {
                'should_block': is_toxic,
                'vpin': vpin,
                'vpin_percentile': percentile,
                'toxicity_level': toxicity_level,
                'reason': f"VPIN at {percentile:.1f} percentile ({toxicity_level})" if is_toxic else "Order flow clean",
                'recommendation': "BLOCK TRADE - Informed trading detected" if is_toxic else "Safe to trade"
            }

        except Exception as e:
            logger.error(f"Error in VPIN block decision: {e}")
            return {
                'should_block': True,  # Conservative: block on error
                'vpin': 0.5,
                'reason': f"Error: {e}"
            }

    def get_stats(self) -> Dict:
        """Get VPIN filter statistics"""
        current_vpin = self.calculate_vpin()
        percentile = self.get_vpin_percentile(current_vpin)

        return {
            'current_vpin': current_vpin,
            'vpin_percentile': percentile,
            'buckets_filled': len(self.buckets),
            'buckets_required': self.num_buckets,
            'history_size': len(self.vpin_history),
            'is_toxic': self.is_toxic(current_vpin),
            'avg_vpin': np.mean(list(self.vpin_history)) if self.vpin_history else 0.5,
            'max_vpin': max(self.vpin_history) if self.vpin_history else 0.5,
            'min_vpin': min(self.vpin_history) if self.vpin_history else 0.5
        }

    def print_status(self):
        """Print VPIN status"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("🔬 VPIN TOXICITY FILTER STATUS")
        print("="*60)
        print(f"Current VPIN: {stats['current_vpin']:.4f} ({stats['vpin_percentile']:.1f} percentile)")
        print(f"Toxic: {'❌ YES - BLOCK TRADES' if stats['is_toxic'] else '✅ NO - SAFE TO TRADE'}")
        print(f"Buckets: {stats['buckets_filled']}/{stats['buckets_required']}")
        print(f"History: {stats['history_size']} samples")
        print(f"Range: {stats['min_vpin']:.4f} - {stats['max_vpin']:.4f} (avg: {stats['avg_vpin']:.4f})")
        print("="*60 + "\n")

    def reset(self):
        """Reset VPIN filter"""
        self.vpin_history.clear()
        self.buckets.clear()
        self.current_bucket = {
            'buy_volume': 0,
            'sell_volume': 0,
            'total_volume': 0
        }
        logger.info("VPIN filter reset")


class SimplifiedVPIN:
    """
    Simplified VPIN for when we don't have tick-by-tick data.

    Uses bar-by-bar volume imbalance instead.
    Less accurate but works with OHLCV bars.
    """

    def __init__(self, lookback: int = 50):
        self.lookback = lookback
        self.vpin_history = deque(maxlen=lookback)

    def calculate_from_bars(self, df: pd.DataFrame) -> float:
        """
        Calculate simplified VPIN from OHLCV bars.

        Uses volume-weighted price direction.
        """
        try:
            if len(df) < 20:
                return 0.5

            # Calculate volume imbalance per bar
            price_changes = df['close'].diff()
            volumes = df['tick_volume']

            # Buy volume = volume when price up
            buy_volume = volumes[price_changes > 0].sum()
            sell_volume = volumes[price_changes < 0].sum()
            total_volume = volumes.sum()

            if total_volume > 0:
                vpin = abs(buy_volume - sell_volume) / total_volume
            else:
                vpin = 0.5

            self.vpin_history.append(vpin)

            return min(1.0, max(0.0, vpin))

        except Exception as e:
            logger.error(f"Error calculating simplified VPIN: {e}")
            return 0.5

    def is_toxic(self, df: pd.DataFrame, threshold: float = 0.7) -> bool:
        """Check if toxic using simplified method"""
        vpin = self.calculate_from_bars(df)
        return vpin > threshold
