# features/enhanced_feature_engineer.py - Enhanced Feature Engineering with V5 Features
"""
Enhanced feature engineering that includes:
- All original 80+ features
- Lead-lag indicators
- News phase features
- Time-based probability features
- Advanced market microstructure
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, Optional


class EnhancedFeatureEngineer:
    """
    Enhanced feature engineer with V5 advanced features.
    """

    def __init__(self):
        self.lead_lag_lookback = 20

    def create_features(self, df_main: pd.DataFrame,
                       df_crypto: Optional[pd.DataFrame] = None,
                       df_eth: Optional[pd.DataFrame] = None,
                       df_gold: Optional[pd.DataFrame] = None,
                       lead_lag_data: Optional[Dict] = None,
                       news_calendar: Optional[Dict] = None,
                       probability_data: Optional[Dict] = None) -> pd.DataFrame:
        """
        Create enhanced features including V5 signals.

        Args:
            df_main: Main asset OHLCV data
            df_crypto: BTC data for sentiment
            df_eth: ETH data for sentiment
            df_gold: Gold data for sentiment
            lead_lag_data: Lead-lag relationship data
            news_calendar: Upcoming news events
            probability_data: Historical win rate by time

        Returns:
            DataFrame with 100+ features
        """
        df = df_main.copy()

        # ============== ORIGINAL FEATURES (80+) ==============

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
        df['bb_position'] = (df['close'] - bollinger.bollinger_lband()) / (
            bollinger.bollinger_hband() - bollinger.bollinger_lband())
        df['bb_width'] = (bollinger.bollinger_hband() - bollinger.bollinger_lband()) / df['close']
        df['atr_14'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['atr_norm'] = df['atr_14'] / df['close']
        df['atr_ratio'] = df['atr_14'] / df['atr_14'].rolling(20).mean()
        df['volatility_10'] = df['returns_1'].rolling(10).std()
        df['volatility_20'] = df['returns_1'].rolling(20).std()

        # Garman-Klass
        h = np.log(df['high'] / df['open'])
        l = np.log(df['low'] / df['open'])
        c = np.log(df['close'] / df['open'])
        df['garman_klass'] = 0.5 * h**2 - 0.39 * (h*c) - 0.39 * (l*c) + 0.26 * (h*l)

        # --- D. Volume ---
        df['volume_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(20).mean()
        df['volume_change'] = df['tick_volume'].pct_change(1)
        df['obv'] = ta.volume.on_balance_volume(df['close'], df['tick_volume'])
        vwap = df['close'] * df['tick_volume']
        df['vwap'] = vwap.rolling(20).sum() / df['tick_volume'].rolling(20).sum()
        df['pv_corr'] = df['close'].rolling(20).corr(df['tick_volume'])
        df['money_flow'] = ta.volume.money_flow_index(df['high'], df['low'], df['close'],
                                                       df['tick_volume'])

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
        df['regime_label'] = np.where((df['adx'] > 25) & (df['close'] > df['sma_20']),
                                      'trending', 'ranging')
        df['regime_code'] = np.where(df['regime_label'] == 'trending', 1, 0)
        df['spread_norm'] = 0.0001
        df['liquidity_proxy'] = df['tick_volume'] * (df['high'] - df['low'])

        # --- G. Lags ---
        lags = [1, 2, 3, 5, 10]
        for lag in lags:
            df[f'rsi_lag_{lag}'] = df['rsi_14'].shift(lag)
            df[f'returns_lag_{lag}'] = df['returns_1'].shift(lag)

        # --- H. Session Reversion ---
        df['london_start'] = (df['hour'] == 8).astype(int)
        df['ny_start'] = (df['hour'] == 13).astype(int)
        df['london_open_price'] = df['open'].where(df['london_start'] == 1).ffill()
        df['ny_open_price'] = df['open'].where(df['ny_start'] == 1).ffill()
        df['stretch_london'] = (df['close'] - df['london_open_price']) / df['atr_14']
        df['stretch_ny'] = (df['close'] - df['ny_open_price']) / df['atr_14']

        # --- I. Crypto Hybrid Index ---
        if df_crypto is not None and df_eth is not None:
            btc_ret = df_crypto['close'].pct_change(5)
            eth_ret = df_eth['close'].pct_change(5)
            df = pd.merge_asof(df, pd.DataFrame({'time': df_crypto['time'], 'btc_ret': btc_ret}),
                              on='time', direction='backward')
            df = pd.merge_asof(df, pd.DataFrame({'time': df_eth['time'], 'eth_ret': eth_ret}),
                              on='time', direction='backward')
            df['btc_ret'].fillna(0, inplace=True)
            df['eth_ret'].fillna(0, inplace=True)
            df['crypto_index_score'] = (df['btc_ret'] * 0.6) + (df['eth_ret'] * 0.4)
        else:
            df['btc_ret'] = 0
            df['eth_ret'] = 0
            df['crypto_index_score'] = 0

        # ============== NEW V5 FEATURES ==============

        # --- J. Lead-Lag Features ---
        if lead_lag_data is not None:
            df = self._add_lead_lag_features(df, lead_lag_data)
        else:
            # Placeholder features
            df['lead_lag_signal'] = 0
            df['lead_lag_confidence'] = 0.5
            df['lead_lag_strength'] = 0
            df['is_follower'] = 0

        # --- K. News Phase Features ---
        if news_calendar is not None:
            df = self._add_news_features(df, news_calendar)
        else:
            # Placeholder features
            df['news_phase_code'] = 0  # 0=normal, 1=pre, 2=blackout, 3=post
            df['news_minutes_away'] = 999
            df['news_impact_score'] = 0
            df['volatility_spike_expected'] = 0

        # --- L. Probability Window Features ---
        if probability_data is not None:
            df = self._add_probability_features(df, probability_data)
        else:
            # Placeholder features
            df['hourly_win_rate'] = 0.5
            df['daily_win_rate'] = 0.5
            df['session_win_rate'] = 0.5
            df['time_probability_score'] = 0.5

        # --- M. Advanced Volatility Features ---
        df = self._add_volatility_features(df)

        # --- N. Multi-Timeframe Features ---
        df = self._add_multi_timeframe_features(df)

        # --- O. Market Microstructure ---
        df = self._add_microstructure_features(df)

        # Drop NaN rows
        df = df.dropna()

        return df

    def _add_lead_lag_features(self, df: pd.DataFrame, lead_lag_data: Dict) -> pd.DataFrame:
        """Add lead-lag relationship features"""
        # Simulate lead-lag detection
        df['lead_lag_signal'] = 0  # -1, 0, 1
        df['lead_lag_confidence'] = 0.5  # 0-1
        df['lead_lag_strength'] = 0.0  # correlation strength
        df['is_follower'] = 0  # Is this symbol a follower?

        # In production, this would use actual lead-lag detector results
        return df

    def _add_news_features(self, df: pd.DataFrame, news_calendar: Dict) -> pd.DataFrame:
        """Add news phase and event features"""
        df['news_phase_code'] = 0  # 0=normal, 1=pre, 2=blackout, 3=post
        df['news_minutes_away'] = 999  # Minutes to next high-impact news
        df['news_impact_score'] = 0  # 0-10 expected impact
        df['volatility_spike_expected'] = 0  # Binary: expecting spike?

        # Calculate actual ATR spike vs average
        df['atr_spike_ratio'] = df['atr_14'] / df['atr_14'].rolling(50).mean()
        df['is_volatility_spike'] = np.where(df['atr_spike_ratio'] > 1.5, 1, 0)

        return df

    def _add_probability_features(self, df: pd.DataFrame, probability_data: Dict) -> pd.DataFrame:
        """Add time-based probability features"""
        # Default values
        df['hourly_win_rate'] = 0.5
        df['daily_win_rate'] = 0.5
        df['session_win_rate'] = 0.5
        df['time_probability_score'] = 0.5

        # In production, lookup actual win rates from probability_data
        # For now, simulate based on session
        df['hourly_win_rate'] = np.where(df['session_london'] == 1, 0.62,
                                         np.where(df['session_ny'] == 1, 0.58, 0.52))
        df['session_win_rate'] = df['hourly_win_rate']  # Simplified
        df['time_probability_score'] = df['hourly_win_rate']

        return df

    def _add_volatility_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add advanced volatility features"""
        # Parkinson volatility (high-low range based)
        df['parkinson_vol'] = np.sqrt((1/(4*np.log(2))) *
                                     (np.log(df['high']/df['low']))**2)

        # Rogers-Satchell volatility
        df['rs_vol'] = np.sqrt(
            np.log(df['high']/df['close']) * np.log(df['high']/df['open']) +
            np.log(df['low']/df['close']) * np.log(df['low']/df['open'])
        )

        # Realized volatility (20-period)
        df['realized_vol'] = df['log_returns'].rolling(20).std() * np.sqrt(20)

        # Volatility clustering
        df['vol_clustering'] = df['volatility_20'].rolling(5).std()

        # Volatility regime (high/low)
        vol_median = df['volatility_20'].rolling(100).median()
        df['vol_regime'] = np.where(df['volatility_20'] > vol_median, 1, 0)

        return df

    def _add_multi_timeframe_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add multi-timeframe trend features"""
        # Simulate MTF analysis (4 timeframes)
        # In production, would calculate actual MTF indicators

        # Short-term trend (5-period)
        df['trend_5'] = np.where(df['close'] > df['close'].shift(5), 1, -1)

        # Medium-term trend (20-period)
        df['trend_20'] = np.where(df['close'] > df['sma_20'], 1, -1)

        # Long-term trend (50-period)
        df['trend_50'] = np.where(df['close'] > df['sma_50'], 1, -1)

        # Trend alignment score (-3 to +3)
        df['trend_alignment'] = df['trend_5'] + df['trend_20'] + df['trend_50']

        # Normalized alignment (0-1)
        df['trend_alignment_norm'] = (df['trend_alignment'] + 3) / 6

        return df

    def _add_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market microstructure features"""
        # Order flow imbalance proxy (close position in bar)
        df['order_flow'] = (df['close'] - df['open']) / (df['high'] - df['low'])

        # Bid-ask spread proxy (normalized range)
        df['spread_proxy'] = (df['high'] - df['low']) / df['close']

        # Price efficiency (how smoothly price moves)
        df['price_efficiency'] = abs(df['close'] - df['close'].shift(10)) / (
            df['high'].rolling(10).max() - df['low'].rolling(10).min())

        # Volume-weighted price change
        df['vwpc'] = df['returns_1'] * df['volume_ratio']

        # Amihud illiquidity (return per unit volume)
        df['illiquidity'] = abs(df['returns_1']) / (df['tick_volume'] + 1)

        return df

    def get_feature_names(self, df: pd.DataFrame) -> list:
        """Get list of feature column names (excluding metadata)"""
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume',
                       'target', 'regime_label']
        feature_cols = [c for c in df.columns if c not in exclude_cols]
        return feature_cols
