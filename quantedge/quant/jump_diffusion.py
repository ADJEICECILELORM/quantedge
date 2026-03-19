# quant/jump_diffusion.py - Merton Jump-Diffusion Model
"""
Merton's Jump-Diffusion Model for News-Driven Price Jumps.

Model: dS = μS dt + σS dW + J dN
Where:
- dS = price change
- μ = drift
- σ = diffusion volatility
- dW = Wiener process (continuous random walk)
- J = jump size
- dN = Poisson process (jump arrivals)

Use Case:
Calculate probability of price jump given high-impact news event.
"""

import logging
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass

from rag.data_schemas import NewsFeatures

logger = logging.getLogger(__name__)


@dataclass
class JumpDiffusionParams:
    """Jump-diffusion model parameters"""
    drift: float                # μ (annual drift)
    diffusion_vol: float        # σ (annual volatility)
    jump_intensity: float       # λ (Poisson arrival rate, jumps per year)
    jump_mean: float            # E[J] (average jump size)
    jump_std: float             # σ_J (jump size volatility)


class JumpDiffusionModel:
    """
    Merton's Jump-Diffusion Model.

    Calculates probability and magnitude of price jumps
    triggered by news events.
    """

    # Model Assumptions
    ASSUMPTIONS = [
        "Log-normal returns for continuous component",
        "Poisson jump arrivals (independent of price)",
        "Jump sizes are normally distributed",
        "Jumps are independent of continuous diffusion"
    ]

    # Valid Regimes
    VALID_REGIMES = [
        "volatility_expansion",
        "trend"  # Can use during strong trends
    ]

    # Required Inputs
    REQUIRED_INPUTS = [
        "current_price",
        "historical_volatility",
        "news_impact_score",
        "news_novelty_score"
    ]

    # Failure Modes
    FAILURE_MODES = [
        "Insufficient historical volatility data (< 20 bars)",
        "No recent jumps for calibration",
        "Extreme volatility (model breakdown)"
    ]

    def __init__(
        self,
        base_jump_intensity: float = 10.0,  # 10 jumps per year baseline
        news_sensitivity: float = 2.0        # Multiplier for news impact
    ):
        self.base_jump_intensity = base_jump_intensity
        self.news_sensitivity = news_sensitivity

        # Default parameters (will be calibrated from data)
        self.params = JumpDiffusionParams(
            drift=0.05,           # 5% annual drift
            diffusion_vol=0.15,   # 15% annual volatility
            jump_intensity=10.0,  # 10 jumps/year
            jump_mean=0.02,       # 2% average jump
            jump_std=0.05         # 5% jump volatility
        )

    def calibrate(self, price_history: np.ndarray, dt: float = 1/252):
        """
        Calibrate model parameters from historical data.

        Args:
            price_history: Array of historical prices
            dt: Time step (default: 1 day = 1/252 years)
        """
        try:
            if len(price_history) < 20:
                logger.warning("Insufficient data for calibration")
                return

            # Calculate returns
            returns = np.diff(np.log(price_history))

            # Estimate drift
            self.params.drift = np.mean(returns) / dt

            # Estimate volatility (diffusion component)
            self.params.diffusion_vol = np.std(returns) / np.sqrt(dt)

            # Detect jumps (simple method: returns > 2 sigma)
            threshold = 2 * np.std(returns)
            jumps = returns[np.abs(returns) > threshold]

            if len(jumps) > 0:
                # Estimate jump parameters
                self.params.jump_intensity = len(jumps) / (len(returns) * dt)
                self.params.jump_mean = np.mean(jumps)
                self.params.jump_std = np.std(jumps)

                logger.info(f"Calibrated jump-diffusion: λ={self.params.jump_intensity:.2f}, "
                           f"E[J]={self.params.jump_mean:.4f}, σ_J={self.params.jump_std:.4f}")
            else:
                logger.warning("No jumps detected in calibration period")

        except Exception as e:
            logger.error(f"Error calibrating jump-diffusion: {e}")

    def calculate_jump_probability(
        self,
        news_features: NewsFeatures,
        time_horizon_hours: float = 1.0
    ) -> float:
        """
        Calculate probability of price jump given news event.

        Args:
            news_features: News features (impact, novelty, sentiment)
            time_horizon_hours: Time horizon to consider (hours)

        Returns:
            Probability of jump (0-1)
        """
        try:
            # Convert time horizon to years
            dt = time_horizon_hours / (365 * 24)

            # Base jump intensity (Poisson arrival rate)
            base_lambda = self.params.jump_intensity

            # Adjust intensity based on news impact and novelty
            # High impact + high novelty = higher jump probability
            news_factor = (news_features.impact_score + news_features.novelty_score) / 2
            adjusted_lambda = base_lambda * (1 + self.news_sensitivity * news_factor)

            # Poisson probability: P(at least 1 jump) = 1 - e^(-λ*dt)
            prob_jump = 1 - np.exp(-adjusted_lambda * dt)

            return min(1.0, max(0.0, prob_jump))

        except Exception as e:
            logger.error(f"Error calculating jump probability: {e}")
            return 0.5  # Default uncertainty

    def estimate_jump_size(
        self,
        news_features: NewsFeatures,
        current_price: float
    ) -> Dict:
        """
        Estimate expected jump size given news.

        Args:
            news_features: News features
            current_price: Current asset price

        Returns:
            Dict with jump size estimate and confidence interval
        """
        try:
            # Base jump size from calibration
            base_jump_mean = self.params.jump_mean
            base_jump_std = self.params.jump_std

            # Adjust based on news sentiment and impact
            # Positive sentiment = positive jump, negative = negative jump
            sentiment_direction = np.sign(news_features.sentiment)
            sentiment_strength = abs(news_features.sentiment)

            # Expected jump size = direction * impact * base_size
            expected_jump = (
                sentiment_direction *
                news_features.impact_score *
                base_jump_mean
            )

            # Jump volatility scales with impact
            jump_std = base_jump_std * (1 + news_features.impact_score)

            # 95% confidence interval
            ci_lower = expected_jump - 1.96 * jump_std
            ci_upper = expected_jump + 1.96 * jump_std

            # Convert to price levels
            price_lower = current_price * (1 + ci_lower)
            price_upper = current_price * (1 + ci_upper)
            price_expected = current_price * (1 + expected_jump)

            return {
                'expected_jump_pct': expected_jump,
                'jump_std': jump_std,
                'ci_lower_pct': ci_lower,
                'ci_upper_pct': ci_upper,
                'expected_price': price_expected,
                'price_lower_95': price_lower,
                'price_upper_95': price_upper,
                'direction': 'bullish' if expected_jump > 0 else 'bearish'
            }

        except Exception as e:
            logger.error(f"Error estimating jump size: {e}")
            return {
                'expected_jump_pct': 0.0,
                'jump_std': 0.05,
                'direction': 'neutral'
            }

    def should_trade_jump(
        self,
        news_features: NewsFeatures,
        min_jump_prob: float = 0.3,
        min_impact: float = 0.5
    ) -> Dict:
        """
        Decide if news event warrants jump trading strategy.

        Args:
            news_features: News features
            min_jump_prob: Minimum jump probability threshold
            min_impact: Minimum impact score threshold

        Returns:
            Dict with trade decision and rationale
        """
        # Calculate jump probability
        jump_prob = self.calculate_jump_probability(news_features)

        # Check conditions
        high_prob = jump_prob >= min_jump_prob
        high_impact = news_features.impact_score >= min_impact
        fresh_news = news_features.time_decay_factor > 0.7

        should_trade = high_prob and high_impact and fresh_news

        return {
            'should_trade': should_trade,
            'jump_probability': jump_prob,
            'impact_score': news_features.impact_score,
            'time_decay': news_features.time_decay_factor,
            'reasons': {
                'high_probability': high_prob,
                'high_impact': high_impact,
                'fresh_news': fresh_news
            },
            'strategy': 'jump_diffusion' if should_trade else 'skip'
        }

    def get_model_info(self) -> Dict:
        """Get model information and assumptions"""
        return {
            'name': 'Merton Jump-Diffusion Model',
            'assumptions': self.ASSUMPTIONS,
            'valid_regimes': self.VALID_REGIMES,
            'required_inputs': self.REQUIRED_INPUTS,
            'failure_modes': self.FAILURE_MODES,
            'current_params': {
                'drift': self.params.drift,
                'diffusion_vol': self.params.diffusion_vol,
                'jump_intensity': self.params.jump_intensity,
                'jump_mean': self.params.jump_mean,
                'jump_std': self.params.jump_std
            }
        }
