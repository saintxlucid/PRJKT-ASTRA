# tests/conftest.py
import asyncio
import tempfile
import pytest

@pytest.fixture(scope="session")
def tmp_workspace():
    with tempfile.TemporaryDirectory(prefix="astra_tests_") as d:
        yield d

@pytest.fixture
def fake_context(tmp_workspace):
    return {"workspace": tmp_workspace, "actor": "test-operator"}

@pytest.fixture
def task_planner(fake_context):
    # Lazy import to avoid collection-time side effects
    from astra.planner.task_planner import TaskPlanner
    return TaskPlanner(
        tool_registry=None,
        max_parallel_steps=2,
        max_retries=1,
        default_timeout=1.0
    )

@pytest.fixture
async def run_bg_task():
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


# No custom event loop policy - let pytest-asyncio handle it