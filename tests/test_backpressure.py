"""
ASTRA Backpressure Tests
Created: October 31, 2025
"""
import time
import pytest
from src.astra.core.backpressure import (
    QueueDepthGuard,
    LatencyTracker,
    RequestTracker
)

def test_queue_depth_guard():
    """Test queue depth limiting"""
    guard = QueueDepthGuard(max_depth=2)
    
    # First two requests accepted
    assert guard.can_accept()
    assert guard.can_accept()
    
    # Third request rejected
    assert not guard.can_accept()
    
    # Complete one request
    guard.complete_request()
    assert guard.can_accept()

def test_latency_tracker():
    """Test latency tracking and SLO monitoring"""
    tracker = LatencyTracker(slo_threshold=1.0)
    
    # Record some latencies
    tracker.record_latency(0.5)  # Under SLO
    tracker.record_latency(0.7)
    tracker.record_latency(1.5)  # Over SLO
    
    # Should have p95 latency
    assert tracker.p95_latency is not None
    
    # Should recommend shedding
    assert tracker.should_shed()

def test_request_tracker():
    """Test request timing"""
    tracker = RequestTracker(start_time=time.time())
    time.sleep(0.1)
    
    elapsed = tracker.elapsed()
    assert elapsed >= 0.1
    assert elapsed < 0.2  # Allow some margin

@pytest.mark.asyncio
async def test_latency_tracking_async():
    """Test async latency tracking"""
    tracker = LatencyTracker(slo_threshold=1.0)
    request = tracker.start_request()
    
    await asyncio.sleep(0.1)
    tracker.record_latency(request.elapsed())
    
    assert len(tracker.latencies) == 1
    assert tracker.p95_latency >= 0.1