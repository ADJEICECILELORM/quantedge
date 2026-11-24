# tests/test_utils/test_multi_timeframe.py
import pandas as pd
import numpy as np
from utils.multi_timeframe import MultiTimeframeAnalyzer


class TestMultiTimeframeAnalyzer:
    """Tests for Multi-Timeframe Analyzer"""

    def test_init(self):
        """Test initialization"""
        mtf = MultiTimeframeAnalyzer()
        assert len(mtf.timeframes) == 4
        assert '5m' in mtf.timeframes
        assert '1h' in mtf.timeframes

    def test_get_trend_bullish(self, sample_ohlcv_data):
        """Test trend detection - bullish case"""
        mtf = MultiTimeframeAnalyzer()

        # Create uptrend data
        df = sample_ohlcv_data.copy()
        df['close'] = pd.Series(range(len(df))) * 0.0001 + df['close'].iloc[0]

        result = mtf.get_trend(df)

        assert result['direction'] in [-1, 0, 1]
        assert 0 <= result['strength'] <= 1
        assert isinstance(result, dict)

    def test_get_trend_insufficient_data(self):
        """Test with insufficient data"""
        mtf = MultiTimeframeAnalyzer()

        # Only 10 bars (need 50+)
        df = pd.DataFrame({
            'close': [1.1] * 10,
            'high': [1.101] * 10,
            'low': [1.099] * 10
        })

        result = mtf.get_trend(df)
        assert result['direction'] == 0
        assert result['strength'] == 0

    def test_get_trend_none_input(self):
        """Test with None input"""
        mtf = MultiTimeframeAnalyzer()
        result = mtf.get_trend(None)
        assert result['direction'] == 0
        assert result['strength'] == 0

    def test_analyze_symbol(self, mock_mt5_connector):
        """Test symbol analysis across timeframes"""
        mtf = MultiTimeframeAnalyzer()
        results = mtf.analyze_symbol(mock_mt5_connector, 'EURUSD')

        assert isinstance(results, dict)
        assert len(results) == 4  # 4 timeframes
        assert all(tf in results for tf in ['5m', '15m', '1h', '4h'])

    def test_analyze_symbol_empty(self, mock_mt5_connector):
        """Test with empty symbol"""
        mtf = MultiTimeframeAnalyzer()
        results = mtf.analyze_symbol(mock_mt5_connector, '')
        assert results == {}

    def test_get_alignment_score(self, mock_mt5_connector):
        """Test alignment score calculation"""
        mtf = MultiTimeframeAnalyzer()

        # Get mock results
        results = mtf.analyze_symbol(mock_mt5_connector, 'EURUSD')
        alignment = mtf.get_alignment_score(results)

        assert isinstance(alignment, dict)
        assert 'aligned' in alignment
        assert 'direction' in alignment
        assert 'score' in alignment
        assert 'agreement' in alignment
        assert alignment['direction'] in [-1, 0, 1]
        assert 0 <= alignment['agreement'] <= 1

    def test_get_alignment_score_empty(self):
        """Test alignment with empty results"""
        mtf = MultiTimeframeAnalyzer()
        alignment = mtf.get_alignment_score({})

        assert alignment['aligned'] is False
        assert alignment['direction'] == 0
        assert alignment['score'] == 0

    def test_should_trade(self):
        """Test trade decision logic"""
        mtf = MultiTimeframeAnalyzer()

        # Aligned case
        alignment_yes = {
            'aligned': True,
            'agreement': 0.8,
            'direction': 1
        }
        assert mtf.should_trade(alignment_yes) is True

        # Not aligned
        alignment_no = {
            'aligned': False,
            'agreement': 0.5,
            'direction': 1
        }
        assert mtf.should_trade(alignment_no) is False

        # Neutral
        alignment_neutral = {
            'aligned': True,
            'agreement': 0.8,
            'direction': 0
        }
        assert mtf.should_trade(alignment_neutral) is False

    def test_get_confidence_multiplier(self):
        """Test confidence multiplier calculation"""
        mtf = MultiTimeframeAnalyzer()

        # Strong alignment
        alignment_strong = {
            'aligned': True,
            'score': 0.8
        }
        multiplier = mtf.get_confidence_multiplier(alignment_strong)
        assert 1.0 <= multiplier <= 1.5

        # Weak alignment
        alignment_weak = {
            'aligned': False,
            'score': 0.2
        }
        multiplier = mtf.get_confidence_multiplier(alignment_weak)
        assert multiplier == 0.9  # Penalty

    def test_vectorized_ema_calculation(self, sample_ohlcv_data):
        """Test vectorized EMA calculation"""
        mtf = MultiTimeframeAnalyzer()
        close_prices = sample_ohlcv_data['close']

        ema_12, ema_26, ema_50 = mtf._calculate_emas_vectorized(close_prices)

        assert isinstance(ema_12, (float, np.floating))
        assert isinstance(ema_26, (float, np.floating))
        assert isinstance(ema_50, (float, np.floating))
        assert ema_12 > 0
        assert ema_26 > 0
        assert ema_50 > 0
