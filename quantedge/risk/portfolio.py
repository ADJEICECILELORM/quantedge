# risk/portfolio.py
"""
Portfolio-level exposure control.

Per-trade risk limits alone let many small positions add up to one large
leveraged book. This manager tracks signed notional exposure per symbol
and enforces gross (sum of absolutes) and net (directional) caps before
any order is placed - the rules-engine step institutional systems run
pre-trade.
"""


class PortfolioExposureManager:
    def __init__(self, max_gross_exposure_usd: float, max_net_exposure_usd: float):
        self.max_gross_exposure_usd = float(max_gross_exposure_usd)
        self.max_net_exposure_usd = float(max_net_exposure_usd)
        self._positions = {}

    @property
    def gross_exposure_usd(self) -> float:
        return float(sum(abs(n) for n in self._positions.values()))

    @property
    def net_exposure_usd(self) -> float:
        return float(sum(self._positions.values()))

    def signed_notional(self, notional_usd: float, direction: int) -> float:
        sign = -1.0 if int(direction) < 0 else 1.0
        return float(abs(notional_usd)) * sign

    def register_position(self, symbol: str, notional_usd: float, direction: int):
        exposure = self.signed_notional(notional_usd, direction)
        self._positions[symbol] = self._positions.get(symbol, 0.0) + exposure
        return self._positions[symbol]

    def release_position(self, symbol: str):
        removed = self._positions.pop(symbol, 0.0)
        return float(removed)

    def can_open(self, symbol: str, notional_usd: float, direction: int) -> dict:
        new_signed = self.signed_notional(notional_usd, direction)

        projected_gross = self.gross_exposure_usd + abs(new_signed)
        if projected_gross > self.max_gross_exposure_usd + 1e-9:
            return {
                "allowed": False,
                "reason": (
                    f"Gross exposure cap: ${projected_gross:,.0f} would exceed "
                    f"cap ${self.max_gross_exposure_usd:,.0f}"
                ),
            }

        projected_net = abs(self.net_exposure_usd + new_signed)
        if projected_net > self.max_net_exposure_usd + 1e-9:
            return {
                "allowed": False,
                "reason": (
                    f"Net exposure cap: ${projected_net:,.0f} would exceed "
                    f"cap ${self.max_net_exposure_usd:,.0f}"
                ),
            }

        return {
            "allowed": True,
            "reason": (
                f"Projected gross ${projected_gross:,.0f} / "
                f"net ${projected_net:,.0f} within caps"
            ),
        }
