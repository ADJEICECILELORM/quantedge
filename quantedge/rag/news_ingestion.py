# rag/news_ingestion.py - News Ingestion Orchestrator
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
from abc import ABC, abstractmethod
import hashlib
import json
import os

from rag.data_schemas import (
    RawNewsEvent, StructuredNewsEvent, EventType, SourceType
)
from rag.source_scoring import SourceScoringEngine, SourceScore

logger = logging.getLogger(__name__)


class NewsSource(ABC):
    """Abstract base class for news sources"""

    def __init__(self, source_name: str, source_type: SourceType):
        self.source_name = source_name
        self.source_type = source_type

    @abstractmethod
    def fetch_latest(self, minutes: int = 60) -> List[RawNewsEvent]:
        """Fetch latest news events from this source"""
        pass


class EconomicCalendarSource(NewsSource):
    """
    Economic calendar source (scheduled events).
    Mock implementation - replace with real API (e.g., ForexFactory, Investing.com)
    """

    def __init__(self):
        super().__init__("Economic Calendar", SourceType.ECONOMIC_CALENDAR)
        self.events_cache = []

    def fetch_latest(self, minutes: int = 60) -> List[RawNewsEvent]:
        """Fetch upcoming economic events"""
        # TODO: Integrate with real economic calendar API
        # For now, return mock data

        logger.info(f"Fetching economic calendar events (last {minutes} min)")

        # Mock events
        mock_events = [
            {
                'title': 'USD - Non-Farm Payrolls',
                'content': 'US employment data release',
                'symbols': ['EURUSD', 'USDJPY', 'GBPUSD'],
                'timestamp': datetime.now(timezone.utc)
            },
            {
                'title': 'EUR - ECB Interest Rate Decision',
                'content': 'European Central Bank policy decision',
                'symbols': ['EURUSD', 'GBPUSD'],
                'timestamp': datetime.now(timezone.utc)
            }
        ]

        events = []
        for event_data in mock_events:
            events.append(RawNewsEvent(
                source=self.source_name,
                source_type=self.source_type,
                timestamp=event_data['timestamp'],
                title=event_data['title'],
                content=event_data['content'],
                related_symbols=event_data['symbols']
            ))

        return events


class TwitterSource(NewsSource):
    """
    Twitter news source (fast public).
    Mock implementation - replace with Twitter API
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("Twitter", SourceType.TWITTER)
        self.api_key = api_key

    def fetch_latest(self, minutes: int = 60) -> List[RawNewsEvent]:
        """Fetch latest tweets"""
        # TODO: Integrate with Twitter API (tweepy)

        logger.info(f"Fetching Twitter news (last {minutes} min)")

        # Mock implementation
        return []


class ReutersSource(NewsSource):
    """
    Reuters news source (authoritative).
    Mock implementation - replace with Reuters API
    """

    def __init__(self, api_key: Optional[str] = None):
        super().__init__("Reuters", SourceType.REUTERS)
        self.api_key = api_key

    def fetch_latest(self, minutes: int = 60) -> List[RawNewsEvent]:
        """Fetch latest Reuters news"""
        # TODO: Integrate with Reuters API

        logger.info(f"Fetching Reuters news (last {minutes} min)")

        # Mock implementation
        return []


class NewsIngestionOrchestrator:
    """
    Orchestrates news ingestion from multiple sources.
    Handles:
    - Fetching from multiple sources
    - Source scoring
    - Deduplication
    - Timestamp normalization
    - Event type classification
    - Structuring events
    """

    def __init__(
        self,
        sources: Optional[List[NewsSource]] = None,
        cache_file: str = "data/news_cache.json"
    ):
        self.sources = sources or []
        self.cache_file = cache_file
        self.scoring_engine = SourceScoringEngine()
        self.processed_events = {}  # event_id -> StructuredNewsEvent
        self.event_cache = []  # For deduplication

        # Load cache
        self.load_cache()

        # Add default sources if none provided
        if not self.sources:
            self.add_default_sources()

    def add_default_sources(self):
        """Add default news sources"""
        logger.info("Adding default news sources")

        # Economic calendar (always useful)
        self.sources.append(EconomicCalendarSource())

        # TODO: Add more sources with API keys from config
        # self.sources.append(TwitterSource(api_key=config.get('twitter_api_key')))
        # self.sources.append(ReutersSource(api_key=config.get('reuters_api_key')))

    def add_source(self, source: NewsSource):
        """Add a news source"""
        self.sources.append(source)
        logger.info(f"Added news source: {source.source_name}")

    def fetch_news(self, minutes: int = 60) -> List[RawNewsEvent]:
        """
        Fetch news from all sources.

        Args:
            minutes: Fetch news from last N minutes

        Returns:
            List of raw news events
        """
        all_events = []

        for source in self.sources:
            try:
                events = source.fetch_latest(minutes=minutes)
                all_events.extend(events)
                logger.info(f"Fetched {len(events)} events from {source.source_name}")
            except Exception as e:
                logger.error(f"Error fetching from {source.source_name}: {e}")

        logger.info(f"Total raw events fetched: {len(all_events)}")
        return all_events

    def process_event(self, raw_event: RawNewsEvent) -> Optional[StructuredNewsEvent]:
        """
        Process a raw news event into structured format.

        Args:
            raw_event: Raw event from source

        Returns:
            StructuredNewsEvent or None if invalid
        """
        try:
            # Generate unique event ID
            event_id = self._generate_event_id(raw_event)

            # Check for duplicates
            if event_id in self.processed_events:
                logger.debug(f"Duplicate event: {event_id}")
                return None

            # Normalize timestamp to UTC
            timestamp_utc = raw_event.timestamp
            if timestamp_utc.tzinfo is None:
                timestamp_utc = timestamp_utc.replace(tzinfo=timezone.utc)

            # Score source
            source_score = self.scoring_engine.score_source(
                raw_event.source,
                raw_event.source_type
            )

            # Classify event type
            event_type = self._classify_event_type(raw_event)

            # Create structured event
            structured_event = StructuredNewsEvent(
                event_id=event_id,
                source=raw_event.source,
                source_type=raw_event.source_type,
                source_score=source_score,
                timestamp=timestamp_utc,
                event_type=event_type,
                title=raw_event.title,
                content=raw_event.content,
                related_symbols=raw_event.related_symbols,
                metadata=raw_event.metadata
            )

            # Store in processed events
            self.processed_events[event_id] = structured_event

            return structured_event

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None

    def _generate_event_id(self, event: RawNewsEvent) -> str:
        """Generate unique event ID"""
        # Hash of content + timestamp + source
        content = f"{event.title}|{event.content}|{event.timestamp.isoformat()}|{event.source}"
        return hashlib.md5(content.encode()).hexdigest()

    def _classify_event_type(self, event: RawNewsEvent) -> EventType:
        """
        Classify event type based on title/content.
        Simple keyword-based classification (can be enhanced with ML).
        """
        title_lower = event.title.lower()
        content_lower = event.content.lower()
        combined = f"{title_lower} {content_lower}"

        # Rate decisions
        if any(kw in combined for kw in ['interest rate', 'fed decision', 'rate decision', 'policy rate']):
            return EventType.RATE_DECISION

        # Earnings
        if any(kw in combined for kw in ['earnings', 'quarterly results', 'revenue', 'profit']):
            return EventType.EARNINGS

        # Economic data
        if any(kw in combined for kw in ['employment', 'nfp', 'gdp', 'inflation', 'cpi', 'ppi']):
            return EventType.ECONOMIC_DATA

        # Geopolitical
        if any(kw in combined for kw in ['war', 'conflict', 'sanctions', 'trade deal', 'tariff']):
            return EventType.GEOPOLITICAL

        # Regulatory
        if any(kw in combined for kw in ['regulation', 'sec', 'law', 'compliance', 'ban']):
            return EventType.REGULATORY

        # Default
        return EventType.UNKNOWN

    def get_latest_events(self, minutes: int = 60) -> List[StructuredNewsEvent]:
        """
        Get latest processed events.

        Args:
            minutes: Get events from last N minutes

        Returns:
            List of structured events
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

        return [
            event for event in self.processed_events.values()
            if event.timestamp >= cutoff_time
        ]

    def save_cache(self):
        """Save processed events to cache file"""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

            cache_data = {
                'events': [event.to_dict() for event in self.processed_events.values()],
                'last_updated': datetime.now(timezone.utc).isoformat()
            }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            logger.info(f"Saved {len(self.processed_events)} events to cache")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def load_cache(self):
        """Load processed events from cache file"""
        if not os.path.exists(self.cache_file):
            return

        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            # TODO: Reconstruct StructuredNewsEvent objects from cache
            logger.info(f"Loaded cache from {self.cache_file}")

        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def get_stats(self) -> Dict:
        """Get ingestion statistics"""
        return {
            'total_sources': len(self.sources),
            'total_events_processed': len(self.processed_events),
            'sources': [source.source_name for source in self.sources]
        }

    def print_stats(self):
        """Print ingestion statistics"""
        stats = self.get_stats()

        print("\n" + "="*60)
        print("📰 NEWS INGESTION STATISTICS")
        print("="*60)
        print(f"Sources: {stats['total_sources']}")
        print(f"Events Processed: {stats['total_events_processed']}")
        print(f"Active Sources: {', '.join(stats['sources'])}")
        print("="*60 + "\n")


# Import timedelta
from datetime import timedelta
