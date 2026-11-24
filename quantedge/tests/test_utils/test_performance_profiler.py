# tests/test_utils/test_performance_profiler.py
import time
from utils.performance_profiler import PerformanceProfiler, Timer, timed


class TestPerformanceProfiler:
    """Tests for Performance Profiler"""

    def test_init(self):
        """Test initialization"""
        profiler = PerformanceProfiler()
        assert profiler.enabled is True
        assert len(profiler.timings) == 0
        assert len(profiler.call_counts) == 0

    def test_enable_disable(self):
        """Test enable/disable"""
        profiler = PerformanceProfiler()

        profiler.disable()
        assert profiler.enabled is False

        profiler.enable()
        assert profiler.enabled is True

    def test_time_function_decorator(self):
        """Test timing decorator"""
        profiler = PerformanceProfiler()

        @profiler.time_function()
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()

        assert result == "done"
        assert len(profiler.timings) > 0
        assert profiler.call_counts[f"{slow_function.__module__}.{slow_function.__name__}"] == 1
        assert slow_function.__name__ not in profiler.call_counts

    def test_multiple_calls(self):
        """Test multiple function calls"""
        profiler = PerformanceProfiler()

        @profiler.time_function()
        def test_func():
            return "result"

        # Call multiple times
        for _ in range(5):
            test_func()

        assert profiler.call_counts[f"{test_func.__module__}.{test_func.__name__}"] == 5
        assert len(profiler.timings[f"{test_func.__module__}.{test_func.__name__}"]) == 5

    def test_get_statistics(self):
        """Test statistics generation"""
        profiler = PerformanceProfiler()

        @profiler.time_function()
        def test_func():
            time.sleep(0.01)

        test_func()
        test_func()

        stats = profiler.get_statistics()

        qualified = f"{test_func.__module__}.{test_func.__name__}"
        assert qualified in stats
        func_stats = stats[qualified]

        assert 'count' in func_stats
        assert 'total_time_ms' in func_stats
        assert 'avg_time_ms' in func_stats
        assert 'min_time_ms' in func_stats
        assert 'max_time_ms' in func_stats

        assert func_stats['count'] == 2
        assert func_stats['avg_time_ms'] > 0

    def test_get_bottlenecks(self):
        """Test bottleneck detection"""
        profiler = PerformanceProfiler()

        @profiler.time_function()
        def slow_func():
            time.sleep(0.15)  # 150ms - above threshold

        @profiler.time_function()
        def fast_func():
            time.sleep(0.01)  # 10ms - below threshold

        slow_func()
        fast_func()

        bottlenecks = profiler.get_bottlenecks(threshold_ms=100)

        slow_qualified = f"{slow_func.__module__}.{slow_func.__name__}"
        fast_qualified = f"{fast_func.__module__}.{fast_func.__name__}"
        assert slow_qualified in bottlenecks
        assert fast_qualified not in bottlenecks

    def test_clear(self):
        """Test clearing profiler data"""
        profiler = PerformanceProfiler()

        @profiler.time_function()
        def test_func():
            pass

        test_func()
        profiler.clear()

        assert len(profiler.timings) == 0
        assert len(profiler.call_counts) == 0

    def test_disabled_profiler(self):
        """Test that disabled profiler doesn't record"""
        profiler = PerformanceProfiler()
        profiler.disable()

        @profiler.time_function()
        def test_func():
            return "result"

        result = test_func()

        assert result == "result"
        assert len(profiler.timings) == 0  # Should not record


class TestTimer:
    """Tests for Timer context manager"""

    def test_timer_context_manager(self):
        """Test Timer context manager"""
        with Timer("test_operation", verbose=False) as t:
            time.sleep(0.01)

        assert t.elapsed_ms is not None
        assert t.elapsed_ms >= 10  # At least 10ms

    def test_timer_name(self):
        """Test Timer name"""
        with Timer("my_operation", verbose=False) as t:
            pass

        assert t.name == "my_operation"


class TestTimedDecorator:
    """Tests for timed decorator"""

    def test_timed_decorator(self, capsys):
        """Test timed decorator"""
        @timed
        def test_function():
            time.sleep(0.01)
            return "done"

        result = test_function()

        assert result == "done"

        # Check that timing was printed
        captured = capsys.readouterr()
        assert "test_function" in captured.out
        assert "ms" in captured.out
