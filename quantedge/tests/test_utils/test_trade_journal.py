# tests/test_utils/test_trade_journal.py
import pytest

from utils.trade_journal import TradeJournal


@pytest.fixture
def journal(tmp_path):
    j = TradeJournal(str(tmp_path / "journal.db"))
    yield j
    j.close()


class TestTradeJournal:
    def test_log_and_get(self, journal):
        trade_id = journal.log_trade(
            symbol="EURUSD", direction=1, mode="shadow",
            entry_price=1.10, lot_size=0.1, position_size_usd=200.0,
            confidence=0.72, regime="trending", news_driven=False,
        )
        rows = journal.get_trades(symbol="EURUSD")
        assert len(rows) == 1
        assert rows[0]["id"] == trade_id
        assert rows[0]["mode"] == "shadow"

    def test_close_trade_updates_pnl(self, journal):
        trade_id = journal.log_trade(symbol="XAUUSD", direction=1, entry_price=1800.0)
        journal.close_trade(trade_id, exit_price=1805.0, pnl_usd=50.0)
        rows = journal.get_trades()
        assert rows[0]["pnl_usd"] == 50.0
        assert rows[0]["exit_price"] == 1805.0

    def test_summary_counts(self, journal):
        a = journal.log_trade(symbol="EURUSD", direction=1)
        journal.close_trade(a, pnl_usd=10.0)
        b = journal.log_trade(symbol="GBPUSD", direction=-1)
        journal.close_trade(b, pnl_usd=-5.0)
        summary = journal.summary()
        assert summary["total_trades"] == 2
        assert summary["closed_trades"] == 2
        assert summary["win_rate"] == 0.5
        assert summary["total_pnl_usd"] == 5.0

    def test_mode_filter(self, journal):
        journal.log_trade(symbol="EURUSD", direction=1, mode="shadow")
        journal.log_trade(symbol="EURUSD", direction=1, mode="live")
        assert len(journal.get_trades(mode="live")) == 1
        assert journal.get_trades(mode="live")[0]["mode"] == "live"
