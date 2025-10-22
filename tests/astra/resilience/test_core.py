"""Tests for resilience utilities."""
import time
import pytest
from unittest.mock import Mock, patch

from astra.resilience.core import (
    CircuitBreaker,
    CircuitConfig,
    CircuitBreakerDecorator,
    HealthMonitor,
    health
)

def test_circuit_config():
    """Test circuit breaker configuration."""
    config = CircuitConfig(
        failure_threshold=3,
        reset_timeout=15.0,
        half_open_calls=2
    )
    assert config.failure_threshold == 3
    assert config.reset_timeout == 15.0
    assert config.half_open_calls == 2

def test_circuit_initial_state():
    """Test initial circuit breaker state."""
    breaker = CircuitBreaker("test")
    assert breaker.state == "closed"
    assert breaker.failures == 0

def test_circuit_opens_on_failures():
    """Test circuit opens after failures."""
    config = CircuitConfig(failure_threshold=2)
    breaker = CircuitBreaker("test", config)
    
    # First failure
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError))
    assert breaker.state == "closed"
    
    # Second failure opens circuit
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError))
    assert breaker.state == "open"
    
    # Further calls fail fast
    with pytest.raises(Exception) as exc:
        breaker.call(lambda: True)
    assert "Circuit test is open" in str(exc.value)

def test_circuit_half_open_reset():
    """Test circuit transitions to half-open."""
    config = CircuitConfig(
        failure_threshold=1,
        reset_timeout=0.1  # Short timeout for testing
    )
    breaker = CircuitBreaker("test", config)
    
    # Fail and open circuit
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError))
    assert breaker.state == "open"
    
    # Wait for reset timeout
    time.sleep(0.2)
    
    # Should allow retry
    result = breaker.call(lambda: "success")
    assert result == "success"
    assert breaker.state == "half-open"

def test_circuit_closes_after_success():
    """Test circuit closes after successful calls."""
    config = CircuitConfig(
        failure_threshold=1,
        reset_timeout=0.1,
        half_open_calls=2
    )
    breaker = CircuitBreaker("test", config)
    
    # Open circuit
    with pytest.raises(ValueError):
        breaker.call(lambda: (_ for _ in ()).throw(ValueError))
    assert breaker.state == "open"
    
    # Wait for reset
    time.sleep(0.2)
    
    # First success
    breaker.call(lambda: "success")
    assert breaker.state == "half-open"
    
    # Second success closes circuit
    breaker.call(lambda: "success")
    assert breaker.state == "closed"

def test_retry_with_backoff():
    """Test retry mechanism with backoff."""
    config = CircuitConfig(
        max_retries=2,
        initial_delay=0.1,
        backoff_factor=2.0
    )
    breaker = CircuitBreaker("test", config)
    
    mock_func = Mock(side_effect=[ValueError, ValueError, "success"])
    
    result = breaker.call(mock_func)
    assert result == "success"
    assert mock_func.call_count == 3

def test_decorator():
    """Test circuit breaker decorator."""
    config = CircuitConfig(failure_threshold=2)
    
    @CircuitBreakerDecorator("test", config)
    def flaky_function(succeed: bool):
        if not succeed:
            raise ValueError("Failed")
        return "success"
    
    # Successful call
    assert flaky_function(True) == "success"
    
    # Failures open circuit
    with pytest.raises(ValueError):
        flaky_function(False)
    with pytest.raises(ValueError):
        flaky_function(False)
        
    # Circuit now open
    with pytest.raises(Exception) as exc:
        flaky_function(True)
    assert "Circuit test is open" in str(exc.value)

def test_health_monitor():
    """Test health monitoring."""
    monitor = HealthMonitor()
    
    # Initially unhealthy
    assert not monitor.is_healthy("test")
    assert not monitor.all_healthy()
    
    # Set component health
    monitor.set_health("test", True)
    assert monitor.is_healthy("test")
    
    # Multiple components
    monitor.set_health("other", False)
    assert not monitor.all_healthy()
    
    # Get full status
    status = monitor.get_status()
    assert status == {"test": True, "other": False}

def test_global_health():
    """Test global health monitor."""
    health.set_health("qdrant", True)
    assert health.is_healthy("qdrant")
    
    health.set_health("embedder", False)
    assert not health.all_healthy()

@pytest.mark.integration
def test_qdrant_resilience():
    """Test Qdrant resilience (integration test)."""
    from astra.store.qdrant_store import QdrantStore
    
    store = QdrantStore.from_env()
    breaker = CircuitBreaker("qdrant")
    
    # Wrap operations with circuit breaker
    def protected_operation():
        return store.get_metrics()
    
    try:
        # Should succeed if Qdrant up
        result = breaker.call(protected_operation)
        assert isinstance(result, dict)
        
        # Simulate Qdrant down
        store.client = None  # Break connection
        
        with pytest.raises(Exception):
            breaker.call(protected_operation)
            
        assert breaker.failures > 0
        
    finally:
        # Restore connection
        store = QdrantStore.from_env()

@pytest.mark.integration
def test_embedder_resilience():
    """Test embedder resilience (integration test)."""
    from astra.embed.bge import BGEM3Embedder
    
    embedder = BGEM3Embedder()
    breaker = CircuitBreaker("embedder")
    
    # Wrap embedding with circuit breaker
    def protected_operation():
        return embedder.embed_query("test")
    
    try:
        # Should succeed if GPU available
        result = breaker.call(protected_operation)
        assert len(result.shape) == 1
        
        # Simulate GPU error
        embedder.device = "invalid_device"
        
        with pytest.raises(Exception):
            breaker.call(protected_operation)
            
        assert breaker.failures > 0
        
    finally:
        # Restore device
        embedder.device = "cuda"