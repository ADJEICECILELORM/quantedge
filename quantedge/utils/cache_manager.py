# utils/cache_manager.py - Intelligent Caching System
import time
import hashlib
import json
import os
from typing import Any, Optional, Dict
from functools import wraps
from collections import OrderedDict


class TTLCache:
    """Time-To-Live cache with automatic expiration"""

    def __init__(self, ttl_seconds: float = 60.0, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.cache = OrderedDict()
        self.timestamps = {}
        self.hits = 0
        self.misses = 0

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry has expired"""
        if key not in self.timestamps:
            return True
        return (time.time() - self.timestamps[key]) > self.ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache and not self._is_expired(key):
            self.hits += 1
            # Move to end (LRU)
            self.cache.move_to_end(key)
            return self.cache[key]

        self.misses += 1
        return None

    def set(self, key: str, value: Any):
        """Set value in cache"""
        # Remove if exists
        if key in self.cache:
            del self.cache[key]

        # Add new entry
        self.cache[key] = value
        self.timestamps[key] = time.time()

        # Enforce max size
        if len(self.cache) > self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.timestamps.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0

        return {
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': total,
            'hit_rate_pct': hit_rate,
            'size': len(self.cache),
            'max_size': self.max_size
        }


class CacheManager:
    """
    Central cache manager for QuantEdge.
    Manages multiple caches with different TTLs.
    """

    def __init__(self):
        # Different caches for different data types
        self.market_data_cache = TTLCache(ttl_seconds=5.0, max_size=100)  # 5 sec for OHLCV
        self.feature_cache = TTLCache(ttl_seconds=60.0, max_size=50)  # 1 min for features
        self.prediction_cache = TTLCache(ttl_seconds=30.0, max_size=50)  # 30 sec for predictions
        self.indicator_cache = TTLCache(ttl_seconds=60.0, max_size=200)  # 1 min for indicators
        self.mtf_cache = TTLCache(ttl_seconds=60.0, max_size=100)  # 1 min for MTF analysis

    @staticmethod
    def _make_key(*args, **kwargs) -> str:
        """Create cache key from arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def cache_market_data(self, func):
        """Decorator for caching market data"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached = self.market_data_cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            if result is not None:
                self.market_data_cache.set(key, result)
            return result
        return wrapper

    def cache_features(self, func):
        """Decorator for caching feature calculations"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached = self.feature_cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            if result is not None:
                self.feature_cache.set(key, result)
            return result
        return wrapper

    def cache_predictions(self, func):
        """Decorator for caching ML predictions"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached = self.prediction_cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            if result is not None:
                self.prediction_cache.set(key, result)
            return result
        return wrapper

    def cache_indicators(self, func):
        """Decorator for caching technical indicators"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached = self.indicator_cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            if result is not None:
                self.indicator_cache.set(key, result)
            return result
        return wrapper

    def cache_mtf_analysis(self, func):
        """Decorator for caching multi-timeframe analysis"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, *args, **kwargs)
            cached = self.mtf_cache.get(key)
            if cached is not None:
                return cached

            result = func(*args, **kwargs)
            if result is not None:
                self.mtf_cache.set(key, result)
            return result
        return wrapper

    def clear_all(self):
        """Clear all caches"""
        self.market_data_cache.clear()
        self.feature_cache.clear()
        self.prediction_cache.clear()
        self.indicator_cache.clear()
        self.mtf_cache.clear()

    def get_all_stats(self) -> Dict:
        """Get statistics for all caches"""
        return {
            'market_data': self.market_data_cache.get_stats(),
            'features': self.feature_cache.get_stats(),
            'predictions': self.prediction_cache.get_stats(),
            'indicators': self.indicator_cache.get_stats(),
            'mtf_analysis': self.mtf_cache.get_stats()
        }

    def print_stats(self):
        """Print cache statistics"""
        print("\n" + "="*60)
        print("💾 CACHE STATISTICS")
        print("="*60)

        stats = self.get_all_stats()
        for cache_name, cache_stats in stats.items():
            print(f"\n📊 {cache_name.upper().replace('_', ' ')}:")
            print(f"   Hit Rate: {cache_stats['hit_rate_pct']:.1f}%")
            print(f"   Hits/Misses: {cache_stats['hits']}/{cache_stats['misses']}")
            print(f"   Size: {cache_stats['size']}/{cache_stats['max_size']}")

        print("\n" + "="*60 + "\n")

    def save_to_file(self, filepath: str = "data/cache_stats.json"):
        """Save cache statistics to file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        stats = self.get_all_stats()

        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)


# Global cache manager instance
cache_manager = CacheManager()


# Convenience decorators
def cache_market_data(func):
    """Cache market data with 5-second TTL"""
    return cache_manager.cache_market_data(func)


def cache_features(func):
    """Cache features with 60-second TTL"""
    return cache_manager.cache_features(func)


def cache_predictions(func):
    """Cache predictions with 30-second TTL"""
    return cache_manager.cache_predictions(func)


def cache_indicators(func):
    """Cache indicators with 60-second TTL"""
    return cache_manager.cache_indicators(func)


def cache_mtf_analysis(func):
    """Cache multi-timeframe analysis with 60-second TTL"""
    return cache_manager.cache_mtf_analysis(func)
