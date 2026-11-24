# tests/test_shadow/test_shadow_run.py
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.getcwd(), "shadow"))

import shadow_run


def make_daily(n=80, seed=3):
    rng = np.random.default_rng(seed)
    close = 1.0 * np.exp(np.cumsum(rng.normal(0, 0.004, n)))
    open_ = np.roll(close, 1)
    open_[0] = 1.0
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="D"),
        "open": open_,
        "high": np.maximum(open_, close) * 1.001,
        "low": np.minimum(open_, close) * 0.999,
        "close": close,
        "tick_volume": rng.integers(1000, 5000, n),
    })


@pytest.fixture
def cfg():
    return shadow_run.load_config()


def fresh_state():
    return {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "deadline_hours": 72.0,
        "start_equity": 10000.0,
        "equity": 10000.0,
        "positions": {},
        "signals": {},
        "finalized": False,
    }


def fake_signal_for(signals_by_symbol):
    def fake(symbol, now):
        return signals_by_symbol.get(symbol, {"direction": 0, "price": 1.0,
                                              "bar_time": f"t_{symbol}", "atr": 0.01})
    return fake


class TestLatestCompletedBars:
    def test_drops_in_progress_bar(self):
        now = datetime(2026, 3, 12, 6, 0, tzinfo=timezone.utc)
        df = make_daily(10)
        df.loc[df.index[-1], "time"] = pd.Timestamp("2026-03-12 00:00:00")
        assert len(shadow_run.latest_completed_bars(df, now)) == 9

    def test_keeps_completed_bar(self):
        now = datetime(2026, 3, 12, 6, 0, tzinfo=timezone.utc)
        df = make_daily(10)
        df.loc[df.index[-1], "time"] = pd.Timestamp("2026-03-11 00:00:00")
        assert len(shadow_run.latest_completed_bars(df, now)) == 10


class TestTick:
    def test_opens_on_signal(self, cfg, tmp_path, monkeypatch):
        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": 1, "price": 1.10, "bar_time": "b1", "atr": 0.01}}))
        state = shadow_run.tick(fresh_state(), cfg, str(tmp_path), str(tmp_path / "journal.jsonl"),
                                datetime.now(timezone.utc))
        assert state["positions"]["EURUSD"]["direction"] == 1
        records = [json.loads(l) for l in open(tmp_path / "journal.jsonl")]
        assert records[0]["type"] == "open"

    def test_flip_closes_then_reopens(self, cfg, tmp_path, monkeypatch):
        journal = str(tmp_path / "journal.jsonl")
        state = fresh_state()
        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": 1, "price": 1.10, "bar_time": "b1", "atr": 0.01}}))
        state = shadow_run.tick(state, cfg, str(tmp_path), journal, datetime.now(timezone.utc))
        eq_after_open = state["equity"]

        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": -1, "price": 1.12, "bar_time": "b2", "atr": 0.01}}))
        state = shadow_run.tick(state, cfg, str(tmp_path), journal, datetime.now(timezone.utc))
        assert state["positions"]["EURUSD"]["direction"] == -1

        records = [json.loads(l) for l in open(journal)]
        assert [r["type"] for r in records] == ["open", "close", "open"]
        assert records[1]["reason"] == "signal_flip"
        assert state["equity"] != eq_after_open

    def test_no_new_bar_no_action(self, cfg, tmp_path, monkeypatch):
        journal = str(tmp_path / "journal.jsonl")
        state = fresh_state()
        sig = {"direction": 1, "price": 1.10, "bar_time": "b1", "atr": 0.01}
        monkeypatch.setattr(shadow_run, "evaluate_signal", fake_signal_for({"EURUSD": sig}))
        state = shadow_run.tick(state, cfg, str(tmp_path), journal, datetime.now(timezone.utc))
        eq_after = state["equity"]

        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": dict(sig, price=1.50)}))
        state = shadow_run.tick(state, cfg, str(tmp_path), journal, datetime.now(timezone.utc))
        assert state["equity"] == eq_after

    def test_flat_signal_does_not_open(self, cfg, tmp_path, monkeypatch):
        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": 0, "price": 1.10, "bar_time": "b1", "atr": 0.01}}))
        state = shadow_run.tick(fresh_state(), cfg, str(tmp_path), str(tmp_path / "journal.jsonl"),
                                datetime.now(timezone.utc))
        assert not state["positions"]


class TestFinalize:
    def test_closes_positions_and_writes_report(self, cfg, tmp_path, monkeypatch):
        state = fresh_state()
        state["positions"] = {"EURUSD": {"direction": 1, "entry_price": 1.10, "units": 100,
                                          "entry_ts": "", "entry_bar": "x"}}
        journal = str(tmp_path / "journal.jsonl")
        report = str(tmp_path / "shadow_report.md")
        state_path = str(tmp_path / "state.json")

        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": 1, "price": 1.15, "bar_time": "y", "atr": 0.01}}))
        shadow_run.finalize(state, cfg, journal, report, state_path)

        assert state["finalized"] is True
        final = json.load(open(state_path))
        assert final["finalized"] is True
        records = [json.loads(l) for l in open(journal)]
        assert records[-1]["type"] == "close"
        assert records[-1]["reason"] == "experiment_end"
        assert "Shadow experiment report" in open(report).read()

    def test_finalize_without_positions(self, cfg, tmp_path):
        state = fresh_state()
        state_path = str(tmp_path / "state.json")
        shadow_run.finalize(state, shadow_run.load_config(),
                            str(tmp_path / "journal.jsonl"),
                            str(tmp_path / "shadow_report.md"), state_path)
        assert state["finalized"] is True
        assert "No closed trades" in open(tmp_path / "shadow_report.md").read()


class TestMainLifecycle:
    def test_expired_start_finalizes(self, cfg, tmp_path, monkeypatch):
        state = fresh_state()
        state["started_at"] = (datetime.now(timezone.utc) - timedelta(hours=73)).isoformat()
        state["positions"] = {"EURUSD": {"direction": 1, "entry_price": 1.10, "units": 100,
                                          "entry_ts": "", "entry_bar": "x"}}
        state_path = str(tmp_path / "state.json")
        shadow_run._save_state(state_path, state)

        monkeypatch.setattr(shadow_run, "evaluate_signal",
                            fake_signal_for({"EURUSD": {"direction": 1, "price": 1.15, "bar_time": "y", "atr": 0.01}}))
        monkeypatch.setattr(sys, "argv", ["shadow_run.py", "--state-dir", str(tmp_path)])
        assert shadow_run.main() == 0

        final = shadow_run._load_state(state_path)
        assert final["finalized"] is True

    def test_finalized_state_is_noop(self, cfg, tmp_path, monkeypatch):
        state = fresh_state()
        state["finalized"] = True
        state_path = str(tmp_path / "state.json")
        shadow_run._save_state(state_path, state)

        def boom(symbol, now):
            raise AssertionError("should not evaluate signals after finalize")
        monkeypatch.setattr(shadow_run, "evaluate_signal", boom)
        monkeypatch.setattr(sys, "argv", ["shadow_run.py", "--state-dir", str(tmp_path)])
        assert shadow_run.main() == 0

    def test_cli_symbol_and_cost_overrides(self, cfg, tmp_path, monkeypatch):
        seen = []

        def fake_eval(symbol, now):
            seen.append(symbol)
            return None

        monkeypatch.setattr(shadow_run, "evaluate_signal", fake_eval)
        monkeypatch.setattr(sys, "argv", [
            "shadow_run.py", "--state-dir", str(tmp_path / "sc"),
            "--symbols", "BTC-USD", "ETH-USD",
            "--feature", "price_vs_sma50",
            "--spread-fraction", "0.0008",
            "--slippage-fraction", "0.0004",
            "--commission-per-lot", "0.0",
        ])
        old_map = dict(shadow_run.SYMBOL_MAP)
        old_feat = shadow_run.SIGNAL_FEATURE
        try:
            assert shadow_run.main() == 0
            state = shadow_run._load_state(str(tmp_path / "sc" / "state.json"))
            assert sorted(state["symbols"]) == ["BTC-USD", "ETH-USD"]
            assert state["feature"] == "price_vs_sma50"
            assert set(shadow_run.SYMBOL_MAP) == {"BTC-USD", "ETH-USD"}
            assert set(seen) <= {"BTC-USD", "ETH-USD"}
        finally:
            shadow_run.SYMBOL_MAP = old_map
            shadow_run.SIGNAL_FEATURE = old_feat
