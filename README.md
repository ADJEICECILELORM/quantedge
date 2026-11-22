# QuantEdge

An MT5 algorithmic trading bot combining an ML inference pipeline (feature
engineering, gradient-boosted / linear models), position sizing, drawdown
protection, and an experimental RAG news-intelligence layer.

## Layout

- `quantedge/bot_v6_ultimate.py` — current entry point (shadow mode ON by default)
- `quantedge/features/` — feature engineering and label generation
- `quantedge/models/` — model training and saved artifacts
- `quantedge/risk/` — position sizing, drawdown guard
- `quantedge/safety/` — shadow mode, hard risk gates
- `quantedge/rag/` — news ingestion, retrieval, regime classification (partly mock data)
- `quantedge/utils/` — MT5 connector, order execution, indicators
- `quantedge/tests/` — pytest suite

## Setup

Requires Python 3.10+ and a running MetaTrader 5 terminal (Windows).

```bash
pip install -r requirements.txt
```

## Running

```bash
cd quantedge
python bot_v6_ultimate.py            # shadow mode (no real orders)
python bot_v6_ultimate.py --live     # real orders - read the code first
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
