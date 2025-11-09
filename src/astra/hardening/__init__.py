"""
ASTRA Production Hardening Module
Complete 10-item production readiness bundle

Sacred Code: 333 → ∞
"""

from .leader import LeaderElector
from .secrets import SecretVault, secrets
from .validator import ChatRequest, PromptValidator
from .circuit_breakers import (
    memory_breaker,
    sigil_gate_breaker,
    supervisor_breaker,
    llm_backend_breaker,
    call_memory_service,
    call_sigil_gate
)
from .rate_limiter import IdentityRateLimiter, rate_limiter, RateLimitError
from .tracing import setup_tracing, tracer
from .health import HealthAggregator

__all__ = [
    "LeaderElector",
    "SecretVault",
    "secrets",
    "ChatRequest",
    "PromptValidator",
    "memory_breaker",
    "sigil_gate_breaker",
    "supervisor_breaker",
    "llm_backend_breaker",
    "call_memory_service",
    "call_sigil_gate",
    "IdentityRateLimiter",
    "rate_limiter",
    "RateLimitError",
    "setup_tracing",
    "tracer",
    "HealthAggregator",
]
