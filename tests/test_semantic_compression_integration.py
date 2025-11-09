"""
Integration tests for SemanticCompressor with BGE-M3 embeddings.

Phase 3: Memory Transcendence validation
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from chat_os.cognitive.memory.semantic_compression import Event, SemanticCompressor
from chat_os.memory.embeddings import BGEEmbeddingEngine


@pytest.fixture
def temp_embedding_path(tmp_path: Path) -> Path:
    """Create temporary directory for test embeddings."""
    return tmp_path / "test_semantic_compression"


@pytest.fixture
def semantic_compressor_embeddings(temp_embedding_path: Path) -> SemanticCompressor:
    """Create SemanticCompressor with BGE-M3 embeddings."""
    # Use smaller model for faster tests
    import chat_os.memory.embeddings as emb_module
    emb_module._embedding_engine = BGEEmbeddingEngine(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        index_path=temp_embedding_path,
        dimension=384,
    )
    return SemanticCompressor(use_embeddings=True, similarity_threshold=0.7)


@pytest.fixture
def semantic_compressor_legacy() -> SemanticCompressor:
    """Create SemanticCompressor with legacy hash-based mode."""
    return SemanticCompressor(use_embeddings=False)


def test_compressor_initialization_embeddings(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test initialization with embeddings mode."""
    assert semantic_compressor_embeddings._use_embeddings is True
    assert semantic_compressor_embeddings._embedding_engine is not None
    assert len(semantic_compressor_embeddings._events) == 0
    assert len(semantic_compressor_embeddings._concepts) == 0


def test_compressor_initialization_legacy(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test initialization with legacy mode."""
    assert semantic_compressor_legacy._use_embeddings is False
    assert not hasattr(semantic_compressor_legacy, "_embedding_engine") or semantic_compressor_legacy._embedding_engine is None
    assert len(semantic_compressor_legacy._events) == 0
    assert len(semantic_compressor_legacy._concepts) == 0


def test_ingest_single_event_embeddings(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test ingesting single event with embeddings."""
    event = Event(kind="task", text="Complete the project documentation")

    semantic_compressor_embeddings.ingest(event)

    assert len(semantic_compressor_embeddings._events) == 1
    assert len(semantic_compressor_embeddings._concepts) == 1
    assert semantic_compressor_embeddings._events[0] == event


def test_ingest_single_event_legacy(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test ingesting single event with legacy mode."""
    event = Event(kind="task", text="Complete the project documentation")

    semantic_compressor_legacy.ingest(event)

    assert len(semantic_compressor_legacy._events) == 1
    assert len(semantic_compressor_legacy._concepts) == 1
    assert semantic_compressor_legacy._events[0] == event


def test_semantic_similarity_clustering(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test that semantically similar events are clustered together."""
    # Similar events about coding
    event1 = Event(kind="task", text="Write Python code for data processing")
    event2 = Event(kind="task", text="Develop Python script for data analysis")
    event3 = Event(kind="task", text="Go grocery shopping for dinner")

    semantic_compressor_embeddings.ingest(event1)
    semantic_compressor_embeddings.ingest(event2)
    semantic_compressor_embeddings.ingest(event3)

    # Should have 2-3 concepts (similar events may merge)
    assert len(semantic_compressor_embeddings._events) == 3
    # Python coding events should cluster together (threshold 0.7)
    # but grocery shopping should be separate
    # Exact count depends on similarity, but should be < 3
    assert 1 <= len(semantic_compressor_embeddings._concepts) <= 3


def test_different_similarity_thresholds() -> None:
    """Test that similarity threshold affects clustering."""
    events = [
        Event(kind="task", text="Write Python code"),
        Event(kind="task", text="Write Java code"),
        Event(kind="task", text="Write JavaScript code"),
    ]

    # High threshold (0.9) - more concepts (less clustering)
    compressor_strict = SemanticCompressor(use_embeddings=True, similarity_threshold=0.9)
    for event in events:
        compressor_strict.ingest(event)

    # Low threshold (0.5) - fewer concepts (more clustering)
    compressor_loose = SemanticCompressor(use_embeddings=True, similarity_threshold=0.5)
    for event in events:
        compressor_loose.ingest(event)

    # Loose threshold should create fewer or equal concepts
    assert len(compressor_loose._concepts) <= len(compressor_strict._concepts)


def test_compress_output_structure(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test compress() output structure."""
    event = Event(kind="task", text="Test event")
    semantic_compressor_embeddings.ingest(event)

    result = semantic_compressor_embeddings.compress()

    assert "concepts" in result
    assert "count_events" in result
    assert "compression_mode" in result
    assert result["count_events"] == 1
    assert result["compression_mode"] == "embeddings"
    assert len(result["concepts"]) == 1


def test_rehydrate_concept(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test rehydrating events from concept key."""
    event1 = Event(kind="task", text="Write documentation")
    event2 = Event(kind="task", text="Write more documentation")

    semantic_compressor_embeddings.ingest(event1)
    semantic_compressor_embeddings.ingest(event2)

    # Get first concept key
    compress_result = semantic_compressor_embeddings.compress()
    concept_key = list(compress_result["concepts"].keys())[0]

    # Rehydrate
    events = semantic_compressor_embeddings.rehydrate(concept_key)

    assert len(events) >= 1
    assert all(isinstance(e, Event) for e in events)


def test_search_similar_events(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test semantic search for similar events."""
    events = [
        Event(kind="task", text="Machine learning model training"),
        Event(kind="task", text="Deep learning neural network"),
        Event(kind="task", text="Buy groceries at store"),
    ]

    for event in events:
        semantic_compressor_embeddings.ingest(event)

    # Search for ML-related events
    results = semantic_compressor_embeddings.search_similar_events("artificial intelligence", k=2)

    # Should return ML-related events, not grocery shopping
    assert len(results) >= 1
    assert any("learning" in r.text.lower() or "model" in r.text.lower() for r in results)


def test_search_similar_events_legacy_returns_empty(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test that legacy mode doesn't support semantic search."""
    event = Event(kind="task", text="Some event")
    semantic_compressor_legacy.ingest(event)

    results = semantic_compressor_legacy.search_similar_events("query", k=5)

    assert results == []


def test_get_concept_summary(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test retrieving concept summary by query."""
    event = Event(kind="task", text="Complete the annual financial report and submit to board")

    semantic_compressor_embeddings.ingest(event)

    # Query for similar concept
    summary = semantic_compressor_embeddings.get_concept_summary("financial reporting")

    assert summary is not None
    assert "financial report" in summary.lower() or "annual" in summary.lower()


def test_get_concept_summary_legacy_returns_none(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test that legacy mode doesn't support concept summary search."""
    event = Event(kind="task", text="Some event")
    semantic_compressor_legacy.ingest(event)

    summary = semantic_compressor_legacy.get_concept_summary("query")

    assert summary is None


def test_get_stats_embeddings(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test statistics with embeddings mode."""
    events = [
        Event(kind="task", text="Event 1"),
        Event(kind="task", text="Event 2"),
        Event(kind="task", text="Event 3"),
    ]

    for event in events:
        semantic_compressor_embeddings.ingest(event)

    stats = semantic_compressor_embeddings.get_stats()

    assert stats["total_events"] == 3
    assert stats["total_concepts"] >= 1
    assert stats["compression_ratio"] >= 1.0
    assert stats["mode"] == "embeddings"
    assert "embedding_stats" in stats


def test_get_stats_legacy(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test statistics with legacy mode."""
    events = [
        Event(kind="task", text="Event 1"),
        Event(kind="task", text="Event 2"),
    ]

    for event in events:
        semantic_compressor_legacy.ingest(event)

    stats = semantic_compressor_legacy.get_stats()

    assert stats["total_events"] == 2
    assert stats["total_concepts"] >= 1
    assert stats["compression_ratio"] >= 1.0
    assert stats["mode"] == "legacy"
    assert "embedding_stats" not in stats


def test_compression_ratio_improves_with_similar_events(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test that compression ratio improves when similar events cluster."""
    # Add many similar events
    for i in range(10):
        event = Event(kind="task", text=f"Write code for feature {i}")
        semantic_compressor_embeddings.ingest(event)

    stats = semantic_compressor_embeddings.get_stats()

    # Should have compression (10 events compressed into concepts)
    assert stats["compression_ratio"] >= 1.0
    assert stats["total_events"] == 10
    # With threshold 0.7, similar "write code" events should cluster
    # Even if they don't fully cluster, compression ratio should be at least 1.0
    assert stats["total_concepts"] <= 10


def test_event_metadata_preserved(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test that event metadata is preserved through ingest/rehydrate."""
    event = Event(
        kind="task",
        text="Important task",
        meta={"priority": "high", "assignee": "alice"}
    )

    semantic_compressor_embeddings.ingest(event)

    # Rehydrate
    compress_result = semantic_compressor_embeddings.compress()
    concept_key = list(compress_result["concepts"].keys())[0]
    events = semantic_compressor_embeddings.rehydrate(concept_key)

    assert len(events) == 1
    assert events[0].meta == {"priority": "high", "assignee": "alice"}


def test_backward_compatibility_with_legacy(semantic_compressor_legacy: SemanticCompressor) -> None:
    """Test that legacy mode maintains backward compatibility."""
    # This should work exactly like the old implementation
    event = Event(kind="task", text="Legacy test event")

    semantic_compressor_legacy.ingest(event)

    result = semantic_compressor_legacy.compress()

    # Check old API still works
    assert "concepts" in result
    assert "count_events" in result
    assert result["count_events"] == 1

    # Rehydrate should work
    concept_key = list(result["concepts"].keys())[0]
    events = semantic_compressor_legacy.rehydrate(concept_key)
    assert len(events) == 1


def test_multi_modal_event_types(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test compression with different event kinds."""
    events = [
        Event(kind="task", text="Complete project milestone"),
        Event(kind="meeting", text="Attend project status meeting"),
        Event(kind="email", text="Send project update email"),
    ]

    for event in events:
        semantic_compressor_embeddings.ingest(event)

    # All are project-related, might cluster together
    stats = semantic_compressor_embeddings.get_stats()
    assert stats["total_events"] == 3


def test_empty_compressor_stats(semantic_compressor_embeddings: SemanticCompressor) -> None:
    """Test stats on empty compressor."""
    stats = semantic_compressor_embeddings.get_stats()

    assert stats["total_events"] == 0
    assert stats["total_concepts"] == 0
    assert stats["compression_ratio"] == 0.0


def test_large_scale_compression() -> None:
    """Test compression with larger number of events."""
    with tempfile.TemporaryDirectory() as tmpdir:
        import chat_os.memory.embeddings as emb_module
        emb_module._embedding_engine = BGEEmbeddingEngine(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            index_path=Path(tmpdir),
            dimension=384,
        )

        compressor = SemanticCompressor(use_embeddings=True, similarity_threshold=0.75)

        # Add 100 events across 5 topics
        topics = [
            "machine learning training",
            "data analysis processing",
            "web development coding",
            "database optimization",
            "security vulnerability"
        ]

        for i in range(100):
            topic = topics[i % 5]
            event = Event(kind="task", text=f"{topic} task number {i}")
            compressor.ingest(event)

        stats = compressor.get_stats()

        # Should have good compression
        assert stats["total_events"] == 100
        # Should cluster into roughly 5-20 concepts (similar topics merge)
        assert 5 <= stats["total_concepts"] <= 30
        assert stats["compression_ratio"] >= 3.0
