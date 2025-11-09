"""
ASTRA Memory Transcendence — BGE-M3 Semantic Embeddings

Phase 3: Replace hash-based compression with real semantic similarity.

BGE-M3 (BAAI General Embedding, Multilingual, Multifunctional, Multi-Granularity):
- 1024-dimensional embeddings
- Multi-modal: text, code, structured data
- Cross-lingual semantic understanding
- State-of-art retrieval performance

Architecture:
    Input (text/code/context) → BGE-M3 Model → 1024-dim vector → FAISS Index
    Query → Embedding → Similarity Search → Top-K Results (with temporal decay)

Temporal Decay Formula:
    importance = base_importance * (1 - age_decay_factor) + access_boost
    
    Where:
    - age_decay_factor = min(age_days / max_age_days, 0.9)  # Max 90% decay
    - access_boost = min(access_count * 0.05, 0.5)          # Max 50% boost
    - base_importance = cosine_similarity(query, embedding)
"""
from __future__ import annotations

import pickle
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


@dataclass
class EmbeddingMetadata:
    """
    Metadata for stored embeddings.

    Attributes:
        content: Original text/code content
        content_type: Type of content (text, code, trace, macro)
        created_at: Unix timestamp when embedding was created
        access_count: Number of times this embedding has been retrieved
        last_accessed: Unix timestamp of last access
        tags: Optional tags for filtering
        source: Source of content (file path, tool name, etc.)
    """

    content: str
    content_type: str
    created_at: float
    access_count: int = 0
    last_accessed: float = 0.0
    tags: list[str] = field(default_factory=list)
    source: str = ""

    def age_days(self) -> float:
        """Get age of embedding in days."""
        return (time.time() - self.created_at) / 86400.0

    def days_since_access(self) -> float:
        """Get days since last access."""
        if self.last_accessed == 0.0:
            return self.age_days()
        return (time.time() - self.last_accessed) / 86400.0


@dataclass
class SearchResult:
    """
    Result from semantic search.

    Attributes:
        content: Original content
        similarity: Base cosine similarity (0-1)
        importance: Adjusted importance with temporal decay
        metadata: Full metadata object
        embedding_id: Index of embedding in FAISS
    """

    content: str
    similarity: float
    importance: float
    metadata: EmbeddingMetadata
    embedding_id: int

    def __repr__(self) -> str:
        return (
            f"SearchResult(similarity={self.similarity:.3f}, "
            f"importance={self.importance:.3f}, "
            f"type={self.metadata.content_type}, "
            f"age={self.metadata.age_days():.1f}d)"
        )


class BGEEmbeddingEngine:
    """
    BGE-M3 semantic embedding engine with FAISS vector store.

    Features:
    - Multi-modal embeddings (text, code, context)
    - Fast similarity search (FAISS with HNSW index)
    - Temporal decay with access reinforcement
    - Persistent storage (embeddings + metadata)
    - Automatic cache warming
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        index_path: Path | None = None,
        dimension: int = 1024,
        max_age_days: float = 90.0,
    ):
        """
        Initialize BGE embedding engine.

        Args:
            model_name: HuggingFace model identifier (bge-m3 default)
            index_path: Path to store FAISS index and metadata
            dimension: Embedding dimension (1024 for bge-m3)
            max_age_days: Maximum age for decay calculation (default 90 days)
        """
        self.model_name = model_name
        self.dimension = dimension
        self.max_age_days = max_age_days

        # Set default index path
        if index_path is None:
            index_path = Path(__file__).parent / "embeddings_store"
        self.index_path = index_path
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Load or create model
        self.model = self._load_model()

        # Load or create FAISS index
        self.index = self._load_or_create_index()

        # Load or create metadata store
        self.metadata: list[EmbeddingMetadata] = self._load_metadata()

        # Performance tracking
        self.embedding_calls = 0
        self.search_calls = 0
        self.cache_hits = 0

    def _load_model(self) -> SentenceTransformer:
        """
        Load BGE-M3 model from HuggingFace.

        Returns:
            Loaded SentenceTransformer model
        """
        print(f"Loading BGE-M3 model: {self.model_name}...")
        model = SentenceTransformer(self.model_name)
        print(f"✓ Model loaded (dimension={self.dimension})")
        return model

    def _load_or_create_index(self) -> faiss.Index:
        """
        Load existing FAISS index or create new one.

        Uses HNSW (Hierarchical Navigable Small World) for fast approximate
        nearest neighbor search. Better than flat index for >10K embeddings.

        Returns:
            FAISS index (HNSW or Flat)
        """
        index_file = self.index_path / "faiss_index.bin"

        if index_file.exists():
            print(f"Loading existing FAISS index from {index_file}...")
            index = faiss.read_index(str(index_file))
            print(f"✓ Index loaded ({index.ntotal} embeddings)")
            return index

        # Create new HNSW index
        # M=32: number of connections per layer (higher = better recall, slower build)
        # efConstruction=40: search depth during construction (higher = better quality)
        print("Creating new FAISS HNSW index...")
        index = faiss.IndexHNSWFlat(self.dimension, 32)
        index.hnsw.efConstruction = 40
        print("✓ Index created")
        return index

    def _load_metadata(self) -> list[EmbeddingMetadata]:
        """
        Load embedding metadata from disk.

        Returns:
            List of metadata objects (ordered by FAISS index)
        """
        metadata_file = self.index_path / "metadata.pkl"

        if metadata_file.exists():
            with open(metadata_file, "rb") as f:
                metadata = pickle.load(f)
            print(f"✓ Loaded {len(metadata)} metadata entries")
            return metadata

        print("✓ Created empty metadata store")
        return []

    def save(self) -> None:
        """Save FAISS index and metadata to disk."""
        # Save FAISS index
        index_file = self.index_path / "faiss_index.bin"
        faiss.write_index(self.index, str(index_file))

        # Save metadata
        metadata_file = self.index_path / "metadata.pkl"
        with open(metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"✓ Saved index ({self.index.ntotal} embeddings) and metadata")

    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for text/code.

        Args:
            text: Input text or code

        Returns:
            1024-dimensional embedding vector
        """
        self.embedding_calls += 1

        # BGE-M3 expects list input
        embedding = self.model.encode([text], convert_to_numpy=True)[0]

        # Normalize for cosine similarity (FAISS inner product = cosine after normalization)
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    def add(
        self,
        content: str,
        content_type: str = "text",
        tags: list[str] | None = None,
        source: str = "",
    ) -> int:
        """
        Add content to embedding store.

        Args:
            content: Text or code to embed
            content_type: Type of content (text, code, trace, macro)
            tags: Optional tags for filtering
            source: Source identifier (file path, tool name)

        Returns:
            Embedding ID (index in FAISS)
        """
        # Generate embedding
        embedding = self.embed(content)

        # Add to FAISS index
        self.index.add(np.array([embedding], dtype=np.float32))

        # Store metadata
        metadata = EmbeddingMetadata(
            content=content,
            content_type=content_type,
            created_at=time.time(),
            access_count=0,
            last_accessed=0.0,
            tags=tags or [],
            source=source,
        )
        self.metadata.append(metadata)

        embedding_id = len(self.metadata) - 1
        return embedding_id

    def search(
        self,
        query: str,
        k: int = 10,
        content_type: str | None = None,
        tags: list[str] | None = None,
        min_similarity: float = 0.3,
    ) -> list[SearchResult]:
        """
        Semantic search with temporal decay and access reinforcement.

        Args:
            query: Search query (text or code)
            k: Number of results to return
            content_type: Filter by content type
            tags: Filter by tags (any match)
            min_similarity: Minimum similarity threshold

        Returns:
            List of search results ordered by importance (temporal-adjusted similarity)
        """
        self.search_calls += 1

        # Generate query embedding
        query_embedding = self.embed(query)

        # Search FAISS index (retrieve more than k for filtering)
        k_search = min(k * 5, self.index.ntotal)  # Get 5x results for filtering
        if k_search == 0:
            return []

        distances, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), k_search
        )

        # Convert to search results with temporal decay
        results: list[SearchResult] = []
        for distance, idx in zip(distances[0], indices[0], strict=True):
            if idx == -1:  # FAISS uses -1 for empty slots
                continue

            metadata = self.metadata[idx]

            # Apply filters
            if content_type and metadata.content_type != content_type:
                continue
            if tags and not any(tag in metadata.tags for tag in tags):
                continue

            # Calculate base similarity (FAISS inner product = cosine after normalization)
            similarity = float(distance)

            # Skip if below threshold
            if similarity < min_similarity:
                continue

            # Calculate temporal-adjusted importance
            importance = self._calculate_importance(similarity, metadata)

            results.append(
                SearchResult(
                    content=metadata.content,
                    similarity=similarity,
                    importance=importance,
                    metadata=metadata,
                    embedding_id=idx,
                )
            )

        # Sort by importance (not just similarity)
        results.sort(key=lambda r: r.importance, reverse=True)

        # Update access metadata for top results
        for result in results[:k]:
            self._record_access(result.embedding_id)

        return results[:k]

    def _calculate_importance(
        self, similarity: float, metadata: EmbeddingMetadata
    ) -> float:
        """
        Calculate temporal-adjusted importance.

        Formula:
            importance = similarity * (1 - age_decay) + access_boost

        Args:
            similarity: Base cosine similarity
            metadata: Embedding metadata

        Returns:
            Adjusted importance score
        """
        # Age decay (older embeddings decay, max 90% decay)
        age_days = metadata.age_days()
        age_decay = min(age_days / self.max_age_days, 0.9)

        # Access boost (frequently accessed embeddings get boost, max 50%)
        access_boost = min(metadata.access_count * 0.05, 0.5)

        # Combined importance
        importance = similarity * (1 - age_decay) + access_boost

        return importance

    def _record_access(self, embedding_id: int) -> None:
        """
        Record access to embedding (reinforcement learning).

        Args:
            embedding_id: Index of accessed embedding
        """
        metadata = self.metadata[embedding_id]
        metadata.access_count += 1
        metadata.last_accessed = time.time()

    def get_stats(self) -> dict[str, Any]:
        """
        Get embedding engine statistics.

        Returns:
            Dictionary with performance metrics
        """
        total_embeddings = self.index.ntotal
        content_type_counts = {}
        for metadata in self.metadata:
            content_type_counts[metadata.content_type] = (
                content_type_counts.get(metadata.content_type, 0) + 1
            )

        avg_age = (
            sum(m.age_days() for m in self.metadata) / len(self.metadata)
            if self.metadata
            else 0
        )
        avg_access = (
            sum(m.access_count for m in self.metadata) / len(self.metadata)
            if self.metadata
            else 0
        )

        return {
            "total_embeddings": total_embeddings,
            "content_type_distribution": content_type_counts,
            "avg_age_days": avg_age,
            "avg_access_count": avg_access,
            "embedding_calls": self.embedding_calls,
            "search_calls": self.search_calls,
            "cache_hits": self.cache_hits,
            "model": self.model_name,
            "dimension": self.dimension,
        }

    def compact(self, max_age_days: float = 180.0, min_access_count: int = 1) -> int:
        """
        Remove old, unused embeddings to reduce index size.

        Args:
            max_age_days: Remove embeddings older than this (if not accessed)
            min_access_count: Keep embeddings with at least this many accesses

        Returns:
            Number of embeddings removed
        """
        # Identify embeddings to keep
        keep_indices = []
        for idx, metadata in enumerate(self.metadata):
            if (
                metadata.age_days() < max_age_days
                or metadata.access_count >= min_access_count
            ):
                keep_indices.append(idx)

        removed_count = len(self.metadata) - len(keep_indices)

        if removed_count == 0:
            print("✓ No embeddings need compaction")
            return 0

        # Rebuild index with kept embeddings
        print(f"Compacting: removing {removed_count} old embeddings...")

        new_index = faiss.IndexHNSWFlat(self.dimension, 32)
        new_index.hnsw.efConstruction = 40
        new_metadata = []

        for idx in keep_indices:
            # Re-embed content (no way to extract from FAISS)
            embedding = self.embed(self.metadata[idx].content)
            new_index.add(np.array([embedding], dtype=np.float32))
            new_metadata.append(self.metadata[idx])

        self.index = new_index
        self.metadata = new_metadata

        print(f"✓ Compaction complete ({len(new_metadata)} embeddings remaining)")
        return removed_count


# Global embedding engine (singleton)
_embedding_engine: BGEEmbeddingEngine | None = None


def get_embedding_engine() -> BGEEmbeddingEngine:
    """Get global embedding engine (singleton with lazy loading)."""
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = BGEEmbeddingEngine()
    return _embedding_engine
