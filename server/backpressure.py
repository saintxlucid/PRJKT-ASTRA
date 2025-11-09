"""
Backpressure handling and request throttling
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class RequestStats:
    """Request statistics for backpressure monitoring"""
    total_requests: int = 0
    active_requests: int = 0
    queue_depth: int = 0
    avg_latency: float = 0.0
    peak_queue_depth: int = 0
    last_throttle: Optional[datetime] = None

class BackpressureManager:
    def __init__(
        self,
        max_concurrent: int = 100,
        max_queue_depth: int = 50,
        latency_threshold: float = 2.0,
        throttle_period: float = 60.0,
        sample_window: int = 100
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_depth = max_queue_depth
        self.latency_threshold = latency_threshold
        self.throttle_period = throttle_period
        self.sample_window = sample_window
        
        # Request tracking
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = RequestStats()
        self.latencies: list[float] = []
        
    async def acquire(self) -> bool:
        """Try to acquire a request slot"""
        if self.stats.queue_depth >= self.max_queue_depth:
            # Queue full, reject immediately
            return False
            
        self.stats.queue_depth += 1
        self.stats.peak_queue_depth = max(
            self.stats.peak_queue_depth,
            self.stats.queue_depth
        )
        
        try:
            await asyncio.wait_for(
                self.semaphore.acquire(),
                timeout=self.latency_threshold
            )
            self.stats.active_requests += 1
            self.stats.queue_depth -= 1
            return True
            
        except asyncio.TimeoutError:
            self.stats.queue_depth -= 1
            return False
            
    def release(self, latency: float):
        """Release a request slot and record metrics"""
        self.stats.active_requests -= 1
        self.stats.total_requests += 1
        
        # Update running latency average
        self.latencies.append(latency)
        if len(self.latencies) > self.sample_window:
            self.latencies.pop(0)
        self.stats.avg_latency = sum(self.latencies) / len(self.latencies)
        
        self.semaphore.release()
        
    def should_throttle(self) -> bool:
        """Check if we should start throttling"""
        if self.stats.last_throttle:
            if datetime.now() - self.stats.last_throttle < timedelta(seconds=self.throttle_period):
                return True
                
        high_latency = self.stats.avg_latency > self.latency_threshold
        high_queue = self.stats.queue_depth > self.max_queue_depth * 0.8
        
        if high_latency or high_queue:
            self.stats.last_throttle = datetime.now()
            return True
            
        return False
        
    def get_stats(self) -> Dict[str, Any]:
        """Get current backpressure stats"""
        return {
            "total_requests": self.stats.total_requests,
            "active_requests": self.stats.active_requests,
            "queue_depth": self.stats.queue_depth,
            "peak_queue_depth": self.stats.peak_queue_depth,
            "avg_latency": self.stats.avg_latency,
            "is_throttling": self.should_throttle()
        }

# Global backpressure manager instance
backpressure = BackpressureManager()

async def handle_request(func, *args, **kwargs):
    """Wrapper for handling backpressure on requests"""
    if backpressure.should_throttle():
        raise ThrottleError("Service is currently throttling requests")
        
    if not await backpressure.acquire():
        raise QueueFullError("Request queue is full")
        
    start_time = time.time()
    try:
        result = await func(*args, **kwargs)
        return result
    finally:
        latency = time.time() - start_time
        backpressure.release(latency)

class ThrottleError(Exception):
    """Raised when service is throttling"""
    pass

class QueueFullError(Exception):
    """Raised when request queue is full"""
    pass