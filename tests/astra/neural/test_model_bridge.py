import pytest
import asyncio
from astra.neural.model_bridge import ModelBridge

@pytest.mark.asyncio
async def test_health():
    mb = ModelBridge(endpoint="http://127.0.0.1:59999")  # assumed missing endpoint
    res = await mb.health()
    assert isinstance(res, dict)
    assert "ok" in res

@pytest.mark.asyncio
async def test_infer_fallback():
    # If no endpoint and no cli, should return error dict
    mb = ModelBridge(endpoint="http://127.0.0.1:59999", cli_fallback_cmd=None)
    r = await mb.infer("hello test", max_tokens=4, temperature=0.1)
    assert isinstance(r, dict)
    assert "error" in r or "text" in r or "_astra_provenance" in r