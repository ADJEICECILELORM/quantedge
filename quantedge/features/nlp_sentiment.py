# features/nlp_sentiment.py - NLP Bag-of-Words for BTC-ETH Correlation
import pandas as pd
from collections import Counter
from typing import List, Dict

class NLPSentimentAnalyzer:
    """
    NLP-based sentiment analysis using Bag-of-Words approach.
    Analyzes BTC and ETH price movements to generate sentiment features.
    """
    def __init__(self):
        # Define "vocabulary" for price action patterns
        self.bullish_words = [
            'breakout', 'rally', 'surge', 'pump', 'moon',
            'bullish', 'accumulation', 'support_hold', 'higher_high'
        ]

        self.bearish_words = [
            'breakdown', 'crash', 'dump', 'capitulation', 'bearish',
            'distribution', 'resistance_reject', 'lower_low'
        ]

        self.neutral_words = [
            'consolidation', 'ranging', 'sideways', 'chop', 'equilibrium'
        ]

    def price_to_words(self, df: pd.DataFrame) -> List[str]:
        """
        Convert price action into 'words' (patterns).
        df: DataFrame with OHLC data
        """
        if len(df) < 20:
            return []

        words = []

        # Calculate features
        close = df['close']
        high = df['high']
        low = df['low']

        # Returns
        ret_1 = close.pct_change(1).iloc[-1]
        ret_5 = close.pct_change(5).iloc[-1]

        # Highs/Lows
        is_higher_high = high.iloc[-1] > high.iloc[-2]
        is_lower_low = low.iloc[-1] < low.iloc[-2]

        # Volatility
        volatility = close.rolling(10).std().iloc[-1] / close.iloc[-1]

        # Pattern detection
        if ret_5 > 0.05:  # 5% gain in 5 periods
            words.append('surge')
            words.append('bullish')
        elif ret_5 > 0.02:
            words.append('rally')
        elif ret_5 < -0.05:
            words.append('dump')
            words.append('bearish')
        elif ret_5 < -0.02:
            words.append('crash')

        if is_higher_high and ret_1 > 0:
            words.append('higher_high')
            words.append('breakout')

        if is_lower_low and ret_1 < 0:
            words.append('lower_low')
            words.append('breakdown')

        if abs(ret_5) < 0.01:  # Low movement
            words.append('consolidation')
            words.append('sideways')

        if volatility > 0.03:
            words.append('pump' if ret_1 > 0 else 'dump')

        return words

    def calculate_sentiment_score(self, words: List[str]) -> Dict:
        """
        Calculate sentiment score from bag-of-words.
        Returns: {'bullish_score': 0-1, 'bearish_score': 0-1, 'sentiment': 'bullish'/'bearish'/'neutral'}
        """
        if not words:
            return {'bullish_score': 0.5, 'bearish_score': 0.5, 'sentiment': 'neutral'}

        # Count word occurrences
        word_counts = Counter(words)

        # Calculate scores
        bullish_count = sum(word_counts[w] for w in self.bullish_words if w in word_counts)
        bearish_count = sum(word_counts[w] for w in self.bearish_words if w in word_counts)
        total_count = len(words)

        bullish_score = bullish_count / total_count if total_count > 0 else 0.5
        bearish_score = bearish_count / total_count if total_count > 0 else 0.5

        # Normalize to 0-1
        total_sentiment = bullish_score + bearish_score
        if total_sentiment > 0:
            bullish_score = bullish_score / total_sentiment
            bearish_score = bearish_score / total_sentiment
        else:
            bullish_score = 0.5
            bearish_score = 0.5

        # Determine sentiment
        if bullish_score > 0.6:
            sentiment = 'bullish'
        elif bearish_score > 0.6:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        return {
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'sentiment': sentiment,
            'words': words
        }

    def analyze_btc_eth_correlation(self, df_btc: pd.DataFrame, df_eth: pd.DataFrame) -> Dict:
        """
        Analyze BTC-ETH correlation and generate trading signals.
        Returns: {'correlation': float, 'divergence': float, 'signal': str}
        """
        if df_btc is None or df_eth is None:
            return {'correlation': 0, 'divergence': 0, 'signal': 'none', 'confidence': 0}

        if len(df_btc) < 20 or len(df_eth) < 20:
            return {'correlation': 0, 'divergence': 0, 'signal': 'none', 'confidence': 0}

        # Get sentiment for both
        btc_words = self.price_to_words(df_btc)
        eth_words = self.price_to_words(df_eth)

        btc_sentiment = self.calculate_sentiment_score(btc_words)
        eth_sentiment = self.calculate_sentiment_score(eth_words)

        # Calculate correlation (using last 20 bars)
        btc_returns = df_btc['close'].pct_change().iloc[-20:]
        eth_returns = df_eth['close'].pct_change().iloc[-20:]

        correlation = btc_returns.corr(eth_returns)

        # Calculate divergence
        divergence = abs(btc_sentiment['bullish_score'] - eth_sentiment['bullish_score'])

        # Generate signal
        signal = 'none'
        confidence = 0

        # Strategy: When BTC and ETH diverge, it signals market confusion or opportunity
        if divergence > 0.3 and correlation < 0.5:
            # High divergence, low correlation = Opportunity
            if btc_sentiment['sentiment'] == 'bullish' and eth_sentiment['sentiment'] == 'bearish':
                signal = 'btc_strong_eth_weak'
                confidence = divergence
            elif btc_sentiment['sentiment'] == 'bearish' and eth_sentiment['sentiment'] == 'bullish':
                signal = 'eth_strong_btc_weak'
                confidence = divergence

        # Strategy 2: When both align strongly, follow the trend
        if btc_sentiment['sentiment'] == eth_sentiment['sentiment'] and divergence < 0.2:
            if btc_sentiment['sentiment'] == 'bullish':
                signal = 'crypto_bullish'
                confidence = 1 - divergence
            elif btc_sentiment['sentiment'] == 'bearish':
                signal = 'crypto_bearish'
                confidence = 1 - divergence

        return {
            'correlation': correlation,
            'divergence': divergence,
            'signal': signal,
            'confidence': confidence,
            'btc_sentiment': btc_sentiment,
            'eth_sentiment': eth_sentiment
        }

    def create_nlp_features(self, df_btc: pd.DataFrame, df_eth: pd.DataFrame) -> Dict:
        """
        Create NLP-derived features for the main trading model.
        Returns a dict of features to add to the feature engineer.
        """
        analysis = self.analyze_btc_eth_correlation(df_btc, df_eth)

        features = {
            'crypto_correlation': analysis['correlation'],
            'crypto_divergence': analysis['divergence'],
            'crypto_signal_strength': analysis['confidence'],
            'btc_bullish_score': analysis.get('btc_sentiment', {}).get('bullish_score', 0.5),
            'eth_bullish_score': analysis.get('eth_sentiment', {}).get('bullish_score', 0.5),
        }

        # Encode signal as numeric
        signal_encoding = {
            'none': 0,
            'crypto_bullish': 1,
            'crypto_bearish': -1,
            'btc_strong_eth_weak': 0.5,
            'eth_strong_btc_weak': -0.5
        }
        features['crypto_signal_encoded'] = signal_encoding.get(analysis['signal'], 0)

        return features
