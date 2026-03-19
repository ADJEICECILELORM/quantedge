# quant/kelly_enhanced.py - Enhanced Kelly Criterion with News Intelligence
"""
Enhanced Kelly Criterion for position sizing with news confidence.

Standard Kelly: f* = (p*b - q) / b
Where:
- f* = fraction of capital to bet
- p = probability of winning
- b = win/loss ratio
- q = 1 - p (probability of losing)

Enhancement:
Incorporate news confidence and regime classification to adjust Kelly fraction.
"""

import logging
import numpy as np
from typing import Dict, Optional
from collections import deque

from rag.data_schemas import NewsFeatures, MarketRegime

logger = logging.getLogger(__name__)


class EnhancedKellyCriterion:
    """
    Enhanced Kelly Criterion with news intelligence integration.

    Improvements over standard Kelly:
    1. News confidence adjustment
    2. Regime-based multipliers
    3. Dynamic risk scaling
    4. Drawdown protection
    """

    def __init__(
        self,
        lookback: int = 50,
        fraction: float = 0.25,  # Quarter-Kelly (conservative)
        max_kelly: float = 0.10,  # Maximum 10% per trade
        min_kelly: float = 0.01   # Minimum 1% per trade
    ):
        self.lookback = lookback
        self.fraction = fraction
        self.max_kelly = max_kelly
        self.min_kelly = min_kelly

        # Trade history
        self.trade_history = deque(maxlen=lookback)

        # Default parameters (if no history)
        self.default_win_rate = 0.55
        self.default_win_loss_ratio = 1.5

    def add_trade_result(
        self,
        pnl: float,
        outcome: str,
        news_contribution: float = 0.5
    ):
        """
        Record trade result.

        Args:
            pnl: Profit/loss amount
            outcome: 'win' or 'loss'
            news_contribution: How much news contributed (0-1)
        """
        self.trade_history.append({
            'pnl': pnl,
            'outcome': outcome,
            'news_contribution': news_contribution
        })

    def calculate_base_kelly(self) -> Dict:
        """
        Calculate base Kelly fraction from historical performance.

        Returns:
            Dict with Kelly stats
        """
        if len(self.trade_history) < 10:
            # Use defaults
            p = self.default_win_rate
            b = self.default_win_loss_ratio
        else:
            # Calculate from history
            wins = [t for t in self.trade_history if t['outcome'] == 'win']
            losses = [t for t in self.trade_history if t['outcome'] == 'loss']

            # Win rate
            p = len(wins) / len(self.trade_history)

            # Win/loss ratio
            if wins and losses:
                avg_win = np.mean([t['pnl'] for t in wins])
                avg_loss = np.mean([abs(t['pnl']) for t in losses])
                b = avg_win / avg_loss if avg_loss > 0 else self.default_win_loss_ratio
            else:
                b = self.default_win_loss_ratio

        # Kelly formula: f* = (p*b - q) / b
        q = 1 - p
        kelly = (p * b - q) / b

        # Apply fractional Kelly (more conservative)
        fractional_kelly = kelly * self.fraction

        # Clamp to min/max
        clamped_kelly = max(self.min_kelly, min(self.max_kelly, fractional_kelly))

        return {
            'raw_kelly': kelly,
            'fractional_kelly': fractional_kelly,
            'clamped_kelly': clamped_kelly,
            'win_rate': p,
            'win_loss_ratio': b,
            'sample_size': len(self.trade_history)
        }

    def calculate_enhanced_position_size(
        self,
        account_balance: float,
        news_features: Optional[NewsFeatures] = None,
        regime: Optional[MarketRegime] = None,
        current_drawdown: float = 0.0
    ) -> Dict:
        """
        Calculate optimal position size with enhancements.

        Args:
            account_balance: Current account balance
            news_features: News features (if news-driven trade)
            regime: Market regime
            current_drawdown: Current drawdown (0-1)

        Returns:
            Dict with position sizing recommendation
        """
        # Input validation
        if account_balance <= 0:
            raise ValueError(f"Account balance must be positive, got {account_balance}")

        if not isinstance(account_balance, (int, float)):
            raise TypeError(f"Account balance must be numeric, got {type(account_balance)}")

        if current_drawdown < 0 or current_drawdown > 1:
            raise ValueError(f"Drawdown must be between 0 and 1, got {current_drawdown}")

        # Get base Kelly
        kelly_stats = self.calculate_base_kelly()
        base_kelly = kelly_stats['clamped_kelly']

        # Apply adjustments
        adjusted_kelly = base_kelly

        # 1. News Confidence Adjustment
        if news_features:
            news_multiplier = self._get_news_multiplier(news_features)
            adjusted_kelly *= news_multiplier
            adjustment_reasons = [f"News confidence: {news_multiplier:.2f}x"]
        else:
            adjustment_reasons = ["No news input"]

        # 2. Regime Adjustment
        if regime:
            regime_multiplier = self._get_regime_multiplier(regime)
            adjusted_kelly *= regime_multiplier
            adjustment_reasons.append(f"Regime ({regime.regime_type}): {regime_multiplier:.2f}x")

        # 3. Drawdown Protection
        if current_drawdown > 0:
            dd_multiplier = self._get_drawdown_multiplier(current_drawdown)
            adjusted_kelly *= dd_multiplier
            adjustment_reasons.append(f"Drawdown protection: {dd_multiplier:.2f}x")

        # Final clamp
        final_kelly = max(self.min_kelly, min(self.max_kelly, adjusted_kelly))

        # Calculate risk amount
        risk_amount = account_balance * final_kelly

        return {
            'base_kelly': base_kelly,
            'adjusted_kelly': adjusted_kelly,
            'final_kelly': final_kelly,
            'risk_amount': risk_amount,
            'risk_pct': final_kelly * 100,
            'adjustment_reasons': adjustment_reasons,
            'win_rate': kelly_stats['win_rate'],
            'win_loss_ratio': kelly_stats['win_loss_ratio'],
            'recommendation': self._get_recommendation(final_kelly)
        }

    def _get_news_multiplier(self, news_features: NewsFeatures) -> float:
        """
        Get position size multiplier based on news features.

        High confidence + High impact = Larger position
        Low confidence + Low impact = Smaller position
        """
        # Combine confidence and impact
        news_quality = (news_features.confidence + news_features.impact_score) / 2

        # Source credibility
        source_quality = news_features.source_score_composite

        # Time decay (recent news = better)
        time_quality = news_features.time_decay_factor

        # Overall news score
        overall_score = (news_quality * 0.5 + source_quality * 0.3 + time_quality * 0.2)

        # Multiplier ranges from 0.5x (weak news) to 1.5x (strong news)
        multiplier = 0.5 + (overall_score * 1.0)

        return min(1.5, max(0.5, multiplier))

    def _get_regime_multiplier(self, regime: MarketRegime) -> float:
        """
        Get position size multiplier based on market regime.

        Trend/Volatility = Larger positions
        Low Vol/Unknown = Smaller positions
        """
        regime_multipliers = {
            'trend': 1.2,           # Trend-following works well
            'volatility': 1.3,      # Breakouts can be profitable
            'reversion': 1.0,       # Standard size
            'low_vol': 0.6,         # Reduce in low volatility
            'unknown': 0.7          # Conservative when uncertain
        }

        base_mult = regime_multipliers.get(regime.regime_type, 0.8)

        # Adjust by regime confidence
        confidence_adj = 0.8 + (regime.confidence * 0.4)  # 0.8 to 1.2

        return base_mult * confidence_adj

    def _get_drawdown_multiplier(self, drawdown: float) -> float:
        """
        Reduce position size during drawdowns.

        0% DD = 1.0x (full size)
        5% DD = 0.75x (25% reduction)
        10% DD = 0.5x (50% reduction)
        """
        if drawdown <= 0:
            return 1.0

        # Linear reduction
        multiplier = 1.0 - (drawdown * 5)  # 5x multiplier on drawdown

        return max(0.3, min(1.0, multiplier))

    def _get_recommendation(self, kelly_fraction: float) -> str:
        """Get human-readable recommendation"""
        if kelly_fraction < 0.02:
            return "Very small position - low edge detected"
        elif kelly_fraction < 0.04:
            return "Small position - moderate edge"
        elif kelly_fraction < 0.06:
            return "Standard position - good edge"
        elif kelly_fraction < 0.08:
            return "Large position - strong edge"
        else:
            return "Maximum position - very strong edge"

    def get_news_trade_sizing(
        self,
        account_balance: float,
        news_features: NewsFeatures,
        stop_loss_pct: float,
        regime: Optional[MarketRegime] = None
    ) -> Dict:
        """
        Calculate position size specifically for news-driven trade.

        Args:
            account_balance: Account balance
            news_features: News features
            stop_loss_pct: Stop loss distance (e.g., 0.02 for 2%)
            regime: Market regime

        Returns:
            Dict with lot size and risk details
        """
        # Get enhanced Kelly fraction
        kelly_result = self.calculate_enhanced_position_size(
            account_balance=account_balance,
            news_features=news_features,
            regime=regime
        )

        # Calculate lot size based on stop loss
        risk_amount = kelly_result['risk_amount']

        # Position size = risk_amount / (stop_loss_pct * current_price)
        # This will be calculated by position sizer with actual price

        return {
            'kelly_fraction': kelly_result['final_kelly'],
            'risk_amount': risk_amount,
            'risk_pct': kelly_result['risk_pct'],
            'stop_loss_pct': stop_loss_pct,
            'recommendation': kelly_result['recommendation'],
            'adjustments': kelly_result['adjustment_reasons'],
            'confidence_breakdown': {
                'base_win_rate': kelly_result['win_rate'],
                'win_loss_ratio': kelly_result['win_loss_ratio'],
                'news_confidence': news_features.confidence,
                'news_impact': news_features.impact_score
            }
        }

    def get_stats(self) -> Dict:
        """Get Kelly statistics"""
        kelly_stats = self.calculate_base_kelly()

        return {
            'kelly_fraction': kelly_stats['clamped_kelly'],
            'win_rate': kelly_stats['win_rate'],
            'win_loss_ratio': kelly_stats['win_loss_ratio'],
            'trades_tracked': len(self.trade_history),
            'fraction_multiplier': self.fraction,
            'max_kelly': self.max_kelly
        }
