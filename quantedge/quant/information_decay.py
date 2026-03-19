# quant/information_decay.py - Information Decay Model
"""
Information Decay Model for News Alpha Half-Life.

Model: I(t) = I₀ * e^(-kt)

Where:
- I(t) = information value at time t
- I₀ = initial information value
- k = decay rate (determines half-life)
- t = time elapsed since news release

Half-life: t₁/₂ = ln(2) / k

Use Case:
Determine how quickly news impact fades and when to exit positions.
"""

import logging
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

from rag.data_schemas import NewsFeatures

logger = logging.getLogger(__name__)


class InformationDecayModel:
    """
    Information decay model for news alpha half-life.

    Tracks how quickly news impact fades over time.
    """

    def __init__(
        self,
        default_half_life_hours: float = 12.0,  # Default 12 hours
        decay_rate_by_event_type: Optional[Dict[str, float]] = None
    ):
        """
        Initialize information decay model.

        Args:
            default_half_life_hours: Default half-life in hours
            decay_rate_by_event_type: Custom decay rates for different event types
        """
        self.default_half_life_hours = default_half_life_hours

        # Decay rates for different event types (k = ln(2) / half_life)
        self.decay_rates = decay_rate_by_event_type or {
            'rate_decision': 0.0289,      # 24 hour half-life (slow decay)
            'economic_data': 0.0578,      # 12 hour half-life (medium)
            'earnings': 0.0693,           # 10 hour half-life
            'geopolitical': 0.0462,       # 15 hour half-life
            'regulatory': 0.0347,         # 20 hour half-life
            'market_commentary': 0.1386,  # 5 hour half-life (fast decay)
            'unknown': 0.0578             # 12 hour half-life (default)
        }

    def calculate_decay(
        self,
        initial_impact: float,
        hours_elapsed: float,
        event_type: str = 'unknown'
    ) -> float:
        """
        Calculate current information value after decay.

        Args:
            initial_impact: Initial news impact (0-1)
            hours_elapsed: Hours since news release
            event_type: Type of news event (affects decay rate)

        Returns:
            Current information value (0-1)
        """
        try:
            # Get decay rate for event type
            k = self.decay_rates.get(event_type, self.decay_rates['unknown'])

            # Exponential decay: I(t) = I₀ * e^(-kt)
            current_value = initial_impact * np.exp(-k * hours_elapsed)

            return max(0.0, min(1.0, current_value))

        except Exception as e:
            logger.error(f"Error calculating decay: {e}")
            return initial_impact * 0.5  # Default to half value

    def get_half_life(self, event_type: str = 'unknown') -> float:
        """
        Get half-life for event type.

        Args:
            event_type: Type of news event

        Returns:
            Half-life in hours
        """
        k = self.decay_rates.get(event_type, self.decay_rates['unknown'])
        half_life = np.log(2) / k
        return half_life

    def get_time_to_threshold(
        self,
        initial_impact: float,
        threshold: float,
        event_type: str = 'unknown'
    ) -> float:
        """
        Calculate time until information value drops below threshold.

        Args:
            initial_impact: Initial news impact
            threshold: Threshold value (e.g., 0.1)
            event_type: Type of news event

        Returns:
            Hours until threshold reached
        """
        try:
            if initial_impact <= threshold:
                return 0.0

            k = self.decay_rates.get(event_type, self.decay_rates['unknown'])

            # Solve: threshold = initial_impact * e^(-kt)
            # t = -ln(threshold / initial_impact) / k
            time_hours = -np.log(threshold / initial_impact) / k

            return max(0.0, time_hours)

        except Exception as e:
            logger.error(f"Error calculating time to threshold: {e}")
            return 24.0  # Default 24 hours

    def should_exit_position(
        self,
        news_features: NewsFeatures,
        current_time: datetime,
        exit_threshold: float = 0.2
    ) -> Dict:
        """
        Determine if position should be exited based on information decay.

        Args:
            news_features: Original news features
            current_time: Current time
            exit_threshold: Exit when info value drops below this

        Returns:
            Dict with exit decision and rationale
        """
        try:
            # Calculate hours elapsed
            hours_elapsed = (current_time - news_features.timestamp).total_seconds() / 3600

            # Calculate current information value
            current_value = self.calculate_decay(
                initial_impact=news_features.impact_score,
                hours_elapsed=hours_elapsed,
                event_type=news_features.event_type.value
            )

            # Should exit if value dropped below threshold
            should_exit = current_value < exit_threshold

            # Calculate time remaining until threshold
            if not should_exit:
                time_to_exit = self.get_time_to_threshold(
                    initial_impact=news_features.impact_score,
                    threshold=exit_threshold,
                    event_type=news_features.event_type.value
                )
                time_remaining = max(0, time_to_exit - hours_elapsed)
            else:
                time_remaining = 0

            return {
                'should_exit': should_exit,
                'current_info_value': current_value,
                'initial_impact': news_features.impact_score,
                'hours_elapsed': hours_elapsed,
                'time_remaining_hours': time_remaining,
                'exit_threshold': exit_threshold,
                'half_life_hours': self.get_half_life(news_features.event_type.value),
                'reason': 'information_decay' if should_exit else 'still_relevant'
            }

        except Exception as e:
            logger.error(f"Error in exit decision: {e}")
            return {
                'should_exit': False,
                'current_info_value': 0.5,
                'reason': 'error'
            }

    def get_optimal_holding_period(
        self,
        initial_impact: float,
        event_type: str = 'unknown',
        min_value_threshold: float = 0.3
    ) -> Dict:
        """
        Calculate optimal holding period for news-driven trade.

        Args:
            initial_impact: Initial news impact
            event_type: Type of news event
            min_value_threshold: Minimum acceptable information value

        Returns:
            Dict with optimal holding period
        """
        half_life = self.get_half_life(event_type)
        time_to_threshold = self.get_time_to_threshold(
            initial_impact, min_value_threshold, event_type
        )

        # Optimal period is typically 1-2 half-lives
        optimal_hours = half_life * 1.5

        return {
            'optimal_holding_hours': optimal_hours,
            'half_life_hours': half_life,
            'time_until_threshold': time_to_threshold,
            'recommendation': self._get_holding_recommendation(optimal_hours)
        }

    def _get_holding_recommendation(self, hours: float) -> str:
        """Get human-readable holding recommendation"""
        if hours < 1:
            return "Exit quickly (< 1 hour)"
        elif hours < 4:
            return "Short-term hold (1-4 hours)"
        elif hours < 12:
            return "Medium-term hold (4-12 hours)"
        elif hours < 24:
            return "Day hold (12-24 hours)"
        else:
            return "Multi-day hold (> 24 hours)"

    def update_decay_rate(
        self,
        event_type: str,
        observed_half_life_hours: float
    ):
        """
        Update decay rate based on observed behavior.

        Args:
            event_type: Type of news event
            observed_half_life_hours: Observed half-life from historical data
        """
        # Calculate new decay rate: k = ln(2) / half_life
        new_k = np.log(2) / observed_half_life_hours
        self.decay_rates[event_type] = new_k

        logger.info(f"Updated decay rate for {event_type}: "
                   f"half-life = {observed_half_life_hours:.1f} hours")

    def get_model_info(self) -> Dict:
        """Get model information"""
        return {
            'name': 'Information Decay Model',
            'formula': 'I(t) = I₀ * e^(-kt)',
            'half_lives': {
                event_type: self.get_half_life(event_type)
                for event_type in self.decay_rates.keys()
            },
            'decay_rates': self.decay_rates
        }
