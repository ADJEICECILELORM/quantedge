# optimizer/fitness_functions.py - Fitness Functions for GA
"""
Fitness functions for constrained genetic algorithm.

NOT profit-only! Includes:
- Risk-adjusted returns (Sortino Ratio)
- Drawdown penalties
- Overtrading penalties
- Stability across regimes
- Consistency over time
"""

import logging
import numpy as np
from typing import Dict, List

logger = logging.getLogger(__name__)


class FitnessFunction:
    """
    Multi-objective fitness function for trading strategy optimization.

    Prevents overfitting by penalizing:
    - High drawdowns
    - Overtrading
    - Regime instability
    - Inconsistent performance
    """

    def __init__(
        self,
        sortino_weight: float = 0.40,
        drawdown_weight: float = 0.25,
        consistency_weight: float = 0.20,
        trade_efficiency_weight: float = 0.15
    ):
        self.sortino_weight = sortino_weight
        self.drawdown_weight = drawdown_weight
        self.consistency_weight = consistency_weight
        self.trade_efficiency_weight = trade_efficiency_weight

    def calculate_fitness(
        self,
        returns: List[float],
        trades: List[Dict],
        regime_performance: Dict[str, float]
    ) -> float:
        """
        Calculate comprehensive fitness score.

        Args:
            returns: List of trade returns
            trades: List of trade details
            regime_performance: Performance by regime

        Returns:
            Fitness score (0-1, higher is better)
        """
        if not returns or len(returns) < 10:
            return 0.0

        # Component 1: Sortino Ratio (40%)
        sortino_score = self._calculate_sortino_score(returns)

        # Component 2: Drawdown Penalty (25%)
        dd_score = self._calculate_drawdown_score(returns)

        # Component 3: Consistency (20%)
        consistency_score = self._calculate_consistency_score(returns)

        # Component 4: Trade Efficiency (15%)
        efficiency_score = self._calculate_trade_efficiency(trades)

        # Weighted fitness
        fitness = (
            sortino_score * self.sortino_weight +
            dd_score * self.drawdown_weight +
            consistency_score * self.consistency_weight +
            efficiency_score * self.trade_efficiency_weight
        )

        # Regime penalty
        regime_penalty = self._calculate_regime_penalty(regime_performance)
        fitness *= regime_penalty

        return max(0.0, min(1.0, fitness))

    def _calculate_sortino_score(self, returns: List[float]) -> float:
        """
        Calculate Sortino Ratio score (only penalizes downside volatility).

        Sortino = (Mean Return - Risk-Free Rate) / Downside Deviation
        """
        try:
            returns_array = np.array(returns)

            if len(returns_array) == 0:
                return 0.0

            # Mean return
            mean_return = np.mean(returns_array)

            # Downside deviation (only negative returns)
            downside_returns = returns_array[returns_array < 0]

            if len(downside_returns) == 0:
                # No losses = perfect
                return 1.0

            downside_std = np.std(downside_returns)

            if downside_std == 0:
                return 1.0

            # Sortino ratio (annualized, assuming daily returns)
            risk_free_rate = 0.02 / 252  # 2% annual
            sortino = (mean_return - risk_free_rate) / downside_std

            # Normalize to 0-1
            # Sortino > 2.0 = excellent (score 1.0)
            # Sortino < 0 = poor (score 0.0)
            score = max(0.0, min(1.0, sortino / 2.0))

            return score

        except Exception as e:
            logger.error(f"Error calculating Sortino: {e}")
            return 0.5

    def _calculate_drawdown_score(self, returns: List[float]) -> float:
        """
        Calculate drawdown score (penalizes large drawdowns).

        Lower drawdown = higher score
        """
        try:
            cumulative = np.cumsum(returns)
            running_max = np.maximum.accumulate(cumulative)
            drawdowns = (cumulative - running_max)

            max_drawdown = abs(np.min(drawdowns))

            # Score based on max drawdown
            # 0% DD = 1.0
            # 10% DD = 0.5
            # 20%+ DD = 0.0
            if max_drawdown == 0:
                return 1.0

            score = max(0.0, 1.0 - (max_drawdown / 0.20))

            return score

        except Exception as e:
            logger.error(f"Error calculating drawdown: {e}")
            return 0.5

    def _calculate_consistency_score(self, returns: List[float]) -> float:
        """
        Calculate consistency score (steady performance over time).

        Measures:
        - Win rate stability
        - Return variance
        - No long losing streaks
        """
        try:
            returns_array = np.array(returns)

            # Win rate
            win_rate = sum(1 for r in returns_array if r > 0) / len(returns_array)

            # Rolling win rate stability
            window = 20
            if len(returns_array) > window:
                rolling_wr = []
                for i in range(len(returns_array) - window):
                    window_returns = returns_array[i:i+window]
                    wr = sum(1 for r in window_returns if r > 0) / window
                    rolling_wr.append(wr)

                wr_std = np.std(rolling_wr)
                stability_score = max(0.0, 1.0 - wr_std * 3)
            else:
                stability_score = 0.5

            # Longest losing streak penalty
            current_streak = 0
            max_losing_streak = 0

            for r in returns_array:
                if r < 0:
                    current_streak += 1
                    max_losing_streak = max(max_losing_streak, current_streak)
                else:
                    current_streak = 0

            streak_score = max(0.0, 1.0 - (max_losing_streak / 10))

            # Combined consistency
            consistency = (stability_score * 0.6 + streak_score * 0.4)

            return max(0.0, min(1.0, consistency))

        except Exception as e:
            logger.error(f"Error calculating consistency: {e}")
            return 0.5

    def _calculate_trade_efficiency(self, trades: List[Dict]) -> float:
        """
        Calculate trade efficiency score (not just quantity).

        Penalizes:
        - Overtrading (too many trades)
        - Poor profit factor
        """
        try:
            if not trades:
                return 0.0

            num_trades = len(trades)

            # Trade frequency score
            # Optimal: 50-150 trades (for backtesting period)
            # Too few: not enough data
            # Too many: overtrading
            if num_trades < 30:
                freq_score = num_trades / 30 * 0.5  # Penalty for too few
            elif num_trades <= 150:
                freq_score = 1.0  # Ideal range
            else:
                freq_score = max(0.3, 1.0 - ((num_trades - 150) / 200))  # Penalty for too many

            # Profit factor
            wins = [t for t in trades if t.get('pnl', 0) > 0]
            losses = [t for t in trades if t.get('pnl', 0) < 0]

            if wins and losses:
                total_wins = sum(t.get('pnl', 0) for t in wins)
                total_losses = abs(sum(t.get('pnl', 0) for t in losses))

                if total_losses > 0:
                    profit_factor = total_wins / total_losses
                else:
                    profit_factor = 3.0

                # Score profit factor
                # PF > 2.0 = excellent (1.0)
                # PF = 1.0 = breakeven (0.0)
                pf_score = max(0.0, min(1.0, (profit_factor - 1.0) / 1.0))
            else:
                pf_score = 0.5

            # Combined efficiency
            efficiency = (freq_score * 0.4 + pf_score * 0.6)

            return max(0.0, min(1.0, efficiency))

        except Exception as e:
            logger.error(f"Error calculating trade efficiency: {e}")
            return 0.5

    def _calculate_regime_penalty(self, regime_performance: Dict[str, float]) -> float:
        """
        Penalize strategies that only work in one regime.

        Good strategy should work across multiple regimes.
        """
        try:
            if not regime_performance:
                return 1.0  # No penalty if no regime data

            # Check performance in each regime
            regime_scores = list(regime_performance.values())

            if len(regime_scores) < 2:
                return 1.0  # Need multiple regimes

            # Count how many regimes are profitable
            profitable_regimes = sum(1 for score in regime_scores if score > 0)

            # Penalty if only works in 1 regime
            if profitable_regimes <= 1:
                return 0.6  # 40% penalty
            elif profitable_regimes == 2:
                return 0.85  # 15% penalty
            else:
                return 1.0  # No penalty (works in 3+ regimes)

        except Exception as e:
            logger.error(f"Error calculating regime penalty: {e}")
            return 1.0


def explain_why_prevents_overfitting():
    """
    Explain how this fitness function prevents overfitting.
    """
    explanation = """
    🛡️ HOW THIS FITNESS FUNCTION PREVENTS OVERFITTING:

    1. SORTINO RATIO (40%):
       - Penalizes downside volatility
       - Not just total return (which can be gamed)
       - Requires consistent positive returns

    2. DRAWDOWN PENALTY (25%):
       - Punishes strategies with large drawdowns
       - Prevents high-risk, high-reward overfits
       - Ensures capital preservation

    3. CONSISTENCY SCORE (20%):
       - Measures stability over time
       - Penalizes long losing streaks
       - Requires rolling win rate stability
       - Prevents "lucky" one-time wins

    4. TRADE EFFICIENCY (15%):
       - Penalizes overtrading (curve-fitting)
       - Requires good profit factor
       - Optimal trade count (not too many, not too few)

    5. REGIME PENALTY:
       - Strategy must work in 3+ regimes
       - Prevents regime-specific overfitting
       - Ensures robustness

    Result: Forces GA to find ROBUST strategies, not over-fitted ones.
    """
    return explanation
