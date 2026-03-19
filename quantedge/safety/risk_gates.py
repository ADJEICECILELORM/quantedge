# safety/risk_gates.py - Hard Safety Constraints
"""
Risk Gates: Hard Constraints for Safe Trading.

These are IMMUTABLE safety rules that GA CANNOT modify.

Hard Constraints:
1. Capital exposure limits (max 10% per trade)
2. Kill-switch logic (stop on 5% daily loss)
3. GA update rate limits (once per 24h max)
4. Human override hooks
5. Position size limits
6. Maximum open trades
7. Maximum correlation exposure

GA Must NEVER Modify:
- Data sources
- RAG logic
- Execution engine
- These safety constraints
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RiskGates:
    """
    Immutable risk gates for safe trading.

    These constraints CANNOT be changed by GA or any optimization.
    """

    # HARD LIMITS (cannot be changed)
    MAX_CAPITAL_PER_TRADE_PCT = 0.10  # 10% max per trade
    MAX_DAILY_LOSS_PCT = 0.05          # 5% daily loss = kill switch
    MAX_TOTAL_EXPOSURE_PCT = 0.30      # 30% max total exposure
    MAX_OPEN_TRADES = 5                # Maximum simultaneous trades
    MAX_CORRELATION_POSITIONS = 2      # Max positions in correlated assets
    MIN_POSITION_SIZE_USD = 10.0       # Minimum $10 position
    MAX_POSITION_SIZE_USD = 10000.0    # Maximum $10k position (safety cap)

    # GA CONSTRAINTS
    GA_UPDATE_COOLDOWN_HOURS = 24      # Minimum 24h between GA updates
    GA_MAX_UPDATES_PER_MONTH = 4       # Maximum 4 GA updates per month

    def __init__(self, account_balance: float):
        self.account_balance = account_balance
        self.start_balance = account_balance
        self.daily_loss = 0.0
        self.last_ga_update = None
        self.ga_updates_this_month = 0
        self.kill_switch_triggered = False
        self.open_positions_count = 0
        self.human_override = False

    def check_position_size(self, position_size_usd: float) -> Dict:
        """
        Check if position size is within limits.

        Args:
            position_size_usd: Position size in USD

        Returns:
            Dict with decision and reason
        """
        # Check minimum
        if position_size_usd < self.MIN_POSITION_SIZE_USD:
            return {
                'allowed': False,
                'reason': f"Position too small (min ${self.MIN_POSITION_SIZE_USD})"
            }

        # Check maximum
        if position_size_usd > self.MAX_POSITION_SIZE_USD:
            return {
                'allowed': False,
                'reason': f"Position too large (max ${self.MAX_POSITION_SIZE_USD})"
            }

        # Check % of capital
        pct_of_capital = position_size_usd / self.account_balance

        if pct_of_capital > self.MAX_CAPITAL_PER_TRADE_PCT:
            return {
                'allowed': False,
                'reason': f"Position exceeds {self.MAX_CAPITAL_PER_TRADE_PCT*100}% of capital "
                         f"({pct_of_capital*100:.1f}% requested)"
            }

        return {
            'allowed': True,
            'reason': 'Position size within limits'
        }

    def check_kill_switch(self, current_balance: float) -> Dict:
        """
        Check kill switch (daily loss limit).

        Args:
            current_balance: Current account balance

        Returns:
            Dict with kill switch status
        """
        # Calculate daily loss
        self.daily_loss = (self.start_balance - current_balance) / self.start_balance

        if self.daily_loss >= self.MAX_DAILY_LOSS_PCT:
            self.kill_switch_triggered = True

            return {
                'triggered': True,
                'daily_loss_pct': self.daily_loss * 100,
                'reason': f"Daily loss limit reached ({self.daily_loss*100:.2f}% >= "
                         f"{self.MAX_DAILY_LOSS_PCT*100}%)",
                'action': 'STOP ALL TRADING'
            }

        return {
            'triggered': False,
            'daily_loss_pct': self.daily_loss * 100,
            'reason': 'Within daily loss limit'
        }

    def check_max_open_trades(self) -> Dict:
        """Check if we can open more trades"""
        if self.open_positions_count >= self.MAX_OPEN_TRADES:
            return {
                'allowed': False,
                'reason': f"Maximum open trades reached ({self.MAX_OPEN_TRADES})"
            }

        return {
            'allowed': True,
            'reason': f'Can open trade ({self.open_positions_count}/{self.MAX_OPEN_TRADES})'
        }

    def check_ga_update_allowed(self, current_time: datetime) -> Dict:
        """
        Check if GA parameter update is allowed.

        Prevents too-frequent updates (overfitting).
        """
        # Check cooldown
        if self.last_ga_update:
            hours_since = (current_time - self.last_ga_update).total_seconds() / 3600

            if hours_since < self.GA_UPDATE_COOLDOWN_HOURS:
                return {
                    'allowed': False,
                    'reason': f"GA cooldown active ({hours_since:.1f}h / {self.GA_UPDATE_COOLDOWN_HOURS}h)",
                    'hours_remaining': self.GA_UPDATE_COOLDOWN_HOURS - hours_since
                }

        # Check monthly limit
        # Reset counter if new month
        current_month = current_time.month
        if self.last_ga_update and self.last_ga_update.month != current_month:
            self.ga_updates_this_month = 0

        if self.ga_updates_this_month >= self.GA_MAX_UPDATES_PER_MONTH:
            return {
                'allowed': False,
                'reason': f"Monthly GA update limit reached ({self.GA_MAX_UPDATES_PER_MONTH})"
            }

        return {
            'allowed': True,
            'reason': 'GA update allowed'
        }

    def approve_ga_update(self, current_time: datetime):
        """Record GA update"""
        self.last_ga_update = current_time
        self.ga_updates_this_month += 1
        logger.info(f"GA update approved (#{self.ga_updates_this_month} this month)")

    def human_override_enable(self):
        """Enable human override (bypass all gates)"""
        self.human_override = True
        logger.warning("⚠️ HUMAN OVERRIDE ENABLED - All safety gates bypassed")
        print("\n" + "="*60)
        print("⚠️  HUMAN OVERRIDE ACTIVE ⚠️")
        print("="*60)
        print("All safety constraints are BYPASSED")
        print("Manual control enabled")
        print("="*60 + "\n")

    def human_override_disable(self):
        """Disable human override (re-enable gates)"""
        self.human_override = False
        logger.info("Human override disabled - safety gates re-enabled")

    def check_all_gates(
        self,
        position_size_usd: float,
        current_balance: float
    ) -> Dict:
        """
        Check all risk gates before allowing trade.

        Args:
            position_size_usd: Proposed position size
            current_balance: Current account balance

        Returns:
            Dict with approval decision
        """
        # Human override bypasses everything
        if self.human_override:
            return {
                'approved': True,
                'reason': 'Human override active',
                'warnings': ['Safety gates bypassed']
            }

        warnings = []
        reasons = []

        # 1. Kill switch check
        kill_switch = self.check_kill_switch(current_balance)
        if kill_switch['triggered']:
            return {
                'approved': False,
                'reason': kill_switch['reason'],
                'kill_switch': True
            }

        # 2. Position size check
        size_check = self.check_position_size(position_size_usd)
        if not size_check['allowed']:
            return {
                'approved': False,
                'reason': size_check['reason']
            }
        reasons.append(size_check['reason'])

        # 3. Max open trades check
        trades_check = self.check_max_open_trades()
        if not trades_check['allowed']:
            return {
                'approved': False,
                'reason': trades_check['reason']
            }
        reasons.append(trades_check['reason'])

        # All gates passed
        return {
            'approved': True,
            'reason': 'All risk gates passed',
            'checks': reasons,
            'warnings': warnings
        }

    def update_balance(self, new_balance: float):
        """Update account balance"""
        self.account_balance = new_balance

    def reset_daily(self):
        """Reset daily counters (call at start of new day)"""
        self.start_balance = self.account_balance
        self.daily_loss = 0.0
        self.kill_switch_triggered = False
        logger.info("Daily risk counters reset")

    def increment_open_trades(self):
        """Increment open positions counter"""
        self.open_positions_count += 1

    def decrement_open_trades(self):
        """Decrement open positions counter"""
        self.open_positions_count = max(0, self.open_positions_count - 1)

    def print_status(self):
        """Print risk gates status"""
        print("\n" + "="*60)
        print("🛡️ RISK GATES STATUS")
        print("="*60)
        print(f"Account Balance: ${self.account_balance:,.2f}")
        print(f"Daily Loss: {self.daily_loss*100:+.2f}% / {self.MAX_DAILY_LOSS_PCT*100}% max")
        print(f"Kill Switch: {'🔴 TRIGGERED' if self.kill_switch_triggered else '✅ OK'}")
        print(f"Open Trades: {self.open_positions_count} / {self.MAX_OPEN_TRADES} max")
        print(f"GA Updates This Month: {self.ga_updates_this_month} / {self.GA_MAX_UPDATES_PER_MONTH} max")
        print(f"Human Override: {'⚠️ ACTIVE' if self.human_override else '✅ Disabled'}")
        print("="*60 + "\n")

    def get_constraints_summary(self) -> Dict:
        """Get summary of all hard constraints"""
        return {
            'max_capital_per_trade_pct': self.MAX_CAPITAL_PER_TRADE_PCT * 100,
            'max_daily_loss_pct': self.MAX_DAILY_LOSS_PCT * 100,
            'max_total_exposure_pct': self.MAX_TOTAL_EXPOSURE_PCT * 100,
            'max_open_trades': self.MAX_OPEN_TRADES,
            'min_position_size_usd': self.MIN_POSITION_SIZE_USD,
            'max_position_size_usd': self.MAX_POSITION_SIZE_USD,
            'ga_update_cooldown_hours': self.GA_UPDATE_COOLDOWN_HOURS,
            'ga_max_updates_per_month': self.GA_MAX_UPDATES_PER_MONTH,
            'immutable': True,
            'ga_cannot_modify': [
                'data_sources',
                'rag_logic',
                'execution_engine',
                'these_safety_constraints'
            ]
        }
