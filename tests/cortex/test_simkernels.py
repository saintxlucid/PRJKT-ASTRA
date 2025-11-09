"""
ASTRA Cortex Test Suite: Similarity Kernels
============================================

Validate parity between Cython and NumPy implementations.
"""

import numpy as np
import pytest

# Try to import Cython kernels, fall back to NumPy if not compiled
try:
    from astra_core.cortex import cosine, dot_product, l2_distance, CORTEX_AVAILABLE
except ImportError:
    CORTEX_AVAILABLE = False
    pytestmark = pytest.mark.skip("Cython extensions not built")


class TestCosineSimilarity:
    """Test batched cosine similarity."""
    
    def test_cosine_parity_small(self):
        """Verify Cython matches NumPy for small matrices."""
        np.random.seed(42)
        A = np.random.rand(10, 64).astype(np.float64)
        B = np.random.rand(5, 64).astype(np.float64)
        
        # NumPy reference
        A_norm = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
        B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        ref = A_norm @ B_norm.T
        
        # Cython implementation
        out = cosine(A, B)
        
        assert np.allclose(out, ref, atol=1e-8)
    
    def test_cosine_parity_large(self):
        """Verify Cython matches NumPy for large matrices."""
        np.random.seed(123)
        A = np.random.rand(256, 384).astype(np.float64)
        B = np.random.rand(128, 384).astype(np.float64)
        
        # NumPy reference
        A_norm = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-12)
        B_norm = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-12)
        ref = A_norm @ B_norm.T
        
        # Cython implementation
        out = cosine(A, B)
        
        assert np.allclose(out, ref, atol=1e-7)
    
    def test_cosine_zero_vectors(self):
        """Handle zero vectors gracefully."""
        A = np.array([[1, 2, 3], [0, 0, 0], [4, 5, 6]], dtype=np.float64)
        B = np.array([[1, 1, 1], [0, 0, 0]], dtype=np.float64)
        
        out = cosine(A, B)
        
        # Zero vectors should produce 0 similarity
        assert out[1, 0] == 0.0
        assert out[1, 1] == 0.0
        assert out[0, 1] == 0.0
        assert out[2, 1] == 0.0
    
    @pytest.mark.benchmark
    def test_cosine_performance(self, benchmark):
        """Benchmark Cython vs NumPy speed."""
        A = np.random.rand(1000, 768).astype(np.float64)
        B = np.random.rand(500, 768).astype(np.float64)
        
        result = benchmark(cosine, A, B)
        assert result.shape == (1000, 500)


class TestDotProduct:
    """Test batched dot products."""
    
    def test_dot_parity(self):
        """Verify Cython matches NumPy."""
        np.random.seed(42)
        A = np.random.rand(100, 64).astype(np.float64)
        B = np.random.rand(50, 64).astype(np.float64)
        
        ref = A @ B.T
        out = dot_product(A, B)
        
        assert np.allclose(out, ref, atol=1e-10)


class TestL2Distance:
    """Test L2 distance computation."""
    
    def test_l2_parity(self):
        """Verify Cython matches NumPy."""
        np.random.seed(42)
        A = np.random.rand(50, 32).astype(np.float64)
        B = np.random.rand(30, 32).astype(np.float64)
        
        # NumPy reference
        ref = np.sqrt(np.sum((A[:, None, :] - B[None, :, :]) ** 2, axis=2))
        
        # Cython
        out = l2_distance(A, B)
        
        assert np.allclose(out, ref, atol=1e-9)
    
    def test_l2_self_distance(self):
        """Distance to self should be zero."""
        A = np.random.rand(10, 16).astype(np.float64)
        out = l2_distance(A, A)
        
        assert np.allclose(np.diag(out), 0.0, atol=1e-10)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_input(self):
        """Handle empty arrays gracefully."""
        A = np.empty((0, 10), dtype=np.float64)
        B = np.random.rand(5, 10).astype(np.float64)
        
        out = cosine(A, B)
        assert out.shape == (0, 5)
    
    def test_dimension_mismatch(self):
        """Should raise error on dimension mismatch."""
        A = np.random.rand(10, 64).astype(np.float64)
        B = np.random.rand(5, 32).astype(np.float64)  # Wrong dimension
        
        with pytest.raises((ValueError, Exception)):
            cosine(A, B)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--benchmark-only"])
