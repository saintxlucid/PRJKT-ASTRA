"""
ASTRA Cortex Test Suite: Memory Forge
======================================

Test memory compression and semantic decay.
"""

import numpy as np
import pytest

try:
    from astra_core.cortex import memory_compress, apply_semantic_decay, CORTEX_AVAILABLE
except ImportError:
    CORTEX_AVAILABLE = False
    pytestmark = pytest.mark.skip("Cython extensions not built")


class TestMemoryCompression:
    """Test vector compression and deduplication."""
    
    def test_compression_reduces_size(self):
        """Compression should reduce memory count."""
        # Create similar vectors
        base = np.random.rand(384)
        embeddings = np.array([
            base + np.random.rand(384) * 0.01,  # Very similar
            base + np.random.rand(384) * 0.01,
            base + np.random.rand(384) * 0.01,
            np.random.rand(384),  # Different
        ], dtype=np.float64)
        
        compressed = memory_compress(embeddings, threshold=0.95)
        
        # Should merge similar vectors
        assert compressed.shape[0] < embeddings.shape[0]
        assert compressed.shape[1] == embeddings.shape[1]  # Same dimensionality
    
    def test_compression_preserves_diversity(self):
        """Different vectors should not be merged."""
        embeddings = np.random.rand(10, 128).astype(np.float64)
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        compressed = memory_compress(embeddings, threshold=0.99)
        
        # Very diverse set should not compress much
        assert compressed.shape[0] >= embeddings.shape[0] * 0.7


class TestSemanticDecay:
    """Test biological-inspired memory decay."""
    
    def test_decay_reduces_importance(self):
        """Unused memories should decay."""
        embeddings = np.random.rand(5, 64).astype(np.float64)
        importance = np.ones(5, dtype=np.float64) * 0.8
        time_deltas = np.array([1.0, 5.0, 10.0, 20.0, 50.0], dtype=np.float64)
        
        new_importance = apply_semantic_decay(
            embeddings, importance, time_deltas, decay_rate=0.1
        )
        
        # Older memories should have lower importance
        assert new_importance[0] > new_importance[1]
        assert new_importance[1] > new_importance[2]
        assert new_importance[2] > new_importance[3]
        assert new_importance[3] > new_importance[4]
    
    def test_decay_floor(self):
        """Importance should not decay to zero."""
        embeddings = np.random.rand(3, 64).astype(np.float64)
        importance = np.ones(3, dtype=np.float64)
        time_deltas = np.array([100.0, 200.0, 500.0], dtype=np.float64)
        
        new_importance = apply_semantic_decay(
            embeddings, importance, time_deltas, decay_rate=0.1
        )
        
        # Should maintain minimum importance
        assert np.all(new_importance > 0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
