# safety/shadow_mode.py - Shadow Mode for Safe Testing
"""
Shadow Mode: Log 'Proposed Trades' WITHOUT Executing.

Use Cases:
1. Test new modules before going live
2. Compare strategies side-by-side
3. Verify GA-optimized parameters
4. Debug without risk

How it works:
- All trading logic runs normally
- Trades are logged but NOT sent to MT5
- Performance tracked separately
- Can be toggled on/off per module
"""

import logging
import json
import os
from typing import Dict, List
from datetime import datetime, timezone

from rag.data_schemas import ProposedTrade

logger = logging.getLogger(__name__)


class ShadowModeLogger:
    """
    Shadow mode logger for proposed trades.

    Logs trades without executing them.
    """

    def __init__(
        self,
        log_file: str = "data/shadow_trades.json",
        enabled: bool = True
    ):
        self.log_file = log_file
        self.enabled = enabled
        self.proposed_trades: List[ProposedTrade] = []

        # Performance tracking
        self.shadow_performance = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0
        }

        # Load existing trades
        self.load_from_file()

    def enable(self):
        """Enable shadow mode"""
        self.enabled = True
        logger.info("✅ Shadow mode ENABLED - Trades will be logged, not executed")

    def disable(self):
        """Disable shadow mode"""
        self.enabled = False
        logger.info("⚠️ Shadow mode DISABLED - Trades will be EXECUTED LIVE")

    def is_enabled(self) -> bool:
        """Check if shadow mode is enabled"""
        return self.enabled

    def log_proposed_trade(self, trade: ProposedTrade):
        """
        Log a proposed trade.

        Args:
            trade: Proposed trade to log
        """
        if not self.enabled:
            logger.warning("Shadow mode disabled - trade should be executed, not logged")
            return

        # Mark as shadow mode
        trade.shadow_mode = True
        trade.executed = False

        # Add to list
        self.proposed_trades.append(trade)

        # Save to file
        self.save_to_file()

        logger.info(f"📝 Shadow trade logged: {trade.symbol} {trade.direction} @ {trade.entry_price}")

    def simulate_close_trade(
        self,
        trade: ProposedTrade,
        exit_price: float,
        exit_time: datetime
    ) -> Dict:
        """
        Simulate closing a shadow trade (for performance tracking).

        Args:
            trade: The shadow trade to close
            exit_price: Simulated exit price
            exit_time: Exit timestamp

        Returns:
            Dict with P&L results
        """
        try:
            # Calculate P&L
            if trade.direction == 1:  # Long
                pnl_pct = (exit_price - trade.entry_price) / trade.entry_price
            else:  # Short
                pnl_pct = (trade.entry_price - exit_price) / trade.entry_price

            # Update performance
            self.shadow_performance['total_trades'] += 1

            if pnl_pct > 0:
                self.shadow_performance['wins'] += 1
            else:
                self.shadow_performance['losses'] += 1

            self.shadow_performance['total_pnl'] += pnl_pct

            # Recalculate win rate
            total = self.shadow_performance['total_trades']
            self.shadow_performance['win_rate'] = self.shadow_performance['wins'] / total if total > 0 else 0

            result = {
                'symbol': trade.symbol,
                'entry_price': trade.entry_price,
                'exit_price': exit_price,
                'pnl_pct': pnl_pct,
                'pnl_pips': abs(exit_price - trade.entry_price) * 10000,  # For forex
                'direction': trade.direction,
                'entry_time': trade.timestamp,
                'exit_time': exit_time,
                'outcome': 'win' if pnl_pct > 0 else 'loss'
            }

            logger.info(f"📊 Shadow trade closed: {trade.symbol} {result['outcome']} "
                       f"({pnl_pct*100:+.2f}%)")

            return result

        except Exception as e:
            logger.error(f"Error simulating trade close: {e}")
            return {}

    def get_shadow_performance(self) -> Dict:
        """Get shadow trading performance metrics"""
        return self.shadow_performance.copy()

    def print_performance(self):
        """Print shadow trading performance"""
        perf = self.shadow_performance

        print("\n" + "="*60)
        print("🔮 SHADOW MODE PERFORMANCE")
        print("="*60)
        print(f"Total Trades: {perf['total_trades']}")
        print(f"Wins: {perf['wins']}")
        print(f"Losses: {perf['losses']}")
        print(f"Win Rate: {perf['win_rate']*100:.1f}%")
        print(f"Total P&L: {perf['total_pnl']*100:+.2f}%")
        print(f"Avg per Trade: {(perf['total_pnl']/perf['total_trades']*100 if perf['total_trades'] > 0 else 0):+.2f}%")
        print("="*60 + "\n")

    def save_to_file(self):
        """Save shadow trades to file"""
        try:
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            data = {
                'shadow_mode_enabled': self.enabled,
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'performance': self.shadow_performance,
                'trades': [trade.to_dict() for trade in self.proposed_trades]
            }

            with open(self.log_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Error saving shadow trades: {e}")

    def load_from_file(self):
        """Load shadow trades from file"""
        try:
            if not os.path.exists(self.log_file):
                return

            with open(self.log_file, 'r') as f:
                data = json.load(f)

            self.shadow_performance = data.get('performance', self.shadow_performance)

            # Note: trades are not reconstructed (just kept in file)
            logger.info(f"Loaded shadow mode data from {self.log_file}")

        except Exception as e:
            logger.error(f"Error loading shadow trades: {e}")

    def compare_with_live(self, live_performance: Dict) -> Dict:
        """
        Compare shadow performance with live trading.

        Args:
            live_performance: Live trading performance metrics

        Returns:
            Comparison dict
        """
        shadow_perf = self.shadow_performance
        live_wr = live_performance.get('win_rate', 0)
        shadow_wr = shadow_perf.get('win_rate', 0)

        live_pnl = live_performance.get('total_pnl', 0)
        shadow_pnl = shadow_perf.get('total_pnl', 0)

        return {
            'shadow_win_rate': shadow_wr,
            'live_win_rate': live_wr,
            'win_rate_diff': shadow_wr - live_wr,
            'shadow_pnl': shadow_pnl,
            'live_pnl': live_pnl,
            'pnl_diff': shadow_pnl - live_pnl,
            'shadow_better': shadow_pnl > live_pnl,
            'recommendation': 'Consider deploying shadow strategy' if shadow_pnl > live_pnl * 1.2 else 'Keep testing'
        }

    def clear_trades(self):
        """Clear all shadow trades"""
        self.proposed_trades.clear()
        self.shadow_performance = {
            'total_trades': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0
        }
        self.save_to_file()
        logger.info("Shadow trades cleared")


class ShadowModeToggle:
    """
    Global shadow mode toggle.

    Controls shadow mode across all trading modules.
    """

    _shadow_enabled = True  # Start in shadow mode (safe default)

    @classmethod
    def enable_shadow_mode(cls):
        """Enable shadow mode globally"""
        cls._shadow_enabled = True
        print("\n" + "="*60)
        print("🔮 SHADOW MODE ENABLED")
        print("="*60)
        print("All trades will be LOGGED, not EXECUTED")
        print("This is SAFE for testing new strategies")
        print("="*60 + "\n")

    @classmethod
    def disable_shadow_mode(cls):
        """Disable shadow mode globally (LIVE TRADING)"""
        cls._shadow_enabled = False
        print("\n" + "="*60)
        print("⚠️  LIVE TRADING MODE ENABLED ⚠️")
        print("="*60)
        print("Trades will be EXECUTED on MT5")
        print("REAL MONEY AT RISK")
        print("="*60 + "\n")

    @classmethod
    def is_shadow_mode(cls) -> bool:
        """Check if shadow mode is enabled"""
        return cls._shadow_enabled

    @classmethod
    def get_status(cls) -> str:
        """Get shadow mode status string"""
        if cls._shadow_enabled:
            return "🔮 SHADOW MODE (Safe - Logging Only)"
        else:
            return "⚠️ LIVE TRADING (Real Money)"
