# rag/rag_retriever.py - RAG Intelligence Layer with Vector Database
import logging
from typing import List, Dict
from datetime import datetime, timezone
import numpy as np

from rag.data_schemas import StructuredNewsEvent

logger = logging.getLogger(__name__)


class RAGRetriever:
    """
    RAG (Retrieval-Augmented Generation) Intelligence Layer.

    Uses vector database (Qdrant) to:
    - Store news events as embeddings
    - Retrieve semantically similar events
    - Apply time-weighted relevance
    - Prevent hallucination through source attribution
    """

    def __init__(
        self,
        collection_name: str = "news_events",
        embedding_model: str = "bge-small-en-v1.5"
    ):
        self.collection_name = collection_name
        self.embedding_model_name = embedding_model

        # Try to import qdrant and fastembed
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            from fastembed import TextEmbedding

            self.qdrant_client = QdrantClient(path="data/qdrant_data")
            self.embedding_model = TextEmbedding(model_name=embedding_model)

            # Create collection if doesn't exist
            self._init_collection()

            self.qdrant_available = True
            logger.info(f"RAG initialized with Qdrant + {embedding_model}")

        except ImportError:
            logger.warning("Qdrant/fastembed not installed - RAG running in mock mode")
            logger.warning("Install: pip install qdrant-client fastembed")
            self.qdrant_available = False
            self.mock_storage = []  # Fallback storage

    def _init_collection(self):
        """Initialize Qdrant collection"""
        if not self.qdrant_available:
            return

        try:
            from qdrant_client.models import Distance, VectorParams

            # Check if collection exists
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                # Create collection with vector size matching bge-small-en-v1.5 (384 dims)
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")

        except Exception as e:
            logger.error(f"Error initializing Qdrant collection: {e}")

    def store_event(self, event: StructuredNewsEvent) -> bool:
        """
        Store news event in vector database.

        Args:
            event: Structured news event

        Returns:
            True if stored successfully
        """
        try:
            # Generate embedding
            text = f"{event.title} {event.content}"
            embedding = self._generate_embedding(text)

            if self.qdrant_available:
                from qdrant_client.models import PointStruct

                # Store in Qdrant
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=[
                        PointStruct(
                            id=hash(event.event_id) % (2**63),  # Convert to int
                            vector=embedding,
                            payload={
                                'event_id': event.event_id,
                                'source': event.source,
                                'timestamp': event.timestamp.isoformat(),
                                'event_type': event.event_type.value,
                                'title': event.title,
                                'content': event.content,
                                'related_symbols': event.related_symbols,
                                'source_score': event.source_score.composite_score
                            }
                        )
                    ]
                )
                logger.debug(f"Stored event {event.event_id} in Qdrant")
            else:
                # Mock storage
                self.mock_storage.append({
                    'event_id': event.event_id,
                    'embedding': embedding,
                    'event': event
                })

            return True

        except Exception as e:
            logger.error(f"Error storing event: {e}")
            return False

    def retrieve_similar(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.5,
        time_decay_hours: float = 24.0
    ) -> List[Dict]:
        """
        Retrieve semantically similar events.

        Args:
            query: Query text (e.g., "interest rate decision")
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            time_decay_hours: Time decay factor (recent events weighted higher)

        Returns:
            List of dicts with event data and scores
        """
        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            if self.qdrant_available:
                # Search in Qdrant
                results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_embedding,
                    limit=top_k * 2  # Get more, filter after time weighting
                )

                # Apply time weighting and filter
                weighted_results = []
                now = datetime.now(timezone.utc)

                for result in results:
                    # Get time decay factor
                    event_time = datetime.fromisoformat(result.payload['timestamp'])
                    hours_elapsed = (now - event_time).total_seconds() / 3600
                    time_decay = np.exp(-hours_elapsed / time_decay_hours)

                    # Weighted score = similarity * time_decay
                    weighted_score = result.score * time_decay

                    if weighted_score >= min_score:
                        weighted_results.append({
                            'event_id': result.payload['event_id'],
                            'title': result.payload['title'],
                            'content': result.payload['content'],
                            'timestamp': result.payload['timestamp'],
                            'event_type': result.payload['event_type'],
                            'similarity_score': result.score,
                            'time_decay': time_decay,
                            'weighted_score': weighted_score,
                            'source': result.payload['source'],
                            'source_score': result.payload['source_score']
                        })

                # Sort by weighted score
                weighted_results.sort(key=lambda x: x['weighted_score'], reverse=True)
                return weighted_results[:top_k]

            else:
                # Mock retrieval (simple cosine similarity)
                similarities = []
                for stored in self.mock_storage:
                    sim = self._cosine_similarity(query_embedding, stored['embedding'])
                    similarities.append({
                        'event': stored['event'],
                        'similarity': sim
                    })

                similarities.sort(key=lambda x: x['similarity'], reverse=True)
                return [
                    {
                        'event_id': s['event'].event_id,
                        'title': s['event'].title,
                        'similarity_score': s['similarity'],
                        'weighted_score': s['similarity']
                    }
                    for s in similarities[:top_k]
                    if s['similarity'] >= min_score
                ]

        except Exception as e:
            logger.error(f"Error retrieving similar events: {e}")
            return []

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.qdrant_available:
            # Use fastembed
            embeddings = list(self.embedding_model.embed([text]))
            return embeddings[0].tolist()
        else:
            # Mock embedding (random vector)
            np.random.seed(hash(text) % 2**32)
            return np.random.randn(384).tolist()

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    def get_stats(self) -> Dict:
        """Get RAG statistics"""
        if self.qdrant_available:
            try:
                collection_info = self.qdrant_client.get_collection(self.collection_name)
                return {
                    'total_events': collection_info.points_count,
                    'qdrant_available': True,
                    'embedding_model': self.embedding_model_name
                }
            except:
                return {'total_events': 0, 'qdrant_available': True}
        else:
            return {
                'total_events': len(self.mock_storage),
                'qdrant_available': False,
                'embedding_model': 'mock'
            }
