"""Integration tests for Phase 2 Task 1: Vector Store & RAG."""

import tempfile
import time
from pathlib import Path

import pytest

from astra.memory.vector_store import LocalVectorStore, EmbeddingConfig, RetrievalResult


@pytest.fixture
async def vector_store():
    """Create temporary vector store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalVectorStore(
            embedding_config=EmbeddingConfig(device="cpu"),
            collection_name="test_knowledge",
            persist_directory=tmpdir,
            ttl_days=90
        )
        await store.initialize()
        yield store


@pytest.mark.asyncio
async def test_vector_store_initialization():
    """Test vector store initializes correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalVectorStore(
            embedding_config=EmbeddingConfig(device="cpu"),
            persist_directory=tmpdir
        )
        await store.initialize()

        assert store.collection is not None
        assert store.client is not None
        assert store.collection_name == "astra_knowledge"


@pytest.mark.asyncio
async def test_add_documents(vector_store):
    """Test adding documents to vector store."""
    documents = [
        "ASTRA is an advanced system for task reasoning and automation.",
        "The vector store uses ChromaDB with HNSW indexing.",
        "Local embeddings are provided by sentence-transformers.",
    ]

    result = await vector_store.add_documents(documents)

    assert result["status"] == "success"
    assert result["documents_added"] == 3
    assert vector_store.metrics["documents_added"] == 3


@pytest.mark.asyncio
async def test_retrieve_documents(vector_store):
    """Test retrieving documents from vector store."""
    documents = [
        "ASTRA is an advanced system for task reasoning and automation.",
        "The vector store uses ChromaDB with HNSW indexing.",
        "Local embeddings are provided by sentence-transformers.",
    ]

    await vector_store.add_documents(documents)

    # Query similar to first document
    results = await vector_store.retrieve("What is ASTRA?", top_k=1)

    assert len(results) > 0
    assert isinstance(results[0], RetrievalResult)
    assert results[0].similarity_score >= 0.0
    assert results[0].text in documents


@pytest.mark.asyncio
async def test_retrieval_latency(vector_store):
    """Test retrieval latency meets <100ms target."""
    # Add test documents
    documents = [f"Document {i}: content about topic {i}" for i in range(50)]
    await vector_store.add_documents(documents)

    # Measure retrieval latency
    start = time.time()
    results = await vector_store.retrieve("topic 25", top_k=5)
    latency_ms = (time.time() - start) * 1000

    assert latency_ms < 100, f"Retrieval latency {latency_ms:.2f}ms exceeds 100ms target"
    assert len(results) == 5


@pytest.mark.asyncio
async def test_batch_processing(vector_store):
    """Test batch processing of documents."""
    # Large batch of documents
    documents = [f"Content {i}: This is document number {i} with test content." for i in range(100)]

    result = await vector_store.add_documents(documents, batch_size=32)

    assert result["documents_added"] == 100
    assert vector_store.metrics["documents_added"] == 100


@pytest.mark.asyncio
async def test_metadata_preservation(vector_store):
    """Test that metadata is preserved during retrieval."""
    documents = ["Test document 1", "Test document 2"]
    metadatas = [
        {"source": "test_1.md", "category": "docs"},
        {"source": "test_2.md", "category": "docs"}
    ]

    await vector_store.add_documents(documents, metadatas=metadatas)
    results = await vector_store.retrieve("test", top_k=2)

    assert len(results) > 0
    assert "source" in results[0].metadata
    assert "category" in results[0].metadata


@pytest.mark.asyncio
async def test_ttl_purge(vector_store):
    """Test TTL-based document purging."""
    documents = ["Test document"]
    await vector_store.add_documents(documents)

    initial_count = vector_store.collection.count()
    assert initial_count > 0

    # Purge expired documents
    result = await vector_store.purge_expired()
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_persistence(vector_store):
    """Test vector store persistence to disk."""
    documents = ["Persistent document"]
    await vector_store.add_documents(documents)

    # Persist to disk
    result = await vector_store.persist()
    assert result["status"] == "success"
    assert Path(result["persist_directory"]).exists()


@pytest.mark.asyncio
async def test_get_metrics(vector_store):
    """Test metrics collection."""
    documents = ["Metric test document"]
    await vector_store.add_documents(documents)

    # Retrieve to accumulate metrics
    await vector_store.retrieve("test", top_k=3)

    metrics = vector_store.get_metrics()
    assert "documents_added" in metrics
    assert "documents_retrieved" in metrics
    assert "avg_retrieval_latency_ms" in metrics
    assert metrics["documents_added"] == 1


@pytest.mark.asyncio
async def test_empty_retrieval(vector_store):
    """Test retrieval from empty store."""
    results = await vector_store.retrieve("nonexistent", top_k=5)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_duplicate_detection(vector_store):
    """Test handling of duplicate documents."""
    documents = ["Duplicate content", "Duplicate content", "Unique content"]
    result = await vector_store.add_documents(documents)

    assert result["documents_added"] == 3
    # Store should accept duplicates; deduplication handled upstream


@pytest.mark.asyncio
async def test_ranking_accuracy(vector_store):
    """Test ranking accuracy of retrieved documents."""
    documents = [
        "Python is a programming language",
        "Java is a programming language",
        "ASTRA is an autonomous system",
        "ChromaDB stores vectors",
    ]

    await vector_store.add_documents(documents)

    # Query about programming languages
    results = await vector_store.retrieve("programming language", top_k=4)

    # Top result should be about programming languages
    assert "programming language" in results[0].text.lower()
    assert results[0].similarity_score > results[-1].similarity_score


@pytest.mark.asyncio
async def test_large_document_chunking():
    """Test handling of large documents with chunking."""
    from scripts.load_knowledge_base import KnowledgeBaseLoader

    loader = KnowledgeBaseLoader()

    # Create a large document
    large_doc = "Sample content. " * 1000  # Large document
    documents = [{"text": large_doc, "source": "large.txt", "category": "test"}]

    chunked = await loader.batch_process(documents, chunk_size=500)

    # Should be split into multiple chunks
    assert len(chunked) > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
