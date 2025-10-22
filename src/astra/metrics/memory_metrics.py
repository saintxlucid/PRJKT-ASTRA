"""
Performance metrics for memory operations.

This module provides Prometheus metrics for tracking memory performance:
- Context building latency 
- Memory retrieval stats
- Token counts
- Identity generation timing
- Memory subsystem metrics

Created: October 30, 2025
Project: ASTRA v2.0
"""

from dataclasses import dataclass
from typing import Dict, Optional

import structlog
from prometheus_client import Counter, Gauge, Histogram, Summary

logger = structlog.get_logger(__name__)

# Context building metrics
CONTEXT_BUILD_TIME = Histogram(
    "astra_memory_context_build_seconds",
    "Time to build conversation context",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
    labelnames=["include_memory"]
)

MEMORY_SEARCH_TIME = Histogram(
    "astra_memory_search_latency_seconds", 
    "Memory search operation latency",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
    labelnames=["memory_type"]  # semantic, episodic, procedural
)

IDENTITY_GEN_TIME = Histogram(
    "astra_identity_generation_seconds",
    "Identity prompt generation time",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
    labelnames=["has_memory"]
)

# Memory operation stats
MEMORY_RETRIEVAL_COUNT = Counter(
    "astra_memory_retrieval_total",
    "Number of memories retrieved",
    labelnames=["memory_type"]
)

MEMORY_STORAGE_COUNT = Counter(
    "astra_memory_storage_total",
    "Number of memories stored",
    labelnames=["memory_type"]
)

MEMORY_ERRORS = Counter(
    "astra_memory_errors_total",
    "Number of memory operation errors",
    labelnames=["operation", "error_type"]
)

# Token counting metrics
CONTEXT_TOKEN_COUNT = Histogram(
    "astra_context_tokens_total",
    "Number of tokens in context components",
    buckets=(50, 100, 200, 500, 1000, 2000, 5000),
    labelnames=["component"]  # system, memory, total
)

# Performance metrics
MEMORY_LOAD = Gauge(
    "astra_memory_load",
    "Current memory subsystem load",
    labelnames=["memory_type"]
)

MEMORY_LATENCY = Summary(
    "astra_memory_latency_seconds",
    "Memory operation latency summary",
    labelnames=["operation"],
    quantiles=(0.5, 0.9, 0.95, 0.99)
)

@dataclass
class MemoryMetrics:
    """Metrics for memory operations."""
    
    def record_context_build(self, duration: float, include_memory: bool):
        """Record context building time."""
        CONTEXT_BUILD_TIME.labels(
            include_memory=str(include_memory)
        ).observe(duration)
        MEMORY_LATENCY.labels(
            operation="context_build"
        ).observe(duration)

    def record_memory_search(self, duration: float, memory_type: str):
        """Record memory search time."""
        MEMORY_SEARCH_TIME.labels(
            memory_type=memory_type
        ).observe(duration)
        MEMORY_LATENCY.labels(
            operation="search"
        ).observe(duration)

    def record_memory_retrieval(self, memory_type: str, count: int):
        """Record memory retrieval count."""
        MEMORY_RETRIEVAL_COUNT.labels(
            memory_type=memory_type
        ).inc(count)
        # Update load gauge
        MEMORY_LOAD.labels(memory_type=memory_type).set(count)

    def record_memory_storage(self, memory_type: str):
        """Record memory storage operation."""
        MEMORY_STORAGE_COUNT.labels(
            memory_type=memory_type
        ).inc()

    def record_memory_error(self, operation: str, error_type: str):
        """Record memory operation error."""
        MEMORY_ERRORS.labels(
            operation=operation,
            error_type=error_type
        ).inc()

    def record_context_tokens(self, component: str, token_count: int):
        """Record token count for context component."""
        CONTEXT_TOKEN_COUNT.labels(
            component=component
        ).observe(token_count)

    def record_identity_gen(self, duration: float, has_memory: bool = False):
        """Record identity generation time."""
        IDENTITY_GEN_TIME.labels(
            has_memory=str(has_memory)
        ).observe(duration)
        MEMORY_LATENCY.labels(
            operation="identity"
        ).observe(duration)