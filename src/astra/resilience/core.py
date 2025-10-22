"""
Resilience utilities for ASTRA components.

This module provides:
- Circuit breaker pattern implementation
- Retry mechanisms with backoff
- Health monitoring
- Error handling policies
"""
import time
import random
from typing import TypeVar, Callable, Any, Dict, Optional
from dataclasses import dataclass
import structlog
from functools import wraps

logger = structlog.get_logger()

T = TypeVar('T')

@dataclass
class CircuitConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5      # Failures before opening
    reset_timeout: float = 30.0     # Seconds until reset attempt
    half_open_calls: int = 3       # Successful calls to close
    backoff_factor: float = 1.5    # Exponential backoff multiplier
    max_retries: int = 3           # Maximum retry attempts
    initial_delay: float = 1.0     # Initial retry delay in seconds

class CircuitBreaker:
    """Circuit breaker implementation."""
    
    def __init__(self, name: str, config: Optional[CircuitConfig] = None):
        """Initialize circuit breaker.
        
        Args:
            name: Name for this circuit breaker
            config: Optional configuration
        """
        self.name = name
        self.config = config or CircuitConfig()
        
        # State
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "closed"
        self.half_open_successes = 0
        
    def _should_open(self) -> bool:
        """Check if circuit should open."""
        return self.failures >= self.config.failure_threshold
        
    def _should_retry(self) -> bool:
        """Check if in half-open state."""
        if self.state != "open":
            return True
            
        # Check if enough time has passed
        if time.time() - self.last_failure_time >= self.config.reset_timeout:
            self.state = "half-open"
            self.half_open_successes = 0
            return True
            
        return False
        
    def _record_success(self):
        """Record successful call."""
        if self.state == "half-open":
            self.half_open_successes += 1
            if self.half_open_successes >= self.config.half_open_calls:
                self.state = "closed"
                self.failures = 0
                logger.info(
                    "circuit_closed",
                    name=self.name
                )
        elif self.state == "closed":
            self.failures = 0
            
    def _record_failure(self):
        """Record failed call."""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self._should_open():
            self.state = "open"
            logger.warning(
                "circuit_opened",
                name=self.name,
                failures=self.failures
            )
            
    def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Make protected call through circuit breaker.
        
        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception if circuit is open or call fails
        """
        if not self._should_retry():
            raise Exception(f"Circuit {self.name} is open")
            
        retries = 0
        delay = self.config.initial_delay
        
        while True:
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
                
            except Exception as e:
                self._record_failure()
                
                if retries >= self.config.max_retries:
                    raise
                    
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0.0, 0.1 * delay)
                time.sleep(delay + jitter)
                
                delay *= self.config.backoff_factor
                retries += 1
                
                logger.warning(
                    "retry_attempt",
                    name=self.name,
                    attempt=retries,
                    delay=delay,
                    error=str(e)
                )

class CircuitBreakerDecorator:
    """Decorator for adding circuit breaker protection."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitConfig] = None
    ):
        """Initialize decorator.
        
        Args:
            name: Circuit breaker name
            config: Optional configuration
        """
        self.breaker = CircuitBreaker(name, config)
        
    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Apply circuit breaker to function."""
        @wraps(func)
        def wrapped(*args, **kwargs) -> T:
            return self.breaker.call(func, *args, **kwargs)
        return wrapped

class HealthMonitor:
    """Health monitoring for components."""
    
    def __init__(self):
        """Initialize monitor."""
        self.components: Dict[str, bool] = {}
        
    def set_health(self, component: str, healthy: bool):
        """Set component health status."""
        self.components[component] = healthy
        logger.info(
            "health_status",
            component=component,
            healthy=healthy
        )
        
    def is_healthy(self, component: str) -> bool:
        """Check if component is healthy."""
        return self.components.get(component, False)
        
    def all_healthy(self) -> bool:
        """Check if all components are healthy."""
        return all(self.components.values())
        
    def get_status(self) -> Dict[str, bool]:
        """Get health status for all components."""
        return dict(self.components)

# Global health monitor
health = HealthMonitor()