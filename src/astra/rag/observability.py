"""
ASTRA Multi-RAG Metrics
Prometheus metrics for monitoring RAG pipeline performance.
"""
from typing import Dict, Any, Optional
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
import structlog
from functools import wraps
import time

logger = structlog.get_logger()

# Pipeline metrics
RETRIEVAL_LATENCY = Histogram(
    "astra_rag_retrieval_latency_seconds",
    "Multi-RAG retrieval latency in seconds",
    ["stage"],  # bm25, dense, fusion, rerank
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

RETRIEVAL_HITS = Counter(
    "astra_rag_retrieval_hits_total",
    "Number of documents retrieved",
    ["category", "stage"]
)

FUSION_SCORE = Gauge(
    "astra_rag_fusion_score",
    "Cross-encoder fusion confidence score",
    ["category"]
)

ANSWER_LATENCY = Histogram(
    "astra_rag_answer_latency_seconds", 
    "Answer generation latency in seconds",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

ANSWER_TOKENS = Counter(
    "astra_rag_answer_tokens_total",
    "Number of tokens in generated answers"
)

CONTEXT_LENGTH = Histogram(
    "astra_rag_context_length_chars",
    "Length of retrieved context in characters",
    buckets=(100, 500, 1000, 2000, 5000)
)

# Memory metrics
MEMORY_CACHE_HITS = Counter(
    "astra_rag_memory_cache_hits_total",
    "Number of memory cache hits",
    ["type"]  # semantic, episodic
)

MEMORY_CACHE_MISSES = Counter(
    "astra_rag_memory_cache_misses_total", 
    "Number of memory cache misses",
    ["type"]  # semantic, episodic
)

# Track all metrics in a registry
registry = CollectorRegistry()
for metric in [
    RETRIEVAL_LATENCY, RETRIEVAL_HITS, FUSION_SCORE,
    ANSWER_LATENCY, ANSWER_TOKENS, CONTEXT_LENGTH,
    MEMORY_CACHE_HITS, MEMORY_CACHE_MISSES
]:
    registry.register(metric)

def track_retrieval(stage: str):
    """Decorator to track retrieval stage latency and hits."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            # Track latency
            RETRIEVAL_LATENCY.labels(stage=stage).observe(duration)
            
            # Track hits if result has docs
            if isinstance(result, dict) and "docs" in result:
                for doc in result["docs"]:
                    category = doc.get("category", "unknown")
                    RETRIEVAL_HITS.labels(
                        category=category,
                        stage=stage
                    ).inc()
            
            return result
        return wrapper
    return decorator

def track_memory_cache(memory_type: str):
    """Decorator to track memory cache hits/misses."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            
            # Detect cache hit/miss based on latency
            duration = time.time() - start
            if duration < 0.01:  # Cache hit threshold
                MEMORY_CACHE_HITS.labels(type=memory_type).inc()
            else:
                MEMORY_CACHE_MISSES.labels(type=memory_type).inc()
            
            return result
        return wrapper
    return decorator

def track_answer_generation():
    """Decorator to track answer generation metrics."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start
            
            # Track latency
            ANSWER_LATENCY.observe(duration)
            
            # Track answer properties
            if isinstance(result, dict):
                if "answer" in result:
                    ANSWER_TOKENS.inc(len(result["answer"].split()))
                if "context" in result:
                    CONTEXT_LENGTH.observe(len(result["context"]))
            
            return result
        return wrapper
    return decorator