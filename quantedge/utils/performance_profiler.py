# utils/performance_profiler.py - Performance Profiling & Monitoring
import time
import functools
import tracemalloc
from typing import Dict, Callable, Any
from collections import defaultdict
import json
import os
from datetime import datetime


class PerformanceProfiler:
    """
    Professional performance profiler for tracking execution times,
    memory usage, and bottlenecks.
    """

    def __init__(self):
        self.timings = defaultdict(list)
        self.memory_usage = defaultdict(list)
        self.call_counts = defaultdict(int)
        self.enabled = True

    def enable(self):
        """Enable profiling"""
        self.enabled = True

    def disable(self):
        """Disable profiling"""
        self.enabled = False

    def clear(self):
        """Clear all profiling data"""
        self.timings.clear()
        self.memory_usage.clear()
        self.call_counts.clear()

    def time_function(self, name: str = None):
        """
        Decorator to time function execution.

        Usage:
            @profiler.time_function()
            def my_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            func_name = name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

                self.timings[func_name].append(elapsed)
                self.call_counts[func_name] += 1

                return result
            return wrapper
        return decorator

    def profile_memory(self, name: str = None):
        """
        Decorator to profile memory usage.

        Usage:
            @profiler.profile_memory()
            def my_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            func_name = name or f"{func.__module__}.{func.__name__}"

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)

                tracemalloc.start()
                result = func(*args, **kwargs)
                current, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()

                self.memory_usage[func_name].append({
                    'current': current / 1024 / 1024,  # MB
                    'peak': peak / 1024 / 1024  # MB
                })

                return result
            return wrapper
        return decorator

    def get_statistics(self) -> Dict:
        """Get comprehensive performance statistics"""
        stats = {}

        for func_name, times in self.timings.items():
            if times:
                stats[func_name] = {
                    'count': self.call_counts[func_name],
                    'total_time_ms': sum(times),
                    'avg_time_ms': sum(times) / len(times),
                    'min_time_ms': min(times),
                    'max_time_ms': max(times),
                    'last_time_ms': times[-1]
                }

        return stats

    def get_memory_statistics(self) -> Dict:
        """Get memory usage statistics"""
        stats = {}

        for func_name, mem_records in self.memory_usage.items():
            if mem_records:
                stats[func_name] = {
                    'count': len(mem_records),
                    'avg_current_mb': sum(r['current'] for r in mem_records) / len(mem_records),
                    'avg_peak_mb': sum(r['peak'] for r in mem_records) / len(mem_records),
                    'max_peak_mb': max(r['peak'] for r in mem_records),
                    'last_peak_mb': mem_records[-1]['peak']
                }

        return stats

    def print_report(self, top_n: int = 10):
        """Print performance report"""
        print("\n" + "="*80)
        print("⚡ PERFORMANCE PROFILING REPORT")
        print("="*80)

        # Time statistics
        stats = self.get_statistics()
        if stats:
            print("\n📊 TOP SLOWEST FUNCTIONS:")
            sorted_stats = sorted(stats.items(), key=lambda x: x[1]['total_time_ms'], reverse=True)

            for i, (func_name, data) in enumerate(sorted_stats[:top_n], 1):
                print(f"\n{i}. {func_name}")
                print(f"   Calls: {data['count']}")
                print(f"   Total: {data['total_time_ms']:.2f} ms")
                print(f"   Avg: {data['avg_time_ms']:.2f} ms")
                print(f"   Min/Max: {data['min_time_ms']:.2f} / {data['max_time_ms']:.2f} ms")

        # Memory statistics
        mem_stats = self.get_memory_statistics()
        if mem_stats:
            print("\n💾 MEMORY USAGE:")
            sorted_mem = sorted(mem_stats.items(), key=lambda x: x[1]['max_peak_mb'], reverse=True)

            for i, (func_name, data) in enumerate(sorted_mem[:top_n], 1):
                print(f"\n{i}. {func_name}")
                print(f"   Calls: {data['count']}")
                print(f"   Avg Peak: {data['avg_peak_mb']:.2f} MB")
                print(f"   Max Peak: {data['max_peak_mb']:.2f} MB")

        print("\n" + "="*80 + "\n")

    def save_report(self, filename: str = None):
        """Save performance report to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"logs/performance_report_{timestamp}.json"

        os.makedirs(os.path.dirname(filename), exist_ok=True)

        report = {
            'timestamp': datetime.now().isoformat(),
            'timing_statistics': self.get_statistics(),
            'memory_statistics': self.get_memory_statistics()
        }

        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"💾 Performance report saved to {filename}")

    def get_bottlenecks(self, threshold_ms: float = 100) -> Dict:
        """Identify performance bottlenecks"""
        bottlenecks = {}

        for func_name, times in self.timings.items():
            if times:
                avg_time = sum(times) / len(times)
                if avg_time > threshold_ms:
                    bottlenecks[func_name] = {
                        'avg_time_ms': avg_time,
                        'total_time_ms': sum(times),
                        'calls': self.call_counts[func_name],
                        'severity': 'CRITICAL' if avg_time > 1000 else 'HIGH' if avg_time > 500 else 'MEDIUM'
                    }

        return bottlenecks


# Global profiler instance
profiler = PerformanceProfiler()


# Context manager for timing code blocks
class Timer:
    """
    Context manager for timing code blocks.

    Usage:
        with Timer("my_operation"):
            # code to time
    """
    def __init__(self, name: str, verbose: bool = True):
        self.name = name
        self.verbose = verbose
        self.start_time = None
        self.elapsed_ms = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start_time) * 1000
        if self.verbose:
            print(f"⏱️ {self.name}: {self.elapsed_ms:.2f} ms")


# Decorator for quick timing
def timed(func: Callable) -> Callable:
    """
    Simple decorator to time any function.

    Usage:
        @timed
        def my_function():
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"⏱️ {func.__name__}: {elapsed:.2f} ms")
        return result
    return wrapper
