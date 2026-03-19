# tests/test_utils/test_kelly_criterion.py
import pytest
from utils.kelly_criterion import KellyCriterion


class TestKellyCriterion:
    """Tests for Kelly Criterion position sizing"""

    def test_init(self):
        """Test initialization"""
        kelly = KellyCriterion(lookback=50, fraction=0.25)
        assert kelly.lookback == 50
        assert kelly.fraction == 0.25
        assert len(kelly.trade_history) == 0

    def test_add_trade_result(self):
        """Test adding trade results"""
        kelly = KellyCriterion()
        kelly.add_trade_result(100, 'win')
        kelly.add_trade_result(-50, 'loss')

        assert len(kelly.trade_history) == 2
        assert kelly.trade_history[0]['pnl'] == 100
        assert kelly.trade_history[1]['outcome'] == 'loss'

    def test_calculate_win_rate_default(self):
        """Test win rate with insufficient history"""
        kelly = KellyCriterion()
        win_rate = kelly.calculate_win_rate()
        assert win_rate == 0.55  # Default

    def test_calculate_win_rate_with_data(self, sample_trade_history):
        """Test win rate calculation with data"""
        kelly = KellyCriterion()

        for trade in sample_trade_history:
            kelly.add_trade_result(trade['pnl'], trade['outcome'])

        win_rate = kelly.calculate_win_rate()
        assert 0 <= win_rate <= 1
        assert win_rate == 0.5  # 5 wins out of 10

    def test_calculate_win_loss_ratio_default(self):
        """Test win/loss ratio with insufficient history"""
        kelly = KellyCriterion()
        ratio = kelly.calculate_win_loss_ratio()
        assert ratio == 1.5  # Default

    def test_calculate_win_loss_ratio_with_data(self, sample_trade_history):
        """Test win/loss ratio calculation"""
        kelly = KellyCriterion()

        for trade in sample_trade_history:
            kelly.add_trade_result(trade['pnl'], trade['outcome'])

        ratio = kelly.calculate_win_loss_ratio()
        assert ratio > 0
        # Average win ~135, average loss ~57, ratio should be ~2.36
        assert 2.0 < ratio < 3.0

    def test_calculate_kelly_fraction(self):
        """Test Kelly fraction calculation"""
        kelly = KellyCriterion(fraction=0.25)

        # Add winning trades
        for i in range(20):
            kelly.add_trade_result(100, 'win')
        for i in range(10):
            kelly.add_trade_result(-50, 'loss')

        fraction = kelly.calculate_kelly_fraction()

        assert 0.01 <= fraction <= 0.10  # Clamped range
        assert isinstance(fraction, float)

    def test_calculate_position_size(self):
        """Test position size calculation"""
        kelly = KellyCriterion()

        # Add sample trades
        for i in range(15):
            kelly.add_trade_result(100, 'win')
        for i in range(10):
            kelly.add_trade_result(-50, 'loss')

        result = kelly.calculate_position_size(10000, 0.02)

        assert 'kelly_fraction' in result
        assert 'risk_per_trade' in result
        assert 'recommendation' in result
        assert 'win_rate' in result
        assert 'win_loss_ratio' in result

        assert 0 < result['risk_per_trade'] <= 0.10

    def test_get_stats(self):
        """Test statistics retrieval"""
        kelly = KellyCriterion()

        for i in range(20):
            kelly.add_trade_result(100 if i % 2 == 0 else -50, 'win' if i % 2 == 0 else 'loss')

        stats = kelly.get_stats()

        assert 'kelly_fraction' in stats
        assert 'win_rate' in stats
        assert 'win_loss_ratio' in stats
        assert 'trades_tracked' in stats
        assert stats['trades_tracked'] == 20

    def test_lookback_limit(self):
        """Test that lookback limit is enforced"""
        kelly = KellyCriterion(lookback=10)

        # Add 20 trades
        for i in range(20):
            kelly.add_trade_result(100, 'win')

        # Should only keep last 10
        assert len(kelly.trade_history) == 10
