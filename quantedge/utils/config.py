# utils/config.py
import copy
import json
import os


DEFAULTS = {
    "account": {
        "balance": 10000,
        "risk_per_trade": 0.02,
    },
    "symbols": {
        "forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
        "metals": ["XAUUSD"],
    },
    "timeframe": "M5",
    "shadow_mode": True,
    "risk": {
        "max_daily_loss_percent": 5.0,
        "max_correlation": 0.7,
        "max_lot": 1.0,
        "vol_target_per_bar": 0.0015,
        "max_gross_exposure_usd": 20000,
        "max_net_exposure_usd": 10000,
    },
    "rag": {
        "enabled": False,
    },
    "sessions": {
        "allowed_utc_ranges": [[7, 17]],
    },
    "paths": {
        "models_dir": "models/saved",
        "logs_dir": "logs",
    },
    "backtest": {
        "warmup_bars": 100,
        "spread_fraction": 0.00005,
        "commission_per_lot_usd": 7.0,
        "slippage_fraction": 0.00002,
        "atr_sl_multiple": 1.5,
        "atr_tp_multiple": 2.5,
        "bars_per_year": 28800,
        "min_confidence": 0.55,
        "mc_paths": 10000,
        "ruin_drawdown_pct": 50.0,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    if not os.path.exists(path):
        return copy.deepcopy(DEFAULTS)
    with open(path, "r", encoding="utf-8") as f:
        user_config = json.load(f)
    return _deep_merge(DEFAULTS, user_config)


def resolve_timeframe(name: str):
    import MetaTrader5 as mt5
    constants = {
        "m1": mt5.TIMEFRAME_M1,
        "m5": mt5.TIMEFRAME_M5,
        "m15": mt5.TIMEFRAME_M15,
        "m30": mt5.TIMEFRAME_M30,
        "h1": mt5.TIMEFRAME_H1,
        "h4": mt5.TIMEFRAME_H4,
        "d1": mt5.TIMEFRAME_D1,
    }
    return constants[str(name).lower()]
