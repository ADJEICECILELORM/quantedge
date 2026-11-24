import MetaTrader5 as mt5
import pytest

from utils.order_executor import OrderExecutor


class FakeTick:
    def __init__(self, ask=1.1000, bid=1.0998):
        self.ask = ask
        self.bid = bid


class FakeResult:
    def __init__(self, retcode, order=12345, price=1.1005, comment=""):
        self.retcode = retcode
        self.order = order
        self.price = price
        self.comment = comment


@pytest.fixture
def filled_terminal(monkeypatch):
    monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: FakeTick())
    monkeypatch.setattr(mt5, "order_send", lambda request: FakeResult(mt5.TRADE_RETCODE_DONE))


class TestOrderExecutor:
    def test_successful_buy_returns_fill_details(self, filled_terminal):
        result = OrderExecutor().execute_order("EURUSD", 1, 0.5, 1.09, 1.12)
        assert result["success"] is True
        assert result["ticket"] == 12345
        assert result["requested_price"] == pytest.approx(1.1000)
        assert result["fill_price"] == pytest.approx(1.1005)

    def test_sell_tick_uses_bid(self, monkeypatch):
        monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: FakeTick())
        monkeypatch.setattr(mt5, "order_send", lambda request: FakeResult(mt5.TRADE_RETCODE_DONE))
        result = OrderExecutor().execute_order("EURUSD", -1, 0.5, 1.11, 1.08)
        assert result["requested_price"] == pytest.approx(1.0998)

    def test_rejection_returns_error_dict_not_exception(self, monkeypatch):
        monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: FakeTick())
        monkeypatch.setattr(mt5, "order_send", lambda request: FakeResult(10004, comment="requote"))
        result = OrderExecutor().execute_order("EURUSD", 1, 0.5, 1.09, 1.12)
        assert result["success"] is False
        assert "10004" in result["error"]

    def test_none_order_send_handled(self, monkeypatch):
        monkeypatch.setattr(mt5, "symbol_info_tick", lambda s: FakeTick())
        monkeypatch.setattr(mt5, "order_send", lambda request: None)
        result = OrderExecutor().execute_order("EURUSD", 1, 0.5, 1.09, 1.12)
        assert result["success"] is False
        assert "None" in result["error"]

    def test_invalid_lots_rejected_before_network(self, monkeypatch):
        calls = []
        monkeypatch.setattr(mt5, "order_send", lambda request: calls.append(request))
        result = OrderExecutor().execute_order("EURUSD", 1, 0, 1.09, 1.12)
        assert result["success"] is False
        assert calls == []

    def test_wrap_send_order_returns_ticket(self, filled_terminal):
        assert OrderExecutor().send_order("EURUSD", 1, 0.5, 1.09, 1.12) == 12345
