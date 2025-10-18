"""
Security Module

Provides encryption, rate limiting, and API key authentication for ASTRA production deployment.

Features:
1. EncryptedText field decorator for SQLAlchemy
2. RateLimitMiddleware for FastAPI (global rate limiting)
3. PerKeyLimiter for per-API-key token bucket limiting
4. ApiKeyMiddleware for API key authentication
5. Fernet-based symmetric encryption

Configuration:
    ASTRA_ENCRYPTION_KEY - Fernet key for encryption (required)
    ASTRA_RATE_LIMIT_REQUESTS - Max requests per window (default: 30)
    ASTRA_RATE_LIMIT_WINDOW - Time window in seconds (default: 5)
    ASTRA_API_KEY - API key for authentication (required)
    ASTRA_PER_KEY_RATE - Max requests per key per period (default: 120)
    ASTRA_PER_KEY_PERIOD_SEC - Time period for per-key limits (default: 60)

Generate encryption key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    
Generate API key:
    python -c "import secrets; print(secrets.token_urlsafe(48))"
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading
import time
from collections import defaultdict
from typing import Dict, Optional

import structlog
from cryptography.fernet import Fernet
from fastapi import HTTPException, Request
from sqlalchemy import String, TypeDecorator
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# Load encryption key from environment
ENCRYPTION_KEY = os.getenv("ASTRA_ENCRYPTION_KEY")
if ENCRYPTION_KEY:
    try:
        _fernet = Fernet(ENCRYPTION_KEY.encode())
        logger.info("encryption_enabled")
    except Exception as e:
        logger.error("invalid_encryption_key", error=str(e))
        _fernet = None
else:
    logger.warning("encryption_disabled", 
                   message="Set ASTRA_ENCRYPTION_KEY to enable encryption")
    _fernet = None


class EncryptedText(TypeDecorator):
    """
    SQLAlchemy type decorator for encrypted text fields.
    
    Transparently encrypts data before storing and decrypts when loading.
    Uses Fernet symmetric encryption (AES-128-CBC with HMAC authentication).
    
    Usage:
        from sqlalchemy import Column
        from astra.security import EncryptedText
        
        class User(Base):
            __tablename__ = "users"
            
            id = Column(Integer, primary_key=True)
            api_key = Column(EncryptedText)  # Encrypted in database
            notes = Column(EncryptedText)
    """
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Encrypt value before storing in database.
        
        Args:
            value: Plain text value
            dialect: SQLAlchemy dialect
            
        Returns:
            Encrypted value or None
        """
        if value is None:
            return None
        
        if _fernet is None:
            logger.warning("encryption_unavailable", 
                          message="Storing unencrypted (ASTRA_ENCRYPTION_KEY not set)")
            return value
        
        try:
            encrypted = _fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error("encryption_failed", error=str(e))
            # Fail closed - don't store unencrypted data
            raise
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """
        Decrypt value after loading from database.
        
        Args:
            value: Encrypted value
            dialect: SQLAlchemy dialect
            
        Returns:
            Decrypted plain text or None
        """
        if value is None:
            return None
        
        if _fernet is None:
            # If encryption is disabled, assume data is plain text
            return value
        
        try:
            decrypted = _fernet.decrypt(value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error("decryption_failed", error=str(e))
            # Return None instead of raising to avoid breaking app
            return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiter middleware.
    
    Enforces per-IP rate limits with configurable requests per window.
    Returns 429 Too Many Requests when limit exceeded.
    
    Configuration:
        ASTRA_RATE_LIMIT_REQUESTS - Max requests per window (default: 30)
        ASTRA_RATE_LIMIT_WINDOW - Time window in seconds (default: 5)
    
    Usage:
        from fastapi import FastAPI
        from astra.security import RateLimitMiddleware
        
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware)
    """
    
    def __init__(self, app, max_requests: int | None = None, window_seconds: int | None = None):
        """
        Initialize rate limiter.
        
        Args:
            app: FastAPI application
            max_requests: Maximum requests per window (default: from env or 30)
            window_seconds: Time window in seconds (default: from env or 5)
        """
        super().__init__(app)
        
        self.max_requests = (
            max_requests 
            or int(os.getenv("ASTRA_RATE_LIMIT_REQUESTS", "30"))
        )
        self.window_seconds = (
            window_seconds 
            or int(os.getenv("ASTRA_RATE_LIMIT_WINDOW", "5"))
        )
        
        # In-memory storage: {client_ip: [(timestamp, ...)]}
        self.requests: dict[str, list[float]] = defaultdict(list)
        
        logger.info("rate_limiter_initialized",
                   max_requests=self.max_requests,
                   window_seconds=self.window_seconds,
                   rate=f"{self.max_requests / self.window_seconds:.1f} req/sec")
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce rate limit.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or 429 error
        """
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/metrics", "/v1/system/health"]:
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        # Clean old requests outside window
        cutoff = now - self.window_seconds
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] 
            if ts > cutoff
        ]
        
        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning("rate_limit_exceeded",
                          client_ip=client_ip,
                          requests=len(self.requests[client_ip]))
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit: {self.max_requests} requests per {self.window_seconds}s",
                    "retry_after": self.window_seconds
                }
            )
        
        # Record request
        self.requests[client_ip].append(now)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.max_requests - len(self.requests[client_ip])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))
        
        return response
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Checks X-Forwarded-For header first (for proxy/load balancer),
        then falls back to direct connection IP.
        
        Args:
            request: FastAPI request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (set by proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can be a comma-separated list
            # First IP is the original client
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header (set by some proxies)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection IP
        if request.client:
            return request.client.host
        
        return "unknown"


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        Base64-encoded encryption key string
    """
    key = Fernet.generate_key()
    return key.decode()


class _TokenBucket:
    """Token bucket state for a single API key."""
    __slots__ = ("tokens", "last")
    
    def __init__(self, capacity: float):
        self.tokens = capacity
        self.last = time.time()


class PerKeyLimiter:
    """
    Token-bucket rate limiter keyed by API key.
    
    Protects llama.cpp from single noisy tenant by enforcing per-key budgets.
    Uses constant-time operations and privacy-preserving key hashing.
    
    Configuration:
        rate: Tokens per period (default: 120)
        period_sec: Time period in seconds (default: 60.0)
        
    Example:
        limiter = PerKeyLimiter(rate=120, period_sec=60)
        if limiter.allow(api_key):
            # Process request
        else:
            # Return 429
    """
    
    def __init__(self, rate: int = 120, period_sec: float = 60.0):
        """
        Initialize per-key limiter.
        
        Args:
            rate: Tokens per period (burst capacity)
            period_sec: Time period in seconds
        """
        self.rate = float(rate)
        self.period = float(period_sec)
        self.capacity = float(rate)  # burst == rate (1 period)
        self._lock = threading.Lock()
        self._buckets: Dict[str, _TokenBucket] = defaultdict(
            lambda: _TokenBucket(self.capacity)
        )
        
        logger.info(
            "per_key_limiter_initialized",
            rate=rate,
            period_sec=period_sec,
            rate_per_sec=f"{rate / period_sec:.2f}",
        )
    
    def _hash_key(self, key: str) -> str:
        """
        Generate privacy-preserving hash of API key for metrics.
        
        Args:
            key: API key string
            
        Returns:
            SHA-256 hash (truncated to 16 chars)
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    
    def allow(self, key: str) -> bool:
        """
        Check if request is allowed for this API key.
        
        Implements token bucket algorithm with refill.
        
        Args:
            key: API key (or empty string for unauthenticated)
            
        Returns:
            True if request allowed, False if rate limit exceeded
        """
        # Import here to avoid circular dependency
        from astra.metrics import LIMITER_PER_KEY_ALLOWED, LIMITER_PER_KEY_BLOCKED
        
        # Treat empty key as single shared bucket (safe default)
        label = self._hash_key(key or "anon")
        now = time.time()
        
        with self._lock:
            bucket = self._buckets[label]
            
            # Refill tokens based on elapsed time
            elapsed = now - bucket.last
            if elapsed > 0:
                refill = (elapsed / self.period) * self.rate
                bucket.tokens = min(self.capacity, bucket.tokens + refill)
                bucket.last = now
            
            # Check if token available
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                LIMITER_PER_KEY_ALLOWED.labels(key_hash=label).inc()
                return True
            
            # Rate limit exceeded
            LIMITER_PER_KEY_BLOCKED.labels(key_hash=label).inc()
            return False


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """
    API key authentication middleware.
    
    Requires X-API-Key header for protected endpoints.
    Exempts health checks, metrics, and documentation endpoints.
    
    Configuration:
        ASTRA_API_KEY - API key for authentication (required)
    
    Usage:
        from fastapi import FastAPI
        from astra.security import ApiKeyMiddleware
        
        app = FastAPI()
        app.add_middleware(ApiKeyMiddleware)
    
    Generate API key:
        python -c "import secrets; print(secrets.token_urlsafe(48))"
    """
    
    def __init__(self, app):
        """Initialize API key middleware"""
        super().__init__(app)
        
        self.key = os.getenv("ASTRA_API_KEY", "").strip()
        
        # Exempt paths (no auth required)
        self.exempt_paths = {
            "/",
            "/v1/system/health",
            "/v1/system/version",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        
        # Per-key rate limiter config
        per_key_rate = int(os.getenv("ASTRA_PER_KEY_RATE", "120"))
        per_key_period = float(os.getenv("ASTRA_PER_KEY_PERIOD_SEC", "60"))
        self.per_key_limiter = PerKeyLimiter(rate=per_key_rate, period_sec=per_key_period)
        
        if self.key:
            if len(self.key) < 32:
                logger.warning(
                    "api_key_weak",
                    message="ASTRA_API_KEY should be ≥32 chars for security"
                )
            logger.info("api_key_auth_enabled", exempt_paths=list(self.exempt_paths))
        else:
            logger.warning(
                "api_key_auth_disabled",
                message="Set ASTRA_API_KEY to enable API key authentication"
            )
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request and check API key.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
            
        Returns:
            Response or 401 error
        """
        # Skip auth if no key configured or path is exempt
        if not self.key or request.url.path in self.exempt_paths:
            return await call_next(request)
        
        # Get provided API key from header
        provided = request.headers.get("x-api-key", "").strip()
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided, self.key):
            logger.warning(
                "api_key_invalid",
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown"
            )
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "unauthorized",
                    "message": "Invalid or missing API key. Provide X-API-Key header."
                }
            )
        
        # Per-key rate limiting check
        if not self.per_key_limiter.allow(provided):
            logger.warning(
                "per_key_rate_limit_exceeded",
                path=request.url.path,
                client_ip=request.client.host if request.client else "unknown",
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded for your API key. Please slow down."
                }
            )
        
        # API key valid, proceed
        return await call_next(request)


# Example usage:
"""
# 1. Generate encryption key
python -c "from astra.security import generate_encryption_key; print(generate_encryption_key())"

# 2. Add to .env
ASTRA_ENCRYPTION_KEY=your-generated-key-here

# 3. Use in models
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from astra.security import EncryptedText

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)  # Not encrypted
    api_key = Column(EncryptedText)  # Encrypted
    notes = Column(EncryptedText)  # Encrypted

# 4. Add rate limiting to app
from fastapi import FastAPI
from astra.security import RateLimitMiddleware

app = FastAPI()
app.add_middleware(RateLimitMiddleware)

# Result: 30 requests per 5 seconds = 6 requests/second per IP
"""
