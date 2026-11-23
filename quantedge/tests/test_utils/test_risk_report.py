from datetime import datetime, timezone

from utils.risk_report import generate_daily_report, write_daily_report
from utils.trade_journal import TradeJournal


def seed_journal(path):
    journal = TradeJournal(str(path / "journal.db"))
    t1 = journal.log_trade(
        symbol="EURUSD", direction=1, mode="shadow", entry_price=1.1,
        position_size_usd=200.0, lot_size=0.5, confidence=0.8, regime="Trend",
    )
    journal.close_trade(t1, exit_price=1.105, pnl_usd=250.0)
    t2 = journal.log_trade(
        symbol="GBPUSD", direction=-1, mode="shadow", entry_price=1.27,
        position_size_usd=150.0, lot_size=0.4, confidence=0.7, regime="Mean Reversion",
    )
    journal.close_trade(t2, exit_price=1.275, pnl_usd=-180.0)
    journal.log_trade(
        symbol="USDJPY", direction=1, mode="live", entry_price=150.0,
        position_size_usd=180.0, lot_size=0.3, confidence=0.75, regime="Trend",
    )
    return journal


class TestGenerateDailyReport:
    def test_contains_attribution_sections(self, tmp_path):
        journal = seed_journal(tmp_path)
        report = generate_daily_report(journal, equity=10000.0)
        assert "## Overview" in report
        assert "## P&L by Symbol" in report
        assert "## P&L by Regime" in report
        assert "EURUSD" in report
        assert "Trend" in report

    def test_daily_gate_headroom(self, tmp_path):
        journal = seed_journal(tmp_path)
        report = generate_daily_report(journal, config={"risk": {"max_daily_loss_percent": 5.0}}, equity=10000.0)
        # net pnl = 250 - 180 = +70 -> full headroom
        assert "5.0% headroom" in report

    def test_var_and_worst_trade(self, tmp_path):
        journal = seed_journal(tmp_path)
        report = generate_daily_report(journal)
        assert "VaR 95%" in report
        assert "$-180.00" in report

    def test_no_trades_report(self, tmp_path):
        journal = TradeJournal(str(tmp_path / "empty.db"))
        report = generate_daily_report(journal, now=datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc))
        assert "No trades in the last 24h" in report

    def test_hourly_breakdown_derived_from_ts(self, tmp_path):
        journal = seed_journal(tmp_path)
        report = generate_daily_report(journal)
        assert "## P&L by Hour (UTC)" in report


class TestWriteDailyReport:
    def test_writes_markdown_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        journal = seed_journal(tmp_path)
        path = write_daily_report(journal, out_dir="reports")
        content = open(path, encoding="utf-8").read()
        assert path.startswith(str(tmp_path / "reports" / "daily_"))
        assert "# QuantEdge Daily Risk Report" in content
