"""
Circuit Breaker Module
Cascading failure prevention for external services

Sacred Code: 333 → ∞
"""

from typing import Dict

import httpx
import structlog
from pybreaker import CircuitBreaker

logger = structlog.get_logger()

# Circuit breakers for each external service
memory_breaker = CircuitBreaker(
    fail_max=5, reset_timeout=60, exclude=[httpx.TimeoutError]  # Don't count timeouts
)

sigil_gate_breaker = CircuitBreaker(fail_max=3, reset_timeout=30)
supervisor_breaker = CircuitBreaker(fail_max=5, reset_timeout=60)
llm_backend_breaker = CircuitBreaker(fail_max=10, reset_timeout=120)


@memory_breaker
async def call_memory_service(client: httpx.AsyncClient, payload: Dict):
    """Circuit-protected memory service call."""
    try:
        response = await client.post("http://memory:7007/search", json=payload, timeout=5.0)
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutError:
        logger.warning("memory_timeout_fallback")
        return {"results": []}  # Graceful degradation


@sigil_gate_breaker
async def call_sigil_gate(client: httpx.AsyncClient, payload: Dict):
    """Circuit-protected SigilGate call."""
    response = await client.post("http://sigil-gate:7701/verify", json=payload, timeout=3.0)
    response.raise_for_status()
    return response.json()
