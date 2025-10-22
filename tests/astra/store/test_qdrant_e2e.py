"""End-to-end tests for Qdrant integration."""
import os
import uuid
import pytest
import time
from pathlib import Path
import structlog
from typing import List, Dict, Any, Optional

import numpy as np

from astra.store.qdrant_store import QdrantStore
from astra.embed.bge import BGEM3Embedder
from astra.rag.indexes import DenseIndex
from astra.rag.documents import Document
from astra.telemetry.events import EventLogger

logger = structlog.get_logger()

# Skip if Qdrant URL not configured
TEST_DOCS = [
    """ASTRA (Advanced Semantic Text Retrieval Architecture) is a distributed 
    RAG system optimized for low-latency retrieval at scale.""",
    
    """The system uses BGE-M3 embeddings with Qdrant for dense retrieval,
    combined with BM25 for hybrid search.""",
    
    """Key features include layout-aware PDF parsing, vector sliding for
    chunk merging, and robust telemetry.""",
    
    """The Windows ingestion service provides automated document processing
    with readiness-based health checks.""",
    
    """ASTRA's multi-RAG pipeline implements reciprocal rank fusion (RRF)
    for optimal retrieval fusion."""
]

@pytest.fixture
def collection_name() -> str:
    """Create unique collection name for test isolation."""
    return f"test_collection_{uuid.uuid4().hex[:8]}"

@pytest.fixture
def qdrant_store(collection_name: str) -> QdrantStore:
    """Initialize Qdrant store for testing."""
    if not os.getenv("QDRANT_URL"):
        pytest.skip("Qdrant URL not configured")
        
    # Initialize store
    store = QdrantStore.from_env()
    
    # Create collection
    store.create_collection(
        collection_name,
        dim=1024,  # BGE-M3 dimension
        distance="Cosine"
    )
    
    yield store
    
    # Cleanup
    store.delete_collection(collection_name)

@pytest.fixture
def embedder() -> BGEM3Embedder:
    """Initialize BGE-M3 embedder."""
    return BGEM3Embedder()

@pytest.fixture
def event_logger(tmp_path: Path) -> EventLogger:
    """Create event logger for testing."""
    return EventLogger(
        log_dir=str(tmp_path),
        rotation_bytes=1048576,
        max_files=2
    )

def test_qdrant_e2e(
    qdrant_store: QdrantStore,
    embedder: BGEM3Embedder,
    event_logger: EventLogger,
    collection_name: str
):
    """Test complete Qdrant workflow."""
    # Create index
    index = DenseIndex(
        store=qdrant_store,
        embedder=embedder,
        collection=collection_name,
        event_logger=event_logger
    )
    
    # Create test documents
    docs = [
        Document(
            id=f"doc{i}",
            text=text,
            metadata={"source": "test"}
        )
        for i, text in enumerate(TEST_DOCS)
    ]
    
    # Track metrics before
    metrics_before = index.get_metrics()
    
    # Ingest documents
    index.index_documents(docs)
    
    # Verify ingestion metrics
    metrics_after = index.get_metrics()
    assert metrics_after["docs_indexed"] > metrics_before["docs_indexed"]
    
    # Check events
    events = event_logger.read_events()
    assert any(e["event"] == "ingestion.complete" for e in events)
    
    # Test retrieval
    query = "What is ASTRA?"
    results = index.search(query, top_k=3)
    
    # Verify results
    assert len(results) > 0
    assert any("ASTRA" in r.text for r in results)
    assert all(0 <= r.score <= 1.0 for r in results)
    
    # Test cache hit
    start = time.time()
    cached_results = index.search(query, top_k=3)
    cache_query_time = time.time() - start
    
    # Verify cache hit is faster
    assert len(cached_results) == len(results)
    assert cache_query_time < 0.1  # Should be much faster
    
    # Check cache metrics
    final_metrics = index.get_metrics()
    assert final_metrics["cache_hits"] > metrics_after["cache_hits"]

def test_qdrant_bulk_ingest(
    qdrant_store: QdrantStore,
    embedder: BGEM3Embedder, 
    event_logger: EventLogger,
    collection_name: str
):
    """Test bulk ingestion with batching."""
    # Create larger document set
    docs = []
    for i in range(20):  # 20 docs
        text = f"Test document {i} with some content for embedding."
        docs.append(Document(
            id=f"bulk{i}",
            text=text,
            metadata={"batch": i // 5}  # Group in batches of 5
        ))
    
    index = DenseIndex(
        store=qdrant_store,
        embedder=embedder,
        collection=collection_name,
        event_logger=event_logger
    )
    
    # Bulk ingest
    index.index_documents(docs, batch_size=5)
    
    # Verify all docs indexed
    points = qdrant_store.get_points(collection_name)
    assert len(points) == 20
    
    # Check batch events
    events = event_logger.read_events()
    batch_events = [e for e in events if e["event"] == "batch.complete"]
    assert len(batch_events) == 4  # 20 docs / 5 per batch

def test_qdrant_search_quality(
    qdrant_store: QdrantStore,
    embedder: BGEM3Embedder,
    event_logger: EventLogger,
    collection_name: str
):
    """Test search result quality and scoring."""
    index = DenseIndex(
        store=qdrant_store,
        embedder=embedder,
        collection=collection_name,
        event_logger=event_logger
    )
    
    # Index test docs
    docs = [
        Document(id=f"doc{i}", text=text)
        for i, text in enumerate(TEST_DOCS)
    ]
    index.index_documents(docs)
    
    # Test queries
    queries = [
        ("What is ASTRA?", ["ASTRA", "distributed", "RAG"]),
        ("What embeddings are used?", ["BGE-M3", "embeddings"]),
        ("How does it handle PDFs?", ["PDF", "parsing", "layout"]),
    ]
    
    for query, expected_terms in queries:
        results = index.search(query, top_k=3)
        
        # Verify relevance
        assert len(results) > 0
        result_text = " ".join(r.text for r in results)
        assert any(term.lower() in result_text.lower() 
                  for term in expected_terms)
        
        # Check score distribution
        scores = [r.score for r in results]
        assert all(0.5 <= s <= 1.0 for s in scores)  # Reasonable scores
        assert scores == sorted(scores, reverse=True)  # Sorted by score