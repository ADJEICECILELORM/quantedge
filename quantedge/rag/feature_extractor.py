# rag/feature_extractor.py - News Feature Extraction
"""
Extracts structured ML features from news events.
NO raw text decisions - only quantifiable features.
"""

import logging
from typing import List, Dict
from datetime import datetime, timezone
import numpy as np

from rag.data_schemas import (
    StructuredNewsEvent, NewsFeatures, EventType
)

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """
    Extracts trading features from news events.

    Outputs ONLY structured features:
    - Sentiment (-1 to +1)
    - Novelty (0-1: how surprising)
    - Impact (0-1: expected market move)
    - Confidence (0-1: confidence in analysis)
    - Time decay (0-1: based on event age)
    """

    def __init__(self):
        # Sentiment lexicons (simple keyword-based for now)
        self.bullish_keywords = [
            'positive', 'growth', 'increase', 'rise', 'beat', 'exceed',
            'strong', 'robust', 'improve', 'gain', 'rally', 'boost',
            'optimistic', 'expansion', 'recovery', 'surge'
        ]

        self.bearish_keywords = [
            'negative', 'decline', 'fall', 'miss', 'weak', 'poor',
            'recession', 'crisis', 'concern', 'risk', 'drop', 'plunge',
            'pessimistic', 'contraction', 'slowdown', 'crash'
        ]

        # High-impact event types
        self.high_impact_types = [
            EventType.RATE_DECISION,
            EventType.ECONOMIC_DATA,
            EventType.GEOPOLITICAL
        ]

    def extract_features(
        self,
        event: StructuredNewsEvent,
        similar_events: List[Dict]
    ) -> NewsFeatures:
        """
        Extract all features from news event.

        Args:
            event: The news event to analyze
            similar_events: Similar historical events from RAG

        Returns:
            NewsFeatures with all extracted features
        """
        try:
            # Calculate sentiment
            sentiment = self._calculate_sentiment(event)

            # Calculate novelty (how unique is this event?)
            novelty = self._calculate_novelty(event, similar_events)

            # Calculate impact (expected market move)
            impact = self._calculate_impact(event, similar_events)

            # Calculate confidence
            confidence = self._calculate_confidence(event, similar_events)

            # Calculate time decay
            hours_since = (datetime.now(timezone.utc) - event.timestamp).total_seconds() / 3600
            time_decay = self._calculate_time_decay(hours_since)

            # Historical context
            similar_count = len(similar_events)
            historical_avg_impact = self._calculate_historical_avg_impact(similar_events)

            return NewsFeatures(
                event_id=event.event_id,
                event_type=event.event_type,
                sentiment=sentiment,
                novelty_score=novelty,
                impact_score=impact,
                confidence=confidence,
                source_score_composite=event.source_score.composite_score,
                time_decay_factor=time_decay,
                similar_events_count=similar_count,
                historical_avg_impact=historical_avg_impact,
                timestamp=event.timestamp,
                hours_since_event=hours_since
            )

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            # Return default low-confidence features
            return self._get_default_features(event)

    def _calculate_sentiment(self, event: StructuredNewsEvent) -> float:
        """
        Calculate sentiment from -1 (bearish) to +1 (bullish).

        Simple keyword-based approach (can be enhanced with ML).
        """
        text = f"{event.title} {event.content}".lower()

        # Count keywords
        bullish_count = sum(1 for keyword in self.bullish_keywords if keyword in text)
        bearish_count = sum(1 for keyword in self.bearish_keywords if keyword in text)

        total_count = bullish_count + bearish_count

        if total_count == 0:
            return 0.0  # Neutral

        # Sentiment = (bullish - bearish) / total
        sentiment = (bullish_count - bearish_count) / total_count

        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, sentiment))

    def _calculate_novelty(
        self,
        event: StructuredNewsEvent,
        similar_events: List[Dict]
    ) -> float:
        """
        Calculate novelty score (0-1).

        Logic:
        - If many similar events exist → low novelty
        - If few/no similar events → high novelty (surprising)
        """
        if not similar_events:
            return 1.0  # Completely novel

        # Average similarity of top events
        avg_similarity = np.mean([
            e.get('similarity_score', 0.5) for e in similar_events[:3]
        ])

        # Novelty = 1 - similarity
        # High similarity → low novelty
        novelty = 1.0 - avg_similarity

        return max(0.0, min(1.0, novelty))

    def _calculate_impact(
        self,
        event: StructuredNewsEvent,
        similar_events: List[Dict]
    ) -> float:
        """
        Calculate expected market impact (0-1).

        Based on:
        - Event type (rate decisions = high impact)
        - Source credibility
        - Historical impact of similar events
        """
        # Base impact from event type
        if event.event_type in self.high_impact_types:
            base_impact = 0.8
        elif event.event_type == EventType.EARNINGS:
            base_impact = 0.6
        elif event.event_type == EventType.CORPORATE_ACTION:
            base_impact = 0.5
        else:
            base_impact = 0.3

        # Adjust by source credibility
        source_mult = 0.5 + (event.source_score.credibility_score * 0.5)
        impact = base_impact * source_mult

        # If we have historical data, use it
        if similar_events and len(similar_events) >= 3:
            # TODO: Calculate actual historical volatility spike
            # For now, use default
            pass

        return max(0.0, min(1.0, impact))

    def _calculate_confidence(
        self,
        event: StructuredNewsEvent,
        similar_events: List[Dict]
    ) -> float:
        """
        Calculate confidence in analysis (0-1).

        Based on:
        - Source credibility
        - Number of similar historical events (more history = higher confidence)
        - Event age (very recent = lower confidence, need confirmation)
        """
        # Source credibility component (40%)
        source_conf = event.source_score.credibility_score * 0.4

        # Historical sample size component (30%)
        # More similar events = higher confidence
        sample_conf = min(1.0, len(similar_events) / 10) * 0.3

        # Time component (30%)
        # Events 1-6 hours old have highest confidence (confirmed but still relevant)
        hours_since = (datetime.now(timezone.utc) - event.timestamp).total_seconds() / 3600

        if hours_since < 0.5:  # Very recent (< 30 min)
            time_conf = 0.5 * 0.3  # Lower confidence (needs confirmation)
        elif hours_since < 6:  # Sweet spot (30 min - 6 hours)
            time_conf = 1.0 * 0.3  # High confidence
        elif hours_since < 24:  # Still relevant (6-24 hours)
            time_conf = 0.7 * 0.3
        else:  # Old news
            time_conf = 0.3 * 0.3

        confidence = source_conf + sample_conf + time_conf

        return max(0.0, min(1.0, confidence))

    def _calculate_time_decay(self, hours_since_event: float, half_life: float = 12.0) -> float:
        """
        Calculate time decay factor using exponential decay.

        Args:
            hours_since_event: Hours since event occurred
            half_life: Half-life in hours (default 12 hours)

        Returns:
            Decay factor from 0 to 1 (1 = just happened, 0 = very old)
        """
        # Exponential decay: e^(-t * ln(2) / half_life)
        decay = np.exp(-hours_since_event * np.log(2) / half_life)
        return max(0.0, min(1.0, decay))

    def _calculate_historical_avg_impact(self, similar_events: List[Dict]) -> float:
        """
        Calculate average historical impact from similar events.

        TODO: Implement actual volatility calculation from historical data.
        For now, return default based on count.
        """
        if not similar_events:
            return 0.5  # Unknown

        # If we have source scores in similar events
        if similar_events[0].get('source_score'):
            avg_score = np.mean([e.get('source_score', 0.5) for e in similar_events])
            return avg_score

        return 0.5

    def _get_default_features(self, event: StructuredNewsEvent) -> NewsFeatures:
        """Return default low-confidence features"""
        hours_since = (datetime.now(timezone.utc) - event.timestamp).total_seconds() / 3600

        return NewsFeatures(
            event_id=event.event_id,
            event_type=event.event_type,
            sentiment=0.0,
            novelty_score=0.5,
            impact_score=0.3,
            confidence=0.3,
            source_score_composite=event.source_score.composite_score,
            time_decay_factor=self._calculate_time_decay(hours_since),
            similar_events_count=0,
            historical_avg_impact=0.5,
            timestamp=event.timestamp,
            hours_since_event=hours_since
        )

    def batch_extract(
        self,
        events: List[StructuredNewsEvent],
        rag_retriever
    ) -> List[NewsFeatures]:
        """
        Extract features for multiple events.

        Args:
            events: List of structured news events
            rag_retriever: RAG retriever for finding similar events

        Returns:
            List of extracted features
        """
        features_list = []

        for event in events:
            try:
                # Retrieve similar events for context
                query = f"{event.title} {event.event_type.value}"
                similar = rag_retriever.retrieve_similar(
                    query=query,
                    top_k=5,
                    min_score=0.5
                )

                # Extract features
                features = self.extract_features(event, similar)
                features_list.append(features)

            except Exception as e:
                logger.error(f"Error in batch extraction for {event.event_id}: {e}")

        return features_list
