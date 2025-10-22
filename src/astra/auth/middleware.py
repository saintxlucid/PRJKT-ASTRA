"""
FastAPI middleware for memory isolation.
"""

from typing import Optional, Callable
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import structlog
from prometheus_client import Histogram

from .isolation import memory_isolation

logger = structlog.get_logger(__name__)

# Metrics
MIDDLEWARE_LATENCY = Histogram(
    "astra_memory_middleware_latency_seconds",
    "Memory middleware processing latency",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05)
)

class MemoryIsolationMiddleware(BaseHTTPMiddleware):
    """Middleware that handles memory isolation for requests."""
    
    def __init__(
        self,
        app: ASGIApp,
        user_id_extractor: Optional[Callable[[Request], str]] = None
    ):
        """Initialize middleware.
        
        Args:
            app: The ASGI app
            user_id_extractor: Optional function to extract user ID from request.
                             If not provided, uses default JWT extraction.
        """
        super().__init__(app)
        self.user_id_extractor = user_id_extractor or self._default_user_id_extractor

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """Process the request and handle memory isolation."""
        start_time = time.time()
        
        # Extract user ID
        try:
            user_id = self.user_id_extractor(request)
            request.state.user_id = user_id
            
            # Add memory isolation instance to request state
            request.state.memory = memory_isolation
            
            # Process request
            response = await call_next(request)
            
            latency = time.time() - start_time
            MIDDLEWARE_LATENCY.labels(operation="success").observe(latency)
            
            return response
            
        except Exception as e:
            latency = time.time() - start_time
            MIDDLEWARE_LATENCY.labels(operation="error").observe(latency)
            
            logger.error("memory_middleware_error",
                        error=str(e),
                        path=request.url.path)
            raise

    def _default_user_id_extractor(self, request: Request) -> str:
        """Default method to extract user ID from JWT token.
        
        Override this or provide custom extractor if using different auth.
        """
        # Get bearer token from header
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise ValueError("No valid authorization token found")
            
        token = auth.split()[1]
        
        # Get user ID from token payload
        # Note: This assumes JWT handling is done by auth decorators
        # and token is already validated
        user_id = request.state.token_payload.get("sub")
        if not user_id:
            raise ValueError("No user ID found in token")
            
        return user_id