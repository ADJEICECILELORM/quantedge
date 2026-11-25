# shadow/compare_report.py
"""Compare a finalized shadow run against backtest expectations.

Turns the Nov 27 verdict into a mechanical check: given the shadow
state.json and journal.jsonl (fetch them from the shadow-trading /
shadow-crypto branches), compute realized stats and grade each one
against expected ranges supplied on the CLI. PASS/FAIL lines make the
deploy/don't-deploy call explicit instead of eyeballed.

Usage:
  python shadow/compare_report.py \
      --state shadow-state/state.json --journal shadow-state/journal.jsonl \
      --expect-trades-min 1 --expect-pnl-min -500 \
      --expect-win-rate-min 20 --expect-pf-min 0.9
"""
import argparse
import json
import os


def load_journal(path: str) -> list:
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def closed_trades(journal: list) -> list:
    return [r for r in journal if r.get("type") == "close"]


def summarize_shadow(state: dict, journal: list) -> dict:
    trades = closed_trades(journal)
    start = float(state.get("start_equity", 10000.0))
    end = float(state.get("equity", start))
    wins = [t for t in trades if t.get("pnl_usd", 0) > 0]
    gross_win = sum(t.get("pnl_usd", 0) for t in wins)
    gross_loss = -sum(t.get("pnl_usd", 0) for t in trades if t.get("pnl_usd", 0) <= 0)
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")
    opened = len([r for r in journal if r.get("type") == "open"])
    per_symbol = {}
    for t in trades:
        per_symbol[t["symbol"]] = per_symbol.get(t["symbol"], 0.0) + t.get("pnl_usd", 0)
    journal_equity = start + sum(t.get("pnl_usd", 0) for t in trades)
    longest_streak, streak = 0, 0
    for t in trades:
        if t.get("pnl_usd", 0) <= 0:
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0
    days = max(1, _run_days(state))
    return {
        "finalized": bool(state.get("finalized")),
        "n_opens": opened,
        "n_trades": len(trades),
        "pnl_usd": round(end - start, 2),
        "return_pct": round((end - start) / start * 100, 2),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 1) if trades else None,
        "profit_factor": round(pf, 2) if gross_loss > 0 else None,
        "longest_losing_streak": longest_streak,
        "pnl_per_symbol": {k: round(v, 2) for k, v in per_symbol.items()},
        "equity_discrepancy_usd": round(end - journal_equity, 2),
        "run_days": days,
        "trades_per_day": round(len(trades) / days, 2),
    }


def _run_days(state: dict) -> float:
    started = state.get("started_at")
    ended = state.get("finalized_at")
    if not started or not ended:
        return 1.0
    from datetime import datetime
    try:
        delta = datetime.fromisoformat(ended) - datetime.fromisoformat(started)
        return max(1.0, delta.total_seconds() / 86400.0)
    except ValueError:
        return 1.0


def compare(realized: dict, expectations: dict) -> list:
    """expectations: {check_name: (operator, threshold)} resolved from CLI."""
    results = []
    for name, (op, threshold) in expectations.items():
        value = realized.get(name)
        if value is None:
            results.append((name, value, threshold, "SKIP", "no data"))
            continue
        if op == "min":
            ok = value >= threshold
            results.append((name, value, f">= {threshold}", "PASS" if ok else "FAIL", ""))
        elif op == "max":
            ok = value <= threshold
            results.append((name, value, f"<= {threshold}", "PASS" if ok else "FAIL", ""))
        elif op == "is":
            ok = value == threshold
            results.append((name, value, f"== {threshold}", "PASS" if ok else "FAIL", ""))
        else:
            raise ValueError(f"unknown operator {op!r}")
    return results


def format_comparison(realized: dict, results: list) -> str:
    lines = ["# Shadow vs backtest expectations", ""]
    for key in ("finalized", "n_opens", "n_trades", "pnl_usd", "return_pct", "win_rate_pct",
                "profit_factor", "longest_losing_streak", "pnl_per_symbol",
                "equity_discrepancy_usd", "trades_per_day"):
        lines.append(f"- {key}: {realized.get(key)}")
    lines.append("")
    for name, value, threshold, verdict, note in results:
        label = f"{name} = {value}" if value is not None else name
        suffix = f" ({note})" if note else ""
        lines.append(f"- [{verdict}] {label} vs {threshold}{suffix}")
    failed = [r for r in results if r[3] == "FAIL"]
    lines.append("")
    if failed:
        lines.append(f"VERDICT: DO NOT DEPLOY - {len(failed)} expectation(s) failed")
    elif results:
        lines.append("VERDICT: expectations met (3 days is operability evidence, not profitability)")
    else:
        lines.append("VERDICT: no expectations supplied")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Shadow run vs backtest expectations")
    parser.add_argument("--state", required=True, help="path to state.json")
    parser.add_argument("--journal", required=True, help="path to journal.jsonl")
    parser.add_argument("--expect-finalized", type=str, default="true")
    parser.add_argument("--expect-trades-min", type=int, default=None)
    parser.add_argument("--expect-trades-max", type=int, default=None)
    parser.add_argument("--expect-pnl-min", type=float, default=None)
    parser.add_argument("--expect-pnl-max", type=float, default=None)
    parser.add_argument("--expect-win-rate-min", type=float, default=None)
    parser.add_argument("--expect-pf-min", type=float, default=None)
    parser.add_argument("--expect-streak-max", type=int, default=None)
    parser.add_argument("--expect-equity-diff-max", type=float, default=None,
                        help="max tolerated |state equity - journal-recomputed equity| in USD")
    parser.add_argument("--out", default=None, help="write markdown report here")
    args = parser.parse_args(argv)

    with open(args.state, "r", encoding="utf-8") as f:
        state = json.load(f)
    journal = load_journal(args.journal)
    realized = summarize_shadow(state, journal)

    expectations = {"finalized": ("is", args.expect_finalized == "true")}
    for flag, (name, op) in {
        "expect_trades_min": ("n_trades", "min"),
        "expect_trades_max": ("n_trades", "max"),
        "expect_pnl_min": ("pnl_usd", "min"),
        "expect_pnl_max": ("pnl_usd", "max"),
        "expect_win_rate_min": ("win_rate_pct", "min"),
        "expect_pf_min": ("profit_factor", "min"),
        "expect_streak_max": ("longest_losing_streak", "max"),
        "expect_equity_diff_max": ("equity_discrepancy_usd", "max"),
    }.items():
        threshold = getattr(args, flag)
        if threshold is not None:
            expectations[name] = (op, threshold)
    results = compare(realized, expectations)
    report = format_comparison(realized, results)
    print(report)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
    failed = [r for r in results if r[3] == "FAIL"]
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
