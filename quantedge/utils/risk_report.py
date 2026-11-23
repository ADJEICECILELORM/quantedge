# utils/risk_report.py
"""
Daily risk report - the mini-Aladdin view: what did we trade, why, and
how exposed are we? Reads the SQLite trade journal and renders a
markdown report with PnL attribution by symbol/regime/hour, empirical
VaR from realized trade PnL, and the daily-loss gate status.

Usage:
    from utils.trade_journal import TradeJournal
    from utils.risk_report import generate_daily_report, write_daily_report

    journal = TradeJournal()
    print(generate_daily_report(journal, equity=10000.0))
    write_daily_report(journal)   # writes reports/daily_YYYY-MM-DD.md
"""
import os
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np


def _parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None


def _var_from_pnl(pnls, quantile=0.05):
    if len(pnls) == 0:
        return None
    return float(np.quantile(np.asarray(pnls, dtype=float), quantile))


def generate_daily_report(journal, config=None, equity=None, now=None) -> str:
    config = config or {}
    now = now or datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    trades = journal.get_trades(limit=2000)
    recent = []
    for t in trades:
        ts = _parse_ts(t["ts"])
        if ts is not None:
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= day_start:
                recent.append({**t, "ts_dt": ts})

    lines = [f"# QuantEdge Daily Risk Report", f"", f"**Date (UTC):** {now:%Y-%m-%d %H:%M}"]

    if equity is not None:
        lines.append(f"**Equity:** ${equity:,.2f}")

    risk_cfg = config.get("risk", {})
    lines += ["", "## Overview", ""]
    if not recent:
        lines.append("No trades in the last 24h.")
    else:
        closed = [t for t in recent if t["pnl_usd"] is not None]
        total_pnl = sum(t["pnl_usd"] for t in closed) if closed else 0.0
        wins = [t for t in closed if t["pnl_usd"] > 0]
        win_rate = (len(wins) / len(closed) * 100) if closed else 0.0
        lines += [
            f"- Trades logged: **{len(recent)}** (closed: {len(closed)})",
            f"- Total P&L: **${total_pnl:,.2f}**",
            f"- Win rate: **{win_rate:.1f}%**",
        ]

        if equity is not None:
            daily_gate = float(risk_cfg.get("max_daily_loss_percent", 5.0))
            loss_pct = min(0.0, total_pnl) / equity * 100
            headroom = daily_gate + loss_pct
            lines.append(
                f"- Daily loss gate {daily_gate:.1f}%: "
                f"**{'at gate' if headroom <= 0 else f'{headroom:.1f}% headroom'}**"
            )

        var95 = _var_from_pnl([t["pnl_usd"] for t in closed], 0.05)
        worst = min((t["pnl_usd"] for t in closed), default=None)
        if var95 is not None:
            lines += [
                f"- Empirical VaR 95% (per trade): **${var95:,.2f}**",
                f"- Worst trade: **${worst:,.2f}**",
            ]

    def _breakdown(key, title):
        grouped = defaultdict(lambda: {"n": 0, "pnl": 0.0})
        for t in recent:
            if key == "hour":
                name = f"{t['ts_dt'].hour:02d}:00"
            else:
                name = t.get(key) or "unknown"
            grouped[name]["n"] += 1
            if t["pnl_usd"] is not None:
                grouped[name]["pnl"] += t["pnl_usd"]
        if not grouped:
            return []
        out = ["", f"## P&L by {title}", "", f"| {title} | Trades | P&L |", "|---|---|---|"]
        for name, agg in sorted(grouped.items(), key=lambda kv: -kv[1]["n"]):
            out.append(f"| {name} | {agg['n']} | ${agg['pnl']:,.2f} |")
        return out

    lines += _breakdown("symbol", "Symbol")
    lines += _breakdown("regime", "Regime")
    lines += _breakdown("hour", "Hour (UTC)")

    if recent:
        open_positions = sum(1 for t in recent if t["pnl_usd"] is None)
        lines += [
            "",
            "## Stress scenario notes",
            "",
            f"- Open (unclosed) logged positions: **{open_positions}**",
            "- Spread-stress assumption: costs model 10x spread widening at news; "
            "verify live fills against backtest slippage assumptions",
        ]

    limits = [
        ("max_daily_loss_percent", risk_cfg.get("max_daily_loss_percent")),
        ("max_correlation", risk_cfg.get("max_correlation")),
        ("max_lot", risk_cfg.get("max_lot")),
        ("max_gross_exposure_usd", risk_cfg.get("max_gross_exposure_usd")),
        ("max_net_exposure_usd", risk_cfg.get("max_net_exposure_usd")),
    ]
    active = [f"- `{k}`: {v}" for k, v in limits if v is not None]
    if active:
        lines += ["", "## Active risk limits", ""] + active

    drift = getattr(journal, "last_drift_status", None)
    if drift:
        lines += ["", f"## Model drift (last known): **{drift}**"]

    return "\n".join(lines) + "\n"


def write_daily_report(journal, config=None, out_dir: str = "reports") -> str:
    report = generate_daily_report(journal, config=config)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.abspath(os.path.join(out_dir, f"daily_{datetime.now(timezone.utc):%Y-%m-%d}.md"))
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    return path


if __name__ == "__main__":
    import argparse

    from utils.config import load_config
    from utils.trade_journal import TradeJournal

    parser = argparse.ArgumentParser(description="QuantEdge daily risk report")
    parser.add_argument("--journal", default="data/journal.db")
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    print(generate_daily_report(TradeJournal(args.journal), config=load_config(args.config)))
