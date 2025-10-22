"""
Performance metrics for LLM operations.

This module provides Prometheus metrics for tracking LLM performance:
- Response latency (p95, p99)
- Token throughput
- Memory usage
- Cache efficiency
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

import structlog
from prometheus_client import Counter, Gauge, Histogram

logger = structlog.get_logger(__name__)

# Latency histograms with buckets optimized for typical chat latency ranges
CHAT_LATENCY = Histogram(
    "llm_chat_latency_seconds",
    "Total chat request latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0),  # Sub-second to 10s range
    labelnames=["model", "preset"]
)

PROMPT_PROCESS_TIME = Histogram(
    "llm_prompt_process_seconds", 
    "Time to process and encode prompt",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1),  # Sub-ms to 100ms range
    labelnames=["model"]
)

TOKEN_GENERATION_SPEED = Histogram(
    "llm_token_generation_speed",
    "Tokens generated per second",
    buckets=(1, 5, 10, 20, 50, 100),  # 1-100 tokens/sec
    labelnames=["model", "preset"]
)

# Memory usage gauges
MODEL_MEMORY_USAGE = Gauge(
    "llm_model_memory_bytes",
    "Memory used by model",
    labelnames=["model", "memory_type"]  # weights, kv_cache, scratch
)

REQUEST_MEMORY_USAGE = Histogram(
    "llm_request_memory_bytes",
    "Memory used per request",
    buckets=(1e6, 1e7, 1e8, 1e9),  # 1MB to 1GB range
    labelnames=["model"]
)

# Token counters
PROMPT_TOKENS = Counter(
    "llm_prompt_tokens_total",
    "Total number of prompt tokens processed",
    labelnames=["model"]
)

COMPLETION_TOKENS = Counter(
    "llm_completion_tokens_total", 
    "Total number of completion tokens generated",
    labelnames=["model"]
)

# Cache metrics
CACHE_SIZE = Gauge(
    "llm_kv_cache_size_bytes",
    "Size of KV cache in bytes",
    labelnames=["model"]
)

CACHE_HITS = Counter(
    "llm_kv_cache_hits_total",
    "Number of KV cache hits",
    labelnames=["model"]
)

CACHE_MISSES = Counter(
    "llm_kv_cache_misses_total",
    "Number of KV cache misses", 
    labelnames=["model"]
)

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    
    start_time: float
    model: str
    sampling_preset: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    prompt_process_time: float = 0.0
    peak_memory: int = 0
    finished: bool = False

    def record_prompt_processed(self, duration: float):
        """Record prompt processing time."""
        self.prompt_process_time = duration
        PROMPT_PROCESS_TIME.labels(model=self.model).observe(duration)
        PROMPT_TOKENS.labels(model=self.model).inc(self.prompt_tokens)

    def record_completion(self, duration: float, memory_used: int):
        """Record completion metrics."""
        if self.finished:
            return
            
        self.finished = True
        self.peak_memory = memory_used

        # Overall latency
        CHAT_LATENCY.labels(
            model=self.model,
            preset=self.sampling_preset
        ).observe(duration)

        # Token generation speed (tokens/sec)
        if duration > 0:
            tokens_per_sec = self.completion_tokens / duration
            TOKEN_GENERATION_SPEED.labels(
                model=self.model,
                preset=self.sampling_preset
            ).observe(tokens_per_sec)

        # Memory
        REQUEST_MEMORY_USAGE.labels(model=self.model).observe(memory_used)
        
        # Tokens
        COMPLETION_TOKENS.labels(model=self.model).inc(self.completion_tokens)

    def record_cache_hit(self, token_count: int):
        """Record KV cache hit."""
        self.cached_tokens += token_count
        CACHE_HITS.labels(model=self.model).inc()

    def record_cache_miss(self):
        """Record KV cache miss."""
        CACHE_MISSES.labels(model=self.model).inc()

    def get_summary(self) -> Dict[str, float]:
        """Get summary metrics for logging."""
        duration = time.time() - self.start_time
        return {
            "total_duration": duration,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_tokens": self.cached_tokens,
            "tokens_per_sec": self.completion_tokens / duration if duration > 0 else 0,
            "prompt_process_time": self.prompt_process_time,
            "peak_memory_mb": self.peak_memory / 1024 / 1024
        }