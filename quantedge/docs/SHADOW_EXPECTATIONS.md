# Pre-registered shadow grading thresholds

**Registered: 2026-11-25 (UTC), before either chain finalized.**
Per `docs/PLAYBOOK.md` section 4: thresholds below were fixed from the
backtests and operating logic BEFORE the shadow reports existed. They
must not be edited after seeing shadow results; if a threshold is later
felt to be "wrong", it is documented here with the reason and date, and
the run is graded under BOTH registrations.

Grading rule: `compare_report.py` exit 0 = gate 2 contribution; exit 2
= the run does NOT count as deployment evidence.

## Chain 1: FX 3-pair momentum (shadow-momentum, shadow-trading branch)

Window 12:13 UTC Nov 24 -> 12:13 UTC Nov 27 (72h). Equity $10,000,
risk 2%/trade, commission $7/lot, spread+slippage from config.json.

Backtest context: the FX 7-pair portfolio did NOT clear the validation
bar (PSR 0.869 < 0.95). This run measures operability only; a passing
grade never promotes FX to deployable.

Expectations:
- finalized == true (required)
- n_trades: 0-30 (h1-driven flips can be frequent; sanity bound only)
- pnl_usd >= -1,200 (kill analog: 1.5x backtest-window maxDD 12.6% -> ~-19% ceiling on 3 days is too generous; -12% absolute is the operability bound)
- equity_discrepancy_usd <= 30 (open commissions of ~$7/lot x units are not journaled; a few open commissions round to < $30)
- win rate / PF: NOT graded (far too few closed trades for significance)

Command (run from quantedge/ after fetching state files):
```
python shadow/compare_report.py \
  --state shadow/state.json --journal shadow/journal.jsonl \
  --expect-trades-max 30 --expect-pnl-min -1200 \
  --expect-equity-diff-max 30
```

## Chain 2: crypto-3 momentum (shadow-crypto, shadow-crypto branch)

Window 17:02 UTC Nov 24 -> 17:02 UTC Nov 27 (72h). Equity $10,000,
risk 2%/trade, spread 8bp, slippage 4bp, commission 0. THE deployable
candidate (the only strategy that cleared the full validation bar).

Backtest context: pooled portfolio, per-symbol slices, 510 trades over
~4,380 days = 0.116 trades/day across 3 symbols; per-trade risk $200
with 3xATR stops; maxDD 15.5% in the sliced portfolio run.

Expectations:
- finalized == true (required)
- n_trades <= 5 (expected ~0.35; bound is generous +1 sanity margin)
- pnl_usd >= -1,000 (-10%; ~1.5x the expected loss of a handful of risk units)
- equity_discrepancy_usd <= 1.00 (commission is 0 for crypto, so equity
  changes and journal PnL must reconcile almost exactly - this is the
  strongest integrity check of the two runs)
- win rate / PF: NOT graded (statistically meaningless below ~20 trades)

Command:
```
python shadow/compare_report.py \
  --state shadow-crypto/state.json --journal shadow-crypto/journal.jsonl \
  --expect-trades-max 5 --expect-pnl-min -1000 \
  --expect-equity-diff-max 1.0
```

## After grading: the 30-day longrun

The crypto chain auto-respawns into a 720h (30d) longrun: on 72h
finalization the chain archives the run under
`shadow-crypto/archive/<timestamp>/` and re-dispatches itself with
`deadline_hours=720`. Expected longrun trades: ~3.5 (0.116/day x 30d).
The longrun is graded with SEPARATE pre-registrations to be written
here on its start date. FX chain finalizes and stops - it is not
promoted (below validation bar) and a 30d extension would burn compute
on pretending otherwise.
