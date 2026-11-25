# QuantEdge Operations Playbook

Institutional runbook for operating the QuantEdge system: what runs
where, how to monitor, how to recover, and the exact gates between
"validated in backtest" and "trading real money".

## 1. System map

| Component | Location | Trigger | State |
|---|---|---|---|
| CI | `.github/workflows/ci.yml` | push/PR | - |
| Weekly retrain | `.github/workflows/retrain_models.yml` | cron Sun 04:05 UTC, manual, push on relevant paths | models as workflow artifacts (90d); report on `model-artifacts` branch |
| FX shadow chain | `.github/workflows/shadow_momentum.yml` | hourly cron + self-perpetuating chain | `shadow-trading` branch |
| Crypto shadow chain | `.github/workflows/shadow_crypto.yml` | hourly cron + self-perpetuating chain | `shadow-crypto` branch |

Both shadow chains hedge against GitHub's unreliable top-of-hour cron:
each run sleeps until just past the next hour, then dispatches itself
via the in-runner `GITHUB_TOKEN` (which has `actions:write`). The hourly
cron plus a push-trigger on the state branch act as safety nets.

Branches:

- `main` - code only. Pushing code here is safe; shadow bots never commit to it.
- `shadow-trading` / `shadow-crypto` - bot-owned state. Do not hand-edit; if a code push to one races a bot commit, merge the remote state and push the merge to that branch only.
- `model-artifacts` - retrain reports and model binaries (append-only log).

## 2. Monitoring

- **Alerts**: any failed run of the three autonomous workflows opens or
  comments on a `quantedge-alert` GitHub issue with the run URL.
  Shadow chains additionally re-dispatch one recovery tick for
  schedule/push-triggered failures. A second consecutive failure does
  NOT re-dispatch (loop protection); the hourly cron is the backstop.
- **Health check**: `gh run list` for the three workflow names - every
  hour should have one success per shadow chain. A gap of >2 hours on a
  not-yet-finalized chain means the chain is dead: restart it from the
  Actions tab ("Run workflow" button on `shadow-trading`/`shadow-crypto`
  ref) or fix the code and push to the state branch.
- **Retrain gate**: every Sunday report lists per-pair OOS PSR.
  Deployment rule per pair: PSR >= 0.95 validated, 0.50-0.95
  noise-adjacent (keep in shadow), < 0.50 do-not-deploy.

## 3. Recovery procedures

**Chain dead / workflow disabled by mistake**: dispatch manually from
the Actions tab with the state branch as ref. The chain re-perpetuates
from any single successful run.

**State branch diverged (push rejected, non-fast-forward)**:
```
git fetch origin shadow-trading
git checkout -b tmp-state origin/shadow-trading   # or: git merge origin/shadow-trading
git merge <your-branch>                            # resolve, prefer keeping bot state
git push origin tmp-state:shadow-trading tmp-state   # merge only to the state branch
```
Never push a rewritten state branch history and never delete the branch
while a chain is live.

**Rerun a shadow experiment**: delete/rename the state branch, edit the
`--symbols` / cost flags in the workflow, push the workflow file to
main, then dispatch on the state branch. Every experiment gets its own
state branch so verdicts stay attributable.

## 4. Shadow run grading

After a chain reports `"finalized": true`, pull the state and journal
from the state branch and grade mechanically:
```
python shadow/compare_report.py \
  --state shadow/state.json --journal shadow/journal.jsonl \
  --expect-trades-min 1 --expect-pnl-min -500 \
  --expect-win-rate-min 20 --expect-pf-min 0.9 \
  --expect-equity-diff-max 50
```
Exit code 2 = at least one expectation failed = the run does NOT count
as evidence toward deployment. Expectation thresholds must be chosen
from the backtest (trades/day scaled to the window), never tuned after
seeing the shadow numbers first - write them down before fetching.

A 72h run measures **operability** (signals fire, fills book, state
persists, chain survives), NOT profitability. Only the long-horizon
backtests establish edge. The crypto chain auto-respawns into a 30d
longrun after its 72h finalization (archive + re-dispatch with
`deadline_hours=720`); grading thresholds for both runs live in
`docs/SHADOW_EXPECTATIONS.md` and are pre-registered - never edited
after results exist.

## 5. Go-live checklist (sequential gates; no skips)

1. **Strategy validated**: pooled walk-forward PSR and same-market DSR
   >= 0.95 across >= 3 markets, both legs profitable, survives real
   funding/commission/spread/slippage costs. Current status: crypto-3
   (BTC/ETH/SOL price_vs_sma50 LS + flip-exit + 3-ATR stop) is the ONLY
   strategy that has cleared this bar. ML direction prediction: dead.
   FX 7-pair momentum: below bar. Altcoin rotation: dead.
2. **Shadow reports meet expectations**: both chains finalized,
   `compare_report.py` exits 0 against pre-registered thresholds.
3. **Exposure sizing fixed and verified**: per-symbol equity slices
   enforced; combined peak notional inside the account cap (note the
   residual compounding drift for multi-year slices - equalize slices
   at deployment and monthly thereafter).
4. **Paper execution**: create Alpaca paper keys, set
   `ALPACA_API_KEY_ID`/`ALPACA_API_SECRET_KEY`, run the adapter
   (`execution/alpaca.py`) against the paper endpoint for >= 1 week
   with production-size orders. Alpaca paper does not cover perpetual
   funding settlement; treat as execution smoke test only.

   **Capital-preservation profile (measured 2026-11-25)** - crypto-3
   portfolio over the full backtest span, per-symbol equity slices,
   Monte Carlo ruin estimate (P of -50% drawdown):
5. **Decision point (human)**: move to real money ONLY with money you
   can lose entirely, in a subaccount, with a kill switch (below).
   Crypto perpetual trading needs a venue account the USER creates;
   keys never go into chat, email, or the repo - GitHub Secrets only,
   and scoped to the lowest required permission.
6. **Kill criteria (pre-registered, mechanical)**: halt trading and
   flatten if any of: drawdown > 1.5x backtest maxDD; equity < 90%
   after 100 closed trades despite positive backtest expectation;
   two consecutive failed retrain gates; venue changes fee/funding
   structure materially.

   | risk_per_trade | 12y return | maxDD | Sharpe | P(ruin) |
   |---|---|---|---|---|
   | 2.0% (backtest default) | +688% | 15.5% | 1.38 | 0.08% |
   | 1.0% (deployment profile) | +191% | 8.3% | 1.32 | ~0 |
   | 0.5% (ultra-conservative) | +73% | 4.2% | 1.26 | ~0 |

   Caveat: these Monte Carlo probabilities are computed on the
   historical path - they quantify variance, not regime risk. The
   deployment profile is 1%: it keeps Sharpe nearly intact while
   removing essentially all simulation-level ruin probability and
   halving live drawdowns.

## 6. Non-negotiables

- No strategy ships without the validation bar in gate 1.
- Never bypass the exposure caps to "fix" a sizing error; reduce
  `risk_per_trade` instead.
- Never commit API keys; never paste keys in any chat interface.
- Every experiment documented in `CHANGELOG.md`, including failures
  (the rotation kill and ML kill are part of the value).
- The bot's state commits win conflicts on state branches; code
  changes merge around them.
