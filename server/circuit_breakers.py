"""
Circuit breaker pattern implementation with health integration
"""
from typing import Optional, Callable, Awaitable, Any, AsyncContextManager
from datetime import datetime, timedelta
from contextlib import AbstractAsyncContextManager
import asyncio
import logging
from enum import Enum
import time
import statistics

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, reject fast
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker(AbstractAsyncContextManager):
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_limit: int = 3,
        reset_timeout: float = 60.0,
        latency_threshold: float = 1000.0  # ms
    ):
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_limit = half_open_limit
        self.reset_timeout = reset_timeout
        self.latency_threshold = latency_threshold
        self.last_failure_time: Optional[datetime] = None
        self.half_open_successes = 0
        self.trip_time: Optional[datetime] = None
        self._lock = asyncio.Lock()
        self._latencies: list[float] = []
        self._start_time: Optional[float] = None

    def _update_health(self, status: str = "healthy", error: Optional[str] = None) -> None:
        """Update component health status"""
        # Lazy import to avoid circular dependency
        from server.health import health_manager
        
        # Calculate latency stats if we have data
        latency_ms = None
        if self._latencies:
            latency_ms = statistics.mean(self._latencies[-100:])  # Use last 100 samples
            
        # Only mark as degraded/failed if we're not already recovering
        if self.state != CircuitState.HALF_OPEN:
            if status == "healthy" and latency_ms and latency_ms > self.latency_threshold:
                status = "degraded"
                error = f"High latency: {latency_ms:.2f}ms > {self.latency_threshold}ms"
                
        try:
            health_manager.update_component(
                name=self.name,
                status=status,
                error=error,
                latency=latency_ms
            )
        except Exception as e:
            logger.error(f"Failed to update health status: {e}")

    async def __aenter__(self) -> 'CircuitBreaker':
        """Enter the async context manager"""
        await self._lock.acquire()
        try:
            self._start_time = time.time()
            
            if self.state == CircuitState.OPEN:
                if self.trip_time and datetime.now() - self.trip_time > timedelta(seconds=self.recovery_timeout):
                    logger.info(f"Circuit {self.name} entering half-open state")
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_successes = 0
                    self._update_health(status="degraded", error="Circuit in recovery")
                else:
                    self._update_health(status="failed", error="Circuit is open")
                    raise CircuitBreakerOpen(f"Circuit {self.name} is open")
            return self
        except:
            self._lock.release()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        """Exit the async context manager"""
        try:
            # Track latency
            if self._start_time:
                latency = (time.time() - self._start_time) * 1000  # Convert to ms
                self._latencies.append(latency)
                # Keep only last 1000 samples
                if len(self._latencies) > 1000:
                    self._latencies = self._latencies[-1000:]
            
            if exc_type is not None:
                self.record_failure(error=str(exc_val) if exc_val else None)
                self._update_health(
                    status="failed",
                    error=f"Circuit error: {str(exc_val) if exc_val else 'Unknown error'}"
                )
            elif self.state == CircuitState.HALF_OPEN:
                self.half_open_successes += 1
                if self.half_open_successes >= self.half_open_limit:
                    logger.info(f"Circuit {self.name} closing - recovered")
                    self.reset()
                    self._update_health(status="healthy")
                else:
                    self._update_health(
                        status="degraded",
                        error=f"Circuit in recovery ({self.half_open_successes}/{self.half_open_limit} successes)"
                    )
            else:
                self._update_health(status="healthy")
                
            return None  # Let exceptions propagate
        finally:
            self._lock.release()

    async def __call__(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs
    ) -> Any:
        """Execute function with circuit breaker pattern"""
        async with self:
            return await func(*args, **kwargs)
            
    def record_failure(self, error: Optional[str] = None):
        """Record a failure and potentially open the circuit"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit {self.name} tripped after {self.failure_count} failures")
            self.trip()
            self._update_health(
                status="failed",
                error=f"Circuit tripped: {error if error else 'Threshold exceeded'}"
            )
            
        elif self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit {self.name} re-opened after half-open failure")
            self.trip()
            self._update_health(
                status="failed",
                error=f"Circuit re-opened during recovery: {error if error else 'Recovery failed'}"
            )
    
    def trip(self):
        """Open the circuit"""
        self.state = CircuitState.OPEN
        self.trip_time = datetime.now()
        self._update_health(
            status="failed",
            error=f"Circuit open after {self.failure_count} failures"
        )
        
    def reset(self):
        """Reset the circuit to closed state"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.trip_time = None
        self.half_open_successes = 0
        
        # Clear latency history on reset
        self._latencies = []
        self._start_time = None
        
        if old_state != CircuitState.CLOSED:
            self._update_health(
                status="healthy",
                error=None
            )

class CircuitBreakerOpen(Exception):
    """Exception raised when circuit is open"""
    pass

# Circuit breaker instances with latency thresholds
memory_circuit = CircuitBreaker(
    name="memory",
    failure_threshold=5,
    recovery_timeout=30.0,
    latency_threshold=200.0  # 200ms max for memory ops
)

inference_circuit = CircuitBreaker(
    name="inference",
    failure_threshold=3,
    recovery_timeout=45.0,
    latency_threshold=1000.0  # 1s max for inference
)