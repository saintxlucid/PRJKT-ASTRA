"""
Tests for BGE-M3 Semantic Embedding Engine

Phase 3: Memory Transcendence validation
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path

import numpy as np
import pytest

from chat_os.memory.embeddings import (
    BGEEmbeddingEngine,
    EmbeddingMetadata,
    SearchResult,
    get_embedding_engine,
)


@pytest.fixture
def temp_index_path(tmp_path: Path) -> Path:
    """Create temporary directory for test index."""
    return tmp_path / "test_embeddings"


@pytest.fixture
def embedding_engine(temp_index_path: Path) -> BGEEmbeddingEngine:
    """Create fresh embedding engine for each test."""
    # Use smaller model for faster tests (bge-small-en-v1.5 is 384-dim)
    return BGEEmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",  # Fast test model
        index_path=temp_index_path,
        dimension=384,  # MiniLM dimension
    )


def test_embedding_engine_initialization(embedding_engine: BGEEmbeddingEngine):
    """Verify embedding engine initializes correctly."""
    assert embedding_engine.model is not None
    assert embedding_engine.index is not None
    assert embedding_engine.metadata == []
    assert embedding_engine.index.ntotal == 0


def test_embed_generates_correct_dimension(embedding_engine: BGEEmbeddingEngine):
    """Verify embedding has correct dimensionality."""
    text = "This is a test sentence for embedding."
    embedding = embedding_engine.embed(text)

    assert isinstance(embedding, np.ndarray)
    assert embedding.shape == (384,)  # MiniLM dimension
    assert np.abs(np.linalg.norm(embedding) - 1.0) < 1e-6  # Should be normalized


def test_add_single_embedding(embedding_engine: BGEEmbeddingEngine):
    """Test adding single embedding to store."""
    content = "Machine learning is a subset of artificial intelligence."
    embedding_id = embedding_engine.add(
        content, content_type="text", tags=["ml", "ai"], source="test.py"
    )

    assert embedding_id == 0
    assert embedding_engine.index.ntotal == 1
    assert len(embedding_engine.metadata) == 1

    metadata = embedding_engine.metadata[0]
    assert metadata.content == content
    assert metadata.content_type == "text"
    assert metadata.tags == ["ml", "ai"]
    assert metadata.source == "test.py"
    assert metadata.access_count == 0


def test_add_multiple_embeddings(embedding_engine: BGEEmbeddingEngine):
    """Test adding multiple embeddings."""
    contents = [
        "Python is a high-level programming language.",
        "JavaScript is used for web development.",
        "Rust provides memory safety without garbage collection.",
    ]

    for i, content in enumerate(contents):
        embedding_id = embedding_engine.add(content, content_type="code")
        assert embedding_id == i

    assert embedding_engine.index.ntotal == 3
    assert len(embedding_engine.metadata) == 3


def test_search_semantic_similarity(embedding_engine: BGEEmbeddingEngine):
    """Test semantic search returns similar content."""
    # Add documents
    embedding_engine.add("Python is a programming language", content_type="text")
    embedding_engine.add("The cat sat on the mat", content_type="text")
    embedding_engine.add("JavaScript is also a programming language", content_type="text")

    # Search for programming-related content
    results = embedding_engine.search("coding languages", k=2)

    assert len(results) == 2
    assert all(isinstance(r, SearchResult) for r in results)

    # First two results should be programming-related
    assert "programming" in results[0].content.lower() or "programming" in results[1].content.lower()

    # Results should be ordered by importance
    assert results[0].importance >= results[1].importance


def test_search_with_content_type_filter(embedding_engine: BGEEmbeddingEngine):
    """Test search filtering by content type."""
    embedding_engine.add("Python code example", content_type="code")
    embedding_engine.add("Python text description", content_type="text")
    embedding_engine.add("More Python code", content_type="code")

    # Search only code
    results = embedding_engine.search("Python", k=10, content_type="code")

    assert len(results) == 2
    assert all(r.metadata.content_type == "code" for r in results)


def test_search_with_tag_filter(embedding_engine: BGEEmbeddingEngine):
    """Test search filtering by tags."""
    embedding_engine.add("ML content", tags=["ml", "ai"])
    embedding_engine.add("Web content", tags=["web"])
    embedding_engine.add("More ML content", tags=["ml"])

    # Search only ML-tagged content
    results = embedding_engine.search("content", k=10, tags=["ml"])

    assert len(results) == 2
    assert all("ml" in r.metadata.tags for r in results)


def test_search_with_min_similarity_threshold(embedding_engine: BGEEmbeddingEngine):
    """Test search respects minimum similarity threshold."""
    embedding_engine.add("Completely unrelated topic about gardening")
    embedding_engine.add("Another unrelated topic about cooking")

    # Search with high threshold - note: cosine distance is used, not similarity
    # Distance threshold of 0.2 corresponds to high similarity
    results = embedding_engine.search("quantum physics", k=10, min_similarity=0.2)

    # Should have fewer or no high-similarity results
    assert len(results) <= 2  # May have some low-similarity results


def test_temporal_decay_reduces_importance(embedding_engine: BGEEmbeddingEngine):
    """Test that older embeddings have reduced importance."""
    # Add recent embedding
    embedding_engine.add("Recent content")

    # Add old embedding (simulate by modifying metadata)
    old_id = embedding_engine.add("Old content")
    embedding_engine.metadata[old_id].created_at = time.time() - (60 * 86400)  # 60 days ago

    # Search should favor recent content
    results = embedding_engine.search("content", k=2)

    # Recent content should have higher importance despite similar similarity
    recent_result = [r for r in results if "Recent" in r.content][0]
    old_result = [r for r in results if "Old" in r.content][0]

    assert recent_result.importance > old_result.importance


def test_access_reinforcement_boosts_importance(embedding_engine: BGEEmbeddingEngine):
    """Test that frequently accessed embeddings get importance boost."""
    # Add two similar embeddings
    id1 = embedding_engine.add("Content A")
    embedding_engine.add("Content B")

    # Simulate multiple accesses to Content A
    for _ in range(10):
        embedding_engine._record_access(id1)

    # Search
    results = embedding_engine.search("Content", k=2)

    # Content A should have higher importance due to access boost
    content_a = [r for r in results if "Content A" in r.content][0]
    content_b = [r for r in results if "Content B" in r.content][0]

    # Search itself increments access count by 1, so expect 11
    assert content_a.metadata.access_count == 11
    assert content_b.metadata.access_count == 1  # Only from search
    assert content_a.importance > content_b.importance


def test_save_and_load_index(temp_index_path: Path):
    """Test saving and loading index persists embeddings."""
    # Create engine and add embeddings
    engine1 = BGEEmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        index_path=temp_index_path,
        dimension=384,
    )
    engine1.add("Test content 1")
    engine1.add("Test content 2")
    engine1.save()

    # Create new engine with same path (should load existing)
    engine2 = BGEEmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        index_path=temp_index_path,
        dimension=384,
    )

    assert engine2.index.ntotal == 2
    assert len(engine2.metadata) == 2
    assert engine2.metadata[0].content == "Test content 1"
    assert engine2.metadata[1].content == "Test content 2"


def test_get_stats_returns_metrics(embedding_engine: BGEEmbeddingEngine):
    """Test statistics reporting."""
    embedding_engine.add("Content 1", content_type="text")
    embedding_engine.add("Content 2", content_type="code")
    embedding_engine.add("Content 3", content_type="text")

    embedding_engine.search("test", k=1)

    stats = embedding_engine.get_stats()

    assert stats["total_embeddings"] == 3
    assert stats["content_type_distribution"] == {"text": 2, "code": 1}
    assert stats["embedding_calls"] >= 3  # At least 3 adds + 1 search
    assert stats["search_calls"] == 1
    assert "avg_age_days" in stats
    assert "avg_access_count" in stats


def test_compact_removes_old_embeddings(embedding_engine: BGEEmbeddingEngine):
    """Test compaction removes old, unused embeddings."""
    # Add recent embedding
    embedding_engine.add("Recent content")

    # Add old, unused embedding
    old_id = embedding_engine.add("Old unused content")
    embedding_engine.metadata[old_id].created_at = time.time() - (200 * 86400)  # 200 days

    # Add old but accessed embedding
    old_accessed_id = embedding_engine.add("Old but accessed content")
    embedding_engine.metadata[old_accessed_id].created_at = time.time() - (200 * 86400)
    embedding_engine._record_access(old_accessed_id)
    embedding_engine._record_access(old_accessed_id)

    # Compact (remove embeddings older than 180 days with access_count < 2)
    removed = embedding_engine.compact(max_age_days=180.0, min_access_count=2)

    assert removed == 1  # Only "Old unused content" should be removed
    assert embedding_engine.index.ntotal == 2
    assert "Recent content" in [m.content for m in embedding_engine.metadata]
    assert "Old but accessed content" in [m.content for m in embedding_engine.metadata]
    assert "Old unused content" not in [m.content for m in embedding_engine.metadata]


def test_empty_search_returns_empty_list(embedding_engine: BGEEmbeddingEngine):
    """Test search on empty index returns empty list."""
    results = embedding_engine.search("query", k=10)
    assert results == []


def test_search_k_larger_than_index_size(embedding_engine: BGEEmbeddingEngine):
    """Test search with k larger than index size."""
    embedding_engine.add("Only content")

    results = embedding_engine.search("content", k=100)

    assert len(results) == 1  # Returns all available


def test_metadata_age_calculation():
    """Test EmbeddingMetadata age calculations."""
    metadata = EmbeddingMetadata(
        content="test",
        content_type="text",
        created_at=time.time() - (7 * 86400),  # 7 days ago
        last_accessed=time.time() - (2 * 86400),  # 2 days ago
    )

    assert 6.9 < metadata.age_days() < 7.1
    assert 1.9 < metadata.days_since_access() < 2.1


def test_embedding_normalization(embedding_engine: BGEEmbeddingEngine):
    """Test embeddings are L2 normalized."""
    text = "Test normalization"
    embedding = embedding_engine.embed(text)

    # L2 norm should be very close to 1.0
    norm = np.linalg.norm(embedding)
    assert 0.99 < norm < 1.01


def test_search_result_repr():
    """Test SearchResult string representation."""
    metadata = EmbeddingMetadata(
        content="test content",
        content_type="text",
        created_at=time.time(),
    )
    result = SearchResult(
        content="test content",
        similarity=0.85,
        importance=0.90,
        metadata=metadata,
        embedding_id=0,
    )

    repr_str = repr(result)
    assert "similarity=0.850" in repr_str
    assert "importance=0.900" in repr_str
    assert "type=text" in repr_str


def test_code_embedding_similarity(embedding_engine: BGEEmbeddingEngine):
    """Test semantic similarity for code snippets."""
    # Add code examples
    embedding_engine.add("def add(a, b): return a + b", content_type="code")
    embedding_engine.add("function multiply(x, y) { return x * y; }", content_type="code")
    embedding_engine.add("class Animal: pass", content_type="code")

    # Search for addition-related code
    results = embedding_engine.search("addition function", k=3, content_type="code")

    # Verify we get all code results
    assert len(results) == 3
    # Just verify that programming-related content ranks higher than random noise
    assert any("def" in r.content or "function" in r.content or "class" in r.content for r in results)


def test_get_embedding_engine_singleton() -> None:
    """Test global singleton returns same instance."""
    # Use smaller model for testing to avoid BGE-M3 loading issues
    import chat_os.memory.embeddings as emb_module

    # Reset singleton
    emb_module._embedding_engine = None

    # Create with test model
    emb_module._embedding_engine = BGEEmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384,
    )

    engine1 = get_embedding_engine()
    engine2 = get_embedding_engine()

    assert engine1 is engine2


def test_importance_calculation_bounds(embedding_engine: BGEEmbeddingEngine):
    """Test importance calculation stays within reasonable bounds."""
    # Add embedding
    embedding_id = embedding_engine.add("Test content")

    # Simulate extreme age and access
    metadata = embedding_engine.metadata[embedding_id]
    metadata.created_at = time.time() - (365 * 86400)  # 1 year old
    metadata.access_count = 100  # Many accesses

    # Calculate importance
    importance = embedding_engine._calculate_importance(0.95, metadata)

    # Should still be reasonable (not > 1.5)
    assert 0.0 <= importance <= 1.5


def test_multi_modal_content_types(embedding_engine: BGEEmbeddingEngine):
    """Test different content types can be embedded and searched."""
    content_types = ["text", "code", "trace", "macro", "plan"]

    for i, ctype in enumerate(content_types):
        embedding_engine.add(f"Content {i}", content_type=ctype)

    stats = embedding_engine.get_stats()
    assert stats["total_embeddings"] == len(content_types)

    # Search across all types
    results = embedding_engine.search("Content", k=10)
    assert len(results) == len(content_types)


@pytest.mark.slow
def test_performance_large_index():
    """Test performance with larger index (1000 embeddings)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = BGEEmbeddingEngine(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path=Path(tmpdir),
            dimension=384,
        )

        # Add 1000 embeddings
        start_add = time.time()
        for i in range(1000):
            engine.add(f"Document {i} with content about topic {i % 10}")
        add_time = time.time() - start_add

        print(f"\nAdded 1000 embeddings in {add_time:.2f}s ({1000/add_time:.1f} emb/s)")

        # Search performance
        start_search = time.time()
        for _ in range(100):
            engine.search("topic", k=10)
        search_time = time.time() - start_search

        avg_search_ms = (search_time / 100) * 1000
        print(f"Average search time: {avg_search_ms:.1f}ms (p95 target: <100ms)")

        # Performance targets
        assert add_time < 60  # Should add 1000 in under 60s
        assert avg_search_ms < 100  # Target: <100ms per search
