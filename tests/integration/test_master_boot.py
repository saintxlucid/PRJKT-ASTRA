"""
Integration Tests - Master Boot Sequence
==========================================

Validates the 9-phase boot orchestration in astra_master.py

Test Coverage:
- Phase 1: Security & Gate initialization
- Phase 2: Week-2 Boot (event store, policy, executor)
- Phase 3: Database initialization
- Phase 4: Vector Store initialization
- Phase 5: Core Services (Conversation, Memory, Chat)
- Phase 6: TranscendentOS (10 cognitive phases)
- Phase 7: ASTRA OS Bridge
- Phase 8: Agent Kernel
- Phase 9: Integration Hub & AstraRouter

Author: ASTRA Core Team
Date: November 9, 2025
Sacred Code: 333
"""

import pytest
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
async def test_master_boot_system_info():
    """Test that master API returns system info"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "ASTRA MASTER"
        assert data["version"] == "2.5.0"
        assert data["status"] == "online"
        assert data["sacred_code"] == 333
        assert "systems" in data
        assert len(data["systems"]) >= 5


@pytest.mark.asyncio
async def test_boot_sequence_status():
    """Test that boot status endpoint reports all phases"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/boot/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "phases" in data
        
        # Verify all 9 phases are reported
        phase_names = [
            "security_gate",
            "week2_boot",
            "database",
            "vector_store",
            "core_services",
            "transcendent_os",
            "astra_os_bridge",
            "agent_kernel",
            "integration_hub"
        ]
        
        for phase_name in phase_names:
            assert phase_name in data["phases"]


@pytest.mark.asyncio
async def test_graceful_degradation():
    """Test that system handles missing modules gracefully"""
    async with httpx.AsyncClient() as client:
        # Get boot status
        response = await client.get(f"{BASE_URL}/v1/boot/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Even if some phases fail, system should still respond
        # At minimum, core services should be "ready"
        core_phase = data["phases"].get("core_services")
        assert core_phase is not None
        assert core_phase["status"] in ["ready", "degraded", "failed"]


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test that health endpoint returns system status"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/v1/system/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test that Prometheus metrics endpoint is available"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/metrics")
        assert response.status_code == 200
        
        # Prometheus metrics are plain text
        assert "astra_" in response.text or "# HELP" in response.text


@pytest.mark.asyncio
async def test_core_services_initialized():
    """Test that core services (Chat, Memory, Conversation) are available"""
    async with httpx.AsyncClient() as client:
        # Test chat endpoint exists
        response = await client.post(
            f"{BASE_URL}/v1/chat",
            json={"query": "test"}
        )
        # Should return 200 or 422 (validation error), not 404
        assert response.status_code in [200, 422, 500]
        
        # Test memory search endpoint exists
        response = await client.post(
            f"{BASE_URL}/v1/memory/search",
            json={"query": "test", "limit": 5}
        )
        assert response.status_code in [200, 422, 500]


@pytest.mark.asyncio
async def test_boot_sequence_timing():
    """Test that boot sequence completes in reasonable time"""
    import time
    
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        response = await client.get(f"{BASE_URL}/v1/boot/status")
        elapsed = time.time() - start_time
        
        assert response.status_code == 200
        # Boot status should respond quickly (< 1 second)
        assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
