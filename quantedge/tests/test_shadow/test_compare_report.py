import json

import pytest

from shadow.compare_report import (
    compare,
    load_journal,
    main,
    summarize_shadow,
)


@pytest.fixture
def state(tmp_path):
    s = {
        "start_equity": 10000.0,
        "equity": 10090.0,
        "finalized": True,
        "started_at": "2026-11-24T12:00:00",
        "finalized_at": "2026-11-27T12:00:00",
    }
    return s


@pytest.fixture
def journal(tmp_path):
    records = [
        {"type": "open", "symbol": "BTC-USD", "direction": -1, "entry_price": 61000.0,
         "units": 0.1, "bar_time": "2026-11-24 12:00:00", "ts": "2026-11-24T12:05:00"},
        {"type": "close", "symbol": "BTC-USD", "direction": -1, "entry_price": 61000.0,
         "exit_price": 59000.0, "units": 0.1, "pnl_usd": 200.0, "reason": "signal_flip",
         "ts": "2026-11-25T12:05:00"},
        {"type": "open", "symbol": "ETH-USD", "direction": -1, "entry_price": 1700.0,
         "units": 1.0, "bar_time": "2026-11-25 12:00:00", "ts": "2026-11-25T12:06:00"},
        {"type": "close", "symbol": "ETH-USD", "direction": -1, "entry_price": 1700.0,
         "exit_price": 1710.0, "units": 1.0, "pnl_usd": -10.0, "reason": "signal_flip",
         "ts": "2026-11-26T12:06:00"},
        {"type": "close", "symbol": "SOL-USD", "direction": -1, "entry_price": 72.0,
         "exit_price": 73.0, "units": 5.0, "pnl_usd": -5.0, "reason": "experiment_end",
         "ts": "2026-11-27T12:06:00"},
    ]
    path = tmp_path / "journal.jsonl"
    with open(path, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in records)
    return str(path)


class TestSummarize:
    def test_summary_math(self, state, journal):
        realized = summarize_shadow(state, load_journal(journal))
        assert realized["n_trades"] == 3
        assert realized["n_opens"] == 2
        assert realized["pnl_usd"] == 90.0
        assert realized["return_pct"] == pytest.approx(0.9)
        assert realized["win_rate_pct"] == pytest.approx(33.3, abs=0.1)
        assert realized["profit_factor"] == pytest.approx(200.0 / 15.0, abs=0.01)
        assert realized["longest_losing_streak"] == 2
        assert realized["run_days"] == pytest.approx(3.0)
        assert realized["trades_per_day"] == pytest.approx(1.0)
        assert realized["pnl_per_symbol"] == {"BTC-USD": 200.0, "ETH-USD": -10.0, "SOL-USD": -5.0}

    def test_journal_equity_discrepancy(self, state, journal):
        state = dict(state, equity=10500.0)
        realized = summarize_shadow(state, load_journal(journal))
        assert realized["equity_discrepancy_usd"] == pytest.approx(315.0)

    def test_empty_journal(self, state):
        realized = summarize_shadow(state, [])
        assert realized["n_trades"] == 0
        assert realized["win_rate_pct"] is None
        assert realized["profit_factor"] is None


class TestCompare:
    def test_pass_fail_skip(self):
        realized = {"n_trades": 3, "pnl_usd": -50.0, "win_rate_pct": None}
        results = compare(realized, {
            "n_trades": ("min", 1),
            "pnl_usd": ("min", 0.0),
            "win_rate_pct": ("min", 20.0),
            "profit_factor": ("min", 1.0),
        })
        verdicts = {name: v for name, _, _, v, _ in results}
        assert verdicts["n_trades"] == "PASS"
        assert verdicts["pnl_usd"] == "FAIL"
        assert verdicts["win_rate_pct"] == "SKIP"
        assert verdicts["profit_factor"] == "SKIP"

    def test_is_operator(self):
        results = compare({"finalized": True}, {"finalized": ("is", True)})
        assert results[0][3] == "PASS"


class TestCLI:
    def test_main_pass_writes_report(self, state, journal, tmp_path, capsys):
        sp = tmp_path / "state.json"
        sp.write_text(json.dumps(state))
        out = tmp_path / "out" / "report.md"
        main(["--state", str(sp), "--journal", journal, "--out", str(out),
              "--expect-trades-min", "1", "--expect-pnl-min", "-500"])
        assert out.exists()
        assert "VERDICT: expectations met" in out.read_text()

    def test_main_fails_exit_code_2(self, state, journal, tmp_path):
        sp = tmp_path / "state.json"
        sp.write_text(json.dumps(state))
        with pytest.raises(SystemExit) as e:
            main(["--state", str(sp), "--journal", journal, "--expect-pnl-min", "1000"])
        assert e.value.code == 2

    def test_unfinalized_state_fails_default_check(self, state, journal, tmp_path):
        state = dict(state, finalized=False)
        sp = tmp_path / "state.json"
        sp.write_text(json.dumps(state))
        with pytest.raises(SystemExit) as e:
            main(["--state", str(sp), "--journal", journal])
        assert e.value.code == 2

    def test_missing_journal_is_empty(self, state, tmp_path, capsys):
        sp = tmp_path / "state.json"
        sp.write_text(json.dumps(state))
        main(["--state", str(sp), "--journal", str(tmp_path / "nope.jsonl")])
        captured = capsys.readouterr().out
        assert "finalized: True" in captured
