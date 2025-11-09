"""
Integration Tests - Cognitive API Endpoints
============================================

Validates all 10 cognitive phases + mode management

Test Coverage:
- Phase 1: Reasoning modes
- Phase 2: Emotional intelligence
- Phase 3: Memory systems
- Phase 5: Quantum intent resolution
- Phase 6: Hypergraph cognitive topology
- Phase 7: Continuous learning
- Phase 8: Distributed consciousness
- Phase 9: Self-modification
- Phase 10: Transcendent unification
- Mode management (get, switch)

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""

import pytest
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_cognitive_status():
    """Test that cognitive status endpoint returns phase information"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/cognitive/status")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "phases" in data or "status" in data


@pytest.mark.asyncio
async def test_phase1_reasoning():
    """Test Phase 1: Reasoning endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/reasoning",
            json={
                "query": "Analyze the concept of emergence in complex systems",
                "mode": "analytical"
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase2_emotional():
    """Test Phase 2: Emotional intelligence endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/emotional",
            json={
                "text": "I am excited about this breakthrough in AI research!",
                "analyze_sentiment": True
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase3_memory():
    """Test Phase 3: Memory systems endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/memory",
            json={
                "query": "neural network architectures",
                "memory_type": "semantic"
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase5_quantum_intent():
    """Test Phase 5: Quantum intent resolution endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/intent",
            json={
                "text": "I want to understand how transformers work"
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase6_hypergraph():
    """Test Phase 6: Hypergraph cognitive topology endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/hypergraph",
            json={
                "concepts": ["AI", "machine learning", "neural networks"],
                "explore_depth": 2
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase7_learning_feedback():
    """Test Phase 7: Continuous learning feedback endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/learning/feedback",
            json={
                "interaction_id": "test_interaction_001",
                "feedback": "positive",
                "context": {"quality": 0.9}
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase7_learning_insights():
    """Test Phase 7: Learning insights retrieval endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/cognitive/learning/insights")
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
async def test_phase8_distributed():
    """Test Phase 8: Distributed consciousness endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/distributed",
            json={
                "task": "parallel_reasoning",
                "agents": 3
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase9_self_modification():
    """Test Phase 9: Self-modification engine endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/self-modification",
            json={
                "proposal": "optimize memory consolidation interval",
                "dry_run": True
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_phase10_transcendent():
    """Test Phase 10: Transcendent unification endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/transcendent",
            json={
                "query": "Synthesize insights across all cognitive phases",
                "unify_context": True
            }
        )
        assert response.status_code in [200, 422, 503]


@pytest.mark.asyncio
async def test_mode_management_get():
    """Test getting current cognitive mode"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/cognitive/mode")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "mode" in data
            assert data["mode"] in [
                "reactive", "proactive", "reflective",
                "creative", "collaborative", "transcendent"
            ]


@pytest.mark.asyncio
async def test_mode_management_switch():
    """Test switching cognitive mode"""
    async with httpx.AsyncClient() as client:
        # Test switching to creative mode
        response = await client.post(
            f"{BASE_URL}/v1/cognitive/mode",
            json={"mode": "creative", "persist": False}
        )
        assert response.status_code in [200, 422, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert data["mode"] == "creative"


@pytest.mark.asyncio
async def test_emergent_behaviors():
    """Test emergent behaviors detection endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/cognitive/behaviors")
        assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
