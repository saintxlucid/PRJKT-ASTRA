# tests/test_initialization.py
import pytest
import asyncio
from astra.core.initialization import CoreSystemsInitializer

@pytest.mark.asyncio
async def test_init_sequence():
    init = CoreSystemsInitializer(config={})
    status = await init.start()
    assert status["initialized"] is True
    assert status["components"]["memory"]["status"] == "ready"
    assert status["components"]["identity"]["status"] == "ready"
    assert status["components"]["neural"]["status"] == "ready"