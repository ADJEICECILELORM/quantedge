# tests/test_utils/test_cache_manager.py
import time
from utils.cache_manager import TTLCache, CacheManager


class TestTTLCache:
    """Tests for TTL Cache"""

    def test_init(self):
        """Test initialization"""
        cache = TTLCache(ttl_seconds=60, max_size=100)
        assert cache.ttl_seconds == 60
        assert cache.max_size == 100
        assert cache.hits == 0
        assert cache.misses == 0

    def test_set_and_get(self):
        """Test basic set/get"""
        cache = TTLCache()
        cache.set('key1', 'value1')

        value = cache.get('key1')
        assert value == 'value1'
        assert cache.hits == 1
        assert cache.misses == 0

    def test_get_miss(self):
        """Test cache miss"""
        cache = TTLCache()
        value = cache.get('nonexistent')

        assert value is None
        assert cache.misses == 1

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = TTLCache(ttl_seconds=0.1)  # 100ms TTL
        cache.set('key1', 'value1')

        # Should hit immediately
        assert cache.get('key1') == 'value1'

        # Wait for expiration
        time.sleep(0.15)

        # Should miss after expiration
        assert cache.get('key1') is None

    def test_max_size_limit(self):
        """Test max size enforcement"""
        cache = TTLCache(max_size=5)

        # Add 10 entries
        for i in range(10):
            cache.set(f'key{i}', f'value{i}')

        # Should only have 5 (last 5)
        assert len(cache.cache) == 5
        assert cache.get('key0') is None  # First ones evicted
        assert cache.get('key9') == 'value9'  # Last ones kept

    def test_clear(self):
        """Test cache clearing"""
        cache = TTLCache()
        cache.set('key1', 'value1')
        cache.set('key2', 'value2')

        cache.clear()

        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_get_stats(self):
        """Test statistics"""
        cache = TTLCache()
        cache.set('key1', 'value1')
        cache.get('key1')  # Hit
        cache.get('key2')  # Miss

        stats = cache.get_stats()

        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['total_requests'] == 2
        assert stats['hit_rate_pct'] == 50.0
        assert stats['size'] == 1


class TestCacheManager:
    """Tests for Cache Manager"""

    def test_init(self):
        """Test initialization"""
        manager = CacheManager()

        assert manager.market_data_cache is not None
        assert manager.feature_cache is not None
        assert manager.prediction_cache is not None

    def test_make_key(self):
        """Test cache key generation"""
        manager = CacheManager()

        key1 = manager._make_key('func', 'arg1', 'arg2', param1='value1')
        key2 = manager._make_key('func', 'arg1', 'arg2', param1='value1')
        key3 = manager._make_key('func', 'arg1', 'arg3', param1='value1')

        # Same inputs = same key
        assert key1 == key2

        # Different inputs = different key
        assert key1 != key3

    def test_cache_market_data_decorator(self):
        """Test market data caching decorator"""
        manager = CacheManager()
        call_count = [0]

        @manager.cache_market_data
        def get_data(symbol):
            call_count[0] += 1
            return f"data_{symbol}"

        # First call - should execute
        result1 = get_data('EURUSD')
        assert result1 == 'data_EURUSD'
        assert call_count[0] == 1

        # Second call - should use cache
        result2 = get_data('EURUSD')
        assert result2 == 'data_EURUSD'
        assert call_count[0] == 1  # Not incremented

        # Different symbol - should execute
        result3 = get_data('GBPUSD')
        assert result3 == 'data_GBPUSD'
        assert call_count[0] == 2

    def test_clear_all(self):
        """Test clearing all caches"""
        manager = CacheManager()

        # Add data to caches
        manager.market_data_cache.set('key1', 'value1')
        manager.feature_cache.set('key2', 'value2')

        manager.clear_all()

        # All caches should be empty
        assert len(manager.market_data_cache.cache) == 0
        assert len(manager.feature_cache.cache) == 0

    def test_get_all_stats(self):
        """Test getting all statistics"""
        manager = CacheManager()

        # Use caches
        manager.market_data_cache.set('key1', 'value1')
        manager.market_data_cache.get('key1')
        manager.feature_cache.set('key2', 'value2')

        stats = manager.get_all_stats()

        assert 'market_data' in stats
        assert 'features' in stats
        assert stats['market_data']['size'] == 1
        assert stats['features']['size'] == 1
