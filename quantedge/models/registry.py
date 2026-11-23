# models/registry.py
import json
import os
from datetime import datetime, timezone

METADATA_FILE = "metadata.json"


def save_metadata(
    model_dir: str,
    feature_cols,
    data_start=None,
    data_end=None,
    hyperparams=None,
    metrics=None,
    extra=None,
    feature_stats=None,
):
    payload = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "feature_cols": list(feature_cols),
        "n_features": len(feature_cols),
        "data_start": str(data_start) if data_start is not None else None,
        "data_end": str(data_end) if data_end is not None else None,
        "hyperparams": hyperparams or {},
        "metrics": metrics or {},
        "feature_stats": feature_stats or {},
    }
    if extra:
        payload.update(extra)

    os.makedirs(model_dir, exist_ok=True)
    path = os.path.join(model_dir, METADATA_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def load_metadata(model_dir: str):
    path = os.path.join(model_dir, METADATA_FILE)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_features(model_dir: str, feature_cols):
    """
    Compare live feature columns against training metadata.

    Returns (ok, message). ok=False means the model was trained on a
    different feature set and inference results cannot be trusted.
    """
    metadata = load_metadata(model_dir)
    if metadata is None:
        return True, "No metadata found; skipping validation (retrain to enable)"

    expected = metadata.get("feature_cols")
    expected_name = set(expected or [])

    missing = sorted(expected_name - set(feature_cols))
    extra = sorted(set(feature_cols) - expected_name)

    if expected is not None and len(feature_cols) != len(expected):
        return False, (
            f"Feature count mismatch: model expects {len(expected)}, "
            f"got {len(feature_cols)}"
        )

    if missing or extra:
        return False, (
            f"Feature mismatch: missing={missing[:10]}, unexpected={extra[:10]}"
        )

    return True, f"Features match training ({len(expected)} columns)"
