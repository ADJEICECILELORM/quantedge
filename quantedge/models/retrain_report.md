# Model retrain report

Generated: 2026-11-24T16:18:58.296191+00:00

| Symbol | Rows trained | Last data | Trades (OOS 1y) | Return % | PSR | Max PSI | Verdict |
|---|---|---|---|---|---|---|---|
| EURUSD | 3595 | 2026-11-24 | 9 | 14.6 | 0.925 | 3.98 | noise-adjacent - review manually |
| GBPUSD | 3594 | 2026-11-24 | 5 | -4.7 | 0.247 | 4.85 | below chance - do not deploy |
| USDJPY | 3595 | 2026-11-24 | 11 | 5.6 | 0.721 | 5.52 | noise-adjacent - review manually |

## Verdict legend

- **validated** (PSR >= 0.95): run championship review before promotion
- **noise-adjacent** (PSR >= 0.5): within noise of coin-flip
- **below chance**: no edge, do not deploy

Max feature PSI across EURUSD, GBPUSD, USDJPY: EURUSD 3.98 (sma_50), GBPUSD 4.85 (sma_50), USDJPY 5.52 (sma_20)

Promotion is manual: compare challenger vs champion via models/championship.py, then promote_challenger().
