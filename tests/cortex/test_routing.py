"""
ASTRA Cortex Test Suite: Routing & Scoring
===========================================

Test neural routing operations.
"""

import numpy as np
import pytest

try:
    from astra_core.cortex import softmax, CORTEX_AVAILABLE
except ImportError:
    CORTEX_AVAILABLE = False
    pytestmark = pytest.mark.skip("Cython extensions not built")


class TestSoftmax:
    """Test stable softmax implementation."""
    
    def test_softmax_basic(self):
        """Verify softmax properties."""
        X = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float64)
        out = softmax(X, temperature=1.0)
        
        # Should sum to 1 per row
        assert np.allclose(np.sum(out, axis=1), 1.0)
        
        # All values should be positive
        assert np.all(out > 0)
        
        # Higher input → higher output
        assert out[0, 2] > out[0, 1] > out[0, 0]
    
    def test_softmax_temperature(self):
        """Test temperature scaling effect."""
        X = np.array([[1, 2, 3]], dtype=np.float64)
        
        # High temperature → uniform distribution
        out_high = softmax(X, temperature=10.0)
        assert np.std(out_high) < 0.1  # Nearly uniform
        
        # Low temperature → peaked distribution
        out_low = softmax(X, temperature=0.1)
        assert out_low[0, 2] > 0.9  # Mostly on max value
    
    def test_softmax_numerical_stability(self):
        """Test with large values that could overflow."""
        X = np.array([[1000, 1001, 999]], dtype=np.float64)
        out = softmax(X, temperature=1.0)
        
        # Should not produce NaN or Inf
        assert not np.any(np.isnan(out))
        assert not np.any(np.isinf(out))
        assert np.allclose(np.sum(out), 1.0)


class TestRoutingIntegration:
    """Test routing in realistic scenarios."""
    
    def test_agent_selection(self):
        """Simulate agent selection via softmax routing."""
        # Agent capabilities as scores
        agent_scores = np.array([
            [0.8, 0.3, 0.5, 0.2],  # Task 1: Agent 0 best
            [0.2, 0.9, 0.4, 0.3],  # Task 2: Agent 1 best
        ], dtype=np.float64)
        
        probs = softmax(agent_scores, temperature=0.5)
        
        # Highest prob should align with highest score
        assert np.argmax(probs[0]) == 0
        assert np.argmax(probs[1]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
