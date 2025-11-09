"""
ASTRA Observability Stack - OpenTelemetry + Prometheus
=======================================================

Structured logging, distributed tracing, metrics collection.

Author: ASTRA Infra Team
Created: 2025-11-03
"""

import time
from contextlib import contextmanager
from functools import wraps

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Gauge, Histogram, start_http_server


# ============================================================================
# TRACER SETUP
# ============================================================================

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Add console exporter for development
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)


# ============================================================================
# PROMETHEUS METRICS
# ============================================================================

# Model request metrics
model_requests_total = Counter(
    'astra_model_requests_total',
    'Total number of model requests',
    ['model', 'provider', 'status']
)

model_latency_seconds = Histogram(
    'astra_model_latency_seconds',
    'Model request latency in seconds',
    ['model', 'provider'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

model_tokens_total = Counter(
    'astra_model_tokens_total',
    'Total tokens processed',
    ['model', 'provider', 'token_type']  # token_type: input/output
)

model_token_efficiency = Histogram(
    'astra_model_token_efficiency',
    'Output tokens / Input tokens ratio',
    ['model', 'provider'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Model failures
model_failures_total = Counter(
    'astra_model_failures_total',
    'Total model failures',
    ['model', 'provider', 'error_type']
)

model_fallback_total = Counter(
    'astra_model_fallback_total',
    'Total fallback activations',
    ['from_model', 'to_model', 'reason']
)

# Resource metrics
model_vram_used_gb = Gauge(
    'astra_model_vram_used_gb',
    'VRAM used in gigabytes',
    ['model']
)

model_queue_depth = Gauge(
    'astra_model_queue_depth',
    'Request queue depth',
    ['model']
)

# Cache metrics
cache_hits_total = Counter(
    'astra_cache_hits_total',
    'Total cache hits',
    ['cache_type']  # kv_cache/prefix_cache/response_cache
)

cache_misses_total = Counter(
    'astra_cache_misses_total',
    'Total cache misses',
    ['cache_type']
)

# Routing metrics
routing_decisions_total = Counter(
    'astra_routing_decisions_total',
    'Total routing decisions',
    ['policy', 'model', 'complexity']
)

# Soul layer metrics
soul_alignment_checks_total = Counter(
    'astra_soul_alignment_checks_total',
    'Total soul alignment checks',
    ['result']  # aligned/grey/misaligned
)

soul_anti_patterns_detected = Counter(
    'astra_soul_anti_patterns_detected',
    'Anti-patterns detected',
    ['pattern']
)

soul_celebrations_total = Counter(
    'astra_soul_celebrations_total',
    'Positive patterns celebrated',
    ['pattern']
)


# ============================================================================
# METRICS HELPERS
# ============================================================================

def record_model_request(model: str, provider: str, latency: float, tokens_in: int, tokens_out: int, status: str = "success"):
    """Record comprehensive model request metrics."""
    model_requests_total.labels(model=model, provider=provider, status=status).inc()
    model_latency_seconds.labels(model=model, provider=provider).observe(latency)
    model_tokens_total.labels(model=model, provider=provider, token_type="input").inc(tokens_in)
    model_tokens_total.labels(model=model, provider=provider, token_type="output").inc(tokens_out)

    if tokens_in > 0:
        efficiency = tokens_out / tokens_in
        model_token_efficiency.labels(model=model, provider=provider).observe(efficiency)


def record_model_failure(model: str, provider: str, error_type: str):
    """Record model failure."""
    model_failures_total.labels(model=model, provider=provider, error_type=error_type).inc()


def record_fallback(from_model: str, to_model: str, reason: str):
    """Record model fallback."""
    model_fallback_total.labels(from_model=from_model, to_model=to_model, reason=reason).inc()


def record_routing_decision(policy: str, model: str, complexity: float):
    """Record routing decision."""
    complexity_bucket = "low" if complexity < 0.3 else "medium" if complexity < 0.7 else "high"
    routing_decisions_total.labels(policy=policy, model=model, complexity=complexity_bucket).inc()


def record_soul_check(result: str):
    """Record soul alignment check."""
    soul_alignment_checks_total.labels(result=result).inc()


def record_anti_pattern(pattern: str):
    """Record anti-pattern detection."""
    soul_anti_patterns_detected.labels(pattern=pattern).inc()


def record_celebration(pattern: str):
    """Record positive pattern."""
    soul_celebrations_total.labels(pattern=pattern).inc()


def update_vram(model: str, vram_gb: float):
    """Update VRAM gauge."""
    model_vram_used_gb.labels(model=model).set(vram_gb)


def update_queue_depth(model: str, depth: int):
    """Update queue depth gauge."""
    model_queue_depth.labels(model=model).set(depth)


def record_cache_hit(cache_type: str):
    """Record cache hit."""
    cache_hits_total.labels(cache_type=cache_type).inc()


def record_cache_miss(cache_type: str):
    """Record cache miss."""
    cache_misses_total.labels(cache_type=cache_type).inc()


# ============================================================================
# TRACING DECORATORS
# ============================================================================

def traced(span_name: str | None = None):
    """
    Decorator to automatically trace function execution.

    Usage:
        @traced("generate_completion")
        async def generate(request):
            ...
    """
    def decorator(func):
        nonlocal span_name
        if span_name is None:
            span_name = func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name):
                return func(*args, **kwargs)

        # Return appropriate wrapper
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def trace_span(span_name: str, attributes: dict[str, str] | None = None):
    """
    Context manager for manual span creation.

    Usage:
        with trace_span("route_request", {"model": "phi-4"}):
            result = await route()
    """
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield span


@contextmanager
def measure_latency(metric: Histogram, labels: dict[str, str]):
    """
    Context manager to measure and record latency.

    Usage:
        with measure_latency(model_latency_seconds, {"model": "phi-4", "provider": "vllm"}):
            result = await generate()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        latency = time.perf_counter() - start
        metric.labels(**labels).observe(latency)


# ============================================================================
# METRICS SERVER
# ============================================================================

def start_metrics_server(port: int = 9090):
    """
    Start Prometheus metrics HTTP server.

    Args:
        port: Port to expose metrics on (default: 9090)
    """
    start_http_server(port)
    print(f"📊 Metrics server started on http://localhost:{port}/metrics")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Tracer
    "tracer",
    "traced",
    "trace_span",

    # Metrics
    "record_model_request",
    "record_model_failure",
    "record_fallback",
    "record_routing_decision",
    "record_soul_check",
    "record_anti_pattern",
    "record_celebration",
    "update_vram",
    "update_queue_depth",
    "record_cache_hit",
    "record_cache_miss",

    # Helpers
    "measure_latency",
    "start_metrics_server",

    # Raw metrics (for custom usage)
    "model_requests_total",
    "model_latency_seconds",
    "model_tokens_total",
    "model_token_efficiency",
    "model_failures_total",
    "model_fallback_total",
]
