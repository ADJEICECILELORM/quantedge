import io
import json
from urllib.error import HTTPError, URLError

import pytest

from execution.alpaca import AlpacaBroker, order_payload
from execution.broker import (
    AccountInfo,
    BrokerError,
    BrokerOrder,
    OrderRejected,
    Position,
    rebalance_orders,
)


class TestBrokerOrder:
    def test_valid_order(self):
        o = BrokerOrder("AAPL", 10.0, "buy")
        assert o.quantity == 10.0

    def test_rejects_bad_quantity(self):
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", 0, "buy")
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", -2, "buy")

    def test_rejects_bad_side_and_type(self):
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", 1, "hodl")
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", 1, "buy", order_type="iceberg")

    def test_limit_orders_need_price(self):
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", 1, "buy", order_type="limit")
        with pytest.raises(BrokerError):
            BrokerOrder("AAPL", 1, "buy", order_type="limit", limit_price=0)


class TestRebalanceOrders:
    def test_full_cycle(self):
        orders = rebalance_orders(
            target_weights={"AAPL": 0.2, "MSFT": -0.1},
            prices={"AAPL": 200.0, "MSFT": 400.0},
            equity=100_000.0,
            current_positions={"AAPL": 50.0},
            min_notional=10.0,
        )
        by_symbol = {o.symbol: o for o in orders}
        assert by_symbol["AAPL"].side == "buy"
        assert by_symbol["AAPL"].quantity == pytest.approx(100.0 - 50.0)
        assert by_symbol["MSFT"].side == "sell"
        assert by_symbol["MSFT"].quantity == pytest.approx(25.0)

    def test_skips_below_min_notional(self):
        orders = rebalance_orders(
            target_weights={"AAPL": 0.20001},
            prices={"AAPL": 200.0},
            equity=100_000.0,
            current_positions={"AAPL": 100.0},
            min_notional=10.0,
        )
        assert orders == []

    def test_validates_inputs(self):
        with pytest.raises(BrokerError):
            rebalance_orders({"AAPL": 0.2}, {"AAPL": 100.0}, equity=0.0, current_positions={})
        with pytest.raises(BrokerError):
            rebalance_orders({"AAPL": 0.2}, {}, equity=10000.0, current_positions={})


class TestOrderPayload:
    def test_market_payload(self):
        payload = order_payload(BrokerOrder("AAPL", 1.5, "buy"), client_order_id="abc")
        assert payload == {
            "symbol": "AAPL", "qty": "1.5", "side": "buy", "type": "market",
            "time_in_force": "gtc", "client_order_id": "abc",
        }

    def test_limit_payload(self):
        payload = order_payload(
            BrokerOrder("BTC/USD", 2.0, "buy", order_type="limit", limit_price=100.554),
            client_order_id="x",
        )
        assert payload["limit_price"] == "100.55"
        assert payload["type"] == "limit"


class TestAlpacaBroker:
    def test_from_env_requires_keys(self, monkeypatch):
        monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
        monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)
        with pytest.raises(BrokerError, match="ALPACA_API_KEY_ID"):
            AlpacaBroker.from_env()

    def test_from_env_reads_keys(self, monkeypatch):
        monkeypatch.setenv("ALPACA_API_KEY_ID", "kid")
        monkeypatch.setenv("ALPACA_API_SECRET_KEY", "sk")
        broker = AlpacaBroker.from_env()
        assert broker.is_paper

    def test_rejects_empty_credentials(self):
        with pytest.raises(BrokerError):
            AlpacaBroker(key_id="", secret_key="x")

    def _broker(self):
        return AlpacaBroker(key_id="kid", secret_key="sk")

    def test_account_parsing(self, monkeypatch):
        monkeypatch.setattr(
            AlpacaBroker, "_request",
            lambda self, method, path, body=None: {
                "equity": "100000.50", "cash": "50000.25", "buying_power": "400000.00"
            } if path == "/account" else {},
        )
        info = self._broker().account()
        assert isinstance(info, AccountInfo)
        assert info.equity == pytest.approx(100000.50)

    def test_positions_parsing(self, monkeypatch):
        raw = [{
            "symbol": "AAPL", "qty": "10", "avg_entry_price": "200.01",
            "market_value": "2000.1", "unrealized_pl": "-0.9",
        }]
        monkeypatch.setattr(AlpacaBroker, "_request", lambda self, m, p, body=None: raw)
        positions = self._broker().positions()
        assert positions == [Position("AAPL", 10.0, 200.01, 2000.1, -0.9)]

    def test_submit_order_builds_payload(self, monkeypatch):
        captured = {}

        def fake_request(self, method, path, body=None):
            captured["method"], captured["path"], captured["body"] = method, path, body
            return {"id": "order-1", "status": "accepted"}

        monkeypatch.setattr(AlpacaBroker, "_request", fake_request)
        out = self._broker().submit_order(BrokerOrder("AAPL", 1.0, "sell") )
        assert out["status"] == "accepted"
        assert captured["method"] == "POST" and captured["path"] == "/orders"
        assert captured["body"]["side"] == "sell"
        assert "client_order_id" in captured["body"]

    def test_close_position_path(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            AlpacaBroker, "_request",
            lambda self, m, p, body=None: captured.update({"method": m, "path": p}) or {},
        )
        self._broker().close_position("AAPL")
        assert captured == {"method": "DELETE", "path": "/positions/AAPL"}

    def test_request_retries_on_5xx_then_raises(self, monkeypatch):
        sleeps = []
        monkeypatch.setattr("execution.alpaca.time.sleep", lambda s: sleeps.append(s))
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise HTTPError("url", 500, "boom", {}, io.BytesIO(b"boom"))

        monkeypatch.setattr("execution.alpaca.urllib.request.urlopen", fake_urlopen)
        broker = AlpacaBroker(key_id="kid", secret_key="sk", max_retries=2)
        with pytest.raises(BrokerError, match="500"):
            broker._request("GET", "/account")
        assert calls["n"] == 3
        assert len(sleeps) == 2

    def test_request_raises_order_rejected_on_400(self, monkeypatch):
        def fake_urlopen(req, timeout=None):
            raise HTTPError(
                "url", 403, "forbidden", {}, io.BytesIO(json.dumps({"message": "not allowed"}).encode())
            )

        monkeypatch.setattr("execution.alpaca.urllib.request.urlopen", fake_urlopen)
        broker = AlpacaBroker(key_id="kid", secret_key="sk", max_retries=0)
        with pytest.raises(OrderRejected):
            broker._request("POST", "/orders", body={"symbol": "AAPL"})

    def test_request_retries_on_timeout(self, monkeypatch):
        monkeypatch.setattr("execution.alpaca.time.sleep", lambda s: None)
        calls = {"n": 0}

        def fake_urlopen(req, timeout=None):
            calls["n"] += 1
            raise URLError("timeout")

        monkeypatch.setattr("execution.alpaca.urllib.request.urlopen", fake_urlopen)
        broker = AlpacaBroker(key_id="kid", secret_key="sk", max_retries=1)
        with pytest.raises(BrokerError, match="connection error"):
            broker._request("GET", "/account")
        assert calls["n"] == 2
