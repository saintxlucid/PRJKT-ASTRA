"""Distributed Tracing Spans - OpenTelemetry Integration

This module provides distributed tracing capabilities for the ASTRA system,
enabling end-to-end request tracking across services and components.

Key Features:
- Span creation and management for distributed tracing
- Automatic correlation ID propagation
- Performance metrics collection per span
- Integration with OpenTelemetry exporters
- Parent-child span relationships tracking
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class SpanKind(Enum):
    """Types of spans in distributed tracing."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


class SpanStatus(Enum):
    """Status of a span execution."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanEvent:
    """Event that occurred during span execution."""
    name: str
    timestamp_ms: float
    attributes: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """Convert event to dictionary."""
        return {
            "name": self.name,
            "timestamp_ms": self.timestamp_ms,
            "attributes": self.attributes,
        }


@dataclass
class TraceSpan:
    """A single span in a distributed trace.
    
    Represents a unit of work within a trace, with timing, context,
    and performance metrics.
    """
    span_id: str
    trace_id: str
    span_name: str
    parent_span_id: str | None = None
    kind: SpanKind = SpanKind.INTERNAL
    status: SpanStatus = SpanStatus.UNSET
    start_time_ms: float = field(default_factory=lambda: time.time() * 1000)
    end_time_ms: float | None = None
    duration_ms: float = 0.0
    attributes: dict[str, object] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    error_message: str | None = None
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def end_span(self, error: str | None = None) -> float:
        """End the span and calculate duration.
        
        Args:
            error: Optional error message if span failed
            
        Returns:
            Duration of span in milliseconds
        """
        self.end_time_ms = time.time() * 1000
        self.duration_ms = self.end_time_ms - self.start_time_ms
        
        if error:
            self.status = SpanStatus.ERROR
            self.error_message = error
        else:
            self.status = SpanStatus.OK
            
        return self.duration_ms

    def add_event(self, name: str, attributes: dict[str, object] | None = None) -> None:
        """Add an event to this span.
        
        Args:
            name: Name of the event
            attributes: Optional attributes for the event
        """
        event = SpanEvent(
            name=name,
            timestamp_ms=time.time() * 1000,
            attributes=attributes or {}
        )
        self.events.append(event)

    def set_attribute(self, key: str, value: object) -> None:
        """Set an attribute on this span.
        
        Args:
            key: Attribute key
            value: Attribute value
        """
        self.attributes[key] = value

    def to_dict(self) -> dict[str, object]:
        """Convert span to dictionary for serialization."""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "span_name": self.span_name,
            "parent_span_id": self.parent_span_id,
            "kind": self.kind.value,
            "status": self.status.value,
            "start_time_ms": self.start_time_ms,
            "end_time_ms": self.end_time_ms,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": [event.to_dict() for event in self.events],
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
        }

    def to_json(self) -> str:
        """Convert span to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class TracingManager:
    """Manages distributed tracing spans and trace context.
    
    This manager handles creation, tracking, and storage of distributed
    trace spans, enabling end-to-end request tracking across services.
    """

    def __init__(self, service_name: str = "astra-core"):
        """Initialize the tracing manager.
        
        Args:
            service_name: Name of the service for tracing
        """
        self.service_name = service_name
        self.active_spans: dict[str, TraceSpan] = {}
        self.completed_spans: list[TraceSpan] = []
        self.max_spans_history = 1000
        self._lock = asyncio.Lock()

    async def start_span(
        self,
        span_name: str,
        trace_id: str | None = None,
        parent_span_id: str | None = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict[str, object] | None = None,
    ) -> TraceSpan:
        """Start a new span.
        
        Args:
            span_name: Name of the span
            trace_id: Optional trace ID (generates new if not provided)
            parent_span_id: Optional parent span ID for nesting
            kind: Type of span
            attributes: Optional initial attributes
            
        Returns:
            Created TraceSpan object
        """
        async with self._lock:
            span_id = str(uuid.uuid4())
            trace_id = trace_id or str(uuid.uuid4())
            
            span = TraceSpan(
                span_id=span_id,
                trace_id=trace_id,
                span_name=span_name,
                parent_span_id=parent_span_id,
                kind=kind,
                attributes=attributes or {},
            )
            
            # Add service name to all spans
            span.set_attribute("service.name", self.service_name)
            span.set_attribute("span.kind", kind.value)
            
            self.active_spans[span_id] = span
            return span

    async def end_span(self, span_id: str, error: str | None = None) -> float | None:
        """End a span and move it to completed.
        
        Args:
            span_id: ID of the span to end
            error: Optional error message
            
        Returns:
            Duration in milliseconds, or None if span not found
        """
        async with self._lock:
            if span_id not in self.active_spans:
                return None
                
            span = self.active_spans.pop(span_id)
            duration = span.end_span(error)
            
            self.completed_spans.append(span)
            
            # Maintain max history size
            if len(self.completed_spans) > self.max_spans_history:
                self.completed_spans = self.completed_spans[-self.max_spans_history:]
            
            return duration

    async def add_event(
        self,
        span_id: str,
        event_name: str,
        attributes: dict[str, object] | None = None,
    ) -> bool:
        """Add an event to an active span.
        
        Args:
            span_id: ID of the span
            event_name: Name of the event
            attributes: Optional event attributes
            
        Returns:
            True if event added, False if span not found
        """
        async with self._lock:
            if span_id not in self.active_spans:
                return False
                
            span = self.active_spans[span_id]
            span.add_event(event_name, attributes)
            return True

    async def set_span_attribute(
        self,
        span_id: str,
        key: str,
        value: object,
    ) -> bool:
        """Set an attribute on an active span.
        
        Args:
            span_id: ID of the span
            key: Attribute key
            value: Attribute value
            
        Returns:
            True if set, False if span not found
        """
        async with self._lock:
            if span_id not in self.active_spans:
                return False
                
            span = self.active_spans[span_id]
            span.set_attribute(key, value)
            return True

    async def get_span_metrics(self, trace_id: str) -> dict[str, object]:
        """Get aggregated metrics for a trace.
        
        Args:
            trace_id: ID of the trace
            
        Returns:
            Dictionary with trace metrics
        """
        async with self._lock:
            trace_spans = [
                span for span in self.completed_spans
                if span.trace_id == trace_id
            ]
            
            if not trace_spans:
                return {
                    "trace_id": trace_id,
                    "span_count": 0,
                    "total_duration_ms": 0.0,
                    "spans": [],
                }
            
            # Calculate metrics
            total_duration = sum(span.duration_ms for span in trace_spans)
            durations = [span.duration_ms for span in trace_spans]
            durations.sort()
            
            p50 = durations[len(durations) // 2] if durations else 0
            p95 = durations[int(len(durations) * 0.95)] if durations else 0
            p99 = durations[int(len(durations) * 0.99)] if durations else 0
            
            error_count = sum(1 for span in trace_spans if span.status == SpanStatus.ERROR)
            
            return {
                "trace_id": trace_id,
                "span_count": len(trace_spans),
                "total_duration_ms": total_duration,
                "mean_duration_ms": total_duration / len(trace_spans) if trace_spans else 0,
                "p50_duration_ms": p50,
                "p95_duration_ms": p95,
                "p99_duration_ms": p99,
                "error_count": error_count,
                "success_rate": (len(trace_spans) - error_count) / len(trace_spans),
                "spans": [span.to_dict() for span in sorted(trace_spans, key=lambda s: s.start_time_ms)],
            }

    async def get_active_spans_count(self) -> int:
        """Get count of currently active spans.
        
        Returns:
            Number of active spans
        """
        async with self._lock:
            return len(self.active_spans)

    async def get_spans_history(self, limit: int = 100) -> list[dict[str, object]]:
        """Get recent completed spans.
        
        Args:
            limit: Maximum number of spans to return
            
        Returns:
            List of span dictionaries
        """
        async with self._lock:
            recent = self.completed_spans[-limit:] if limit > 0 else self.completed_spans
            return [span.to_dict() for span in sorted(recent, key=lambda s: s.start_time_ms, reverse=True)]

    async def clear_history(self) -> int:
        """Clear completed spans history.
        
        Returns:
            Number of spans cleared
        """
        async with self._lock:
            count = len(self.completed_spans)
            self.completed_spans = []
            return count


class SpanContextManager:
    """Context manager for automatic span lifecycle management."""

    def __init__(self, tracing_manager: TracingManager, span: TraceSpan):
        """Initialize context manager.
        
        Args:
            tracing_manager: TracingManager instance
            span: TraceSpan to manage
        """
        self.tracing_manager = tracing_manager
        self.span = span

    async def __aenter__(self) -> TraceSpan:
        """Enter context - return the span."""
        return self.span

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context - end the span with optional error."""
        error_msg = None
        if exc_type is not None:
            error_msg = f"{exc_type.__name__}: {str(exc_val)}"
        
        await self.tracing_manager.end_span(self.span.span_id, error=error_msg)
