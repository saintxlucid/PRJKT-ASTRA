"""
ASTRA Metrics Middleware
Created: October 31, 2025

Performance and observability metrics for FastAPI endpoints.
"""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from prometheus_client import Counter, Histogram, Gauge
import structlog

# Metrics
REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

RAG_RERANK_LATENCY = Histogram(
    "rag_rerank_duration_seconds",
    "Time spent reranking search results",
    buckets=(0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0)
)

RAG_RERANK_COUNT = Counter(
    "rag_rerank_total",
    "Number of RAG reranking operations",
    ["strategy"]  # mmr, cross_encoder, recency
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)

QUEUE_DEPTH = Gauge(
    "request_queue_depth",
    "Current depth of request queue"
)

QUEUE_WAIT_SECONDS = Histogram(
    "request_queue_wait_seconds",
    "Time requests spend waiting in queue"
)

logger = structlog.get_logger()

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics"""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process request with metrics collection"""
        
        # Start timing
        start_time = time.time()
        
        # Get endpoint for labels
        endpoint = request.url.path
        method = request.method
        
        try:
            # Process request
            response = await call_next(request)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            return response
            
        except Exception as e:
            # Record error metrics
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            
            duration = time.time() - start_time
            LATENCY.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            logger.error(
                "request_error",
                method=method,
                endpoint=endpoint,
                error=str(e)
            )
            raise

def metrics_endpoint() -> Callable:
    """Get metrics endpoint handler"""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    
    async def handler() -> Response:
        """Return current metrics"""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
        
    return handler