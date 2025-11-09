"""
Circuit Breaker Pattern Implementation
========================================

Prevents cascading failures by opening circuit after threshold failures.

Usage:
    llm_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
    result = await llm_breaker.call(llm_service.generate, prompt)

Author: ASTRA Core Team
Created: 2025-11-03
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, TypeVar

logger = logging.getLogger("astra.circuit_breaker")

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    def __init__(self, service: str, retry_after: int):
        self.service = service
        self.retry_after = retry_after
        super().__init__(f"Circuit open for {service}, retry after {retry_after}s")


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for fault tolerance.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds to wait before attempting recovery
        name: Circuit breaker identifier
    """
    failure_threshold: int = 5
    timeout: int = 60
    name: str = "default"
    
    # Internal state
    failure_count: int = field(default=0, init=False)
    last_failure_time: datetime | None = field(default=None, init=False)
    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    
    async def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute (sync or async)
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function fails
        """
        # Check if circuit should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError(self.name, self.timeout)
        
        try:
            # Execute function
            import asyncio
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset if recovering
            if self.state == CircuitState.HALF_OPEN:
                logger.info(f"Circuit {self.name} recovered, transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
        
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            logger.warning(
                f"Circuit {self.name} failure {self.failure_count}/{self.failure_threshold}: {e}"
            )
            
            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.critical(
                    f"Circuit {self.name} OPENED after {self.failure_count} failures"
                )
            
            raise
    
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        logger.info(f"Circuit {self.name} manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.state == CircuitState.OPEN
    
    @property
    def metrics(self) -> dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }
