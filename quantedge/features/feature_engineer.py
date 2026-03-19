# features/feature_engineer.py
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
from typing import Optional, Dict
import hashlib

class FeatureEngineer:
    def __init__(self):
        # Feature caching
        self.feature_cache: Dict[str, Dict] = {}
        self.cache_ttl_seconds = 60  # Cache features for 60 seconds

        # Incremental update tracking
        self.last_processed_time: Dict[str, datetime] = {}
        self.cached_indicators: Dict[str, pd.DataFrame] = {}

    def detect_triangle(self, df):
        """
        Detects Triangle/Compression (Bollinger Squeeze).
        df: Raw MT5 Data (OHLCV).
        """
        if len(df) < 50:
            return False  # Not enough data for indicators

        # 1. Calculate ATR (14) using 'ta' library
        atr = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        current_atr = atr.iloc[-1]
        
        # 2. Calculate SMA (20)
        sma = ta.trend.sma_indicator(df['close'], window=20)
        current_sma = sma.iloc[-1]
        
        # 3. Calculate Bollinger Band Width
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        bb_upper = bollinger.bollinger_hband().iloc[-1]
        bb_lower = bollinger.bollinger_lband().iloc[-1]
        
        bb_width = (bb_upper - bb_lower) / current_sma
        atr_norm = current_atr / current_sma
        
        # 4. Squeeze Condition: Band width is smaller than ATR * 0.5 (Tightening)
        is_squeeze = bb_width < (atr_norm * 0.8)
        
        return is_squeeze

    def create_features(self, df_main, df_crypto=None, df_eth=None, df_gold=None):
        """
        df_main: The asset we are trading (e.g., EURUSD).
        df_crypto, df_eth, df_gold: Sentiment Data for Hybrid features.
        """
        df = df_main.copy()
        
        # --- A. Price Based ---
        df['returns_1'] = df['close'].pct_change(1)
        df['returns_5'] = df['close'].pct_change(5)
        df['returns_20'] = df['close'].pct_change(20)
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
        df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
        
        df['price_vs_sma20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['price_vs_sma50'] = (df['close'] - df['sma_50']) / df['sma_50']
        df['price_vs_ema12'] = (df['close'] - df['ema_12']) / df['ema_12']
        df['sma_cross'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
        df['high_low_range'] = (df['high'] - df['low']) / df['close']
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        df['price_momentum'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)

        # --- B. Oscillators ---
        df['rsi_14'] = ta.momentum.rsi(df['close'], window=14)
        df['rsi_norm'] = (df['rsi_14'] - 50) / 50
        df['rsi_change'] = df['rsi_14'].diff(1)
        df['stoch_k'] = ta.momentum.stochrsi_k(df['close'], window=14)
        df['stoch_d'] = ta.momentum.stochrsi_d(df['close'], window=14)
        df['stoch_diff'] = df['stoch_k'] - df['stoch_d']
        
        macd = ta.trend.MACD(df['close'])
        df['macd_hist'] = macd.macd_diff()
        df['macd_signal'] = macd.macd_signal()
        
        df['cci'] = ta.trend.cci(df['high'], df['low'], df['close'], window=20)
        df['williams_r'] = ta.momentum.williams_r(df['high'], df['low'], df['close'], lbp=14)

        # --- C. Volatility ---
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_position'] = (df['close'] - bollinger.bollinger_lband()) / (bollinger.bollinger_hband() - bollinger.bollinger_lband())
        df['bb_width'] = (bollinger.bollinger_hband() - bollinger.bollinger_lband()) / df['close']
        df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['atr_norm'] = df['atr_14'] / df['close']
        df['atr_ratio'] = df['atr_14'] / df['atr_14'].rolling(20).mean()
        df['volatility_10'] = df['returns_1'].rolling(10).std()
        df['volatility_20'] = df['returns_1'].rolling(20).std()
        
        # Garman-Klass
        h = np.log(df['high']/df['open'])
        l = np.log(df['low']/df['open'])
        c = np.log(df['close']/df['open'])
        df['garman_klass'] = 0.5 * h**2 - 0.39 * (h*c) - 0.39 * (l*c) + 0.26 * (h*l)

        # --- D. Volume ---
        df['volume_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(20).mean()
        df['volume_change'] = df['tick_volume'].pct_change(1)
        df['obv'] = ta.volume.on_balance_volume(df['close'], df['tick_volume'])
        vwap = df['close'] * df['tick_volume']
        df['vwap'] = vwap.rolling(20).sum() / df['tick_volume'].rolling(20).sum()
        df['pv_corr'] = df['close'].rolling(20).corr(df['tick_volume'])
        df['money_flow'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'], df['tick_volume'])

        # --- E. Trend ---
        adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
        df['adx'] = adx.adx()
        df['plus_di'] = adx.adx_pos()
        df['minus_di'] = adx.adx_neg()
        df['trend_strength'] = df['adx'] / 100
        df['higher_high'] = np.where(df['high'] > df['high'].shift(1), 1, 0)
        df['lower_low'] = np.where(df['low'] < df['low'].shift(1), 1, 0)

        # --- F. Market Regime ---
        df['hour'] = df['time'].dt.hour
        df['day_of_week'] = df['time'].dt.dayofweek
        df['session_asian'] = np.where((df['hour'] >= 0) & (df['hour'] < 8), 1, 0)
        df['session_london'] = np.where((df['hour'] >= 8) & (df['hour'] < 13), 1, 0)
        df['session_ny'] = np.where((df['hour'] >= 13) & (df['hour'] < 20), 1, 0)
        df['regime_label'] = np.where((df['adx'] > 25) & (df['close'] > df['sma_20']), 'trending', 'ranging')
        df['regime_code'] = np.where(df['regime_label'] == 'trending', 1, 0)
        df['spread_norm'] = 0.0001 
        df['liquidity_proxy'] = df['tick_volume'] * (df['high'] - df['low'])

        # --- G. Lags ---
        lags = [1, 2, 3, 5, 10]
        for lag in lags:
            df[f'rsi_lag_{lag}'] = df['rsi_14'].shift(lag)
            df[f'returns_lag_{lag}'] = df['returns_1'].shift(lag)

        # --- H. V2.0: Session Reversion (Hedge Fund) ---
        df['london_start'] = (df['hour'] == 8).astype(int)
        df['ny_start'] = (df['hour'] == 13).astype(int)
        df['london_open_price'] = df['open'].where(df['london_start'] == 1).ffill()
        df['ny_open_price'] = df['open'].where(df['ny_start'] == 1).ffill()
        df['stretch_london'] = (df['close'] - df['london_open_price']) / df['atr_14']
        df['stretch_ny'] = (df['close'] - df['ny_open_price']) / df['atr_14']

        # --- I. V2.0: Crypto Hybrid Index (BTC + ETH) ---
        if df_crypto is not None and df_eth is not None:
            btc_ret = df_crypto['close'].pct_change(5)
            eth_ret = df_eth['close'].pct_change(5)
            df = pd.merge_asof(df, pd.DataFrame({'time': df_crypto['time'], 'btc_ret': btc_ret}), on='time', direction='backward')
            df = pd.merge_asof(df, pd.DataFrame({'time': df_eth['time'], 'eth_ret': eth_ret}), on='time', direction='backward')
            
            # FIX: Fill NaNs immediately to prevent row deletion on merge failure
            df['btc_ret'].fillna(0, inplace=True)
            df['eth_ret'].fillna(0, inplace=True)
            
            df['crypto_index_score'] = (df['btc_ret'] * 0.6) + (df['eth_ret'] * 0.4)
            df['crypto_index_score'] = df['crypto_index_score'] * 100
        else:
            df['crypto_index_score'] = 0

        # --- J. V2.0: Mini-ALADDIN Macro USD Strength ---
        if df_gold is not None:
            gold_ret = df_gold['close'].pct_change(5)
            df = pd.merge_asof(df, pd.DataFrame({'time': df_gold['time'], 'gold_ret': gold_ret}), on='time', direction='backward')
            
            # FIX: Fill NaNs immediately
            df['gold_ret'].fillna(0, inplace=True)

            df['returns_5'].fillna(0, inplace=True)
            eur_ret = df['returns_5']
            gold_aligned = df['gold_ret'] * -1
            eur_aligned = eur_ret * -1
            df['macro_usd_strength'] = (gold_aligned + eur_aligned) / 2 * 100
        else:
            df['macro_usd_strength'] = 0

        # Clean up
        df.dropna(inplace=True)
        return df

    def calculate_atr(self, df: pd.DataFrame, window: int = 14) -> float:
        """Calculate ATR (Average True Range) helper method"""
        if df is None or len(df) < window:
            return 0.0

        atr_series = ta.volatility.average_true_range(
            df['high'],
            df['low'],
            df['close'],
            window=window
        )

        return atr_series.iloc[-1] if not atr_series.empty else 0.0

    def _get_cache_key(self, symbol: str, timeframe: int, df_length: int) -> str:
        """Generate cache key for features"""
        return f"{symbol}_{timeframe}_{df_length}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached features are still valid"""
        if cache_key not in self.feature_cache:
            return False

        cached_data = self.feature_cache[cache_key]
        cached_time = cached_data.get('timestamp')

        if not cached_time:
            return False

        age_seconds = (datetime.now() - cached_time).total_seconds()
        return age_seconds < self.cache_ttl_seconds

    def create_features_cached(
        self,
        symbol: str,
        timeframe: int,
        df_main: pd.DataFrame,
        df_crypto=None,
        df_eth=None,
        df_gold=None
    ) -> Optional[pd.DataFrame]:
        """
        Cached version of create_features.

        Returns cached features if valid, otherwise recalculates.
        """
        # Generate cache key
        cache_key = self._get_cache_key(symbol, timeframe, len(df_main))

        # Check cache
        if self._is_cache_valid(cache_key):
            cached_df = self.feature_cache[cache_key].get('features')
            if cached_df is not None and len(cached_df) > 0:
                return cached_df

        # Calculate features
        features = self.create_features(df_main, df_crypto, df_eth, df_gold)

        # Cache results
        if features is not None and len(features) > 0:
            self.feature_cache[cache_key] = {
                'features': features,
                'timestamp': datetime.now()
            }

        return features

    def clear_cache(self):
        """Clear feature cache"""
        self.feature_cache.clear()
        self.last_processed_time.clear()
        self.cached_indicators.clear()