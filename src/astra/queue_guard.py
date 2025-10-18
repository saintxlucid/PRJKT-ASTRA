"""
Concurrency limiter middleware for burst load protection.

This middleware caps the number of concurrent requests and implements
a request queue to prevent server crashes under high load. When the
queue is full, it returns 503 Service Unavailable with Retry-After header.

Emits metrics for queue depth and wait time for capacity planning.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from astra.utils.logging import get_logger

logger = get_logger(__name__)

# Configuration from environment
MAX_INFLIGHT = int(os.getenv("ASTRA_MAX_INFLIGHT", "32"))
MAX_QUEUE = int(os.getenv("ASTRA_MAX_QUEUE", "64"))


class ConcurrencyLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to limit concurrent requests and queue overflows.
    
    This implements a semaphore-based concurrency limiter with a request queue.
    When the system is at capacity, new requests are queued. If the queue is full,
    requests are rejected with 503 status and Retry-After header.
    
    Features:
    - Limits concurrent in-flight requests (ASTRA_MAX_INFLIGHT)
    - Queues excess requests up to a limit (ASTRA_MAX_QUEUE)
    - Returns 503 with Retry-After when saturated
    - Adds x-queue-time header showing time spent in queue
    
    Environment Variables:
        ASTRA_MAX_INFLIGHT: Maximum concurrent requests (default: 32)
        ASTRA_MAX_QUEUE: Maximum queued requests (default: 64)
    """

    def __init__(self, app):
        """Initialize the concurrency limiter middleware."""
        super().__init__(app)
        self.semaphore = asyncio.Semaphore(MAX_INFLIGHT)
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=MAX_QUEUE)
        self.rejected_count = 0
        self.total_requests = 0
        
        logger.info(
            "concurrency_limiter_initialized",
            max_inflight=MAX_INFLIGHT,
            max_queue=MAX_QUEUE,
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with concurrency limiting.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with x-queue-time header or 503 if saturated
        """
        path = request.url.path
        if path in {"/v1/system/health", "/metrics"}:
            return await call_next(request)

        self.total_requests += 1
        enqueue_time = time.perf_counter()
        
        # Import metrics here to avoid circular dependency
        from astra.metrics import QUEUE_DEPTH, QUEUE_WAIT_SECONDS
        
        # Update queue depth metric
        QUEUE_DEPTH.set(self.queue.qsize())
        
        # Try to add request to queue
        try:
            self.queue.put_nowait(None)
        except asyncio.QueueFull:
            # Queue is full - reject with 503
            self.rejected_count += 1
            logger.warning(
                "request_rejected_queue_full",
                rejected_count=self.rejected_count,
                total_requests=self.total_requests,
                rejection_rate=f"{100 * self.rejected_count / self.total_requests:.2f}%",
            )
            return Response(
                content="Server busy - too many requests. Please retry.",
                status_code=503,
                headers={
                    "Retry-After": "1",
                    "X-Rejection-Reason": "Queue full",
                },
            )
        
        # Wait for semaphore (limit concurrent processing)
        async with self.semaphore:
            # Remove from queue, start processing
            _ = self.queue.get_nowait()
            self.queue.task_done()
            
            processing_start = time.perf_counter()
            queue_time = processing_start - enqueue_time
            
            # Record queue wait time
            QUEUE_WAIT_SECONDS.observe(queue_time)
            
            # Process request
            try:
                response = await call_next(request)
                
                # Add queue time header
                response.headers["X-Queue-Time"] = f"{queue_time:.3f}"
                
                # Update queue depth after processing
                QUEUE_DEPTH.set(self.queue.qsize())
                
                # Log slow queue times
                if queue_time > 1.0:
                    logger.warning(
                        "high_queue_time",
                        queue_time_seconds=queue_time,
                        path=request.url.path,
                    )
                
                return response
                
            except Exception as e:
                logger.error(
                    "request_processing_error",
                    error=str(e),
                    path=request.url.path,
                    queue_time_seconds=queue_time,
                )
                raise

    def get_stats(self) -> dict:
        """
        Get concurrency limiter statistics.
        
        Returns:
            Dictionary with current stats
        """
        return {
            "max_inflight": MAX_INFLIGHT,
            "max_queue": MAX_QUEUE,
            "queue_size": self.queue.qsize(),
            "available_slots": self.semaphore._value,
            "total_requests": self.total_requests,
            "rejected_count": self.rejected_count,
            "rejection_rate": (
                f"{100 * self.rejected_count / self.total_requests:.2f}%"
                if self.total_requests > 0
                else "0.00%"
            ),
        }
