# rag/data_schemas.py - Data Schemas for News Intelligence
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from datetime import datetime
from enum import Enum


class EventType(Enum):
    """News event types"""
    RATE_DECISION = "rate_decision"
    EARNINGS = "earnings"
    GEOPOLITICAL = "geopolitical"
    REGULATORY = "regulatory"
    ECONOMIC_DATA = "economic_data"
    CORPORATE_ACTION = "corporate_action"
    MARKET_COMMENTARY = "market_commentary"
    UNKNOWN = "unknown"


class SourceType(Enum):
    """News source types"""
    REUTERS = "reuters"           # Authoritative
    BLOOMBERG = "bloomberg"       # Authoritative
    TWITTER = "twitter"           # Fast public
    REDDIT = "reddit"             # Fast public
    TELEGRAM = "telegram"         # Fast public
    ECONOMIC_CALENDAR = "calendar"  # Scheduled
    EARNINGS_CALENDAR = "earnings"  # Scheduled
    CUSTOM_RSS = "rss"
    UNKNOWN = "unknown"


@dataclass
class RawNewsEvent:
    """
    Raw news event from any source before processing.
    """
    source: str                    # "Reuters", "Twitter", etc.
    source_type: SourceType
    timestamp: datetime
    title: str
    content: str
    url: Optional[str] = None
    author: Optional[str] = None
    related_symbols: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'source': self.source,
            'source_type': self.source_type.value,
            'timestamp': self.timestamp.isoformat(),
            'title': self.title,
            'content': self.content,
            'url': self.url,
            'author': self.author,
            'related_symbols': self.related_symbols,
            'metadata': self.metadata
        }


@dataclass
class SourceScore:
    """
    Source credibility and performance scoring.
    """
    source_name: str
    speed_score: float           # 0-1 (latency vs competitors)
    credibility_score: float     # 0-1 (historical accuracy)
    sensitivity_score: float     # 0-1 (market impact correlation)
    manipulation_risk: float     # 0-1 (likelihood of manipulation)
    composite_score: float       # Weighted average

    def __post_init__(self):
        """Validate scores"""
        for score_name in ['speed_score', 'credibility_score', 'sensitivity_score',
                           'manipulation_risk', 'composite_score']:
            score = getattr(self, score_name)
            if not 0 <= score <= 1:
                raise ValueError(f"{score_name} must be between 0 and 1, got {score}")


@dataclass
class StructuredNewsEvent:
    """
    Processed news event with source scoring and standardization.
    """
    event_id: str                # Unique ID (hash of content + timestamp)
    source: str
    source_type: SourceType
    source_score: SourceScore
    timestamp: datetime          # Normalized UTC
    event_type: EventType
    title: str
    content: str
    related_symbols: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    # Embeddings (populated by RAG)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'event_id': self.event_id,
            'source': self.source,
            'source_type': self.source_type.value,
            'source_score': {
                'speed': self.source_score.speed_score,
                'credibility': self.source_score.credibility_score,
                'sensitivity': self.source_score.sensitivity_score,
                'manipulation_risk': self.source_score.manipulation_risk,
                'composite': self.source_score.composite_score
            },
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type.value,
            'title': self.title,
            'content': self.content,
            'related_symbols': self.related_symbols,
            'metadata': self.metadata
        }


@dataclass
class NewsFeatures:
    """
    Extracted features from news event (for ML/trading).
    NO raw text - only structured outputs.
    """
    event_id: str
    event_type: EventType
    sentiment: float             # -1 to +1 (bearish to bullish)
    novelty_score: float         # 0-1 (how unique/surprising)
    impact_score: float          # 0-1 (expected market impact)
    confidence: float            # 0-1 (confidence in analysis)
    source_score_composite: float  # From source scoring
    time_decay_factor: float     # 0-1 (based on event age)

    # Contextual
    similar_events_count: int    # Number of similar historical events
    historical_avg_impact: float  # Average impact of similar events

    # Timestamp
    timestamp: datetime
    hours_since_event: float

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'sentiment': self.sentiment,
            'novelty_score': self.novelty_score,
            'impact_score': self.impact_score,
            'confidence': self.confidence,
            'source_score_composite': self.source_score_composite,
            'time_decay_factor': self.time_decay_factor,
            'similar_events_count': self.similar_events_count,
            'historical_avg_impact': self.historical_avg_impact,
            'timestamp': self.timestamp.isoformat(),
            'hours_since_event': self.hours_since_event
        }


@dataclass
class MarketRegime:
    """Market regime classification"""
    regime_type: str             # 'trend', 'reversion', 'volatility', 'low_vol'
    confidence: float            # 0-1
    characteristics: Dict        # Additional regime info
    timestamp: datetime

    def to_dict(self) -> Dict:
        return {
            'regime_type': self.regime_type,
            'confidence': self.confidence,
            'characteristics': self.characteristics,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ProposedTrade:
    """
    Proposed trade for shadow mode or execution.
    """
    timestamp: datetime
    symbol: str
    direction: int               # 1=buy, -1=sell
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float         # Lot size
    confidence: float            # Overall confidence

    # Attribution
    news_contribution: float     # 0-1 (how much from news)
    math_contribution: float     # 0-1 (how much from quant models)
    regime: str                  # Market regime at time of decision

    # Features that led to decision
    news_features: Optional[NewsFeatures] = None
    quant_signals: Dict = field(default_factory=dict)
    microstructure_filters: Dict = field(default_factory=dict)

    # Execution
    shadow_mode: bool = True
    executed: bool = False
    execution_price: Optional[float] = None
    ticket: Optional[int] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'position_size': self.position_size,
            'confidence': self.confidence,
            'news_contribution': self.news_contribution,
            'math_contribution': self.math_contribution,
            'regime': self.regime,
            'quant_signals': self.quant_signals,
            'microstructure_filters': self.microstructure_filters,
            'shadow_mode': self.shadow_mode,
            'executed': self.executed,
            'execution_price': self.execution_price,
            'ticket': self.ticket
        }

        if self.news_features:
            result['news_features'] = self.news_features.to_dict()

        return result
