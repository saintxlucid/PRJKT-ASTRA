"""
Unit tests for queue and capacity metrics.

Tests that new metrics are registered and observable.
"""

import pytest

from astra.metrics import QUEUE_DEPTH, QUEUE_WAIT_SECONDS, LIMITER_PER_KEY_ALLOWED, LIMITER_PER_KEY_BLOCKED


def test_queue_depth_metric_exists():
    """Test that queue depth gauge is registered"""
    # Gauge should start at 0
    assert QUEUE_DEPTH._value.get() >= 0
    
    # Should be settable
    QUEUE_DEPTH.set(10)
    assert QUEUE_DEPTH._value.get() == 10
    
    QUEUE_DEPTH.set(0)


def test_queue_wait_seconds_histogram_exists():
    """Test that queue wait histogram is registered"""
    # Record some samples
    QUEUE_WAIT_SECONDS.observe(0.001)
    QUEUE_WAIT_SECONDS.observe(0.01)
    QUEUE_WAIT_SECONDS.observe(0.1)
    QUEUE_WAIT_SECONDS.observe(1.0)
    
    # Verify samples were recorded (check internal counter)
    assert QUEUE_WAIT_SECONDS._sum._value.get() > 0


def test_limiter_per_key_allowed_counter_exists():
    """Test that per-key allowed counter is registered"""
    # Increment with label
    LIMITER_PER_KEY_ALLOWED.labels(key_hash="test_hash_123").inc()
    LIMITER_PER_KEY_ALLOWED.labels(key_hash="test_hash_123").inc(5)
    
    # Verify increments (access internal counter)
    metric = LIMITER_PER_KEY_ALLOWED.labels(key_hash="test_hash_123")
    assert metric._value.get() >= 6


def test_limiter_per_key_blocked_counter_exists():
    """Test that per-key blocked counter is registered"""
    # Increment with different labels
    LIMITER_PER_KEY_BLOCKED.labels(key_hash="hash_abc").inc()
    LIMITER_PER_KEY_BLOCKED.labels(key_hash="hash_xyz").inc(3)
    
    # Verify increments
    assert LIMITER_PER_KEY_BLOCKED.labels(key_hash="hash_abc")._value.get() >= 1
    assert LIMITER_PER_KEY_BLOCKED.labels(key_hash="hash_xyz")._value.get() >= 3


def test_queue_metrics_integration():
    """Test queue metrics work together"""
    # Simulate queue activity
    QUEUE_DEPTH.set(5)
    QUEUE_WAIT_SECONDS.observe(0.025)
    QUEUE_DEPTH.set(4)
    QUEUE_WAIT_SECONDS.observe(0.015)
    QUEUE_DEPTH.set(0)
    
    # Verify final state
    assert QUEUE_DEPTH._value.get() == 0
    assert QUEUE_WAIT_SECONDS._sum._value.get() >= 0.04


def test_per_key_limiter_metrics_integration():
    """Test per-key limiter metrics work together"""
    key_hash = "integration_test_hash"
    
    # Simulate allow/block pattern
    LIMITER_PER_KEY_ALLOWED.labels(key_hash=key_hash).inc(10)
    LIMITER_PER_KEY_BLOCKED.labels(key_hash=key_hash).inc(2)
    
    # Verify counts
    allowed = LIMITER_PER_KEY_ALLOWED.labels(key_hash=key_hash)._value.get()
    blocked = LIMITER_PER_KEY_BLOCKED.labels(key_hash=key_hash)._value.get()
    
    assert allowed >= 10
    assert blocked >= 2
    
    # Allow rate should be 10/(10+2) = 83%
    allow_rate = allowed / (allowed + blocked)
    assert 0.8 <= allow_rate <= 0.85
