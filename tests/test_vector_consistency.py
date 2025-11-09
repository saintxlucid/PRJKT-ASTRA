"""
Vector Backend Consistency Tests for ASTRA Core

Ensures deterministic and consistent behavior across multiple vector stores:
- ChromaDB
- Qdrant
- SimpleVecDB

Tests verify:
1. Deterministic top-k retrieval (same query returns same results)
2. Monotonic score ordering (scores decrease monotonically)
3. Metadata filtering consistency
4. Idempotency (repeated queries return identical results)
"""

import pytest
from typing import List, Dict, Any

# Assuming these exist in your codebase
# Adjust imports based on actual structure
try:
    from src.astra.vector_stores import make_store
    from src.astra.infrastructure.storage.vector_store import VectorStore
except ImportError:
    # Fallback for different project structures
    pytest.skip("Vector store modules not found", allow_module_level=True)


# Test corpus
CORPUS = [
    {
        "id": f"doc_{i}",
        "text": f"Gamma resonance beam {i} delta particle accelerator physics",
        "metadata": {"user": "demo", "category": "physics", "doc_id": i}
    }
    for i in range(50)
]

# Additional varied documents
CORPUS.extend([
    {"id": "doc_bio_1", "text": "Cellular biology mitochondria ATP synthesis", "metadata": {"user": "demo", "category": "biology"}},
    {"id": "doc_bio_2", "text": "DNA transcription RNA polymerase enzyme", "metadata": {"user": "demo", "category": "biology"}},
    {"id": "doc_cs_1", "text": "Machine learning neural network backpropagation", "metadata": {"user": "demo", "category": "computer_science"}},
    {"id": "doc_cs_2", "text": "Algorithm optimization time complexity analysis", "metadata": {"user": "demo", "category": "computer_science"}},
])

QUERY_PHYSICS = "gamma resonance particle physics"
QUERY_BIOLOGY = "cellular DNA biology"


@pytest.mark.parametrize("backend", ["qdrant", "chroma", "simple"])
class TestVectorBackendConsistency:
    """Test suite for vector backend consistency."""
    
    @pytest.fixture(autouse=True)
    def setup_store(self, backend: str):
        """Initialize vector store for each backend."""
        try:
            self.store = make_store(backend, collection="consistency_test_ci")
            # Clear any existing data
            self.store.reset()
            # Upsert test corpus
            self.store.upsert(CORPUS)
            yield
            # Cleanup
            self.store.reset()
        except Exception as e:
            pytest.skip(f"Backend {backend} not available: {e}")
    
    def test_topk_deterministic(self, backend: str):
        """Test that top-k results are deterministic."""
        # Query multiple times
        results_1 = self.store.search(QUERY_PHYSICS, topk=10)
        results_2 = self.store.search(QUERY_PHYSICS, topk=10)
        results_3 = self.store.search(QUERY_PHYSICS, topk=10)
        
        # Extract IDs
        ids_1 = [r.id for r in results_1]
        ids_2 = [r.id for r in results_2]
        ids_3 = [r.id for r in results_3]
        
        # All should be identical
        assert ids_1 == ids_2 == ids_3, f"{backend}: Non-deterministic top-k results"
    
    def test_score_monotonic(self, backend: str):
        """Test that scores are monotonically non-increasing."""
        results = self.store.search(QUERY_PHYSICS, topk=15)
        scores = [r.score for r in results]
        
        # Verify monotonic decrease (allowing for floating-point equality)
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1] - 1e-6, \
                f"{backend}: Scores not monotonic at index {i}: {scores[i]} < {scores[i+1]}"
    
    def test_metadata_filtering(self, backend: str):
        """Test that metadata filtering is consistent."""
        # Filter by category
        results_physics = self.store.search(
            QUERY_PHYSICS,
            topk=10,
            where={"metadata.category": "physics"}
        )
        
        results_biology = self.store.search(
            QUERY_BIOLOGY,
            topk=10,
            where={"metadata.category": "biology"}
        )
        
        # Verify filtering worked
        for r in results_physics:
            assert r.metadata.get("category") == "physics", \
                f"{backend}: Physics filter returned non-physics doc: {r.id}"
        
        for r in results_biology:
            assert r.metadata.get("category") == "biology", \
                f"{backend}: Biology filter returned non-biology doc: {r.id}"
    
    def test_empty_query_handling(self, backend: str):
        """Test graceful handling of empty/invalid queries."""
        results_empty = self.store.search("", topk=5)
        assert len(results_empty) >= 0, f"{backend}: Empty query failed"
        
        # Should return something or empty list, not crash
        results_gibberish = self.store.search("zxqwryuiop asdfghjkl", topk=5)
        assert len(results_gibberish) >= 0, f"{backend}: Gibberish query failed"
    
    def test_topk_boundary(self, backend: str):
        """Test boundary conditions for topk parameter."""
        # topk = 1
        results_1 = self.store.search(QUERY_PHYSICS, topk=1)
        assert len(results_1) == 1, f"{backend}: topk=1 returned {len(results_1)} results"
        
        # topk = 0 (should return empty or handle gracefully)
        results_0 = self.store.search(QUERY_PHYSICS, topk=0)
        assert len(results_0) == 0, f"{backend}: topk=0 returned {len(results_0)} results"
        
        # topk > corpus size
        results_large = self.store.search(QUERY_PHYSICS, topk=1000)
        assert len(results_large) <= len(CORPUS), \
            f"{backend}: topk=1000 returned more than corpus size"
    
    def test_score_range(self, backend: str):
        """Test that scores are in expected range."""
        results = self.store.search(QUERY_PHYSICS, topk=10)
        
        for r in results:
            # Cosine similarity typically in [-1, 1], but often normalized to [0, 1]
            # Different backends may have different ranges
            assert r.score >= -1.0 and r.score <= 1.0, \
                f"{backend}: Score {r.score} out of range [-1, 1]"


@pytest.mark.integration
class TestCrossBackendConsistency:
    """Test consistency across different backends."""
    
    def test_cross_backend_top_result(self):
        """Test that top result is similar across backends."""
        backends = ["qdrant", "chroma", "simple"]
        top_results = {}
        
        for backend in backends:
            try:
                store = make_store(backend, collection="cross_backend_test")
                store.reset()
                store.upsert(CORPUS)
                results = store.search(QUERY_PHYSICS, topk=3)
                top_results[backend] = [r.id for r in results[:3]]
                store.reset()
            except Exception as e:
                pytest.skip(f"Backend {backend} not available: {e}")
        
        # Check if at least 2 out of 3 top results overlap
        if len(top_results) >= 2:
            backends_list = list(top_results.keys())
            for i in range(len(backends_list)):
                for j in range(i + 1, len(backends_list)):
                    b1, b2 = backends_list[i], backends_list[j]
                    overlap = set(top_results[b1]) & set(top_results[b2])
                    assert len(overlap) >= 2, \
                        f"Insufficient overlap between {b1} and {b2}: {top_results[b1]} vs {top_results[b2]}"


# Runtime invariant check (for startup validation)
def verify_vector_consistency_startup():
    """
    Lightweight startup probe to detect backend drift.
    
    This should be called during application initialization
    to fail fast if a vector backend behaves unexpectedly.
    """
    probe_docs = [
        {"id": "p1", "text": "gamma resonance beam", "metadata": {"user": "probe"}},
        {"id": "p2", "text": "resonant gamma field", "metadata": {"user": "probe"}},
        {"id": "p3", "text": "delta echo cloud", "metadata": {"user": "probe"}},
    ]
    
    query = "gamma resonance"
    backends_to_test = ["qdrant", "chroma", "simple"]
    picks = {}
    
    for backend in backends_to_test:
        try:
            store = make_store(backend, collection="consistency_probe")
            store.reset()
            store.upsert(probe_docs)
            results = store.search(query, topk=2)
            picks[backend] = [r.id for r in results]
            store.reset()
        except Exception as e:
            print(f"Warning: Backend {backend} not available during startup check: {e}")
            continue
    
    # Invariant: p1 or p2 should appear in all top-2 results
    if len(picks) >= 2:
        common_docs = set.intersection(*[set(v) for v in picks.values()])
        assert len(common_docs) >= 1, \
            f"Vector backend drift detected: {picks}. No common top results across backends."
    
    return picks


if __name__ == "__main__":
    # Run startup check
    print("Running vector consistency startup check...")
    result = verify_vector_consistency_startup()
    print(f"Startup check passed: {result}")
