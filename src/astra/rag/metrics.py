"""
Runtime metrics for RAG system monitoring.

Provides:
- Memory retrieval latency tracking
- Token usage monitoring
- Cache performance metrics
- Response time tracking
"""
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger(__name__)

# Memory metrics
MEMORY_RETRIEVAL_LATENCY = Histogram(
    "rag_memory_retrieval_seconds",
    "Memory retrieval latency in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

MEMORY_CACHE_HITS = Counter(
    "rag_memory_cache_hits_total",
    "Number of memory cache hits",
)

MEMORY_CACHE_MISSES = Counter(
    "rag_memory_cache_misses_total", 
    "Number of memory cache misses",
)

MEMORY_COUNT = Histogram(
    "rag_memory_count",
    "Number of memories retrieved per query",
    buckets=(1, 2, 4, 8, 16, 32),
)

# Token metrics 
TOKEN_USAGE = Counter(
    "rag_token_usage_total",
    "Total tokens used",
    ["stage"]  # prompt, context, completion
)

TOKEN_BUDGET_USAGE = Histogram(
    "rag_token_budget_percent",
    "Token budget utilization percentage",
    buckets=(10, 25, 50, 75, 90, 95, 98, 100),
)

MEMORY_TOKENS = Histogram(
    "rag_memory_tokens",
    "Tokens per memory chunk",
    buckets=(32, 64, 128, 256, 512, 1024),
)

# Response metrics
FIRST_TOKEN_LATENCY = Histogram(
    "rag_first_token_seconds", 
    "Time to first token in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

TOTAL_LATENCY = Histogram(
    "rag_total_latency_seconds",
    "Total response latency in seconds",
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
)

TOKENS_PER_SECOND = Histogram(
    "rag_tokens_per_second",
    "Token generation rate",
    buckets=(1, 2, 5, 10, 20, 50),
)

# Health metrics
MEMORY_ENGINE_UP = Gauge(
    "rag_memory_engine_up",
    "Memory engine availability status",
)

INFERENCE_QUEUE_SIZE = Gauge(
    "rag_inference_queue_size", 
    "Current size of inference queue",
)

# Error metrics
ERROR_COUNT = Counter(
    "rag_errors_total",
    "Total error count",
    ["type"],  # retrieval, inference, streaming
)