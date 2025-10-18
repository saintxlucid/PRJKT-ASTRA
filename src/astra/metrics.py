"""
Prometheus Metrics Middleware

Exposes OpenMetrics-compatible endpoint with request counts, latency histograms,
and token usage tracking.

Middleware integration:
    from astra.metrics import MetricsMiddleware, metrics_endpoint
    
    app.add_middleware(MetricsMiddleware)
    app.add_route("/metrics", metrics_endpoint)

Metrics exposed:
    - astra_requests_total{method,path,status} - Request counter
    - astra_request_duration_seconds{method,path} - Latency histogram
    - astra_tokens_total{type} - Token usage (prompt/completion)
"""

from __future__ import annotations

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# Metrics definitions
REQUESTS = Counter(
    "astra_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

LATENCY = Histogram(
    "astra_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

TOKENS = Counter(
    "astra_tokens_total",
    "Total tokens processed",
    ["type"]  # prompt, completion
)

# === Capacity / queue / limiter metrics (Ops Hardening v2) ===
QUEUE_DEPTH = Gauge(
    "astra_queue_depth",
    "Current request queue depth"
)

QUEUE_WAIT_SECONDS = Histogram(
    "astra_queue_wait_seconds",
    "Time requests spend waiting in the queue",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)
)

LIMITER_PER_KEY_ALLOWED = Counter(
    "astra_limiter_per_key_allowed_total",
    "Requests allowed by per-key limiter",
    ["key_hash"]
)

LIMITER_PER_KEY_BLOCKED = Counter(
    "astra_limiter_per_key_blocked_total",
    "Requests blocked by per-key limiter",
    ["key_hash"]
)

# === Streaming metrics (Directive 002) ===
STREAM_TOKENS = Counter(
    "astra_stream_tokens_total",
    "Total tokens streamed to clients"
)

STREAM_CLIENTS = Gauge(
    "astra_stream_clients_active",
    "Number of active streaming clients"
)

STREAM_CHUNKS = Histogram(
    "astra_stream_chunk_size_bytes",
    "Size of streaming chunks in bytes",
    buckets=(10, 50, 100, 250, 500, 1000, 2000, 5000)
)

# === Cache metrics (Phase 2 enhancements) ===
CACHE_HITS = Counter(
    "astra_cache_hits_total",
    "Semantic cache hits"
)

CACHE_MISSES = Counter(
    "astra_cache_misses_total",
    "Semantic cache misses"
)

# === LLM health metrics (Phase 2 enhancements) ===
LLM_FAILURES = Counter(
    "astra_llm_failures_total",
    "LLM failures triggering circuit breaker"
)

LLM_LATENCY = Histogram(
    "astra_llm_latency_seconds",
    "LLM call latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# === Memory metrics (Phase 2 enhancements) ===
MEMORY_SEARCHES = Counter(
    "astra_memory_searches_total",
    "Memory search operations"
)

MEMORY_PRECISION = Gauge(
    "astra_memory_precision_at_k",
    "Memory search precision@k score"
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic metrics collection.
    
    Tracks:
    - Request counts by method, path, status
    - Request latency by method, path
    - Exceptions and error rates
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record metrics"""
        method = request.method
        path = request.url.path
        
        # Skip metrics endpoint itself
        if path == "/metrics":
            return await call_next(request)
        
        # Normalize path to avoid cardinality explosion
        # Replace IDs/UUIDs with placeholders
        path_normalized = self._normalize_path(path)
        
        # Start timer
        start = time.perf_counter()
        
        try:
            response = await call_next(request)
            status = response.status_code
            
            # Record metrics
            REQUESTS.labels(method=method, path=path_normalized, status=status).inc()
            LATENCY.labels(method=method, path=path_normalized).observe(time.perf_counter() - start)
            
            return response
        
        except Exception as e:
            # Record error
            REQUESTS.labels(method=method, path=path_normalized, status=500).inc()
            LATENCY.labels(method=method, path=path_normalized).observe(time.perf_counter() - start)
            
            logger.error("request_error",
                        method=method,
                        path=path,
                        error=str(e))
            raise
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path to reduce cardinality.
        
        Example: /conversations/123 -> /conversations/{id}
        """
        parts = path.split("/")
        normalized = []
        
        for part in parts:
            if not part:
                continue
            
            # Replace UUIDs and numeric IDs
            if self._looks_like_id(part):
                normalized.append("{id}")
            else:
                normalized.append(part)
        
        return "/" + "/".join(normalized) if normalized else "/"
    
    def _looks_like_id(self, s: str) -> bool:
        """Check if string looks like an ID"""
        # UUID pattern (8-4-4-4-12 hex)
        if len(s) == 36 and s.count("-") == 4:
            return True
        
        # Numeric ID
        if s.isdigit():
            return True
        
        # MongoDB ObjectId (24 hex chars)
        if len(s) == 24 and all(c in "0123456789abcdef" for c in s.lower()):
            return True
        
        return False


def track_tokens(prompt_tokens: int = 0, completion_tokens: int = 0):
    """
    Track token usage.
    
    Args:
        prompt_tokens: Number of prompt tokens
        completion_tokens: Number of completion tokens
    """
    if prompt_tokens > 0:
        TOKENS.labels(type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        TOKENS.labels(type="completion").inc(completion_tokens)


async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus metrics endpoint handler.
    
    Returns OpenMetrics-compatible text format.
    
    Usage:
        app.add_route("/metrics", metrics_endpoint)
    """
    # Generate metrics in Prometheus text format
    metrics_output = generate_latest()
    
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# Example usage in FastAPI app:
"""
from fastapi import FastAPI
from astra.metrics import MetricsMiddleware, metrics_endpoint

app = FastAPI()

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Expose metrics endpoint
app.add_route("/metrics", metrics_endpoint)

# Use in LLM service:
from astra.metrics import track_tokens

async def generate_completion(...):
    result = await llm.complete(...)
    track_tokens(
        prompt_tokens=result.usage.prompt_tokens,
        completion_tokens=result.usage.completion_tokens
    )
    return result
"""
