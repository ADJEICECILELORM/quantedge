import pytest

from utils.execution_quality import ExecutionQualityTracker


def fill(tracker, slip):
    tracker.record_fill("EURUSD", 1, 1.1000, 1.1000 + slip)


class TestExecutionQualityTracker:
    def test_slippage_sign_buy(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        s = tracker.record_fill("EURUSD", 1, 1.1000, 1.1002)
        assert s == pytest.approx(0.0002)

    def test_slippage_sign_sell(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        s = tracker.record_fill("EURUSD", -1, 1.1000, 1.0997)
        assert s == pytest.approx(0.0003)

    def test_summarize_statistics(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        for slip in [0.0001, 0.0002, 0.0003, 0.0004, 0.0010]:
            fill(tracker, slip)
        stats = tracker.summarize()
        assert stats["n_fills"] == 5
        assert stats["median_slippage"] == pytest.approx(0.0003)
        assert stats["p99_slippage"] >= stats["p90_slippage"] >= stats["median_slippage"]

    def test_symbol_filter(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        tracker.record_fill("EURUSD", 1, 1.1, 1.1)
        tracker.record_fill("GBPUSD", 1, 1.27, 1.28)
        assert tracker.summarize(symbol="EURUSD")["n_fills"] == 1

    def test_compare_insufficient_samples(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        comparison = tracker.compare_to_backtest(0.00002)
        assert comparison["verdict"] == "insufficient_samples"

    def test_compare_flags_underestimated_costs(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        for _ in range(5):
            fill(tracker, 0.0002)
        comparison = tracker.compare_to_backtest(0.00002)
        assert comparison["verdict"] == "costs_underestimated"
        assert comparison["ratio"] > 3.0

    def test_compare_accepts_cost_model(self, tmp_path):
        tracker = ExecutionQualityTracker(str(tmp_path / "fills.jsonl"))
        for _ in range(5):
            fill(tracker, 0.00002)
        comparison = tracker.compare_to_backtest(0.00002)
        assert comparison["verdict"] == "costs_within_assumption"
