# execution/alpaca.py
"""Alpaca paper-trading adapter (stdlib urllib, no new dependencies).

Real trading stays blocked behind user-supplied credentials: this adapter
is inert until ALPACA_API_KEY_ID / ALPACA_API_SECRET_KEY are present in
the environment, and defaults to Alpaca's paper endpoint. It never logs
or persists keys.
"""
import json
import time
import urllib.error
import urllib.request
import uuid

from execution.broker import (
    AccountInfo,
    BrokerError,
    BrokerOrder,
    OrderRejected,
    Position,
)

PAPER_BASE_URL = "https://paper-api.alpaca.markets/v2"
RETRYABLE_ERRORS = (urllib.error.URLError, TimeoutError, ConnectionError)


class AlpacaBroker:
    def __init__(self, key_id: str, secret_key: str, base_url: str = PAPER_BASE_URL,
                 timeout: float = 15.0, max_retries: int = 2):
        if not key_id or not secret_key:
            raise BrokerError("Alpaca credentials are required")
        self.key_id = key_id
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    @classmethod
    def from_env(cls, base_url: str = PAPER_BASE_URL) -> "AlpacaBroker":
        import os
        key_id = os.environ.get("ALPACA_API_KEY_ID", "")
        secret_key = os.environ.get("ALPACA_API_SECRET_KEY", "")
        if not key_id or not secret_key:
            raise BrokerError(
                "Set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY in the environment "
                "to enable the broker adapter (paper-trading keys recommended first)"
            )
        return cls(key_id=key_id, secret_key=secret_key, base_url=base_url)

    @property
    def is_paper(self) -> bool:
        return "paper" in self.base_url

    def _headers(self) -> dict:
        return {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        last_error = None
        for attempt in range(self.max_retries + 1):
            req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode()
                    return json.loads(raw) if raw else {}
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                if e.code in (429,) or e.code >= 500 or e.code == 404:
                    last_error = BrokerError(f"Alpaca {e.code} on {method} {path}: {detail[:300]}")
                else:
                    raise OrderRejected(
                        f"Alpaca rejected {method} {path} ({e.code}): {detail[:300]}"
                    ) from e
            except RETRYABLE_ERRORS as e:
                last_error = BrokerError(f"Alpaca connection error on {method} {path}: {e}")
            if attempt < self.max_retries:
                time.sleep(0.5 * (2 ** attempt))
        raise last_error or BrokerError(f"Alpaca request failed: {method} {path}")

    def account(self) -> AccountInfo:
        data = self._request("GET", "/account")
        return AccountInfo(
            equity=_to_float(data.get("equity")),
            cash=_to_float(data.get("cash")),
            buying_power=_to_float(data.get("buying_power")),
        )

    def positions(self) -> list:
        data = self._request("GET", "/positions")
        return [
            Position(
                symbol=p.get("symbol"),
                quantity=_to_float(p.get("qty")),
                avg_entry_price=_to_float(p.get("avg_entry_price")),
                market_value=_to_float(p.get("market_value")),
                unrealized_pl=_to_float(p.get("unrealized_pl")),
            )
            for p in data
        ]

    def submit_order(self, order: BrokerOrder) -> dict:
        payload = order_payload(order, client_order_id=order.client_order_id or str(uuid.uuid4()))
        return self._request("POST", "/orders", body=payload)

    def close_position(self, symbol: str) -> dict:
        return self._request("DELETE", f"/positions/{symbol}")


def _to_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def order_payload(order: BrokerOrder, client_order_id: str) -> dict:
    payload = {
        "symbol": order.symbol,
        "qty": f"{order.quantity:.4f}".rstrip("0").rstrip("."),
        "side": order.side,
        "type": order.order_type,
        "time_in_force": order.time_in_force,
        "client_order_id": client_order_id,
    }
    if order.order_type == "limit":
        payload["limit_price"] = f"{order.limit_price:.2f}"
    return payload
