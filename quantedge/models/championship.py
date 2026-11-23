# models/championship.py
"""
Champion / challenger model governance.

New models are trained into models/challenger/ and only promoted into
models/saved/ with statistical evidence (walk-forward metrics improved
by a margin, without degrading other metrics). Champion swaps are always
backed up, so a bad promotion is one directory-copy away from a rollback.
"""
import json
import os
import shutil
from datetime import datetime, timezone

from models.registry import load_metadata

PRIMARY_METRIC = "roc_auc"
GUARDED_METRICS = ("accuracy", "precision", "recall")


def challenge_summary(champion_dir: str = "models/saved", challenger_dir: str = "models/challenger") -> dict:
    champion = load_metadata(champion_dir) or {}
    challenger = load_metadata(challenger_dir) or {}

    def _metrics(meta):
        return meta.get("metrics") or {}

    champ_m, chall_m = _metrics(champion), _metrics(challenger)
    comparison = {}
    for metric in [PRIMARY_METRIC] + list(GUARDED_METRICS):
        if metric in champ_m and metric in chall_m:
            comparison[metric] = {
                "champion": champ_m[metric],
                "challenger": chall_m[metric],
                "delta": chall_m[metric] - champ_m[metric],
            }

    return {
        "champion": {
            "exists": bool(champion),
            "trained_at": champion.get("trained_at"),
            "data_start": champion.get("data_start"),
            "data_end": champion.get("data_end"),
        },
        "challenger": {
            "exists": bool(challenger),
            "trained_at": challenger.get("trained_at"),
            "data_start": challenger.get("data_start"),
            "data_end": challenger.get("data_end"),
        },
        "comparison": comparison,
    }


def should_promote(champion_dir: str = "models/saved", challenger_dir: str = "models/challenger",
                   margin: float = 0.02) -> tuple:
    """
    Evidence rule: challenger must beat the champion on the primary
    walk-forward metric by at least `margin`, and must not degrade any
    guarded metric by more than `margin`. Returns (promote, details).
    """
    summary = challenge_summary(champion_dir, challenger_dir)
    details = {"comparison": summary["comparison"], "reason": ""}

    if not summary["challenger"]["exists"]:
        details["reason"] = "No challenger model found"
        return False, details
    if not summary["champion"]["exists"]:
        details["reason"] = "No champion baseline - promoting first trained model"
        return True, details

    comparison = summary["comparison"]
    primary = comparison.get(PRIMARY_METRIC)
    if primary is None:
        details["reason"] = f"Missing {PRIMARY_METRIC} on one of the models; cannot compare"
        return False, details

    if primary["delta"] < margin:
        details["reason"] = (
            f"Challenger {PRIMARY_METRIC} delta {primary['delta']:+.4f} "
            f"below promotion margin {margin}"
        )
        return False, details

    for metric in GUARDED_METRICS:
        guarded = comparison.get(metric)
        if guarded is not None and guarded["delta"] < -margin:
            details["reason"] = (
                f"Challenger regressed {metric} by {-guarded['delta']:.4f} "
                f"(tolerance {margin})"
            )
            return False, details

    details["reason"] = f"Challenger improved {PRIMARY_METRIC} by {primary['delta']:+.4f}"
    return True, details


def promote_challenger(champion_dir: str = "models/saved", challenger_dir: str = "models/challenger",
                       backup_root: str = "models/backup", margin: float = 0.02) -> dict:
    """
    Run the evidence rule; if passed, back up the champion and swap the
    challenger in. Returns a result dict with the decision and paths.
    """
    promote, details = should_promote(champion_dir, challenger_dir, margin=margin)
    result = {"promoted": False, "reason": details["reason"], "backup": None}
    if not promote:
        return result

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    os.makedirs(backup_root, exist_ok=True)
    backup_dir = os.path.join(backup_root, f"champion_{timestamp}")
    if os.path.exists(champion_dir):
        shutil.copytree(champion_dir, backup_dir)

    stale = None
    if os.path.exists(champion_dir):
        stale = os.path.join(backup_root, f"stale_{timestamp}")
        os.rename(champion_dir, stale)
    os.rename(challenger_dir, champion_dir)

    metadata_path = os.path.join(champion_dir, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        metadata["promoted_at"] = datetime.now(timezone.utc).isoformat()
        metadata.setdefault("extra", {})["trainer"] = metadata.get("trainer", "")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

    if stale:
        shutil.rmtree(stale)

    result["promoted"] = True
    result["backup"] = backup_dir
    return result
