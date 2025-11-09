from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from chat_os.memory.embeddings import get_embedding_engine


def _embed(text: str) -> bytes:
    """Legacy hash-based embedding for backward compatibility."""
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


def _bucket_key(vector: bytes, prefix: int = 2) -> str:
    """Legacy bucketing for backward compatibility."""
    return vector[:prefix].hex()


@dataclass
class Event:
    kind: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Concept:
    key: str
    summary: str
    members: list[int] = field(default_factory=list)


class SemanticCompressor:
    """
    Semantic event compression using BGE-M3 embeddings.
    
    Replaces hash-based bucketing with true semantic similarity.
    Events are clustered by semantic meaning, with temporal decay
    and access reinforcement for intelligent concept formation.
    
    Backward compatible: Can still use legacy hash-based mode.
    """

    def __init__(self, use_embeddings: bool = True, similarity_threshold: float = 0.85) -> None:
        """
        Initialize semantic compressor.
        
        Args:
            use_embeddings: If True, use BGE-M3 embeddings. If False, use legacy hashing.
            similarity_threshold: Minimum similarity (0-1) to merge events into same concept.
        """
        self._concepts: dict[str, Concept] = {}
        self._events: list[Event] = []
        self._use_embeddings = use_embeddings
        self._similarity_threshold = similarity_threshold
        
        if use_embeddings:
            self._embedding_engine = get_embedding_engine()

    def ingest(self, event: Event) -> None:
        """
        Ingest an event and cluster it with semantically similar concepts.
        
        Args:
            event: Event to ingest (kind, text, meta)
        """
        index = len(self._events)
        self._events.append(event)
        
        if self._use_embeddings:
            self._ingest_with_embeddings(event, index)
        else:
            self._ingest_legacy(event, index)
    
    def _ingest_with_embeddings(self, event: Event, index: int) -> None:
        """Ingest using BGE-M3 semantic similarity."""
        # Search for similar existing concepts
        similar = self._embedding_engine.search(
            query=event.text,
            k=1,
            content_type="event",
            min_similarity=self._similarity_threshold
        )
        
        if similar:
            # Merge with existing concept
            bucket = similar[0].metadata.tags[0] if similar[0].metadata.tags else f"concept_{index}"
            concept = self._concepts.get(bucket)
            if concept:
                concept.members.append(index)
                # Update summary if new event is longer/better
                if len(event.text) > len(concept.summary):
                    concept.summary = event.text[:160]
                return
        
        # Create new concept
        bucket = f"concept_{index}"
        self._concepts[bucket] = Concept(key=bucket, summary=event.text[:160], members=[index])
        
        # Store in embedding engine with concept tag
        self._embedding_engine.add(
            content=event.text,
            content_type="event",
            tags=[bucket, event.kind],
            source="semantic_compressor"
        )
    
    def _ingest_legacy(self, event: Event, index: int) -> None:
        """Legacy hash-based ingestion for backward compatibility."""
        vector = _embed(event.text)
        bucket = _bucket_key(vector)
        concept = self._concepts.get(bucket)
        if concept is None:
            self._concepts[bucket] = Concept(key=bucket, summary=event.text[:160], members=[index])
            return
        concept.members.append(index)
        if len(event.text) > len(concept.summary):
            concept.summary = event.text[:160]

    def compress(self) -> dict[str, Any]:
        """
        Compress to summary dict with concept statistics.

        Returns:
            Dict with concepts (key -> summary/members) and event count.
        """
        return {
            "concepts": {
                key: {"summary": concept.summary, "members": concept.members}
                for key, concept in self._concepts.items()
            },
            "count_events": len(self._events),
            "compression_mode": "embeddings" if self._use_embeddings else "legacy",
        }

    def rehydrate(self, key: str) -> list[Event]:
        """
        Retrieve all events for a concept key.

        Args:
            key: Concept key to rehydrate

        Returns:
            List of events belonging to that concept
        """
        concept = self._concepts.get(key)
        if concept is None:
            return []
        return [self._events[i] for i in concept.members]

    def search_similar_events(self, query: str, k: int = 5) -> list[Event]:
        """
        Search for semantically similar events using BGE-M3.

        Args:
            query: Search query text
            k: Number of similar events to return

        Returns:
            List of similar events, ordered by relevance
        """
        if not self._use_embeddings:
            # Legacy mode: return empty (no semantic search capability)
            return []

        # Search embeddings
        results = self._embedding_engine.search(
            query=query,
            k=k,
            content_type="event",
        )

        # Map back to events
        events = []
        for result in results:
            # Extract concept key from tags
            if result.metadata.tags:
                concept_key = result.metadata.tags[0]
                concept = self._concepts.get(concept_key)
                if concept and concept.members:
                    # Return first event from this concept (could enhance to return all)
                    events.append(self._events[concept.members[0]])

        return events

    def get_concept_summary(self, query: str) -> str | None:
        """
        Get summary of concept most similar to query.

        Args:
            query: Query text

        Returns:
            Summary of most similar concept, or None if not found
        """
        if not self._use_embeddings:
            return None

        results = self._embedding_engine.search(
            query=query,
            k=1,
            content_type="event",
        )

        if results and results[0].metadata.tags:
            concept_key = results[0].metadata.tags[0]
            concept = self._concepts.get(concept_key)
            return concept.summary if concept else None

        return None

    def get_stats(self) -> dict[str, Any]:
        """
        Get compression statistics.

        Returns:
            Dict with event count, concept count, compression ratio, etc.
        """
        total_events = len(self._events)
        total_concepts = len(self._concepts)
        compression_ratio = total_events / max(total_concepts, 1)

        stats = {
            "total_events": total_events,
            "total_concepts": total_concepts,
            "compression_ratio": compression_ratio,
            "mode": "embeddings" if self._use_embeddings else "legacy",
        }

        if self._use_embeddings:
            # Include embedding engine stats
            stats["embedding_stats"] = self._embedding_engine.get_stats()

        return stats

