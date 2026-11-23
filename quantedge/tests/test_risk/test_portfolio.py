import pytest

from risk.portfolio import PortfolioExposureManager


def make_manager(gross=5000.0, net=3000.0):
    return PortfolioExposureManager(gross, net)


class TestPortfolioExposureManager:
    def test_register_and_totals(self):
        m = make_manager()
        m.register_position("EURUSD", 1000.0, 1)
        m.register_position("USDJPY", 500.0, -1)
        assert m.gross_exposure_usd == pytest.approx(1500.0)
        assert m.net_exposure_usd == pytest.approx(500.0)

    def test_gross_cap_blocks(self):
        m = make_manager(gross=1000.0, net=2000.0)
        m.register_position("EURUSD", 800.0, 1)
        check = m.can_open("GBPUSD", 500.0, 1)
        assert check["allowed"] is False
        assert "Gross" in check["reason"]

    def test_net_cap_blocks_directional_buildup(self):
        m = make_manager(gross=5000.0, net=1000.0)
        assert m.can_open("EURUSD", 900.0, 1)["allowed"] is True
        m.register_position("EURUSD", 900.0, 1)
        check = m.can_open("GBPUSD", 500.0, 1)
        assert check["allowed"] is False
        assert "Net" in check["reason"]

    def test_offsetting_position_reduces_net(self):
        m = make_manager(gross=5000.0, net=1000.0)
        m.register_position("EURUSD", 900.0, 1)
        check = m.can_open("EURUSD", 1200.0, -1)
        assert check["allowed"] is True

    def test_release_frees_budget(self):
        m = make_manager(gross=1500.0, net=1000.0)
        m.register_position("EURUSD", 1200.0, 1)
        assert m.can_open("GBPUSD", 500.0, 1)["allowed"] is False
        m.release_position("EURUSD")
        assert m.can_open("GBPUSD", 500.0, 1)["allowed"] is True
