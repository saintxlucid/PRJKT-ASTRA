"""
ASTRA Integration Tests - Smoke Tests
Quick validation that all services are reachable and basic endpoints respond.
"""
import os
import socket

import anyio
import httpx
import pytest

MASTER = os.getenv("ASTRA_MASTER_URL", "http://localhost:8000")
SERVICES = [
    ("memory", "http://localhost:7007"),
    ("sigil_gate", "http://localhost:7701"),
    ("supervisor", "http://localhost:7703"),
]


def _port_open(host: str, port: int) -> bool:
    """Check if a TCP port is open and accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


async def _get(client: httpx.AsyncClient, path: str):
    """Helper to make GET request to master API."""
    r = await client.get(f"{MASTER}{path}", timeout=10)
    r.raise_for_status()
    return r


@pytest.mark.anyio
async def test_system_boots():
    """Verify ASTRA master boots with at least 8 of 9 phases complete."""
    async with httpx.AsyncClient() as c:
        resp = await _get(c, "/v1/boot/status")
        data = resp.json()
        phases_completed = data["boot"]["phases_completed"]
        assert phases_completed >= 8, f"Expected 8+ phases, got {phases_completed}"


@pytest.mark.anyio
async def test_services_reachable():
    """Verify all required microservices are reachable on their ports."""
    for name, url in SERVICES:
        host, port = url.replace("http://", "").split(":")
        assert _port_open(host, int(port)), f"{name} not reachable on {port}"


@pytest.mark.anyio
async def test_critical_endpoints():
    """Verify critical API endpoints return success status codes."""
    async with httpx.AsyncClient() as c:
        critical_paths = [
            "/",
            "/v1/cognitive/status",
            "/v1/agent/status",
            "/metrics",
        ]
        for path in critical_paths:
            r = await c.get(f"{MASTER}{path}", timeout=10)
            assert r.status_code in (200, 204), f"{path} returned {r.status_code}"
