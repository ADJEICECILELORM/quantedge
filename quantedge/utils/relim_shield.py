# utils/relim_shield.py - Relim_conf (The Shield): Dynamic Confidence Threshold
import numpy as np
from collections import deque
from typing import Dict

class RelimShield:
    """
    The Shield: Dynamic confidence threshold optimizer.
    Adjusts minimum confidence based on recent performance.
    """
    def __init__(self, initial_threshold=0.60, min_threshold=0.50, max_threshold=0.80, lookback=20):
        self.threshold = initial_threshold
        self.min_threshold = min_threshold
        self.max_threshold = max_threshold
        self.lookback = lookback

        # Track recent trades
        self.trade_history = deque(maxlen=lookback)

    def add_trade_result(self, confidence: float, outcome: str, pnl: float):
        """
        Record a trade result.
        outcome: 'win' or 'loss'
        pnl: profit/loss in dollars
        """
        self.trade_history.append({
            'confidence': confidence,
            'outcome': outcome,
            'pnl': pnl
        })

    def calculate_win_rate(self) -> float:
        """Calculate recent win rate"""
        if len(self.trade_history) == 0:
            return 0.5

        wins = sum(1 for trade in self.trade_history if trade['outcome'] == 'win')
        return wins / len(self.trade_history)

    def calculate_profit_factor(self) -> float:
        """Calculate recent profit factor"""
        if len(self.trade_history) == 0:
            return 1.0

        gross_profit = sum(trade['pnl'] for trade in self.trade_history if trade['pnl'] > 0)
        gross_loss = abs(sum(trade['pnl'] for trade in self.trade_history if trade['pnl'] < 0))

        if gross_loss == 0:
            return 2.0  # Default high value

        return gross_profit / gross_loss if gross_loss > 0 else 1.0

    def calculate_average_confidence(self) -> float:
        """Calculate average confidence of recent trades"""
        if len(self.trade_history) == 0:
            return 0.60

        return np.mean([trade['confidence'] for trade in self.trade_history])

    def update_threshold(self):
        """
        Update confidence threshold based on recent performance.

        Logic:
        - If win rate > 60% and profit factor > 1.5: LOWER threshold (take more trades)
        - If win rate < 40% or profit factor < 1.0: RAISE threshold (be more selective)
        """
        if len(self.trade_history) < 5:
            # Not enough data yet
            return

        win_rate = self.calculate_win_rate()
        profit_factor = self.calculate_profit_factor()

        # Adjust threshold
        if win_rate > 0.60 and profit_factor > 1.5:
            # Performing well - be more aggressive
            self.threshold = max(self.min_threshold, self.threshold - 0.02)
            print(f"🛡️ Shield: Performance GOOD. Lowering threshold to {self.threshold:.2f}")

        elif win_rate < 0.40 or profit_factor < 1.0:
            # Performing poorly - be more defensive
            self.threshold = min(self.max_threshold, self.threshold + 0.03)
            print(f"🛡️ Shield: Performance POOR. Raising threshold to {self.threshold:.2f}")

        elif win_rate < 0.50:
            # Marginal performance
            self.threshold = min(self.max_threshold, self.threshold + 0.01)
            print(f"🛡️ Shield: Performance MARGINAL. Adjusting threshold to {self.threshold:.2f}")

    def should_trade(self, confidence: float) -> bool:
        """
        Main decision function: Should we take this trade?
        """
        return confidence >= self.threshold

    def get_threshold(self) -> float:
        """Get current threshold"""
        return self.threshold

    def get_stats(self) -> Dict:
        """Get shield statistics"""
        if len(self.trade_history) == 0:
            return {
                'threshold': self.threshold,
                'win_rate': 0,
                'profit_factor': 0,
                'trades_count': 0,
                'avg_confidence': 0
            }

        return {
            'threshold': self.threshold,
            'win_rate': self.calculate_win_rate(),
            'profit_factor': self.calculate_profit_factor(),
            'trades_count': len(self.trade_history),
            'avg_confidence': self.calculate_average_confidence()
        }

    def print_status(self):
        """Print shield status"""
        stats = self.get_stats()
        print("\n🛡️ === RELIM SHIELD STATUS ===")
        print(f"   Current Threshold: {stats['threshold']:.2f}")
        print(f"   Win Rate: {stats['win_rate']*100:.1f}%")
        print(f"   Profit Factor: {stats['profit_factor']:.2f}")
        print(f"   Trades Tracked: {stats['trades_count']}")
        print(f"   Avg Confidence: {stats['avg_confidence']:.2f}")
        print("=========================\n")

    def reset(self):
        """Reset shield to initial state"""
        self.threshold = 0.60
        self.trade_history.clear()
        print("🛡️ Shield reset to default settings.")
