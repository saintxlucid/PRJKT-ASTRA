"""
Tests for Qdrant E2E integration.

This test runs the Qdrant E2E script if QDRANT_URL is set in the environment.
It verifies:
1. Collection creation and vector operations work
2. Ingestion events are emitted correctly
3. Metrics increment as expected
"""
import os
import json
import time
import random
import pytest
from typing import List, Optional
from pathlib import Path

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from astra.telemetry import metrics
from astra.core.types import Document, SearchResult

logger = structlog.get_logger()

# Skip these tests if QDRANT_URL not set
pytestmark = pytest.mark.skipif(
    "QDRANT_URL" not in os.environ,
    reason="QDRANT_URL not set - skipping Qdrant E2E tests"
)

@pytest.fixture
def qdrant_url() -> str:
    """Get Qdrant URL from env or skip"""
    url = os.environ.get("QDRANT_URL")
    if not url:
        pytest.skip("QDRANT_URL not set")
    return url

@pytest.fixture
def test_collection(request) -> str:
    """Get unique test collection name"""
    collection = f"test_e2e_{int(time.time())}"
    
    def cleanup():
        try:
            url = os.environ.get("QDRANT_URL")
            if url:
                client = QdrantClient(url=url)
                client.delete_collection(collection_name=collection)
                logger.info("cleaned_up_collection", name=collection)
        except Exception as e:
            logger.warning("cleanup_failed", collection=collection, error=str(e))
    
    request.addfinalizer(cleanup)
    return collection

@pytest.fixture
def dim() -> int:
    """Vector dimension for testing"""
    return 8  # Small dim for quick tests

def random_vector(dim: int) -> List[float]:
    """Generate random test vector"""
    return [random.random() for _ in range(dim)]

def test_qdrant_e2e_flow(qdrant_url: str, test_collection: str, dim: int):
    """Test the full E2E flow: connect, create, upsert, search, verify events"""
    client = QdrantClient(url=qdrant_url)

    # 1. Create collection
    client.create_collection(
        collection_name=test_collection,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
    )
    collections = client.get_collections()
    assert test_collection in [c.name for c in collections.collections]

    # 2. Upsert test vectors
    points = []
    for i in range(5):
        points.append({
            "id": f"p{i+1}",
            "vector": random_vector(dim),
            "payload": {
                "text": f"test doc {i+1}",
                "meta": {"source": "e2e_test"}
            }
        })
    
    client.upsert(
        collection_name=test_collection,
        points=points
    )

    # 3. Search with random query
    query = random_vector(dim)
    results = client.search(
        collection_name=test_collection,
        query_vector=query,
        limit=3
    )
    assert len(results) > 0

    # 4. Verify events emitted
    time.sleep(0.1)  # Let event write complete
    log_file = Path("logs/events.jsonl")
    assert log_file.exists()

    events = []
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                event = json.loads(line)
                if (event["kind"] == "ingestion.complete" and 
                    event["details"].get("collection") == test_collection):
                    events.append(event)

    assert len(events) >= 1
    latest = events[-1]
    assert latest["details"]["inserted"] == len(points)
    assert latest["details"]["results"] == len(results)

    # 5. Check metrics
    counter = STORE_OPS_COUNTER.labels(operation="upsert")._value.get()
    assert counter >= len(points)

def test_qdrant_error_handling(qdrant_url: str, test_collection: str, dim: int):
    """Test error cases and verify clean error handling"""
    client = QdrantClient(url=qdrant_url)
    
    # Try operations on non-existent collection
    bad_collection = f"nonexistent_{int(time.time())}"
    
    # Search should return empty results, not crash
    results = client.search(
        collection_name=bad_collection,
        query_vector=random_vector(dim),
        limit=3
    )
    assert len(results) == 0

    # Delete non-existent collection should not error
    client.delete_collection(collection_name=bad_collection)

    # Create with wrong dimension should fail gracefully
    with pytest.raises(Exception):
        client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(size=-1, distance=Distance.COSINE)
        )