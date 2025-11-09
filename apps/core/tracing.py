"""
Phase 11: DistributedTracer - OpenTelemetry-Compatible Distributed Tracing

Provides distributed tracing with trace/span IDs, context propagation,
and multiple export formats for observability across system components.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Awaitable, Callable
from contextvars import ContextVar
import json


class SpanStatus(Enum):
    """Span execution status."""
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


@dataclass
class SpanEvent:
    """Event within a span."""
    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'timestamp': self.timestamp.isoformat(),
            'attributes': self.attributes,
        }


@dataclass
class TraceSpan:
    """A trace span representing an operation."""
    trace_id: str                              # Unique trace ID
    span_id: str                               # Unique span ID
    parent_span_id: Optional[str] = None       # Parent span ID
    name: str = ""                             # Operation name
    status: SpanStatus = SpanStatus.UNSET      # Execution status
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None        # When span finished
    attributes: Dict[str, Any] = field(default_factory=dict)  # Span attributes
    events: List[SpanEvent] = field(default_factory=list)      # Span events
    error: Optional[str] = None                # Error message
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        end = self.end_time or datetime.utcnow()
        delta = end - self.start_time
        return delta.total_seconds() * 1000
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> SpanEvent:
        """Add event to span."""
        event = SpanEvent(
            name=name,
            timestamp=datetime.utcnow(),
            attributes=attributes or {}
        )
        self.events.append(event)
        return event
    
    def set_status(self, status: SpanStatus, error: Optional[str] = None) -> None:
        """Set span status."""
        self.status = status
        self.error = error
    
    def finish(self) -> None:
        """Mark span as finished."""
        self.end_time = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_span_id': self.parent_span_id,
            'name': self.name,
            'status': self.status.value,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_ms': self.duration_ms,
            'attributes': self.attributes,
            'events': [e.to_dict() for e in self.events],
            'error': self.error,
        }


class DistributedTracer:
    """OpenTelemetry-compatible distributed tracing."""
    
    def __init__(self, service_name: str = "astra", max_traces: int = 10000):
        """Initialize tracer.
        
        Args:
            service_name: Service name for resource attributes
            max_traces: Maximum traces to keep in memory
        """
        self.service_name = service_name
        self.max_traces = max_traces
        
        # Storage
        self._traces: Dict[str, List[TraceSpan]] = {}  # trace_id -> spans
        self._spans: Dict[str, TraceSpan] = {}  # span_id -> span
        self._lock = asyncio.Lock()
        
        # Current context
        self._current_span: ContextVar[Optional[TraceSpan]] = ContextVar('current_span', default=None)
        
        # Statistics
        self._stats = {
            'spans_created': 0,
            'spans_finished': 0,
            'errors': 0,
        }
        
        # Callbacks
        self._callbacks: List[Callable[[TraceSpan], Awaitable]] = []
    
    def create_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        parent_span: Optional[TraceSpan] = None,
        trace_id: Optional[str] = None,
    ) -> TraceSpan:
        """Create a new span.
        
        Args:
            name: Operation name
            attributes: Span attributes
            parent_span: Parent span (for child spans)
            trace_id: Trace ID (creates new trace if not provided)
        
        Returns:
            Created span
        """
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        span = TraceSpan(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span.span_id if parent_span else None,
            name=name,
            attributes=attributes or {},
        )
        
        self._spans[span.span_id] = span
        
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        self._traces[trace_id].append(span)
        
        # Limit traces in memory
        if len(self._traces) > self.max_traces:
            oldest_trace_id = list(self._traces.keys())[0]
            del self._traces[oldest_trace_id]
        
        self._stats['spans_created'] += 1
        return span
    
    def start_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> TraceSpan:
        """Start a new root span (sets as current context)."""
        # Check if we're in a span context
        parent = self._current_span.get()
        
        span = self.create_span(name, attributes, parent_span=parent)
        self._current_span.set(span)
        return span
    
    def finish_span(self, span: TraceSpan) -> None:
        """Finish a span."""
        span.finish()
        self._stats['spans_finished'] += 1
        
        # Call callbacks
        for callback in self._callbacks:
            try:
                # Don't await here, just schedule
                asyncio.create_task(callback(span))
            except Exception:
                pass
    
    async def span_context(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Async context manager for span creation."""
        span = self.start_span(name, attributes)
        try:
            yield span
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            self._stats['errors'] += 1
            raise
        finally:
            self.finish_span(span)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add event to current span."""
        span = self._current_span.get()
        if span:
            span.add_event(name, attributes)
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set attribute on current span."""
        span = self._current_span.get()
        if span:
            span.attributes[key] = value
    
    def inject_context(self, span: Optional[TraceSpan] = None) -> Dict[str, str]:
        """Inject span context for propagation."""
        if span is None:
            span = self._current_span.get()
        
        if span is None:
            return {}
        
        return {
            'trace_id': span.trace_id,
            'span_id': span.span_id,
            'parent_span_id': span.parent_span_id or '',
        }
    
    def extract_context(self, context_dict: Dict[str, str]) -> Optional[str]:
        """Extract span context and set as current."""
        trace_id = context_dict.get('trace_id')
        parent_span_id = context_dict.get('span_id')
        
        if trace_id:
            # Create child span
            parent_span = self._spans.get(parent_span_id) if parent_span_id else None
            span = self.create_span('extracted_span', trace_id=trace_id, parent_span=parent_span)
            self._current_span.set(span)
            return span.span_id
        
        return None
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get span by ID."""
        return self._spans.get(span_id)
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans in a trace."""
        return self._traces.get(trace_id, [])
    
    def get_traces(self, component: Optional[str] = None) -> List[List[TraceSpan]]:
        """Get all traces, optionally filtered by component."""
        result = list(self._traces.values())
        
        if component:
            result = [
                spans for spans in result
                if any(spans[0].attributes.get('component') == component for _ in [None])
            ]
        
        return result
    
    def export_jaeger_format(self) -> List[Dict[str, Any]]:
        """Export traces in Jaeger format."""
        result = []
        for trace_id, spans in self._traces.items():
            jaeger_spans = []
            for span in spans:
                jaeger_span = {
                    'traceID': span.trace_id,
                    'spanID': span.span_id,
                    'parentSpanID': span.parent_span_id or '',
                    'operationName': span.name,
                    'startTime': int(span.start_time.timestamp() * 1_000_000),  # microseconds
                    'duration': int(span.duration_ms * 1000),
                    'tags': [
                        {'key': k, 'value': v, 'type': type(v).__name__}
                        for k, v in span.attributes.items()
                    ],
                    'logs': [
                        {
                            'timestamp': int(event.timestamp.timestamp() * 1_000_000),
                            'fields': [
                                {'key': k, 'value': v, 'type': type(v).__name__}
                                for k, v in event.attributes.items()
                            ]
                        }
                        for event in span.events
                    ],
                    'status': span.status.value,
                }
                if span.error:
                    jaeger_span['tags'].append({
                        'key': 'error',
                        'value': True,
                        'type': 'bool'
                    })
                    jaeger_span['logs'].append({
                        'timestamp': int(datetime.utcnow().timestamp() * 1_000_000),
                        'fields': [
                            {'key': 'message', 'value': span.error, 'type': 'str'},
                            {'key': 'event', 'value': 'error', 'type': 'str'},
                        ]
                    })
                jaeger_spans.append(jaeger_span)
            
            result.append({
                'traceID': trace_id,
                'processID': self.service_name,
                'spans': jaeger_spans,
            })
        
        return result
    
    def export_zipkin_format(self) -> List[Dict[str, Any]]:
        """Export traces in Zipkin format."""
        result = []
        for trace_id, spans in self._traces.items():
            for span in spans:
                zipkin_span = {
                    'traceId': span.trace_id,
                    'id': span.span_id,
                    'parentId': span.parent_span_id or None,
                    'name': span.name,
                    'timestamp': int(span.start_time.timestamp() * 1_000_000),
                    'duration': int(span.duration_ms * 1000),
                    'tags': {
                        'service': self.service_name,
                        'status': span.status.value,
                        **span.attributes,
                    },
                    'annotations': [
                        {
                            'timestamp': int(event.timestamp.timestamp() * 1_000_000),
                            'value': event.name,
                        }
                        for event in span.events
                    ],
                }
                result.append(zipkin_span)
        
        return result
    
    def export_json(self) -> List[Dict[str, Any]]:
        """Export traces as generic JSON."""
        result = []
        for trace_id, spans in self._traces.items():
            for span in spans:
                result.append(span.to_dict())
        return result
    
    def get_tracer_stats(self) -> Dict[str, Any]:
        """Get tracer statistics."""
        return {
            'service_name': self.service_name,
            'total_traces': len(self._traces),
            'total_spans': len(self._spans),
            'spans_created': self._stats['spans_created'],
            'spans_finished': self._stats['spans_finished'],
            'errors': self._stats['errors'],
        }


# Global tracer instance
_global_tracer: Optional[DistributedTracer] = None


def get_tracer() -> DistributedTracer:
    """Get or create global tracer."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = DistributedTracer()
    return _global_tracer


def set_tracer(tracer: DistributedTracer) -> None:
    """Set global tracer."""
    global _global_tracer
    _global_tracer = tracer
