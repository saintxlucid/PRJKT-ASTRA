"""
Request ID middleware for distributed tracing.

Adds unique request IDs to every request for correlation across logs and responses.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from astra.utils.logging import get_logger, get_request_id, new_request_id, set_request_id

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add request ID to every request.
    
    - Accepts client-provided request IDs (for distributed tracing)
    - Generates new IDs if not provided
    - Adds request ID to response headers
    - Logs request start and end with request ID
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request with request ID tracking"""
        
        # Allow clients to pass request ID for distributed tracing
        rid = request.headers.get("x-request-id") or new_request_id()
        set_request_id(rid)
        
        # Log request start
        logger.info(
            "request_start",
            method=request.method,
            path=str(request.url.path),
            rid=rid
        )
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["x-request-id"] = rid
        
        # Log request end
        logger.info(
            "request_end",
            method=request.method,
            path=str(request.url.path),
            rid=rid,
            status=response.status_code
        )
        
        return response
