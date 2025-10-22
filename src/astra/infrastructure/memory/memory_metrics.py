"""
Memory operation metrics and tracking.

Created: October 30, 2025
Project: ASTRA v2.0
"""
from dataclasses import dataclass, field
from typing import Dict, Optional
import time

import structlog
from prometheus_client import Counter, Histogram, Gauge

logger = structlog.get_logger(__name__)

# Search performance metrics
MEMORY_SEARCH_LATENCY = Histogram(
    "astra_memory_search_seconds",
    "Memory search operation latency",
    labelnames=["memory_type"],  # semantic, episodic, procedural 
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5)
)

MEMORY_RESULTS_COUNT = Counter(
    "astra_memory_search_results_total",
    "Number of memory search results returned",
    labelnames=["memory_type"]
)

MEMORY_SEARCH_ERRORS = Counter(
    "astra_memory_search_errors_total", 
    "Number of memory search errors",
    labelnames=["memory_type", "error_type"]
)

# Token tracking metrics
MEMORY_RESULT_TOKENS = Histogram(
    "astra_memory_result_tokens",
    "Number of tokens in memory search results",
    labelnames=["memory_type"],
    buckets=(50, 100, 200, 500, 1000, 2000, 5000)
)

@dataclass 
class MemoryMetrics:
    """Tracks memory operation metrics."""

    def track_search_latency(self, memory_type: str, duration_seconds: float) -> None:
        """Record search operation latency."""
        MEMORY_SEARCH_LATENCY.labels(
            memory_type=memory_type
        ).observe(duration_seconds)

    def track_result_count(self, memory_type: str, count: int) -> None:
        """Record number of results returned."""
        MEMORY_RESULTS_COUNT.labels(
            memory_type=memory_type
        ).inc(count)

    def track_search_error(self, memory_type: str, error_type: str) -> None:
        """Record search errors by type."""
        MEMORY_SEARCH_ERRORS.labels(
            memory_type=memory_type,
            error_type=error_type
        ).inc()

    def track_result_tokens(self, memory_type: str, token_count: int) -> None:
        """Record token count of results."""
        MEMORY_RESULT_TOKENS.labels(
            memory_type=memory_type
        ).observe(token_count)

    @staticmethod
    def track_operation_time(func):
        """Decorator to track operation timing."""
        async def wrapper(self, *args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = await func(self, *args, **kwargs)
                duration = time.perf_counter() - start_time
                self.metrics.track_search_latency(
                    kwargs.get("memory_type", "all"),
                    duration
                )
                return result
            except Exception as e:
                error_type = e.__class__.__name__
                self.metrics.track_search_error(
                    kwargs.get("memory_type", "all"),
                    error_type
                )
                raise
        return wrapper