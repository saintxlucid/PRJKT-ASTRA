"""
ASTRA Error Middleware
Created: October 25, 2025

Provides global FastAPI error handling, request correlation,
and sensitive data redaction for ASTRA's HTTP endpoints.
"""
import json
import traceback
import time
import os
from uuid import uuid4
from fastapi.responses import JSONResponse
import logging
from typing import Any, Dict, List, Union, Optional

# Keys that should be redacted in logs
SENSITIVE_KEYS = {
    "password", "token", "secret", "authorization",
    "cookie", "api_key", "session"
}

def _redact(obj: Any) -> Any:
    """Recursively redact sensitive values"""
    if isinstance(obj, dict):
        return {
            k: ("<redacted>" if k.lower() in SENSITIVE_KEYS else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return [_redact(v) for v in obj]
    return obj

async def astra_error_guard(request: Any, call_next: Any) -> Any:
    """Global error handling middleware for all HTTP requests"""
    start = time.time()
    req_id = request.headers.get("x-request-id") or str(uuid4())
    
    try:
        response = await call_next(request)
        response.headers["x-request-id"] = req_id
        return response
        
    except Exception as e:
        err_id = str(uuid4())
        
        # Capture light request context (no bodies)
        ctx = {
            "req_id": req_id,
            "path": request.url.path,
            "method": request.method,
            "query": dict(request.query_params),
            "client": request.client.host if request.client else None,
            "headers": {
                k: ("<redacted>" if k.lower() in {"authorization","cookie"} else v)
                for k, v in request.headers.items()
            },
            "uptime_s": round(time.time() - start, 3),
        }
        
        # Log error with correlation IDs and redacted context
        logging.getLogger("astra").exception(
            "unhandled_error",
            extra={
                "err_id": err_id,
                "ctx": _redact(ctx)
            }
        )
        
        # Return standardized error response
        return JSONResponse(
            {
                "error": "internal_error",
                "err_id": err_id,
                "req_id": req_id
            },
            status_code=500
        )