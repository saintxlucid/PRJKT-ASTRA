"""
Tests for ASTRA Persistent Memory System: graph, embeddings, recall, and summarization.

Test coverage includes:
- Memory graph node/edge management and graph traversal
- Embedding store add/search with similarity scoring
- Recall engine with BM25, semantic, and graph expansion
- Text summarization with compression and caching
- Integration tests for full memory workflow
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.astra.observability.metrics import MetricsCollector
from src.astra.observability.structured_logger import StructuredLogger
from src.astra.phase3.memory.embedding_store import EmbeddingRecord, EmbeddingStore
from src.astra.phase3.memory.memory_graph import (
    MemoryGraph,
    MemoryType,
    RelationType,
)
from src.astra.phase3.memory.recall_engine import RecallEngine
from src.astra.phase3.memory.summarizer import TextSummarizer


@pytest.fixture
def mock_logger():
    """Mock structured logger."""
    logger = MagicMock(spec=StructuredLogger)
    logger.log_event = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Mock metrics collector."""
    metrics = MagicMock(spec=MetricsCollector)
    metrics.record_latency = MagicMock()
    return metrics


@pytest.fixture
def memory_graph(mock_logger, mock_metrics):
    """Create memory graph for testing."""
    return MemoryGraph(
        persistence_path="/tmp/test_memory_graph.json",
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.fixture
def embedding_store(mock_logger, mock_metrics):
    """Create embedding store for testing."""
    return EmbeddingStore(
        embedding_dim=384,
        persistence_path="/tmp/test_embeddings.json",
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.fixture
def recall_engine(memory_graph, embedding_store, mock_logger, mock_metrics):
    """Create recall engine for testing."""
    return RecallEngine(
        memory_graph=memory_graph,
        embedding_store=embedding_store,
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.fixture
def summarizer(mock_logger, mock_metrics):
    """Create text summarizer for testing."""
    return TextSummarizer(
        target_compression=0.3,
        logger=mock_logger,
        metrics=mock_metrics,
    )


class TestMemoryGraph:
    """Tests for MemoryGraph."""

    @pytest.mark.asyncio
    async def test_add_node_creates_node(self, memory_graph):
        """Test adding a node."""
        node_id = await memory_graph.add_node(
            content="Paris is the capital of France",
            node_type=MemoryType.FACT,
        )

        assert node_id
        assert node_id in memory_graph.nodes
        assert memory_graph.nodes[node_id].content == "Paris is the capital of France"

    @pytest.mark.asyncio
    async def test_get_node_retrieves_node(self, memory_graph):
        """Test retrieving a node."""
        node_id = await memory_graph.add_node(
            content="Test fact",
            node_type=MemoryType.FACT,
        )

        node = await memory_graph.get_node(node_id)
        assert node is not None
        assert node.content == "Test fact"

    @pytest.mark.asyncio
    async def test_add_edge_creates_relationship(self, memory_graph):
        """Test adding an edge."""
        node1_id = await memory_graph.add_node(
            content="Paris",
            node_type=MemoryType.CONCEPT,
        )
        node2_id = await memory_graph.add_node(
            content="France",
            node_type=MemoryType.CONCEPT,
        )

        edge_id = await memory_graph.add_edge(
            source_id=node1_id,
            target_id=node2_id,
            relation_type=RelationType.PART_OF,
        )

        assert edge_id
        assert edge_id in memory_graph.edges

    @pytest.mark.asyncio
    async def test_get_neighbors_traverses_graph(self, memory_graph):
        """Test graph traversal."""
        node1_id = await memory_graph.add_node(
            content="Node1",
            node_type=MemoryType.CONCEPT,
        )
        node2_id = await memory_graph.add_node(
            content="Node2",
            node_type=MemoryType.CONCEPT,
        )

        await memory_graph.add_edge(
            source_id=node1_id,
            target_id=node2_id,
            relation_type=RelationType.RELATED_TO,
        )

        neighbors = await memory_graph.get_neighbors(node1_id)
        assert len(neighbors) == 1
        assert neighbors[0][0].id == node2_id

    @pytest.mark.asyncio
    async def test_update_node_relevance(self, memory_graph):
        """Test updating node relevance."""
        node_id = await memory_graph.add_node(
            content="Test",
            node_type=MemoryType.FACT,
        )

        original_score = memory_graph.nodes[node_id].relevance_score
        await memory_graph.update_node_relevance(node_id, 0.2)
        updated_score = memory_graph.nodes[node_id].relevance_score

        assert updated_score == original_score + 0.2

    @pytest.mark.asyncio
    async def test_node_expiration(self, memory_graph):
        """Test node TTL expiration."""
        node_id = await memory_graph.add_node(
            content="Temporary fact",
            node_type=MemoryType.FACT,
            ttl_seconds=1,
        )

        node = memory_graph.nodes[node_id]
        assert not node.is_expired()

        # Simulate passage of time
        node.created_at = time.time() - 2
        assert node.is_expired()

    @pytest.mark.asyncio
    async def test_cleanup_expired_nodes(self, memory_graph):
        """Test cleanup of expired nodes."""
        node1_id = await memory_graph.add_node(
            content="Permanent",
            node_type=MemoryType.FACT,
        )
        node2_id = await memory_graph.add_node(
            content="Temporary",
            node_type=MemoryType.FACT,
            ttl_seconds=1,
        )

        # Expire second node
        memory_graph.nodes[node2_id].created_at = time.time() - 2

        removed = await memory_graph.cleanup_expired()
        assert removed == 1
        assert node1_id in memory_graph.nodes
        assert node2_id not in memory_graph.nodes


class TestEmbeddingStore:
    """Tests for EmbeddingStore."""

    @pytest.mark.asyncio
    async def test_add_embedding_stores_vector(self, embedding_store):
        """Test adding embedding."""
        embedding = [0.1, 0.2, 0.3] + [0.0] * 381

        result = await embedding_store.add_embedding(
            vector_id="vec1",
            embedding=embedding,
            metadata={"type": "test"},
        )

        assert result is True
        assert "vec1" in embedding_store.vectors

    @pytest.mark.asyncio
    async def test_search_finds_similar_vectors(self, embedding_store):
        """Test vector similarity search."""
        vec1 = [0.1, 0.2, 0.3] + [0.0] * 381
        vec2 = [0.1, 0.2, 0.3] + [0.0] * 381  # Identical
        vec3 = [0.9, 0.8, 0.7] + [0.0] * 381  # Different

        await embedding_store.add_embedding("vec1", vec1)
        await embedding_store.add_embedding("vec2", vec2)
        await embedding_store.add_embedding("vec3", vec3)

        results = await embedding_store.search(vec1, k=2)

        assert len(results) == 2
        # Most similar vectors should be vec1 and vec2 (identical)
        similar_ids = {r[0] for r in results}
        assert "vec3" not in similar_ids or results[1][1] < 1.0

    @pytest.mark.asyncio
    async def test_remove_embedding_deletes_vector(self, embedding_store):
        """Test removing embedding."""
        embedding = [0.1, 0.2, 0.3] + [0.0] * 381

        await embedding_store.add_embedding("vec1", embedding)
        assert "vec1" in embedding_store.vectors

        result = await embedding_store.remove_embedding("vec1")
        assert result is True
        assert "vec1" not in embedding_store.vectors

    @pytest.mark.asyncio
    async def test_add_batch_adds_multiple_embeddings(self, embedding_store):
        """Test batch add."""
        records = [
            EmbeddingRecord(
                vector_id="vec1",
                embedding=[0.1, 0.2, 0.3] + [0.0] * 381,
                metadata={"id": 1},
                created_at=time.time(),
            ),
            EmbeddingRecord(
                vector_id="vec2",
                embedding=[0.4, 0.5, 0.6] + [0.0] * 381,
                metadata={"id": 2},
                created_at=time.time(),
            ),
        ]

        added = await embedding_store.add_batch(records)
        assert added == 2
        assert len(embedding_store.vectors) == 2


class TestRecallEngine:
    """Tests for RecallEngine."""

    @pytest.mark.asyncio
    async def test_bm25_recall_finds_keywords(self, recall_engine, memory_graph):
        """Test BM25 keyword search."""
        await memory_graph.add_node(
            content="The quick brown fox jumps over the lazy dog",
            node_type=MemoryType.FACT,
        )
        await memory_graph.add_node(
            content="Cats are independent animals",
            node_type=MemoryType.FACT,
        )

        results = await recall_engine.recall(
            query="quick fox",
            use_bm25=True,
            use_semantic=False,
        )

        assert len(results) > 0
        assert "fox" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_recall_deduplicates_results(self, recall_engine, memory_graph):
        """Test that recall removes duplicates."""
        node_id = await memory_graph.add_node(
            content="Unique content",
            node_type=MemoryType.FACT,
        )

        # Mock embedding store to also return same node
        recall_engine.embedding_store.search = AsyncMock(
            return_value=[(node_id, 0.8)]
        )

        results = await recall_engine.recall(
            query="content",
            embedding=[0.1] * 384,
        )

        # Count unique node IDs
        unique_ids = {r.node_id for r in results}
        assert len(unique_ids) == len(results)  # No duplicates

    @pytest.mark.asyncio
    async def test_recall_cache_hits(self, recall_engine, memory_graph):
        """Test recall caching."""
        await memory_graph.add_node(
            content="Test content",
            node_type=MemoryType.FACT,
        )

        # First call
        results1 = await recall_engine.recall("test", use_semantic=False)
        cache_hits_1 = recall_engine.cache_hits

        # Second call (should hit cache)
        results2 = await recall_engine.recall("test", use_semantic=False)
        cache_hits_2 = recall_engine.cache_hits

        assert cache_hits_2 > cache_hits_1
        assert results1 == results2


class TestTextSummarizer:
    """Tests for TextSummarizer."""

    @pytest.mark.asyncio
    async def test_summarize_compresses_text(self, summarizer):
        """Test text summarization."""
        long_text = (
            "This is a test sentence about history. "
            "The Roman Empire was very powerful. "
            "It lasted for many centuries. "
            "Rome was located in Italy. "
            "The empire had many soldiers. "
        )

        summary, metrics = await summarizer.summarize(long_text)

        assert len(summary) < len(long_text)
        assert metrics.compression_ratio < 1.0

    @pytest.mark.asyncio
    async def test_summarize_respects_target_compression(self, summarizer):
        """Test compression ratio."""
        text = " ".join(["Sentence number " + str(i) + "." for i in range(20)])

        summary, metrics = await summarizer.summarize(
            text,
            compression_ratio=0.5,
        )

        assert metrics.compression_ratio <= 0.6  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_summarize_caches_results(self, summarizer):
        """Test summarization caching."""
        text = "Short text. Another sentence. Final sentence."

        summary1, _ = await summarizer.summarize(text)
        cache_size_1 = len(summarizer.summary_cache)

        summary2, _ = await summarizer.summarize(text)
        cache_size_2 = len(summarizer.summary_cache)

        assert summary1 == summary2
        assert cache_size_2 == cache_size_1  # Cache hit, no new entries

    @pytest.mark.asyncio
    async def test_summarize_preserves_order(self, summarizer):
        """Test that sentences stay in original order."""
        text = "First sentence. Second sentence. Third sentence."

        summary, _ = await summarizer.summarize(text)

        assert summary.find("First") < summary.find("Second")
        assert summary.find("Second") < summary.find("Third")


class TestMemorySystemIntegration:
    """Integration tests for full memory system."""

    @pytest.mark.asyncio
    async def test_full_memory_workflow(
        self,
        memory_graph,
        embedding_store,
        recall_engine,
        summarizer,
    ):
        """Test complete memory workflow."""
        # 1. Add facts to memory graph
        node1_id = await memory_graph.add_node(
            content="Paris is the capital of France",
            node_type=MemoryType.FACT,
        )
        node2_id = await memory_graph.add_node(
            content="France is in Western Europe",
            node_type=MemoryType.FACT,
        )

        # 2. Create relationships
        await memory_graph.add_edge(
            source_id=node1_id,
            target_id=node2_id,
            relation_type=RelationType.PART_OF,
        )

        # 3. Add embeddings
        await embedding_store.add_embedding(
            vector_id=node1_id,
            embedding=[0.1] * 384,
        )
        await embedding_store.add_embedding(
            vector_id=node2_id,
            embedding=[0.1] * 384,
        )

        # 4. Recall memories
        query_embedding = [0.1] * 384
        results = await recall_engine.recall(
            query="Paris France",
            embedding=query_embedding,
        )

        assert len(results) > 0

        # 5. Summarize recalled content
        combined_content = " ".join([r.content for r in results])
        summary, metrics = await summarizer.summarize(combined_content)

        assert summary
        assert metrics.compression_ratio > 0

    @pytest.mark.asyncio
    async def test_memory_graph_stats(self, memory_graph):
        """Test graph statistics."""
        node1_id = await memory_graph.add_node(
            content="Test1",
            node_type=MemoryType.FACT,
        )
        node2_id = await memory_graph.add_node(
            content="Test2",
            node_type=MemoryType.FACT,
        )

        await memory_graph.add_edge(
            source_id=node1_id,
            target_id=node2_id,
            relation_type=RelationType.RELATED_TO,
        )

        stats = memory_graph.get_stats()

        assert stats["node_count"] == 2
        assert stats["edge_count"] == 1
        assert stats["total_inserts"] == 2

    @pytest.mark.asyncio
    async def test_embedding_store_stats(self, embedding_store):
        """Test embedding store statistics."""
        await embedding_store.add_embedding(
            vector_id="vec1",
            embedding=[0.1] * 384,
        )

        stats = embedding_store.get_stats()

        assert stats["total_vectors"] == 1
        assert stats["total_inserts"] == 1

    @pytest.mark.asyncio
    async def test_recall_engine_stats(self, recall_engine):
        """Test recall engine statistics."""
        stats = recall_engine.get_stats()

        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["cache_hit_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_summarizer_stats(self, summarizer):
        """Test summarizer statistics."""
        stats = summarizer.get_stats()

        assert stats["cache_size"] == 0
        assert stats["target_compression"] == 0.3
