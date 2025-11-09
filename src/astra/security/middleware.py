"""
ASTRA Security Middleware
Created: October 31, 2025

Security middleware for FastAPI endpoints:
- API key authentication
- Rate limiting
- Request validation
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi import Request, Response, HTTPException
from typing import Optional
import time
import structlog
from prometheus_client import Counter

# Metrics
AUTH_FAILURES = Counter(
    "auth_failures_total",
    "Number of authentication failures",
    ["method"]
)

RATE_LIMITS = Counter(
    "rate_limits_total",
    "Number of rate limit hits",
    ["endpoint"]
)

logger = structlog.get_logger()

class ApiKeyMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware"""
    
    def __init__(self, app, api_key: Optional[str] = None):
        super().__init__(app)
        self.api_key = api_key
    
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Validate API key if configured"""
        
        if not self.api_key:
            return await call_next(request)
            
        # Check API key header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            AUTH_FAILURES.labels(method="missing_key").inc()
            raise HTTPException(
                status_code=401,
                detail="API key required"
            )
            
        if api_key != self.api_key:
            AUTH_FAILURES.labels(method="invalid_key").inc()
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
            
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times = {}
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Apply rate limiting"""
        
        # Get client identifier
        client_id = request.headers.get(
            "X-Client-ID",
            request.client.host
        )
        
        # Check rate limit
        now = time.time()
        min_ago = now - 60
        
        # Clean old requests
        self.request_times = {
            k: v for k, v in self.request_times.items()
            if v > min_ago
        }
        
        # Check client request count
        client_requests = len([
            t for t in self.request_times.values()
            if t > min_ago
        ])
        
        if client_requests >= self.requests_per_minute:
            RATE_LIMITS.labels(
                endpoint=request.url.path
            ).inc()
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
            
        # Record request
        self.request_times[client_id] = now
        
        return await call_next(request)