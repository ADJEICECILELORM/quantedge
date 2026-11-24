# rag/regime_classifier.py - Market Regime Classification
"""
Classifies market regime based on:
- Price action (trend, volatility)
- News features
- Market microstructure

Regimes:
- Trend/Momentum → Use trend-following strategies
- Mean Reversion → Use counter-trend strategies
- Volatility Expansion → Use breakout strategies
- Low Volatility → Reduce positions
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
import pandas as pd

from rag.data_schemas import NewsFeatures, MarketRegime

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types"""
    TREND_MOMENTUM = "trend"
    MEAN_REVERSION = "reversion"
    VOLATILITY_EXPANSION = "volatility"
    LOW_VOLATILITY = "low_vol"
    UNKNOWN = "unknown"


class RegimeClassifier:
    """
    Market regime classification system.

    Uses multiple indicators:
    - ADX (trend strength)
    - Bollinger Band width (volatility)
    - ATR (volatility)
    - News impact scores
    - Volume

    Output: MarketRegime with type and confidence
    """

    def __init__(
        self,
        adx_trend_threshold: float = 25.0,
        bb_squeeze_threshold: float = 0.02,
        atr_expansion_threshold: float = 1.5
    ):
        self.adx_trend_threshold = adx_trend_threshold
        self.bb_squeeze_threshold = bb_squeeze_threshold
        self.atr_expansion_threshold = atr_expansion_threshold

        # Track recent regimes for stability
        self.regime_history = []
        self.max_history = 10

    def classify(
        self,
        df: pd.DataFrame,
        news_features: Optional[NewsFeatures] = None
    ) -> MarketRegime:
        """
        Classify current market regime.

        Args:
            df: OHLCV DataFrame with indicators
            news_features: Latest news features (optional)

        Returns:
            MarketRegime with type and confidence
        """
        try:
            if df is None or len(df) < 50:
                return self._get_default_regime()

            # Calculate regime indicators
            indicators = self._calculate_indicators(df)

            # Score each regime
            scores = {
                RegimeType.TREND_MOMENTUM: self._score_trend(indicators, news_features),
                RegimeType.MEAN_REVERSION: self._score_reversion(indicators, news_features),
                RegimeType.VOLATILITY_EXPANSION: self._score_volatility(indicators, news_features),
                RegimeType.LOW_VOLATILITY: self._score_low_vol(indicators, news_features)
            }

            # Select regime with highest score
            best_regime = max(scores, key=scores.get)
            confidence = scores[best_regime]

            # Apply regime stability filter
            stable_regime, stable_confidence = self._apply_stability_filter(
                best_regime, confidence
            )

            # Create characteristics dict
            characteristics = {
                'adx': indicators.get('adx', 0),
                'bb_width': indicators.get('bb_width', 0),
                'atr_ratio': indicators.get('atr_ratio', 0),
                'volatility': indicators.get('volatility', 0),
                'scores': {r.value: s for r, s in scores.items()}
            }

            if news_features:
                characteristics['news_impact'] = news_features.impact_score
                characteristics['news_sentiment'] = news_features.sentiment

            regime = MarketRegime(
                regime_type=stable_regime.value,
                confidence=stable_confidence,
                characteristics=characteristics,
                timestamp=datetime.now()
            )

            # Store in history
            self.regime_history.append(stable_regime)
            if len(self.regime_history) > self.max_history:
                self.regime_history.pop(0)

            return regime

        except Exception as e:
            logger.error(f"Error classifying regime: {e}")
            return self._get_default_regime()

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate regime indicators"""
        indicators = {}

        try:
            # ADX (trend strength)
            if 'adx' in df.columns:
                indicators['adx'] = df['adx'].iloc[-1]
            else:
                # Simple ADX approximation
                indicators['adx'] = 20.0

            # Bollinger Band width (volatility)
            if 'bb_width' in df.columns:
                indicators['bb_width'] = df['bb_width'].iloc[-1]
            else:
                # Calculate from price
                std_20 = df['close'].rolling(20).std().iloc[-1]
                sma_20 = df['close'].rolling(20).mean().iloc[-1]
                indicators['bb_width'] = (std_20 * 2) / sma_20 if sma_20 > 0 else 0.02

            # ATR ratio (current vs average)
            if 'atr_14' in df.columns:
                current_atr = df['atr_14'].iloc[-1]
                avg_atr = df['atr_14'].rolling(50).mean().iloc[-1]
                indicators['atr_ratio'] = current_atr / avg_atr if avg_atr > 0 else 1.0
            else:
                indicators['atr_ratio'] = 1.0

            # Volatility (returns std)
            returns = df['close'].pct_change()
            indicators['volatility'] = returns.rolling(20).std().iloc[-1]

            # Price momentum
            indicators['momentum'] = (df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")

        return indicators

    def _score_trend(self, indicators: Dict, news: Optional[NewsFeatures]) -> float:
        """
        Score trend/momentum regime.

        High ADX + Clear momentum + Directional news = Strong trend
        """
        score = 0.0

        # ADX component (40%)
        adx = indicators.get('adx', 0)
        if adx > self.adx_trend_threshold:
            adx_score = min(1.0, (adx - self.adx_trend_threshold) / 30.0)
            score += adx_score * 0.4

        # Momentum component (30%)
        momentum = abs(indicators.get('momentum', 0))
        momentum_score = min(1.0, momentum * 20)  # Scale to 0-1
        score += momentum_score * 0.3

        # News alignment (30%)
        if news:
            # Trending regime likes high-impact, directional news
            impact_score = news.impact_score
            sentiment_strength = abs(news.sentiment)  # Strong sentiment (either direction)
            news_score = (impact_score + sentiment_strength) / 2
            score += news_score * 0.3

        return min(1.0, score)

    def _score_reversion(self, indicators: Dict, news: Optional[NewsFeatures]) -> float:
        """
        Score mean-reversion regime.

        Low ADX + Range-bound + No major news = Mean reversion
        """
        score = 0.0

        # Low ADX component (40%)
        adx = indicators.get('adx', 0)
        if adx < self.adx_trend_threshold:
            adx_score = 1.0 - (adx / self.adx_trend_threshold)
            score += adx_score * 0.4

        # Range-bound component (30%)
        # Low BB width = range-bound
        bb_width = indicators.get('bb_width', 0)
        if bb_width < 0.03:  # Tight range
            range_score = 1.0 - (bb_width / 0.03)
            score += range_score * 0.3

        # News component (30%)
        if news:
            # Reversion prefers low-impact news
            low_impact_score = 1.0 - news.impact_score
            score += low_impact_score * 0.3
        else:
            score += 0.3  # No news = good for reversion

        return min(1.0, score)

    def _score_volatility(self, indicators: Dict, news: Optional[NewsFeatures]) -> float:
        """
        Score volatility expansion regime.

        High ATR ratio + Widening BBs + High-impact news = Volatility breakout
        """
        score = 0.0

        # ATR expansion component (40%)
        atr_ratio = indicators.get('atr_ratio', 1.0)
        if atr_ratio > self.atr_expansion_threshold:
            atr_score = min(1.0, (atr_ratio - 1.0) / 0.5)
            score += atr_score * 0.4

        # BB width component (30%)
        bb_width = indicators.get('bb_width', 0)
        if bb_width > 0.04:  # Wide bands
            width_score = min(1.0, bb_width / 0.08)
            score += width_score * 0.3

        # News component (30%)
        if news:
            # Volatility expansion likes high-impact, novel news
            impact_novelty = (news.impact_score + news.novelty_score) / 2
            score += impact_novelty * 0.3

        return min(1.0, score)

    def _score_low_vol(self, indicators: Dict, news: Optional[NewsFeatures]) -> float:
        """
        Score low volatility regime.

        Very low ATR + Tight BBs + No news = Low volatility (reduce positions)
        """
        score = 0.0

        # Low ATR component (40%)
        atr_ratio = indicators.get('atr_ratio', 1.0)
        if atr_ratio < 0.8:
            atr_score = 1.0 - atr_ratio
            score += atr_score * 0.4

        # Tight BB component (30%)
        bb_width = indicators.get('bb_width', 0)
        if bb_width < self.bb_squeeze_threshold:
            tightness_score = 1.0 - (bb_width / self.bb_squeeze_threshold)
            score += tightness_score * 0.3

        # News component (30%)
        if news:
            # Low vol prefers no impact
            low_impact = 1.0 - news.impact_score
            score += low_impact * 0.3
        else:
            score += 0.3  # No news = low vol

        return min(1.0, score)

    def _apply_stability_filter(
        self,
        new_regime: RegimeType,
        confidence: float
    ) -> tuple[RegimeType, float]:
        """
        Apply stability filter to prevent regime flipping.

        Only change regime if:
        - New regime confidence > 0.7 AND
        - Different from recent majority
        """
        if len(self.regime_history) < 3:
            return new_regime, confidence

        # Count recent regimes
        recent = self.regime_history[-5:]
        most_common = max(set(recent), key=recent.count)
        most_common_count = recent.count(most_common)

        # If new regime is very confident, allow change
        if confidence > 0.75:
            return new_regime, confidence

        # If current regime is stable, stick with it
        if most_common_count >= 3:
            # Reduce confidence slightly (we're overriding)
            return most_common, confidence * 0.9

        return new_regime, confidence

    def _get_default_regime(self) -> MarketRegime:
        """Return default unknown regime"""
        return MarketRegime(
            regime_type=RegimeType.UNKNOWN.value,
            confidence=0.3,
            characteristics={'reason': 'insufficient_data'},
            timestamp=datetime.now()
        )

    def get_recommended_strategy(self, regime: MarketRegime) -> Dict:
        """
        Get recommended trading strategy for current regime.

        Returns:
            Dict with strategy recommendations
        """
        strategies = {
            RegimeType.TREND_MOMENTUM.value: {
                'name': 'Trend Following',
                'description': 'Use moving average crossovers, breakout strategies',
                'stop_loss_type': 'trailing',
                'take_profit_ratio': 2.0,
                'position_size_multiplier': 1.0
            },
            RegimeType.MEAN_REVERSION.value: {
                'name': 'Mean Reversion',
                'description': 'Buy oversold, sell overbought (RSI, BB)',
                'stop_loss_type': 'fixed',
                'take_profit_ratio': 1.0,
                'position_size_multiplier': 0.8
            },
            RegimeType.VOLATILITY_EXPANSION.value: {
                'name': 'Breakout Trading',
                'description': 'Trade volatility breakouts, use wide stops',
                'stop_loss_type': 'volatility_adjusted',
                'take_profit_ratio': 2.5,
                'position_size_multiplier': 1.2
            },
            RegimeType.LOW_VOLATILITY.value: {
                'name': 'Reduce Positions',
                'description': 'Low volatility = low opportunity, reduce risk',
                'stop_loss_type': 'tight',
                'take_profit_ratio': 0.8,
                'position_size_multiplier': 0.5  # Half normal size
            },
            RegimeType.UNKNOWN.value: {
                'name': 'Conservative',
                'description': 'Unknown regime, trade cautiously',
                'stop_loss_type': 'fixed',
                'take_profit_ratio': 1.5,
                'position_size_multiplier': 0.6
            }
        }

        return strategies.get(regime.regime_type, strategies[RegimeType.UNKNOWN.value])
