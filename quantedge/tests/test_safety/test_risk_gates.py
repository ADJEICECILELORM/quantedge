# tests/test_safety/test_risk_gates.py
import pytest

from safety.risk_gates import RiskGates


class TestRiskGatesImmutability:
    def test_hard_limits_cannot_be_shadowed(self):
        gates = RiskGates(account_balance=10000)
        with pytest.raises(RuntimeError):
            gates.MAX_DAILY_LOSS_PCT = 0.50

    def test_class_defaults_alone_are_read_only_by_convention(self):
        gates = RiskGates(account_balance=10000)
        assert gates.MAX_DAILY_LOSS_PCT == 0.05
        assert gates.MAX_CAPITAL_PER_TRADE_PCT == 0.10
        assert gates.MAX_TOTAL_EXPOSURE_PCT == 0.30

    def test_mutable_state_still_works(self):
        gates = RiskGates(account_balance=10000)
        gates.daily_loss = 0.01
        gates.open_positions_count = 2
        assert gates.daily_loss == 0.01
        assert gates.open_positions_count == 2

    def test_kill_switch_triggers_on_daily_loss(self):
        gates = RiskGates(account_balance=10000)
        result = gates.check_kill_switch(9400)
        assert result["triggered"] is True
