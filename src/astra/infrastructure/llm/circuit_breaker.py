"""
Circuit Breaker for LLM Calls

Prevents cascading failures when llama.cpp is unavailable.
Opens circuit after N consecutive failures, closes after timeout.

Usage:
    breaker = CircuitBreaker(fail_threshold=3, reset_seconds=30)
    
    if not breaker.allow():
        return {"error": "llm_unavailable"}, 503
    
    try:
        response = await call_llm(...)
        breaker.record_success()
        return response
    except Exception:
        breaker.record_failure()
        raise
"""
import time
from typing import Optional
import structlog

logger = structlog.get_logger()


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker open, retry after {retry_after}s")


class CircuitBreaker:
    """
    Simple circuit breaker for LLM calls.
    
    States:
    - CLOSED: Normal operation
    - OPEN: Failures exceeded threshold, reject requests
    - HALF_OPEN: After timeout, allow one test request
    """
    
    def __init__(self, fail_threshold: int = 3, reset_seconds: int = 30):
        """
        Initialize circuit breaker.
        
        Args:
            fail_threshold: Number of consecutive failures before opening
            reset_seconds: Time to wait before attempting to close
        """
        self.fail_threshold = fail_threshold
        self.reset_seconds = reset_seconds
        self.failures = 0
        self.open_until = 0.0
        self.state = "CLOSED"
    
    def allow(self) -> bool:
        """
        Check if request should be allowed.
        
        Returns:
            True if circuit is closed or half-open
        """
        now = time.time()
        
        if now >= self.open_until:
            if self.state == "OPEN":
                self.state = "HALF_OPEN"
                logger.info("circuit_breaker_half_open", failures=self.failures)
            return True
        
        return False
    
    def record_success(self):
        """Record successful request"""
        if self.state == "HALF_OPEN":
            logger.info("circuit_breaker_closed", previous_failures=self.failures)
        
        self.failures = 0
        self.open_until = 0.0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed request"""
        self.failures += 1
        
        if self.failures >= self.fail_threshold:
            self.open_until = time.time() + self.reset_seconds
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker_open",
                failures=self.failures,
                retry_after=self.reset_seconds
            )
    
    def get_retry_after(self) -> Optional[int]:
        """Get seconds until circuit may close"""
        if self.state != "OPEN":
            return None
        
        remaining = int(self.open_until - time.time())
        return max(0, remaining)
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state,
            "failures": self.failures,
            "retry_after": self.get_retry_after()
        }


# Global circuit breaker instance for LLM calls
_llm_breaker: Optional[CircuitBreaker] = None


def get_llm_breaker() -> CircuitBreaker:
    """Get global LLM circuit breaker instance"""
    global _llm_breaker
    if _llm_breaker is None:
        _llm_breaker = CircuitBreaker(fail_threshold=3, reset_seconds=30)
    return _llm_breaker
