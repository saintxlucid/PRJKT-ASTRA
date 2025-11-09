"""
Test configuration for API integration tests
"""
import pytest
from fastapi.testclient import TestClient
import asyncio

from astra.app import app

@pytest.fixture
def client():
    """Create FastAPI test client"""
    return TestClient(app)

@pytest.fixture
async def run_bg_task():
    """Background task runner fixture"""
    tasks = []
    async def _run(coro):
        t = asyncio.create_task(coro)
        tasks.append(t)
        return t
    try:
        yield _run
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)