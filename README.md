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

## Note

`rag/news_ingestion.py` currently returns mock economic-calendar events.
Verify the RAG layer is disabled or fed by a real source before relying on
its output in live trading.
