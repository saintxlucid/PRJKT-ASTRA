"""
Test configuration for API integration tests
"""
import pytest
from fastapi.testclient import TestClient
import asyncio
from pathlib import Path
import sys

# Add project root to path
root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root))

import sys
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add src directory to path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))

# Mock dependencies
sys.modules["astra.core.answer_api"] = MagicMock()
sys.modules["astra.core.answer_api"].AnswerAPI = AsyncMock()
sys.modules["astra.rag.rag_fusion"] = MagicMock()

# Mock circuit breaker and backpressure
mock_breaker = MagicMock()
mock_breaker.open = False
mock_breaker.failures = 0
mock_breaker.__call__ = MagicMock()
mock_breaker.__enter__ = MagicMock(return_value=None)
mock_breaker.__exit__ = MagicMock(return_value=None)

mock_backpressure = AsyncMock()
mock_backpressure.acquire = AsyncMock()
mock_backpressure.available_tokens = 100
mock_backpressure.max_tokens = 100

sys.modules["astra.core.circuit_breakers"] = MagicMock()
sys.modules["astra.core.circuit_breakers"].CircuitBreaker = MagicMock(return_value=mock_breaker)

sys.modules["astra.core.backpressure"] = MagicMock()
sys.modules["astra.core.backpressure"].Backpressure = MagicMock(return_value=mock_backpressure)

# Import app after mocking
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