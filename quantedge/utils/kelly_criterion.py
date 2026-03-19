# utils/kelly_criterion.py - Kelly Criterion Position Sizing
import numpy as np
from typing import Dict
from collections import deque

class KellyCriterion:
    """
    Optimal position sizing using Kelly Criterion.
    Formula: f* = (p*b - q) / b
    where:
    - p = probability of winning
    - q = probability of losing (1-p)
    - b = win/loss ratio (avg_win / avg_loss)
    """
    def __init__(self, lookback=50, fraction=0.25):
        self.lookback = lookback
        self.fraction = fraction  # Use fractional Kelly (quarter Kelly)
        self.trade_history = deque(maxlen=lookback)

    def add_trade_result(self, pnl: float, outcome: str):
        """Record a trade result"""
        self.trade_history.append({
            'pnl': pnl,
            'outcome': outcome
        })

    def calculate_win_rate(self) -> float:
        """Calculate empirical win rate"""
        if len(self.trade_history) < 10:
            return 0.55  # Default conservative estimate

        wins = sum(1 for trade in self.trade_history if trade['outcome'] == 'win')
        return wins / len(self.trade_history)

    def calculate_win_loss_ratio(self) -> float:
        """Calculate average win / average loss"""
        if len(self.trade_history) < 10:
            return 1.5  # Default estimate

        wins = [trade['pnl'] for trade in self.trade_history if trade['pnl'] > 0]
        losses = [abs(trade['pnl']) for trade in self.trade_history if trade['pnl'] < 0]

        if not wins or not losses:
            return 1.5

        avg_win = np.mean(wins)
        avg_loss = np.mean(losses)

        return avg_win / avg_loss if avg_loss > 0 else 1.5

    def calculate_kelly_fraction(self) -> float:
        """
        Calculate Kelly fraction.
        Returns: fraction of capital to risk (0-1)
        """
        p = self.calculate_win_rate()
        b = self.calculate_win_loss_ratio()
        q = 1 - p

        # Kelly formula
        kelly = (p * b - q) / b

        # Apply fractional Kelly (more conservative)
        fractional_kelly = kelly * self.fraction

        # Clamp between 0 and max risk
        fractional_kelly = max(0.01, min(0.10, fractional_kelly))  # 1% to 10% max

        return fractional_kelly

    def calculate_position_size(self, account_balance: float, stop_loss_pct: float) -> Dict:
        """
        Calculate optimal position size using Kelly.

        Returns:
        - risk_per_trade: % of account to risk
        - kelly_fraction: raw Kelly value
        - recommendation: text recommendation
        """
        kelly_fraction = self.calculate_kelly_fraction()

        # Kelly tells us % of capital to allocate
        # We need to convert to risk per trade
        # If SL is 2% away, and Kelly says 5%, then risk = 5% * (2%/100%) = 0.1%

        risk_per_trade = kelly_fraction

        # Generate recommendation
        if kelly_fraction < 0.02:
            recommendation = "Low edge - minimal position"
        elif kelly_fraction < 0.05:
            recommendation = "Moderate edge - standard position"
        elif kelly_fraction < 0.08:
            recommendation = "Strong edge - increased position"
        else:
            recommendation = "Very strong edge - maximum position"

        return {
            'kelly_fraction': kelly_fraction,
            'risk_per_trade': risk_per_trade,
            'recommendation': recommendation,
            'win_rate': self.calculate_win_rate(),
            'win_loss_ratio': self.calculate_win_loss_ratio(),
            'sample_size': len(self.trade_history)
        }

    def get_stats(self) -> Dict:
        """Get current Kelly statistics"""
        return {
            'kelly_fraction': self.calculate_kelly_fraction(),
            'win_rate': self.calculate_win_rate(),
            'win_loss_ratio': self.calculate_win_loss_ratio(),
            'trades_tracked': len(self.trade_history)
        }
