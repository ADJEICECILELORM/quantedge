# utils/retrain_trigger.py
"""
Retrain trigger: the drift monitor raises this flag when live feature
distributions violate their training reference; the scheduler consum-
es it and launches a challenger retrain. Breaking the loop into a
flag file keeps inference stateless and restart-safe.
"""
import json
import os
from datetime import datetime, timezone

FLAG_NAME = "retrain_required.flag"


def flag_path(model_dir: str) -> str:
    return os.path.join(model_dir, FLAG_NAME)


def raise_flag(model_dir: str, detail: dict = None, reason: str = "feature_drift") -> str:
    os.makedirs(model_dir, exist_ok=True)
    payload = {
        "raised_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
        "detail": detail or {},
    }
    path = flag_path(model_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def check_flag(model_dir: str):
    path = flag_path(model_dir)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_flag(model_dir: str) -> bool:
    path = flag_path(model_dir)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
