# utils/execution_quality.py
"""
Transaction-cost analysis: measures how much worse your real fills are
than your backtest assumptions. Backtests assume a fixed spread + slippage;
live fills differ, and the gap decides whether backtest edge survives
contact with the market.

The bot records (intended vs actual) fill prices on every live order;
this module turns the log into slippage statistics and a cost-model
verdict.
"""
import json
import os
from datetime import datetime, timezone

import numpy as np


def _log_path(path: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return path


class ExecutionQualityTracker:
    """
    Appends fill records to a JSONL file and summarizes slippage.

    One record: {"ts", "symbol", "direction", "intended_price",
    "actual_price", "order_type"}. Slippage is signed from the trader's
    perspective: positive = filled worse than intended.
    """

    def __init__(self, path: str = "data/execution_fills.jsonl"):
        self.path = _log_path(path)

    def record_fill(self, symbol: str, direction: int, intended_price: float,
                    actual_price: float, order_type: str = "market") -> float:
        direction = int(direction)
        intended = float(intended_price)
        actual = float(actual_price)
        if direction == -1:
            slippage = intended - actual
        else:
            slippage = actual - intended

        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "direction": direction,
            "intended_price": intended,
            "actual_price": actual,
            "order_type": order_type,
            "slippage": slippage,
            "slippage_fraction": slippage / intended if intended else 0.0,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return slippage

    def summarize(self, symbol: str = None) -> dict:
        if not os.path.exists(self.path):
            return {"n_fills": 0}
        records = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if symbol is None or rec.get("symbol") == symbol:
                    records.append(rec)

        if not records:
            return {"n_fills": 0}

        slips = np.array([r["slippage"] for r in records], dtype=float)
        fracs = np.array([r["slippage_fraction"] for r in records], dtype=float)
        return {
            "n_fills": len(records),
            "median_slippage": float(np.median(slips)),
            "mean_slippage": float(slips.mean()),
            "p90_slippage": float(np.percentile(slips, 90)),
            "p99_slippage": float(np.percentile(slips, 99)),
            "median_slippage_fraction": float(np.median(fracs)),
            "worst_fills": sorted(
                records, key=lambda r: -r["slippage_fraction"]
            )[:5],
        }

    def compare_to_backtest(self, assumed_slippage_fraction: float, symbol: str = None) -> dict:
        stats = self.summarize(symbol)
        if stats.get("n_fills", 0) < 5:
            return {
                "verdict": "insufficient_samples",
                "n_fills": stats.get("n_fills", 0),
                "message": "Need >= 5 recorded fills to compare against backtest costs",
            }
        median = stats["median_slippage_fraction"]
        ratio = median / assumed_slippage_fraction if assumed_slippage_fraction > 0 else float("inf")
        if ratio > 3.0:
            verdict = "costs_underestimated"
        elif ratio > 1.5:
            verdict = "costs_marginal"
        else:
            verdict = "costs_within_assumption"
        return {
            "verdict": verdict,
            "n_fills": stats["n_fills"],
            "median_slippage_fraction": median,
            "assumed_slippage_fraction": assumed_slippage_fraction,
            "ratio": ratio,
            "message": (
                "Real fills are "
                f"{ratio:.1f}x the slippage assumed in backtests - "
                + (
                    "treat backtest results as optimistic"
                    if verdict == "costs_underestimated"
                    else "cost model is acceptable"
                    if verdict == "costs_marginal"
                    else "backtest cost assumptions hold"
                )
            ),
        }
