"""
Rate limiting for ASTRA API endpoints.
"""

import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import asyncio
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

@dataclass
class RateLimit:
    """Rate limit configuration."""
    requests: int  # Number of requests allowed
    window: int   # Time window in seconds
    scope: str    # Scope identifier (e.g., "api", "memory", "plugin")

class RollingWindowLimiter:
    """Rolling window rate limiter."""

    def __init__(self, limit: RateLimit):
        """Initialize rate limiter."""
        self.limit = limit
        self.window = []  # List of timestamps
        self.last_cleanup = time.time()

    def cleanup(self, now: float) -> None:
        """Remove expired timestamps."""
        cutoff = now - self.limit.window
        while self.window and self.window[0] < cutoff:
            self.window.pop(0)
        self.last_cleanup = now

    def check(self) -> Tuple[bool, Optional[float]]:
        """Check if request is allowed."""
        now = time.time()
        
        # Cleanup old timestamps if needed
        if now - self.last_cleanup > min(60, self.limit.window / 2):
            self.cleanup(now)

        # Check current count
        if len(self.window) < self.limit.requests:
            self.window.append(now)
            return True, None

        # Calculate retry after
        oldest = self.window[0]
        retry_after = oldest + self.limit.window - now
        return False, retry_after

class RateLimiter:
    """Manages rate limits for different users and scopes."""

    def __init__(self):
        """Initialize rate limiter."""
        # Default limits
        self.default_limits = {
            "api": RateLimit(100, 60, "api"),           # 100 requests/minute
            "memory": RateLimit(1000, 60, "memory"),    # 1000 memory ops/minute
            "plugin": RateLimit(50, 60, "plugin"),      # 50 plugin calls/minute
            "os": RateLimit(20, 60, "os"),             # 20 OS operations/minute
        }

        # User-specific limits
        self.user_limits: Dict[str, Dict[str, RollingWindowLimiter]] = {}

        # Global limits
        self.global_limits: Dict[str, RollingWindowLimiter] = {
            scope: RollingWindowLimiter(limit) 
            for scope, limit in self.default_limits.items()
        }

    def get_user_limiter(self, user_id: str, scope: str) -> RollingWindowLimiter:
        """Get or create user-specific limiter."""
        if user_id not in self.user_limits:
            self.user_limits[user_id] = {}
        
        if scope not in self.user_limits[user_id]:
            limit = self.default_limits[scope]
            self.user_limits[user_id][scope] = RollingWindowLimiter(limit)

        return self.user_limits[user_id][scope]

    async def check_rate_limit(
        self,
        user_id: str,
        scope: str = "api"
    ) -> None:
        """Check rate limits for a request."""
        # Check user-specific limit
        user_limiter = self.get_user_limiter(user_id, scope)
        allowed, retry_after = user_limiter.check()
        
        if not allowed:
            logger.warning("rate_limit_exceeded", 
                         user_id=user_id, 
                         scope=scope,
                         retry_after=retry_after)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "scope": scope,
                    "retry_after": retry_after
                }
            )

        # Check global limit
        global_limiter = self.global_limits[scope]
        allowed, retry_after = global_limiter.check()
        
        if not allowed:
            logger.warning("global_rate_limit_exceeded",
                         scope=scope,
                         retry_after=retry_after)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Global rate limit exceeded",
                    "scope": scope,
                    "retry_after": retry_after
                }
            )

    def update_user_limit(
        self,
        user_id: str,
        scope: str,
        requests: int,
        window: int
    ) -> None:
        """Update rate limit for a specific user and scope."""
        limit = RateLimit(requests, window, scope)
        if user_id not in self.user_limits:
            self.user_limits[user_id] = {}
        self.user_limits[user_id][scope] = RollingWindowLimiter(limit)

    async def periodic_cleanup(self) -> None:
        """Periodically cleanup expired entries."""
        while True:
            try:
                now = time.time()
                
                # Cleanup global limiters
                for limiter in self.global_limits.values():
                    limiter.cleanup(now)
                
                # Cleanup user limiters
                for user_limits in self.user_limits.values():
                    for limiter in user_limits.values():
                        limiter.cleanup(now)
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error("rate_limiter_cleanup_error", error=str(e))
                await asyncio.sleep(60)  # Back off on error

# Global rate limiter instance
rate_limiter = RateLimiter()

# Start cleanup task
asyncio.create_task(rate_limiter.periodic_cleanup())