# utils/retrain_job.py
"""
Autonomous retraining job for GitHub Actions.

Per pair: pull fresh daily history from Yahoo, retrain the ML challenger
models, measure feature drift between the training window and the latest
data, then run a quick out-of-sample engine validation on the final year.

Nothing is auto-promoted. The report verdicts are advisory; promotion is
a manual championship decision (models/championship.py) gated by the
PSR/DSR proof bar. Given the standing validation verdict (ML direction
prediction has no edge), this job keeps the challenger pipeline warm and
auditable without ever silently deploying models.
"""
import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

from backtest.engine import BacktestEngine
from backtest.validation import probabilistic_sharpe_ratio
from features.feature_engineer import FeatureEngineer
from features.label_generator import LabelGenerator
from models.advanced_model_trainer import AdvancedModelTrainer
from utils.config import load_config
from utils.download_history import fetch_yahoo_ohlcv
from utils.drift_monitor import compute_psi

PAIR_SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "USDCAD=X",
    "USDCHF": "USDCHF=X",
    "NZDUSD": "NZDUSD=X",
}

BASE_COLS = {"time", "open", "high", "low", "close", "tick_volume",
             "target", "regime_label"}
WARMUP_DAYS = 20
TRAIN_MIN_ROWS = 300
DATA_MIN_ROWS = 800
INITIAL_EQUITY = 10000.0


def retrain_pair(symbol: str, yahoo_symbol: str,
                 artifact_root: str = "models/artifacts",
                 optimize: bool = False, oos_days: int = 365,
                 data_range: str = "15y") -> dict:
    df = fetch_yahoo_ohlcv(symbol=yahoo_symbol, interval="1d", range_=data_range)
    if len(df) < DATA_MIN_ROWS:
        raise ValueError(f"{symbol}: only {len(df)} bars, need >= {DATA_MIN_ROWS}")

    features = FeatureEngineer().create_features(df)
    labeled = LabelGenerator(forward_bars=5, vol_multiple=0.5).create_labels(features)
    if labeled.empty or "time" not in labeled.columns:
        raise ValueError(f"{symbol}: no labeled rows")

    cut_time = df["time"].iloc[-1] - pd.Timedelta(days=oos_days)
    train = labeled[labeled["time"] <= cut_time].copy()
    if len(train) < TRAIN_MIN_ROWS:
        raise ValueError(f"{symbol}: only {len(train)} labeled training rows")

    drift = _drift_psi(features[features["time"] <= cut_time],
                       features[features["time"] > cut_time])

    artifact_dir = os.path.join(artifact_root, symbol)
    trainer = AdvancedModelTrainer(train, model_dir=artifact_dir)
    trainer.train_models(optimize=optimize)
    trainer.save_models(with_backup=False)

    oos_raw = df[df["time"] > cut_time - pd.Timedelta(days=WARMUP_DAYS)].copy()
    oos = _oos_summary(oos_raw, symbol, artifact_dir)

    return {
        "symbol": symbol,
        "rows_total": len(df),
        "rows_trained": len(train),
        "last_data_date": str(df["time"].iloc[-1].date()),
        "artifact_dir": artifact_dir,
        "drift": drift,
        "oos": oos,
    }


def _drift_psi(train_feats: pd.DataFrame, oos_feats: pd.DataFrame) -> dict:
    psis = {}
    for col in train_feats.columns:
        if col in BASE_COLS:
            continue
        a = pd.to_numeric(train_feats[col], errors="coerce").dropna()
        b = pd.to_numeric(oos_feats[col], errors="coerce").dropna()
        if len(a) < 50 or len(b) < 50 or a.nunique() < 3:
            continue
        try:
            psis[col] = float(compute_psi(a, b))
        except Exception as e:  # noqa: BLE001 - PSI is diagnostic, never fatal
            logger.warning("PSI failed for feature %s: %s", col, e)
            continue
    if not psis:
        return {"max_psi": float("nan"), "worst_feature": None,
                "features_checked": 0}
    worst = max(psis, key=psis.get)
    return {"max_psi": psis[worst], "worst_feature": worst,
            "features_checked": len(psis)}


def _load_inference_from(artifact_dir: str):
    import pipeline.inference_pipeline as ip
    os.environ["QUANTEDGE_MODEL_DIR"] = artifact_dir
    ip.InferencePipeline._instance = None
    ip.InferencePipeline._models_loaded = False
    return ip.InferencePipeline()


def _oos_summary(oos_raw: pd.DataFrame, symbol: str, artifact_dir: str) -> dict:
    _load_inference_from(artifact_dir)
    cfg = load_config()
    result = BacktestEngine(oos_raw, symbol=symbol, config=cfg,
                            initial_equity=INITIAL_EQUITY).run()

    out = {"bars": len(oos_raw),
           "trades": len(result.trades),
           "end_equity": float(result.metrics.get("end_equity",
                                                  INITIAL_EQUITY))}
    trades = result.trades
    if len(trades):
        pnl = trades["pnl_usd"].astype(float)
        out["total_pnl"] = float(pnl.sum())
        out["win_rate"] = float((pnl > 0).mean())
        out["return_pct"] = float(pnl.sum() / INITIAL_EQUITY * 100.0)
        out["psr"] = float(probabilistic_sharpe_ratio(pnl / INITIAL_EQUITY))
        out["verdict"] = _verdict(out.get("psr"))
    else:
        out["verdict"] = "no trades in OOS window"
    return out


def _verdict(psr: float) -> str:
    if psr >= 0.95:
        return "validated - championship review"
    if psr >= 0.5:
        return "noise-adjacent - review manually"
    return "below chance - do not deploy"


def format_retrain_report(results: list, generated_at: str) -> str:
    lines = [
        "# Model retrain report",
        "",
        f"Generated: {generated_at}",
        "",
        "| Symbol | Rows trained | Last data | Trades (OOS 1y) | Return % | PSR | Max PSI | Verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ok = [r for r in results if "error" not in r]
    failed = [r for r in results if "error" in r]
    for r in ok:
        oos, drift = r["oos"], r["drift"]
        psi = drift["max_psi"]
        psi_s = f"{psi:.2f}" if pd.notna(psi) else "n/a"
        lines.append(
            f"| {r['symbol']} | {r['rows_trained']} | {r['last_data_date']} "
            f"| {oos.get('trades', 0)} | {oos.get('return_pct', float('nan')):.1f} "
            f"| {oos.get('psr', float('nan')):.3f} | {psi_s} | {oos.get('verdict', '')} |"
        )
    for r in failed:
        lines.append(f"| {r['symbol']} | - | - | - | - | - | ERROR: {r['error']} |")
    lines += [
        "",
        "## Verdict legend",
        "",
        "- **validated** (PSR >= 0.95): run championship review before promotion",
        "- **noise-adjacent** (PSR >= 0.5): within noise of coin-flip",
        "- **below chance**: no edge, do not deploy",
        "",
        f"Max feature PSI across {', '.join(r['symbol'] for r in ok) or 'no pairs'}: "
        + ", ".join(f"{r['symbol']} {r['drift']['max_psi']:.2f} "
                    f"({r['drift']['worst_feature']})" for r in ok)
        or "n/a",
        "",
        ("Promotion is manual: compare challenger vs champion via"
         " models/championship.py, then promote_challenger()."),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Retrain challenger models")
    ap.add_argument("--pairs", default="EURUSD,GBPUSD,USDJPY",
                    help="comma-separated pair codes (keys of PAIR_SYMBOLS)")
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--artifact-root", default="models/artifacts")
    ap.add_argument("--report-out", default="models/retrain_report.md")
    ap.add_argument("--summary-out", default="models/retrain_summary.json")
    ap.add_argument("--data-range", default="15y")
    ap.add_argument("--oos-days", type=int, default=365)
    args = ap.parse_args()

    results = []
    for symbol in (s.strip().upper() for s in args.pairs.split(",")):
        if symbol not in PAIR_SYMBOLS:
            results.append({"symbol": symbol, "error": f"unknown pair {symbol}"})
            continue
        try:
            res = retrain_pair(symbol, PAIR_SYMBOLS[symbol],
                               artifact_root=args.artifact_root,
                               optimize=args.optimize, oos_days=args.oos_days,
                               data_range=args.data_range)
            results.append(res)
            oos = res["oos"]
            print(f"{symbol}: {oos['trades']} OOS trades, "
                  f"return {oos.get('return_pct', float('nan')):.1f}%, "
                  f"PSR {oos.get('psr', float('nan')):.3f} -> {oos['verdict']}")
        except Exception as e:  # noqa: BLE001 - one bad pair must not kill the run
            results.append({"symbol": symbol, "error": str(e)})
            print(f"{symbol}: FAILED - {e}")

    os.makedirs(args.artifact_root, exist_ok=True)
    generated_at = datetime.now(UTC).isoformat()
    with open(args.report_out, "w", encoding="utf-8") as f:
        f.write(format_retrain_report(results, generated_at))
    with open(args.summary_out, "w", encoding="utf-8") as f:
        json.dump({"generated_at": generated_at, "results": results},
                  f, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
