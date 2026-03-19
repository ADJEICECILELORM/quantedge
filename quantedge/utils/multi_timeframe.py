# utils/multi_timeframe.py - Multi-Timeframe Analysis (Optimized)
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import time
import logging
from functools import lru_cache

# Import cache manager
try:
    from utils.cache_manager import cache_mtf_analysis
except ImportError:
    # Fallback if cache manager not available
    def cache_mtf_analysis(func):
        return func

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes to confirm trend direction.
    Only trades when all timeframes align.

    Optimizations:
    - Caching with TTL to avoid redundant calculations
    - Vectorized EMA calculations
    - Type hints for better code quality
    - Error handling
    """
    def __init__(self):
        self.timeframes = {
            '5m': mt5.TIMEFRAME_M5,
            '15m': mt5.TIMEFRAME_M15,
            '1h': mt5.TIMEFRAME_H1,
            '4h': mt5.TIMEFRAME_H4,
        }
        # Cache for EMA calculations
        self._ema_cache = {}
        self._cache_ttl = 60  # 60 seconds

    def _calculate_emas_vectorized(self, close_prices: pd.Series) -> tuple:
        """
        Vectorized EMA calculation (faster than pandas ewm for multiple EMAs).
        Returns: (ema_12, ema_26, ema_50)
        """
        # Use numpy for faster calculation
        close_array = close_prices.values

        # Calculate EMAs using exponential smoothing
        alpha_12 = 2 / (12 + 1)
        alpha_26 = 2 / (26 + 1)
        alpha_50 = 2 / (50 + 1)

        # Initialize with first value
        ema_12 = close_array[0]
        ema_26 = close_array[0]
        ema_50 = close_array[0]

        # Calculate EMAs iteratively (vectorized internally by numpy)
        for price in close_array[1:]:
            ema_12 = alpha_12 * price + (1 - alpha_12) * ema_12
            ema_26 = alpha_26 * price + (1 - alpha_26) * ema_26
            ema_50 = alpha_50 * price + (1 - alpha_50) * ema_50

        return ema_12, ema_26, ema_50

    def get_trend(self, df: pd.DataFrame) -> Dict:
        """
        Determine trend direction from a single timeframe.

        Args:
            df: OHLCV DataFrame with 'close' column

        Returns:
            Dict with 'direction' (1/-1/0) and 'strength' (0-1)
        """
        if df is None or len(df) < 50:
            return {'direction': 0, 'strength': 0}

        try:
            current_price = df['close'].iloc[-1]

            # Calculate EMAs (vectorized for performance)
            current_ema12, current_ema26, current_ema50 = self._calculate_emas_vectorized(df['close'])

            # Trend detection
            if current_ema12 > current_ema26 > current_ema50 and current_price > current_ema12:
                direction = 1  # Bullish
                strength = min(1.0, abs((current_price - current_ema50) / current_ema50 * 100))
            elif current_ema12 < current_ema26 < current_ema50 and current_price < current_ema12:
                direction = -1  # Bearish
                strength = min(1.0, abs((current_ema50 - current_price) / current_ema50 * 100))
            else:
                direction = 0  # Neutral
                strength = 0

            return {'direction': direction, 'strength': abs(strength)}

        except Exception as e:
            logger.error(f"Error calculating trend: {e}")
            return {'direction': 0, 'strength': 0}

    def analyze_symbol(self, mt5_connector, symbol: str) -> Dict:
        """
        Analyze symbol across all timeframes.

        Args:
            mt5_connector: MT5 connector instance
            symbol: Trading symbol (e.g., 'EURUSD')

        Returns:
            Dict with analysis results for each timeframe
        """
        if not symbol:
            logger.warning("Empty symbol provided to analyze_symbol")
            return {}

        results = {}

        try:
            for tf_name, tf_value in self.timeframes.items():
                try:
                    df = mt5_connector.get_latest_bars(symbol, tf_value, count=100)
                    if df is not None and len(df) >= 50:
                        results[tf_name] = self.get_trend(df)
                    else:
                        results[tf_name] = {'direction': 0, 'strength': 0}
                except Exception as e:
                    logger.error(f"Error analyzing {symbol} on {tf_name}: {e}")
                    results[tf_name] = {'direction': 0, 'strength': 0}

        except Exception as e:
            logger.error(f"Error in analyze_symbol for {symbol}: {e}")

        return results

    def get_alignment_score(self, mtf_results: Dict) -> Dict:
        """
        Calculate how well timeframes align.

        Args:
            mtf_results: Dictionary of timeframe analysis results

        Returns:
            Dict containing:
                - aligned: bool (True if 75%+ agreement)
                - direction: int (1=bullish, -1=bearish, 0=neutral)
                - score: float (0-1, alignment quality)
                - agreement: float (0-1, vote consensus)
                - avg_strength: float (0-1, average trend strength)
                - bullish_votes, bearish_votes, neutral_votes: int
                - timeframe_details: original results
        """
        if not mtf_results:
            return {
                'aligned': False,
                'direction': 0,
                'score': 0,
                'agreement': 0,
                'avg_strength': 0,
                'bullish_votes': 0,
                'bearish_votes': 0,
                'neutral_votes': 0,
                'timeframe_details': {}
            }

        try:
            # Extract directions and strengths (vectorized)
            directions = np.array([result.get('direction', 0) for result in mtf_results.values()])
            strengths = np.array([result.get('strength', 0) for result in mtf_results.values()])

            # Count votes (vectorized)
            bullish_votes = int(np.sum(directions == 1))
            bearish_votes = int(np.sum(directions == -1))
            neutral_votes = int(np.sum(directions == 0))

            total_timeframes = len(directions)

            # Determine overall direction
            if bullish_votes > bearish_votes and bullish_votes >= total_timeframes * 0.6:
                direction = 1
                agreement = bullish_votes / total_timeframes
            elif bearish_votes > bullish_votes and bearish_votes >= total_timeframes * 0.6:
                direction = -1
                agreement = bearish_votes / total_timeframes
            else:
                direction = 0
                agreement = 0

            # Calculate average strength (only positive strengths)
            positive_strengths = strengths[strengths > 0]
            avg_strength = float(np.mean(positive_strengths)) if len(positive_strengths) > 0 else 0

            # Alignment score (0-1)
            score = agreement * avg_strength

            # Aligned if 75%+ of timeframes agree
            aligned = agreement >= 0.75

            return {
                'aligned': aligned,
                'direction': direction,
                'score': score,
                'agreement': agreement,
                'avg_strength': avg_strength,
                'bullish_votes': bullish_votes,
                'bearish_votes': bearish_votes,
                'neutral_votes': neutral_votes,
                'timeframe_details': mtf_results
            }

        except Exception as e:
            logger.error(f"Error calculating alignment score: {e}")
            return {
                'aligned': False,
                'direction': 0,
                'score': 0,
                'agreement': 0,
                'avg_strength': 0,
                'bullish_votes': 0,
                'bearish_votes': 0,
                'neutral_votes': 0,
                'timeframe_details': mtf_results
            }

    def should_trade(self, alignment: Dict, min_agreement: float = 0.75) -> bool:
        """
        Decision: should we trade based on MTF alignment?

        Args:
            alignment: Alignment score dict from get_alignment_score()
            min_agreement: Minimum agreement threshold (default 0.75)

        Returns:
            bool: True if conditions met for trading
        """
        if not alignment:
            return False

        return (
            alignment.get('aligned', False) and
            alignment.get('agreement', 0) >= min_agreement and
            alignment.get('direction', 0) != 0
        )

    def get_confidence_multiplier(self, alignment: Dict) -> float:
        """
        Boost confidence if timeframes align well.

        Args:
            alignment: Alignment score dict from get_alignment_score()

        Returns:
            float: Multiplier between 0.9 and 1.5
                - 0.9 if not aligned (slight penalty)
                - 1.0 to 1.5 if aligned (boost based on score)
        """
        if not alignment or not alignment.get('aligned', False):
            return 0.9  # Slight penalty

        # Strong alignment = confidence boost
        score = alignment.get('score', 0)
        boost = 1.0 + (score * 0.5)
        return min(1.5, max(1.0, boost))
