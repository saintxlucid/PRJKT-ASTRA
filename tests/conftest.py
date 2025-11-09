# tests/conftest.py# tests/conftest.py# tests/conftest.py

# Minimal conftest.py for response template tests

import pytest# Minimal conftest.py for response template testsimport asyncio
import os
import tempfile
from typing import Dict, Any, Generator

import numpy as np
import pytest

# Conditional import for missing module
try:
    from astra_evo.gguf_io import GGUFIO
except ImportError:
    GGUFIO = None  # Mock or skip tests requiring GGUFIO

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

# GGUF test fixtures
@pytest.fixture
def temp_gguf() -> Generator[str, None, None]:
    """Temporary GGUF file fixture."""
    with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
        path = f.name
        yield path
        try:
            os.unlink(path)
        except OSError:
            pass
        
@pytest.fixture
def sample_tensors() -> Dict[str, np.ndarray]:
    """Sample tensors for testing."""
    rng = np.random.default_rng(42)
    return {
        "small": rng.standard_normal((7, 3, 5)).astype(np.float32),
        "medium": rng.standard_normal(4096).astype(np.float16),
        "large": rng.standard_normal((1, 77, 64)).astype(np.float32),
        "non_contiguous": np.asfortranarray(rng.standard_normal((10, 10)))
    }
    
@pytest.fixture
def sample_kv() -> Dict[str, Any]:
    """Sample key-value pairs for testing."""
    return {
        "general.architecture": "llama",
        "general.version": 2,
        "tokenizer.model": "llama",
        "llama.context_length": 4096,
        "llama.rope.scale": 1.0,
        "llama.rope.base": 10000.0,
        "llama.embedding_length": 4096,
        "llama.feed_forward_length": 11008,
        "llama.attention.head_count": 32,
        "llama.attention.head_count_kv": 32,
        "llama.attention.layer_count": 32,
        "llama.expert_count": 8,
    }
    
@pytest.fixture
def reference_gguf(temp_gguf: str, sample_tensors: Dict[str, np.ndarray], 
                  sample_kv: Dict[str, Any]) -> GGUFIO:
    """Create a reference GGUF file with sample data."""
    from astra_evo.gguf_io import GGUFIO
    
    io = GGUFIO(temp_gguf)
    
    # Write header
    io.write_header(len(sample_tensors), len(sample_kv))
    
    # Write KV pairs
    for k, v in sample_kv.items():
        io.write_kv(k, v)
        
    # Write tensors  
    for name, data in sample_tensors.items():
        io.write_tensor(name, data)
        
    return io