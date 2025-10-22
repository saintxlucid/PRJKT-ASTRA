"""
Core resilience patterns including retry and circuit breaker.
"""
import time
import functools
import threading
import structlog
from typing import Optional, Any, Callable, Tuple, Type, Union

logger = structlog.get_logger()

def retry(
    times: int = 3,
    backoff_s: float = 0.2,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        times: Maximum number of retry attempts
        backoff_s: Initial backoff time in seconds
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_error = e
                    
                    # Don't sleep on last attempt
                    if attempt < times - 1:
                        delay = backoff_s * (2 ** attempt)
                        logger.warning("retry_attempt",
                                     fn=fn.__name__,
                                     attempt=attempt + 1,
                                     delay=delay,
                                     error=str(e))
                        time.sleep(delay)
                        
            logger.error("retry_exhausted",
                        fn=fn.__name__,
                        attempts=times,
                        error=str(last_error))
            raise last_error
            
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Tracks failures and temporarily prevents execution when threshold is exceeded.
    """
    
    def __init__(
        self,
        name: str,
        fail_threshold: int = 5,
        reset_after: float = 10.0
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Name for this circuit breaker
            fail_threshold: Number of failures before opening circuit
            reset_after: Seconds to wait before attempting reset
        """
        self.name = name
        self.fail_threshold = fail_threshold
        self.reset_after = reset_after
        
        self.failures = 0
        self.open_until = 0.0
        self.lock = threading.Lock()
        self.success_count = 0
        self.total_count = 0
        
        logger.info("circuit_breaker_initialized",
                   name=name,
                   fail_threshold=fail_threshold,
                   reset_after=reset_after)
    
    def __call__(self, fn: Callable) -> Callable:
        """Decorator interface."""
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return self.call(fn, *args, **kwargs)
        return wrapper
    
    def call(self, fn: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            fn: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result if successful
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If call fails
        """
        self.total_count += 1
        
        # Check if circuit is open
        with self.lock:
            if time.time() < self.open_until:
                logger.warning("circuit_open",
                             name=self.name,
                             open_until=self.open_until)
                raise CircuitOpenError(
                    f"Circuit {self.name} open until "
                    f"{time.ctime(self.open_until)}"
                )
        
        # Attempt execution
        try:
            result = fn(*args, **kwargs)
            
            # Success - reset failure count
            with self.lock:
                self.failures = 0
                self.success_count += 1
                
            return result
            
        except Exception as e:
            # Track failure
            with self.lock:
                self.failures += 1
                
                # Open circuit if threshold reached
                if self.failures >= self.fail_threshold:
                    self.open_until = time.time() + self.reset_after
                    logger.error("circuit_opened",
                               name=self.name,
                               failures=self.failures,
                               open_until=self.open_until)
                else:
                    logger.warning("circuit_failure",
                                 name=self.name,
                                 failures=self.failures,
                                 threshold=self.fail_threshold)
            
            raise
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        return self.success_count / max(1, self.total_count)
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open."""
        return time.time() < self.open_until


class CircuitOpenError(Exception):
    """Raised when attempting to call through an open circuit."""
    pass


# Common circuit breakers
CB_DENSE = CircuitBreaker("dense", fail_threshold=3, reset_after=5)
CB_EMBEDDER = CircuitBreaker("embedder", fail_threshold=3, reset_after=5)
CB_RERANKER = CircuitBreaker("reranker", fail_threshold=3, reset_after=5)