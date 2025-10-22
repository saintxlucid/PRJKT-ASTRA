"""
Tests for the RAG telemetry system.
"""

import json
import asyncio
from pathlib import Path
import pytest
from datetime import datetime, UTC
from typing import List, Dict

from astra.core.event_bus import get_event_bus, Event
from astra.rag.telemetry import (
    TelemetryEmitter,
    TelemetryEvent,
    RetrievalMetrics,
    EVENT_RETRIEVAL_STARTED,
    EVENT_RETRIEVAL_COMPLETED,
    EVENT_RETRIEVAL_ERROR
)


class EventCollector:
    """Helper to collect emitted events."""
    
    def __init__(self):
        self.events: List[Event] = []
        
    def collect(self, event: Event):
        self.events.append(event)


@pytest.fixture
def temp_dir(tmp_path):
    """Provide temporary directory."""
    return tmp_path / "telemetry"


@pytest.fixture
def telemetry(temp_dir):
    """Create telemetry emitter instance."""
    emitter = TelemetryEmitter(
        output_dir=str(temp_dir),
        max_file_size=1024,  # 1KB for testing
        rotation_count=3
    )
    return emitter


def test_telemetry_event_creation():
    """Test creation of telemetry events."""
    event = TelemetryEvent(
        event_type=EVENT_RETRIEVAL_STARTED,
        trace_id="test-123",
        metadata={"query": "test query"}
    )
    
    assert event.event_type == EVENT_RETRIEVAL_STARTED
    assert event.trace_id == "test-123"
    assert event.metadata["query"] == "test query"
    assert isinstance(event.timestamp, str)


def test_retrieval_metrics():
    """Test retrieval metrics tracking."""
    metrics = RetrievalMetrics(
        num_candidates=10,
        num_filtered=5,
        latency_ms=100.5,
        tokens_processed=1000,
        embedding_time_ms=50.2,
        search_time_ms=30.1,
        fusion_time_ms=20.2
    )
    
    assert metrics.num_candidates == 10
    assert metrics.num_filtered == 5
    assert metrics.latency_ms == 100.5
    assert metrics.tokens_processed == 1000
    assert metrics.embedding_time_ms == 50.2
    assert metrics.search_time_ms == 30.1
    assert metrics.fusion_time_ms == 20.2


@pytest.mark.asyncio
async def test_telemetry_emission(telemetry, temp_dir):
    """Test emitting events through telemetry system."""
    # Subscribe to events
    bus = get_event_bus()
    collector = EventCollector()
    bus.subscribe(EVENT_RETRIEVAL_STARTED, collector.collect)
    
    # Emit test event
    event = TelemetryEvent(
        event_type=EVENT_RETRIEVAL_STARTED,
        trace_id="test-123",
        metadata={"query": "test query"}
    )
    await telemetry.emit(event)
    
    # Verify event bus received event
    assert len(collector.events) == 1
    assert collector.events[0].name == EVENT_RETRIEVAL_STARTED
    assert collector.events[0].data["trace_id"] == "test-123"
    
    # Verify JSONL file was written
    log_file = list(temp_dir.glob("*.jsonl"))[0]
    assert log_file.exists()
    
    with open(log_file) as f:
        data = json.loads(f.readline())
        assert data["event_type"] == EVENT_RETRIEVAL_STARTED
        assert data["trace_id"] == "test-123"
        assert data["metadata"]["query"] == "test query"


@pytest.mark.asyncio
async def test_file_rotation(telemetry, temp_dir):
    """Test log file rotation."""
    # Generate enough events to trigger rotation
    for i in range(10):
        event = TelemetryEvent(
            event_type=EVENT_RETRIEVAL_STARTED,
            trace_id=f"test-{i}",
            metadata={"large": "x" * 200}  # Create large events
        )
        await telemetry.emit(event)
    
    # Check that files were rotated
    log_files = list(temp_dir.glob("*.jsonl"))
    assert len(log_files) > 1
    assert all(f.stat().st_size <= telemetry.max_file_size for f in log_files)


@pytest.mark.asyncio
async def test_metrics_tracking(telemetry):
    """Test metrics are properly tracked."""
    # Initial metrics
    metrics = telemetry.get_metrics()
    assert metrics["total_retrievals"] == 0
    assert metrics["total_errors"] == 0
    
    # Emit successful retrieval
    await telemetry.emit(TelemetryEvent(
        event_type=EVENT_RETRIEVAL_COMPLETED,
        metadata={"latency_ms": 100.0}
    ))
    
    metrics = telemetry.get_metrics()
    assert metrics["total_retrievals"] == 1
    assert metrics["avg_latency_ms"] > 0
    
    # Emit error
    await telemetry.emit(TelemetryEvent(
        event_type=EVENT_RETRIEVAL_ERROR,
        metadata={"error": "test error"}
    ))
    
    metrics = telemetry.get_metrics()
    assert metrics["total_errors"] == 1
    assert metrics["error_rate"] == 0.5  # 1 error out of 2 total


@pytest.mark.asyncio
async def test_trace_tracking(telemetry):
    """Test trace context management."""
    trace_id = "test-trace-123"
    
    # Start trace
    await telemetry.start_trace(trace_id)
    assert trace_id in telemetry.active_traces
    
    # Emit event with trace
    await telemetry.emit(TelemetryEvent(
        event_type=EVENT_RETRIEVAL_STARTED,
        trace_id=trace_id
    ))
    
    # End trace
    await telemetry.end_trace(trace_id)
    assert trace_id not in telemetry.active_traces