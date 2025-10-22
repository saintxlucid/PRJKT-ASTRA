"""
Async timer context manager for Prometheus metrics.
"""

import time
import asyncio
from types import TracebackType
from typing import Optional, Type
from prometheus_client import Histogram

class AsyncTimer:
    """Async context manager for timing operations."""
    
    def __init__(self, histogram: Histogram, labels: dict):
        """Initialize timer.
        
        Args:
            histogram: Prometheus histogram to record timing
            labels: Labels to apply to the metric
        """
        self.histogram = histogram
        self.labels = labels
        self.start_time = None
        
    async def __aenter__(self) -> None:
        """Start timing."""
        self.start_time = time.time()
        
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ) -> None:
        """Record elapsed time."""
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.histogram.labels(**self.labels).observe(duration)