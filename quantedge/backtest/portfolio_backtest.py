# backtest/portfolio_backtest.py
"""
Multi-symbol portfolio backtest.

Runs each symbol through the single-symbol BacktestEngine (same sizing,
same fills), then evaluates the portfolio as an institution would:
combined equity curve on a shared calendar, portfolio metrics, a
Monte Carlo robustness check on combined trade PnL, a correlation gate
(pairwise return correlations vs risk.max_correlation) and a gross
concurrent-exposure check vs risk.max_gross_exposure_usd.

Per-symbol engines each size off the full starting equity, so combined
exposure can legitimately breach the cap - the point of the check is to
surface that before live trading does.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import compute_metrics, format_report
from backtest.validation import format_robustness_report, robustness_report
from utils.config import load_config


@dataclass
class PortfolioResult:
    per_symbol: dict = field(default_factory=dict)
    combined_equity: pd.Series = None
    combined_trades: pd.DataFrame = None
    metrics: dict = field(default_factory=dict)
    correlation_matrix: pd.DataFrame = None
    correlation_violations: list = field(default_factory=list)
    exposure_violations: list = field(default_factory=list)
    robustness: dict = field(default_factory=dict)
    initial_equity: float = 0.0


def _close_returns(df: pd.DataFrame) -> pd.Series:
    return df.set_index("time")["close"].pct_change()


class PortfolioBacktest:
    def __init__(self, df_by_symbol: dict, config: dict = None, initial_equity: float = None,
                 inference_map: dict = None):
        if not df_by_symbol:
            raise ValueError("df_by_symbol must contain at least one symbol")
        self.config = config or load_config()
        self.initial_equity = (
            initial_equity
            if initial_equity is not None
            else float(self.config["account"]["balance"])
        )
        self.df_by_symbol = df_by_symbol
        self.inference_map = inference_map or {}

    def run(self, seed=7) -> PortfolioResult:
        per_symbol = {}
        for symbol, df in self.df_by_symbol.items():
            engine = BacktestEngine(
                df,
                symbol=symbol,
                config=self.config,
                initial_equity=self.initial_equity,
                inference=self.inference_map.get(symbol),
            )
            per_symbol[symbol] = engine.run()

        combined_equity = self._combine_equity(per_symbol)
        combined_trades = self._combine_trades(per_symbol)

        bt_cfg = self.config["backtest"]
        metrics = compute_metrics(
            combined_equity, combined_trades, bt_cfg.get("bars_per_year", 28800)
        )
        metrics["symbols"] = ",".join(per_symbol.keys())

        returns_by_symbol = {
            sym: _close_returns(df) for sym, df in self.df_by_symbol.items()
        }
        corr = pd.DataFrame(returns_by_symbol).corr()
        violations = []
        max_corr = float(self.config["risk"].get("max_correlation", 0.7))
        symbols = list(corr.columns)
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                c = float(corr.iloc[i, j])
                if abs(c) > max_corr:
                    violations.append((symbols[i], symbols[j], round(c, 3)))

        gross_violations = self._check_gross_exposure(per_symbol)

        robustness = {}
        if len(combined_trades) > 0:
            returns = combined_equity.pct_change().dropna()
            robustness = robustness_report(
                combined_trades,
                self.initial_equity,
                returns=returns,
                n_paths=int(bt_cfg.get("mc_paths", 10000)),
                ruin_drawdown_pct=float(bt_cfg.get("ruin_drawdown_pct", 50.0)),
                seed=seed,
            )

        return PortfolioResult(
            per_symbol=per_symbol,
            combined_equity=combined_equity,
            combined_trades=combined_trades,
            metrics=metrics,
            correlation_matrix=corr,
            correlation_violations=violations,
            exposure_violations=gross_violations,
            robustness=robustness,
            initial_equity=self.initial_equity,
        )

    def _combine_equity(self, per_symbol: dict) -> pd.Series:
        curves = {}
        for symbol, result in per_symbol.items():
            curves[symbol] = result.equity_curve - self.initial_equity
        deltas = pd.DataFrame(curves).ffill().fillna(0.0)
        combined = self.initial_equity + deltas.sum(axis=1)
        combined.name = "equity"
        return combined

    def _combine_trades(self, per_symbol: dict) -> pd.DataFrame:
        frames = []
        for symbol, result in per_symbol.items():
            if result.trades is not None and len(result.trades) > 0:
                trades = result.trades.copy()
                trades.insert(0, "symbol", symbol)
                frames.append(trades)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

    def _check_gross_exposure(self, per_symbol: dict) -> list:
        cap = float(self.config["risk"].get("max_gross_exposure_usd", 20000))
        events = []
        for symbol, result in per_symbol.items():
            if result.trades is None or len(result.trades) == 0:
                continue
            index = result.equity_curve.index
            for _, trade in result.trades.iterrows():
                notional = float(trade["units"]) * float(trade["entry_price"])
                events.append((index[int(trade["entry_bar"])], notional))
                exit_bar = trade["exit_bar"]
                if exit_bar is not None and not (isinstance(exit_bar, float) and np.isnan(exit_bar)):
                    events.append((index[int(exit_bar)], -notional))

        events.sort(key=lambda e: e[0])
        running = 0.0
        peak = 0.0
        peak_time = None
        for ts, delta in events:
            running += delta
            if running > peak:
                peak = running
                peak_time = ts
        if peak > cap + 1e-9:
            return [
                f"Peak concurrent gross notional ${peak:,.0f} at {peak_time} exceeded "
                f"cap ${cap:,.0f} - reduce risk_per_trade or max_lot for multi-symbol deployment"
            ]
        return []


def format_portfolio_report(result: PortfolioResult) -> str:
    lines = ["=" * 60, "PORTFOLIO BACKTEST REPORT", "=" * 60]
    for symbol, r in result.per_symbol.items():
        lines.append(format_report(r.metrics, symbol))
    lines.append(format_report(result.metrics, "PORTFOLIO"))

    if result.correlation_violations:
        lines += ["", "⚠️ Correlation gate violations (risk.max_correlation):"]
        for a, b, c in result.correlation_violations:
            lines.append(f"  {a} / {b}: {c:+.2f}")
    else:
        lines += ["", "Correlation gate: all pairs within limit"]

    if result.exposure_violations:
        lines += ["", "⚠️ Exposure cap violations:"]
        lines += [f"  {v}" for v in result.exposure_violations]

    if result.robustness:
        lines += ["", format_robustness_report(result.robustness, "PORTFOLIO")]

    return "\n".join(lines)
