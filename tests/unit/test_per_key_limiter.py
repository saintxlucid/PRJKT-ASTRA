"""
Unit tests for per-key rate limiting.

Tests the PerKeyLimiter class and ApiKeyMiddleware integration.
"""

import asyncio
import os

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from astra.security import ApiKeyMiddleware, PerKeyLimiter


def test_per_key_limiter_allows_under_limit():
    """Test that requests are allowed when under rate limit"""
    limiter = PerKeyLimiter(rate=5, period_sec=60)
    key = "test_key_123"
    
    # First 5 requests should be allowed
    for _ in range(5):
        assert limiter.allow(key) is True
    
    # 6th request should be blocked
    assert limiter.allow(key) is False


def test_per_key_limiter_different_keys_independent():
    """Test that different keys have independent budgets"""
    limiter = PerKeyLimiter(rate=3, period_sec=60)
    
    key1 = "key_alice"
    key2 = "key_bob"
    
    # Use up key1's budget
    assert limiter.allow(key1) is True
    assert limiter.allow(key1) is True
    assert limiter.allow(key1) is True
    assert limiter.allow(key1) is False  # Exhausted
    
    # key2 should still have full budget
    assert limiter.allow(key2) is True
    assert limiter.allow(key2) is True
    assert limiter.allow(key2) is True
    assert limiter.allow(key2) is False


def test_per_key_limiter_refills_over_time():
    """Test that tokens refill gradually"""
    limiter = PerKeyLimiter(rate=10, period_sec=1.0)  # 10 per second
    key = "test_key"
    
    # Use 5 tokens
    for _ in range(5):
        assert limiter.allow(key) is True
    
    # Wait for refill (0.5s = 5 tokens)
    import time
    time.sleep(0.5)
    
    # Should have ~5 tokens again
    for _ in range(4):
        assert limiter.allow(key) is True


@pytest.mark.asyncio
async def test_api_key_middleware_per_key_limiting(monkeypatch):
    """Test that ApiKeyMiddleware enforces per-key limits"""
    # Create test app
    app = FastAPI()
    
    # Set API key and per-key limits
    test_key = "test_" + "x" * 40
    monkeypatch.setenv("ASTRA_API_KEY", test_key)
    monkeypatch.setenv("ASTRA_PER_KEY_RATE", "5")
    monkeypatch.setenv("ASTRA_PER_KEY_PERIOD_SEC", "60")
    
    # Add middleware
    app.add_middleware(ApiKeyMiddleware)
    
    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}
    
    # Test requests
    async with AsyncClient(app=app, base_url="http://test") as client:
        success_count = 0
        blocked_count = 0
        
        # Send 10 requests
        for _ in range(10):
            response = await client.get("/test", headers={"x-api-key": test_key})
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                blocked_count += 1
        
        # Should have ~5 successes and ~5 blocked
        assert success_count >= 5, f"Expected ≥5 successes, got {success_count}"
        assert blocked_count >= 1, f"Expected ≥1 blocked, got {blocked_count}"
        assert success_count + blocked_count == 10


@pytest.mark.asyncio
async def test_api_key_middleware_exempt_paths_not_limited(monkeypatch):
    """Test that exempt paths bypass per-key limiting"""
    app = FastAPI()
    
    # Set very strict per-key limit
    test_key = "test_" + "x" * 40
    monkeypatch.setenv("ASTRA_API_KEY", test_key)
    monkeypatch.setenv("ASTRA_PER_KEY_RATE", "1")  # Only 1 per minute
    monkeypatch.setenv("ASTRA_PER_KEY_PERIOD_SEC", "60")
    
    app.add_middleware(ApiKeyMiddleware)
    
    @app.get("/v1/system/health")
    async def health():
        return {"status": "ok"}
    
    @app.get("/metrics")
    async def metrics():
        return {"metrics": "..."}
    
    # Health and metrics should never be rate limited (exempt)
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Call health 10 times without API key
        for _ in range(10):
            response = await client.get("/v1/system/health")
            assert response.status_code == 200
        
        # Call metrics 10 times without API key
        for _ in range(10):
            response = await client.get("/metrics")
            assert response.status_code == 200


def test_per_key_limiter_hash_privacy():
    """Test that key hashing produces consistent labels"""
    limiter = PerKeyLimiter(rate=10, period_sec=60)
    
    key = "super_secret_api_key_12345"
    hash1 = limiter._hash_key(key)
    hash2 = limiter._hash_key(key)
    
    # Same key should produce same hash
    assert hash1 == hash2
    
    # Hash should be short (for metrics cardinality)
    assert len(hash1) == 16
    
    # Different keys should produce different hashes
    hash3 = limiter._hash_key("different_key")
    assert hash1 != hash3
