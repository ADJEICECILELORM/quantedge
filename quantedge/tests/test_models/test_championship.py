import os

import pytest

from models.championship import challenge_summary, promote_challenger, should_promote
from models.registry import save_metadata


def make_model_dir(tmp_path, name, metrics):
    model_dir = str(tmp_path / name)
    os.makedirs(model_dir, exist_ok=True)
    save_metadata(model_dir, feature_cols=["a", "b"], metrics=metrics)
    return model_dir


def make_model_files(model_dir):
    with open(os.path.join(model_dir, "scaler.pkl"), "w") as f:
        f.write("stub")
    return model_dir


class TestShouldPromote:
    def test_no_challenger_declined(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.6})
        promote, details = should_promote(champ, str(tmp_path / "missing"))
        assert promote is False
        assert "No challenger" in details["reason"]

    def test_first_model_promoted_without_baseline(self, tmp_path):
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.6})
        promote, details = should_promote(str(tmp_path / "missing"), chall)
        assert promote is True

    def test_improvement_promoted(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.55, "accuracy": 0.6, "precision": 0.5, "recall": 0.5})
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.60, "accuracy": 0.6, "precision": 0.5, "recall": 0.5})
        promote, details = should_promote(champ, chall, margin=0.02)
        assert promote is True
        assert "improved" in details["reason"]

    def test_small_improvement_declined(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.55})
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.56})
        promote, details = should_promote(champ, chall, margin=0.02)
        assert promote is False
        assert "below promotion margin" in details["reason"]

    def test_guarded_regression_blocks_even_with_primary_gain(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.55, "accuracy": 0.7, "precision": 0.5, "recall": 0.5})
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.65, "accuracy": 0.6, "precision": 0.5, "recall": 0.5})
        promote, details = should_promote(champ, chall, margin=0.02)
        assert promote is False
        assert "regressed accuracy" in details["reason"]

    def test_missing_primary_metric_declined(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {})
        chall = make_model_dir(tmp_path, "chall", {})
        promote, _ = should_promote(champ, chall)
        assert promote is False


class TestPromoteChallenger:
    def test_successful_promotion_swaps_and_backs_up(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.55, "accuracy": 0.6, "precision": 0.5, "recall": 0.5})
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.65, "accuracy": 0.6, "precision": 0.5, "recall": 0.5})
        make_model_files(champ)
        make_model_files(chall)
        backup_root = str(tmp_path / "backup")

        result = promote_challenger(champ, chall, backup_root=backup_root, margin=0.02)

        assert result["promoted"] is True
        assert os.path.exists(result["backup"])
        assert os.path.exists(os.path.join(champ, "scaler.pkl"))

        from models.registry import load_metadata
        promoted = load_metadata(champ)
        assert promoted["metrics"]["roc_auc"] == 0.65
        assert "promoted_at" in promoted
        assert not os.path.exists(chall), "challenger dir should be consumed"

    def test_failed_promotion_leaves_everything_in_place(self, tmp_path):
        champ = make_model_dir(tmp_path, "champ", {"roc_auc": 0.9})
        chall = make_model_dir(tmp_path, "chall", {"roc_auc": 0.6})
        make_model_files(champ)

        result = promote_challenger(champ, chall, backup_root=str(tmp_path / "backup"))

        assert result["promoted"] is False
        assert not os.path.exists(str(tmp_path / "backup"))
