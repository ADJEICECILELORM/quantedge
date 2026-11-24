# QuantEdge

An MT5 algorithmic trading bot combining an ML inference pipeline (feature
engineering, gradient-boosted / linear models), position sizing, drawdown
protection, and an experimental RAG news-intelligence layer.

## Layout

- `quantedge/bot.py` — live/shadow entry point (shadow mode ON by default; config in `quantedge/config.json`)
- `quantedge/run_backtest.py` — backtest runner (runs the same feature/inference/sizing code paths on history)
- `quantedge/backtest/` — backtest engine, data loaders, metrics
- `quantedge/utils/config.py` — config loader (`load_config()` deep-merges `config.json` over defaults)
- `quantedge/features/` — feature engineering and label generation
- `quantedge/models/` — model training, artifact registry (`metadata.json`), saved artifacts
- `quantedge/risk/` — position sizing, drawdown guard
- `quantedge/safety/` — shadow mode, hard risk gates (immutable limits)
- `quantedge/rag/` — news ingestion, retrieval, regime classification (partly mock data)
- `quantedge/utils/` — MT5 connector, order execution, indicators
- `quantedge/tests/` — pytest suite (+ leakage detector)

## Setup

Requires Python 3.10+ and, for live trading, a running MetaTrader 5 terminal (Windows).

```bash
pip install -r requirements.txt
cp quantedge/config.json quantedge/config.local.json   # edit to taste
```

## Backtesting

From CSV:
```bash
cd quantedge
python run_backtest.py --csv data/EURUSD_M5.csv --save-trades backtest_results/trades.csv
```
From a connected MT5 terminal:
```bash
python run_backtest.py --mt5 --symbol EURUSD --start 2024-01-01 --end 2025-01-01
```
Always retrain first (`python retrain_models.py`) so `models/saved/metadata.json` exists — inference validates live feature columns against training metadata and refuses to predict on mismatched feature sets.

### Real data without MT5

No MT5 terminal needed to download history:
```bash
cd quantedge
python utils/download_history.py --symbol EURUSD=X --interval 5m --range 60d --out data/EURUSD_M5_60d.csv
python retrain_models.py
python run_backtest.py --csv data/EURUSD_M5_60d.csv
```
Yahoo FX bars carry zero tick volume, so volume-derived features are auto-dropped as degenerate (>50% NaN) instead of poisoning the feature matrix.

Every backtest also prints a robustness report: Monte Carlo bootstrap of the trade sequence (max-drawdown distribution, P(ruin), P(profit)) plus the Probabilistic Sharpe Ratio with a `real edge` / `NOT distinguishable from luck` verdict.

### Portfolio backtest (multi-symbol)

```python
from backtest.portfolio_backtest import PortfolioBacktest, format_portfolio_report
from backtest.data_loader import load_csv_history

result = PortfolioBacktest(
    {"EURUSD": load_csv_history("data/EURUSD_M5.csv"),
     "GBPUSD": load_csv_history("data/GBPUSD_M5.csv")},
).run()
print(format_portfolio_report(result))
```
Prints per-symbol and combined metrics, flags correlation-gate violations and peak concurrent gross exposure vs the configured caps.

## Model governance (champion/challenger)

```bash
python retrain_models.py --challenger   # trains into models/challenger, champion untouched
```
The promotion rule: challenger walk-forward `roc_auc` must beat the champion by ≥0.02 without regressing accuracy/precision/recall. Promote explicitly with `from models.championship import promote_challenger; promote_challenger()` — this backs up the champion first for rollback.

## Running

```bash
cd quantedge
python bot.py                 # shadow mode (no real orders)
python bot.py --live          # real orders - read the code first
python bot.py --balance 5000  # override balance (default: config)
```

## Testing

```bash
cd quantedge
pytest
```

## Daily risk report

```bash
cd quantedge
python utils/risk_report.py                 # reads data/journal.db, prints markdown
python utils/risk_report.py --journal data/journal.db
```
P&L attribution by symbol/regime/hour, empirical VaR from realized trade PnL, daily-loss gate headroom, active risk limits.

## Shadow paper trading (GitHub Actions, 72h cap)

```bash
gh workflow run shadow-momentum.yml --repo ADJEICECILELORM/quantedge
```
An hourly job fetches daily Yahoo data for EURUSD/GBPUSD/USDJPY, applies the validated SMA20/50 momentum signal to the latest completed bar, and journals notional trades to the `shadow-trading` branch. After 72 hours it finalizes `quantedge/shadow/shadow_report.md` and disables itself. Paper trades only - no broker, no live capital.

## Multi-asset validation (2026-11)

The same daily momentum framework was validated on crypto and ETFs with per-market cost calibration (stocks fetched dividend/split-adjusted):

- **Crypto-3 pooled (BTC, ETH, SOL, long-short)**: +2059% portfolio over ~12y, Sharpe 1.41, maxDD 22.2%, PF 3.30, PSR 100.0%, DSR (same-market trials) 1.000, P(profitable) 100% - the first strategy to clear the 0.95 proof bar. Caveats: shorts' funding cost unmodeled; SOL listed 2020; peak gross exposure $63k vs $20k cap under risk-parity sizing
- **ETF-4 pooled (SPY/QQQ/TLT/GLD)**: +153.9%, Sharpe 0.51, PSR 97.5% - GLD-driven; SPY/QQQ correlation 0.93
- **FX 4-pair**: +54.9%, PSR 0.869 - below the bar (see history below)

Across all 14 tested single-asset configs the max DSR was 0.84, so treat the crypto result as "validated pending a clean forward test", not "certified".

## Model retraining (GitHub Actions, weekly)

```bash
gh workflow run retrain-models.yml --repo ADJEICECILELORM/quantedge
# or manually
cd quantedge && python utils/retrain_job.py --pairs EURUSD,GBPUSD,USDJPY
```
A weekly job (`retrain-models.yml`) pulls fresh 15y daily Yahoo data, retrains the challenger models per pair, measures feature drift (max PSI), and runs a 1-year out-of-sample engine validation with a PSR verdict. Model artifacts are attached to the workflow run and the report archived on the `model-artifacts` branch. Promotion to champion is manual (`models/championship.py`) - a challenger only graduates past the PSR >= 0.95 proof bar.

## Note

`rag/news_ingestion.py` currently returns mock economic-calendar events.
Verify the RAG layer is disabled or fed by a real source before relying on
its output in live trading.
