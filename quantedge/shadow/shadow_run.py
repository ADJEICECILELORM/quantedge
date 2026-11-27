# shadow/shadow_run.py
"""
Shadow-mode paper trading loop for the 3-pair momentum basket.

Designed for GitHub Actions: every invocation is one short "tick" that
1) fetches fresh daily OHLCV from Yahoo for the basket,
2) evaluates the validated SMA20/50 momentum signal on the latest
   completed daily bar (never the in-progress one),
3) flips notional positions when the signal changes, sizing exactly like
   BacktestEngine (risk_per_trade / (SL_ATR_multiple * ATR)),
4) journals every round-trip and updates state,
5) stops and writes a final report once the deadline (default 72h) passes.

State and journal live next to this script (shadow/), committed back to
the state branch by the workflow, so the experiment survives across runs.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.strategies import FeatureSignMomentum
from features.feature_engineer import FeatureEngineer
from utils.config import load_config
from utils.download_history import fetch_yahoo_ohlcv

YAHOO_SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
}

# Runtime basket (mutated by main() from CLI args); defaults to the FX basket
SYMBOL_MAP = dict(YAHOO_SYMBOLS)
SIGNAL_FEATURE = "sma_cross"

INCOMPLETE_GRACE_MINUTES = 60  # a daily bar younger than this is treated as in-progress


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_state(state_path: str) -> dict:
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state_path: str, state: dict) -> None:
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def _append_journal(journal_path: str, record: dict) -> None:
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


def latest_completed_bars(df, now):
    """Drop the in-progress daily bar: a row dated 'today' (UTC) or younger
    than the grace window is not a completed session."""
    if df is None or len(df) == 0:
        return df
    last_time = df["time"].iloc[-1]
    hours_old = (now - last_time.to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds() / 3600.0
    if 0 <= hours_old < 23.0:
        return df.iloc[:-1]
    return df


def _finite_positive(value) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return v == v and v > 0


def evaluate_signal(symbol: str, now):
    """Return signal + sizing inputs for one pair on its latest completed
    daily bar, or None on fetch/feature failure."""
    try:
        df = fetch_yahoo_ohlcv(SYMBOL_MAP[symbol], interval="1d", range_="180d")
    except Exception as e:
        print(f"[{symbol}] fetch failed: {e}")
        return None
    df = latest_completed_bars(df, now)
    if df is None or len(df) < 60:
        print(f"[{symbol}] not enough completed bars")
        return None
    try:
        feats = FeatureEngineer().create_features(df)
    except Exception as e:
        print(f"[{symbol}] feature engineering failed: {e}")
        return None
    if len(feats) == 0:
        return None
    row = feats.iloc[-1]
    signal = FeatureSignMomentum(feature=SIGNAL_FEATURE, confidence=0.9).predict(feats.iloc[[-1]])
    atr = row.get("atr_14")
    atr_ok = _finite_positive(atr)
    return {
        "direction": int(signal["direction"]) if (signal["direction"] != 0 and atr_ok) else 0,
        "price": float(df["close"].iloc[-1]),
        "bar_time": str(df["time"].iloc[-1]),
        "atr": float(atr) if atr_ok else None,
    }


def close_position(symbol: str, position: dict, price: dict, equity: float, cfg,
                   journal_path: str, reason: str) -> float:
    units = position["units"]
    raw_pnl = (price["price"] - position["entry_price"]) * units * position["direction"]
    commission = cfg["backtest"]["commission_per_lot_usd"] * (units / 100000.0)
    pnl = raw_pnl - commission
    _append_journal(journal_path, {
        "type": "close",
        "symbol": symbol,
        "direction": position["direction"],
        "entry_price": position["entry_price"],
        "exit_price": price["price"],
        "units": units,
        "pnl_usd": round(pnl, 2),
        "reason": reason,
        "ts": _now().isoformat(),
    })
    return equity + pnl


def tick(state: dict, cfg, state_path: str, journal_path: str, now) -> dict:
    for symbol in sorted(SYMBOL_MAP):
        signal = evaluate_signal(symbol, now)
        if signal is None:
            continue
        last_bar = state["signals"].get(symbol, {}).get("bar_time")
        # Always refresh the recorded signal first: it is the mark-to-market
        # source for open positions. Trade actions below still require a NEW
        # completed bar.
        state["signals"][symbol] = {
            "direction": signal["direction"],
            "price": signal["price"],
            "bar_time": signal["bar_time"],
        }
        if last_bar == signal["bar_time"]:
            continue  # no completed new bar since last tick

        position = state["positions"].get(symbol)
        if position and position["direction"] != signal["direction"]:
            state["equity"] = close_position(symbol, position, signal, state["equity"], cfg,
                                             journal_path, reason="signal_flip")
            del state["positions"][symbol]
            position = None

        if not position and signal["direction"] != 0 and signal.get("atr"):
            risk = state["equity"] * cfg["account"]["risk_per_trade"]
            sl_distance = signal["atr"] * cfg["backtest"]["atr_sl_multiple"]
            if sl_distance > 0:
                units = risk / sl_distance
                spread = cfg["backtest"]["spread_fraction"] * signal["price"]
                slip = cfg["backtest"]["slippage_fraction"] * signal["price"]
                entry_price = signal["price"] + spread + slip if signal["direction"] == 1 \
                    else signal["price"] - spread - slip
                commission = cfg["backtest"]["commission_per_lot_usd"] * (units / 100000.0)
                state["equity"] -= commission
                state["positions"][symbol] = {
                    "direction": signal["direction"],
                    "entry_price": entry_price,
                    "units": units,
                    "entry_ts": _now().isoformat(),
                    "entry_bar": signal["bar_time"],
                }
                _append_journal(journal_path, {
                    "type": "open",
                    "symbol": symbol,
                    "direction": signal["direction"],
                    "entry_price": entry_price,
                    "units": units,
                    "bar_time": signal["bar_time"],
                    "ts": _now().isoformat(),
                })

    # Mark open positions to market (last completed bar prices). Realized
    # equity (state["equity"]) is intentionally UNTOUCHED — closes are the
    # only thing that moves it; marked_equity is reporting-only.
    unrealized = 0.0
    for symbol, position in state.get("positions", {}).items():
        sig = state.get("signals", {}).get(symbol)
        if sig is None or position.get("entry_price") is None:
            continue
        unrealized += (sig["price"] - position["entry_price"]) \
            * position["units"] * position["direction"]
    state["unrealized"] = round(unrealized, 2)
    state["marked_equity"] = round(state["equity"] + unrealized, 2)
    return state


def finalize(state: dict, cfg, journal_path: str, report_path: str, state_path: str) -> None:
    now = _now()
    for symbol, position in list(state.get("positions", {}).items()):
        signal = evaluate_signal(symbol, now)
        if signal is None:
            continue
        state["equity"] = close_position(symbol, position, signal, state["equity"], cfg,
                                         journal_path, reason="experiment_end")
        del state["positions"][symbol]

    trades = []
    if os.path.exists(journal_path):
        with open(journal_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if rec["type"] == "close":
                    trades.append(rec)

    wins = [t for t in trades if t["pnl_usd"] > 0]
    gross_win = sum(t["pnl_usd"] for t in wins)
    gross_loss = -sum(t["pnl_usd"] for t in trades if t["pnl_usd"] <= 0)
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")

    start_equity = state.get("start_equity", 10000.0)
    lines = [
        "# Shadow experiment report",
        "",
        f"Started: {state.get('started_at')} | Ended: {now.isoformat()}",
        f"Deadline: {state.get('deadline_hours')}h | Basket: {', '.join(sorted(SYMBOL_MAP))}",
        "",
        f"- Start equity: ${start_equity:,.2f}",
        f"- End equity:   ${state['equity']:,.2f}",
        f"- Total PnL: ${state['equity'] - start_equity:+,.2f}",
    ]
    if trades:
        lines.append(f"- Closed trades: {len(trades)} | Win rate: {len(wins) / len(trades) * 100:.1f}%")
        lines.append(f"- Profit factor: {pf:.2f}")
    else:
        lines.append("- No closed trades")
    lines += [
        "",
        f"This was a 72-hour paper run of the {state.get('feature', SIGNAL_FEATURE)} momentum basket.",
        "Three days is evidence of operability, NOT of profitability -",
        "see CHANGELOG for the 15-year statistical verdict.",
    ]
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    state["finalized"] = True
    state["finalized_at"] = now.isoformat()
    _save_state(state_path, state)
    print(f"Experiment finalized. Equity {state['equity']:.2f}, {len(trades)} closed trades.")
    print(f"Report: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="Shadow-mode momentum paper trading tick")
    parser.add_argument("--state-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--deadline-hours", type=float, default=72.0)
    parser.add_argument("--report", default=None)
    parser.add_argument("--symbols", nargs="+", default=None,
                        help="Yahoo symbol ids (e.g. BTC-USD ETH-USD); default FX basket")
    parser.add_argument("--feature", default=None,
                        help="FeatureSignMomentum feature (default sma_cross)")
    parser.add_argument("--spread-fraction", type=float, default=None)
    parser.add_argument("--slippage-fraction", type=float, default=None)
    parser.add_argument("--commission-per-lot", type=float, default=None)
    args = parser.parse_args()

    global SYMBOL_MAP, SIGNAL_FEATURE
    if args.symbols:
        SYMBOL_MAP = {s.strip().upper(): s.strip() for s in args.symbols}
    if args.feature:
        SIGNAL_FEATURE = args.feature

    os.makedirs(args.state_dir, exist_ok=True)
    state_path = os.path.join(args.state_dir, "state.json")
    journal_path = os.path.join(args.state_dir, "journal.jsonl")
    report_path = args.report or os.path.join(args.state_dir, "shadow_report.md")

    cfg = load_config()
    if args.spread_fraction is not None:
        cfg["backtest"]["spread_fraction"] = args.spread_fraction
    if args.slippage_fraction is not None:
        cfg["backtest"]["slippage_fraction"] = args.slippage_fraction
    if args.commission_per_lot is not None:
        cfg["backtest"]["commission_per_lot_usd"] = args.commission_per_lot

    state = _load_state(state_path)
    now = _now()

    started_raw = state.get("started_at")
    if not state:
        started = now
        state = {
            "started_at": started.isoformat(),
            "deadline_hours": args.deadline_hours,
            "start_equity": float(cfg["account"]["balance"]),
            "equity": float(cfg["account"]["balance"]),
            "positions": {},
            "signals": {},
            "finalized": False,
            "symbols": sorted(SYMBOL_MAP),
            "feature": SIGNAL_FEATURE,
        }
        _save_state(state_path, state)
        print(f"Initialized shadow experiment (deadline {args.deadline_hours}h)")
    else:
        started = datetime.fromisoformat(str(started_raw))
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

    expired = (now - started).total_seconds() >= state.get("deadline_hours", 72.0) * 3600.0

    if state.get("finalized"):
        print("Experiment already finalized - no-op")
        return 0
    if expired:
        finalize(state, cfg, journal_path, report_path, state_path)
        return 0

    state = tick(state, cfg, state_path, journal_path, now)
    _save_state(state_path, state)
    remaining = max(0.0, (state.get("deadline_hours", 72.0) * 3600.0 - (now - started).total_seconds()) / 3600.0)
    print(f"Tick complete. Equity {state['equity']:.2f}, "
          f"open positions: {list(state['positions'])}, "
          f"{remaining:.1f}h remaining")
    return 0


if __name__ == "__main__":
    sys.exit(main())
