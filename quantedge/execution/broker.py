# execution/broker.py
"""Broker-agnostic order and account primitives.

BrokerAdapter is the narrow interface a live/paper deployment talks to.
Concrete adapters (Alpaca paper, later MT5 bridges) implement it; the
inference pipeline stays broker-agnostic.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

VALID_SIDES = ("buy", "sell")
VALID_TYPES = ("market", "limit")


class BrokerError(Exception):
    pass


class OrderRejected(BrokerError):
    pass


@dataclass
class BrokerOrder:
    symbol: str
    quantity: float
    side: str
    order_type: str = "market"
    limit_price: float = None
    time_in_force: str = "gtc"
    client_order_id: str = None

    def __post_init__(self):
        if self.quantity <= 0:
            raise BrokerError(f"quantity must be > 0, got {self.quantity}")
        if self.side not in VALID_SIDES:
            raise BrokerError(f"side must be one of {VALID_SIDES}, got {self.side!r}")
        if self.order_type not in VALID_TYPES:
            raise BrokerError(f"order_type must be one of {VALID_TYPES}, got {self.order_type!r}")
        if self.order_type == "limit" and (self.limit_price is None or self.limit_price <= 0):
            raise BrokerError("limit orders require a positive limit_price")


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float
    market_value: float = 0.0
    unrealized_pl: float = 0.0


@dataclass
class AccountInfo:
    equity: float
    cash: float
    buying_power: float


def rebalance_orders(
    target_weights: dict,
    prices: dict,
    equity: float,
    current_positions: dict,
    min_notional: float = 1.0,
) -> list:
    """Diff a target weight portfolio against current positions.

    target_weights: {symbol: signed weight of equity} (positive long, negative short)
    prices: {symbol: reference price}
    current_positions: {symbol: signed quantity} (negative = short)
    Returns BrokerOrder list for the deltas; symbols under min_notional
    are skipped to avoid order spam on tiny drifts.
    """
    if equity <= 0:
        raise BrokerError(f"equity must be > 0, got {equity}")
    orders = []
    for symbol, weight in target_weights.items():
        price = prices.get(symbol)
        if price is None or price <= 0:
            raise BrokerError(f"missing or invalid price for {symbol!r}")
        target_qty = weight * equity / price
        current_qty = current_positions.get(symbol, 0.0)
        delta = target_qty - current_qty
        if abs(delta) * price < min_notional:
            continue
        side = "buy" if delta > 0 else "sell"
        orders.append(
            BrokerOrder(
                symbol=symbol,
                quantity=round(abs(delta), 4),
                side=side,
            )
        )
    return orders


class BrokerAdapter(ABC):
    @abstractmethod
    def account(self) -> AccountInfo: ...

    @abstractmethod
    def positions(self) -> list: ...

    @abstractmethod
    def submit_order(self, order: BrokerOrder) -> dict: ...

    @abstractmethod
    def close_position(self, symbol: str) -> dict: ...
