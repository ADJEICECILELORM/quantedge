# utils/latency_monitor.py - Signal Generation Latency Monitoring
"""
Monitors and tracks latency of signal generation process.
Helps identify bottlenecks and optimize performance.
"""

import time
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import json
import os


class LatencyMonitor:
    """
    Monitors latency of signal generation and module processing.
    """

    def __init__(self, warning_threshold_ms: float = 1000.0):
        """
        Args:
            warning_threshold_ms: Threshold in milliseconds to trigger warnings
        """
        self.warning_threshold_ms = warning_threshold_ms
        self.warning_threshold_sec = warning_threshold_ms / 1000.0

        # Timing data
        self.current_timings = {}  # Temporary storage for current analysis
        self.module_latencies = defaultdict(list)  # module_name -> list of latencies
        self.symbol_latencies = defaultdict(list)  # symbol -> list of total latencies
        self.bottlenecks = []  # List of detected bottlenecks

        # Statistics
        self.total_signals_generated = 0
        self.slow_signals_count = 0

    def start_timing(self, operation: str):
        """
        Start timing an operation.

        Args:
            operation: Name of the operation (e.g., 'mtf_analysis', 'ml_prediction')
        """
        self.current_timings[operation] = time.time()

    def end_timing(self, operation: str) -> float:
        """
        End timing an operation and record the latency.

        Args:
            operation: Name of the operation

        Returns:
            Latency in seconds
        """
        if operation not in self.current_timings:
            return 0.0

        start_time = self.current_timings[operation]
        end_time = time.time()
        latency = end_time - start_time

        # Record latency
        self.module_latencies[operation].append(latency)

        # Check for bottleneck
        if latency > self.warning_threshold_sec:
            self.bottlenecks.append({
                'time': datetime.now(),
                'operation': operation,
                'latency_ms': latency * 1000,
                'severity': 'high' if latency > 2.0 else 'medium'
            })

        # Clean up
        del self.current_timings[operation]

        return latency

    def get_timing(self, operation: str) -> Optional[float]:
        """
        Get the latency of the last completed operation.

        Args:
            operation: Name of the operation

        Returns:
            Latency in seconds, or None if not found
        """
        if operation in self.module_latencies and self.module_latencies[operation]:
            return self.module_latencies[operation][-1]
        return None

    def record_signal_latency(self, symbol: str, total_latency: float,
                             breakdown: Dict[str, float]):
        """
        Record total signal generation latency for a symbol.

        Args:
            symbol: Trading symbol
            total_latency: Total time to generate signal (seconds)
            breakdown: Dictionary of module latencies
        """
        self.total_signals_generated += 1
        self.symbol_latencies[symbol].append(total_latency)

        # Check if slow
        if total_latency > self.warning_threshold_sec:
            self.slow_signals_count += 1

    def get_module_stats(self, module: str) -> Dict:
        """
        Get statistics for a specific module.

        Returns:
        {
            'avg_latency_ms': float,
            'min_latency_ms': float,
            'max_latency_ms': float,
            'p50_latency_ms': float,
            'p95_latency_ms': float,
            'p99_latency_ms': float,
            'count': int
        }
        """
        if module not in self.module_latencies or not self.module_latencies[module]:
            return self._empty_stats()

        latencies = self.module_latencies[module]
        latencies_ms = [lat * 1000 for lat in latencies]

        import numpy as np

        return {
            'avg_latency_ms': np.mean(latencies_ms),
            'min_latency_ms': np.min(latencies_ms),
            'max_latency_ms': np.max(latencies_ms),
            'p50_latency_ms': np.percentile(latencies_ms, 50),
            'p95_latency_ms': np.percentile(latencies_ms, 95),
            'p99_latency_ms': np.percentile(latencies_ms, 99),
            'count': len(latencies)
        }

    def _empty_stats(self) -> Dict:
        """Return empty stats structure"""
        return {
            'avg_latency_ms': 0.0,
            'min_latency_ms': 0.0,
            'max_latency_ms': 0.0,
            'p50_latency_ms': 0.0,
            'p95_latency_ms': 0.0,
            'p99_latency_ms': 0.0,
            'count': 0
        }

    def get_symbol_stats(self, symbol: str) -> Dict:
        """Get latency statistics for a specific symbol"""
        if symbol not in self.symbol_latencies or not self.symbol_latencies[symbol]:
            return self._empty_stats()

        latencies = self.symbol_latencies[symbol]
        latencies_ms = [lat * 1000 for lat in latencies]

        import numpy as np

        return {
            'avg_latency_ms': np.mean(latencies_ms),
            'min_latency_ms': np.min(latencies_ms),
            'max_latency_ms': np.max(latencies_ms),
            'p50_latency_ms': np.percentile(latencies_ms, 50),
            'p95_latency_ms': np.percentile(latencies_ms, 95),
            'p99_latency_ms': np.percentile(latencies_ms, 99),
            'count': len(latencies)
        }

    def get_overall_stats(self) -> Dict:
        """Get overall latency statistics"""
        all_latencies = []
        for latencies in self.symbol_latencies.values():
            all_latencies.extend(latencies)

        if not all_latencies:
            return {
                **self._empty_stats(),
                'total_signals': self.total_signals_generated,
                'slow_signals': self.slow_signals_count,
                'slow_percentage': 0.0
            }

        latencies_ms = [lat * 1000 for lat in all_latencies]

        import numpy as np

        return {
            'avg_latency_ms': np.mean(latencies_ms),
            'min_latency_ms': np.min(latencies_ms),
            'max_latency_ms': np.max(latencies_ms),
            'p50_latency_ms': np.percentile(latencies_ms, 50),
            'p95_latency_ms': np.percentile(latencies_ms, 95),
            'p99_latency_ms': np.percentile(latencies_ms, 99),
            'count': len(all_latencies),
            'total_signals': self.total_signals_generated,
            'slow_signals': self.slow_signals_count,
            'slow_percentage': (self.slow_signals_count / self.total_signals_generated * 100)
                              if self.total_signals_generated > 0 else 0.0
        }

    def get_slowest_modules(self, top_n: int = 5) -> List[Dict]:
        """
        Get the slowest modules by average latency.

        Returns:
            List of {module, avg_latency_ms, count}
        """
        module_avgs = []

        for module, latencies in self.module_latencies.items():
            if latencies:
                avg_latency_ms = sum(latencies) / len(latencies) * 1000
                module_avgs.append({
                    'module': module,
                    'avg_latency_ms': avg_latency_ms,
                    'count': len(latencies)
                })

        # Sort by average latency
        module_avgs.sort(key=lambda x: x['avg_latency_ms'], reverse=True)

        return module_avgs[:top_n]

    def get_latency_score(self, symbol: str, current_latency: float) -> Dict:
        """
        Calculate a latency score for the current signal (0-100).

        Args:
            symbol: Trading symbol
            current_latency: Current signal latency in seconds

        Returns:
        {
            'score': float (0-100),
            'rating': str ('excellent', 'good', 'fair', 'poor'),
            'current_latency_ms': float,
            'avg_latency_ms': float,
            'relative_speed': str
        }
        """
        current_latency_ms = current_latency * 1000

        # Get average latency for this symbol
        symbol_stats = self.get_symbol_stats(symbol)
        avg_latency_ms = symbol_stats['avg_latency_ms'] if symbol_stats['count'] > 0 else 500.0

        # Calculate score (100 = fastest, 0 = slowest)
        # Score based on latency thresholds
        if current_latency_ms < 100:
            score = 100
            rating = 'excellent'
        elif current_latency_ms < 300:
            score = 90
            rating = 'excellent'
        elif current_latency_ms < 500:
            score = 80
            rating = 'good'
        elif current_latency_ms < 1000:
            score = 60
            rating = 'fair'
        elif current_latency_ms < 2000:
            score = 40
            rating = 'poor'
        else:
            score = 20
            rating = 'very poor'

        # Determine relative speed
        if current_latency_ms < avg_latency_ms * 0.7:
            relative_speed = 'faster than average'
        elif current_latency_ms < avg_latency_ms * 1.3:
            relative_speed = 'average'
        else:
            relative_speed = 'slower than average'

        return {
            'score': score,
            'rating': rating,
            'current_latency_ms': current_latency_ms,
            'avg_latency_ms': avg_latency_ms,
            'relative_speed': relative_speed
        }

    def print_latency_report(self):
        """Print detailed latency analysis report"""
        print(f"\n{'='*60}")
        print("⚡ LATENCY MONITORING REPORT")
        print(f"{'='*60}")

        # Overall stats
        overall = self.get_overall_stats()
        print("\n📊 OVERALL STATISTICS:")
        print(f"   Total Signals: {overall['total_signals']}")
        print(f"   Slow Signals (>{self.warning_threshold_ms}ms): {overall['slow_signals']} "
              f"({overall['slow_percentage']:.1f}%)")
        print(f"   Avg Latency: {overall['avg_latency_ms']:.1f} ms")
        print(f"   P50 Latency: {overall['p50_latency_ms']:.1f} ms")
        print(f"   P95 Latency: {overall['p95_latency_ms']:.1f} ms")
        print(f"   P99 Latency: {overall['p99_latency_ms']:.1f} ms")

        # Slowest modules
        slowest = self.get_slowest_modules(top_n=5)
        if slowest:
            print("\n🐌 SLOWEST MODULES:")
            for i, module in enumerate(slowest, 1):
                print(f"   {i}. {module['module']}: {module['avg_latency_ms']:.1f} ms "
                      f"({module['count']} samples)")

        # Recent bottlenecks
        recent_bottlenecks = self.bottlenecks[-10:] if self.bottlenecks else []
        if recent_bottlenecks:
            print("\n⚠️ RECENT BOTTLENECKS (Last 10):")
            for bottleneck in recent_bottlenecks:
                severity_emoji = '🔴' if bottleneck['severity'] == 'high' else '🟡'
                print(f"   {severity_emoji} {bottleneck['operation']}: {bottleneck['latency_ms']:.1f} ms "
                      f"at {bottleneck['time'].strftime('%H:%M:%S')}")

        # Per-symbol stats
        print("\n📈 PER-SYMBOL LATENCY:")
        for symbol in sorted(self.symbol_latencies.keys()):
            stats = self.get_symbol_stats(symbol)
            if stats['count'] > 0:
                print(f"   {symbol}: {stats['avg_latency_ms']:.1f} ms avg "
                      f"(min: {stats['min_latency_ms']:.1f}, max: {stats['max_latency_ms']:.1f})")

        print(f"{'='*60}\n")

    def print_module_breakdown(self, module_timings: Dict[str, float]):
        """
        Print breakdown of module timings for a single signal.

        Args:
            module_timings: Dictionary of {module_name: latency_seconds}
        """
        total = sum(module_timings.values())
        total_ms = total * 1000

        print(f"\n⚡ Signal Generation Breakdown (Total: {total_ms:.1f} ms):")

        # Sort by latency
        sorted_modules = sorted(module_timings.items(), key=lambda x: x[1], reverse=True)

        for module, latency in sorted_modules:
            latency_ms = latency * 1000
            percentage = (latency / total * 100) if total > 0 else 0
            print(f"   {module}: {latency_ms:.1f} ms ({percentage:.1f}%)")

    def save_to_file(self, filepath: str = 'data/latency_monitor.json'):
        """Save latency data to file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Convert to serializable format
            data = {
                'module_latencies': {
                    module: latencies
                    for module, latencies in self.module_latencies.items()
                },
                'symbol_latencies': {
                    symbol: latencies
                    for symbol, latencies in self.symbol_latencies.items()
                },
                'bottlenecks': [
                    {**b, 'time': b['time'].isoformat()}
                    for b in self.bottlenecks
                ],
                'total_signals': self.total_signals_generated,
                'slow_signals': self.slow_signals_count
            }

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)

            print(f"💾 Latency data saved to {filepath}")
        except Exception as e:
            print(f"⚠️ Failed to save latency data: {e}")

    def load_from_file(self, filepath: str = 'data/latency_monitor.json') -> bool:
        """Load latency data from file"""
        try:
            if not os.path.exists(filepath):
                return False

            with open(filepath, 'r') as f:
                data = json.load(f)

            # Load module latencies
            for module, latencies in data.get('module_latencies', {}).items():
                self.module_latencies[module] = latencies

            # Load symbol latencies
            for symbol, latencies in data.get('symbol_latencies', {}).items():
                self.symbol_latencies[symbol] = latencies

            # Load bottlenecks
            self.bottlenecks = [
                {**b, 'time': datetime.fromisoformat(b['time'])}
                for b in data.get('bottlenecks', [])
            ]

            self.total_signals_generated = data.get('total_signals', 0)
            self.slow_signals_count = data.get('slow_signals', 0)

            print(f"✅ Loaded latency data from {filepath}")
            return True

        except Exception as e:
            print(f"⚠️ Failed to load latency data: {e}")
            return False

    def reset_statistics(self):
        """Reset all statistics"""
        self.module_latencies.clear()
        self.symbol_latencies.clear()
        self.bottlenecks.clear()
        self.total_signals_generated = 0
        self.slow_signals_count = 0
        print("✅ Latency statistics reset")
