"""
ASTRA Backpressure
Created: October 31, 2025

Backpressure and request shedding for maintaining service health.
"""
import time
import asyncio
from typing import Optional
from collections import deque
from dataclasses import dataclass
from prometheus_client import Gauge, Histogram
from fastapi import HTTPException

# Metrics
QUEUE_DEPTH = Gauge(
    "astra_queue_depth",
    "Current request queue depth"
)
LATENCY_SLO = Histogram(
    "astra_latency_slo_ratio",
    "Ratio of actual latency to SLO threshold",
    buckets=[0.25, 0.5, 0.75, 0.9, 1.0, 1.5, 2.0]
)

@dataclass
class RequestTracker:
    """Tracks timing for a single request"""
    start_time: float
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time

class QueueDepthGuard:
    """Guards against queue overload"""
    
    def __init__(self, max_depth: int = 100):
        self.max_depth = max_depth
        self.current_depth = 0
        
        # Initialize metrics
        QUEUE_DEPTH.set(0)
    
    def can_accept(self) -> bool:
        """Check if new request can be accepted"""
        if self.current_depth >= self.max_depth:
            return False
            
        self.current_depth += 1
        QUEUE_DEPTH.set(self.current_depth)
        return True
    
    def complete_request(self):
        """Mark request as complete"""
        self.current_depth = max(0, self.current_depth - 1)
        QUEUE_DEPTH.set(self.current_depth)

class Backpressure:
    """Provides token-based rate limiting"""

    def __init__(self, tokens: int = 100):
        self.max_tokens = tokens
        self.available_tokens = tokens
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token or raise if none available"""
        async with self.lock:
            if self.available_tokens <= 0:
                raise HTTPException(
                    status_code=503,
                    detail="Service temporarily unavailable"
                )
            self.available_tokens -= 1

    async def release(self):
        """Return a token to the pool"""
        async with self.lock:
            self.available_tokens = min(
                self.available_tokens + 1,
                self.max_tokens
            )
            
    async def queue_size(self) -> int:
        """Get current number of requests in queue"""
        return self.max_tokens - self.available_tokens
        
    async def shutdown(self):
        """Cleanup on shutdown"""
        # Reset metrics
        QUEUE_DEPTH.set(0)
        # Clear any pending tokens
        async with self.lock:
            self.available_tokens = self.max_tokens

class LatencyTracker:
    """Tracks request latencies for adaptive shedding"""
    
    def __init__(
        self,
        slo_threshold: float,
        window_size: int = 100
    ):
        self.slo_threshold = slo_threshold
        self.latencies = deque(maxlen=window_size)
    
    def start_request(self) -> RequestTracker:
        """Start tracking a new request"""
        return RequestTracker(start_time=time.time())
    
    def record_latency(self, latency: float):
        """Record completed request latency"""
        self.latencies.append(latency)
        
        # Record SLO ratio
        LATENCY_SLO.observe(latency / self.slo_threshold)
    
    @property
    def p95_latency(self) -> Optional[float]:
        """Get 95th percentile latency"""
        if not self.latencies:
            return None
            
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[idx]
    
    def should_shed(self) -> bool:
        """Check if requests should be shed based on latency"""
        p95 = self.p95_latency
        if p95 is None:
            return False
            
        return p95 >= self.slo_threshold