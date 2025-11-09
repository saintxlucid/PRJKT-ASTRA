"""
ASTRA Circuit Breakers
Created: October 31, 2025

Circuit breaker pattern implementation for graceful failure handling.
"""
from typing import Optional, Callable, Any
import time
import asyncio
from contextlib import contextmanager
from prometheus_client import Counter, Gauge

# Metrics
CIRCUIT_BREAKS = Counter(
    "astra_circuit_breaks_total",
    "Number of times circuit breaker has tripped",
    ["breaker"]
)
CIRCUIT_STATE = Gauge(
    "astra_circuit_state",
    "Current state of circuit breaker (0=open, 1=closed)",
    ["breaker"]
)

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass

class CircuitBreaker:
    """Circuit breaker for protecting external service calls"""
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        callback: Optional[Callable] = None
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.callback = callback
        
        self.failures = 0
        self.last_failure = 0
        self.open = False
        
        # Initialize metrics
        CIRCUIT_STATE.labels(breaker=name).set(1)
    
    def record_failure(self):
        """Record a failure and check if circuit should open"""
        self.failures += 1
        self.last_failure = time.time()
        
        if self.failures >= self.failure_threshold:
            self.open = True
            CIRCUIT_BREAKS.labels(breaker=self.name).inc()
            CIRCUIT_STATE.labels(breaker=self.name).set(0)
            
            if self.callback:
                asyncio.create_task(self.callback())
    
    def check_reset(self):
        """Check if enough time has passed to try resetting circuit"""
        if not self.open:
            return True
            
        if time.time() - self.last_failure >= self.reset_timeout:
            self.failures = 0
            self.open = False
            CIRCUIT_STATE.labels(breaker=self.name).set(1)
            return True
            
        return False
    
    @contextmanager
    def __call__(self, fallback: Optional[Callable] = None):
        """Context manager for protected calls"""
        if not self.check_reset():
            if fallback:
                yield fallback()
            else:
                raise CircuitBreakerError(
                    f"Circuit {self.name} is open"
                )
        
        try:
            yield
        except Exception as e:
            self.record_failure()
            raise e