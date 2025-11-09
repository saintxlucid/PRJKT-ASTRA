"""
FastAPI extension for inference endpoints.
Integrates with the CoreSystemsInitializer pattern by importing the shared initializer instance
from launcher (or create one if not imported).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import asyncio
from astra.neural.model_bridge import ModelBridge
from astra.neural.inference_queue import InferenceQueue
from astra.neural.adapter_manager import AdapterManager

router = APIRouter(prefix="/astra")

# create local singletons for dev; in production wire from initializer
_model_bridge = ModelBridge()
_inference_queue = InferenceQueue(_model_bridge, concurrency=2)
_adapter_mgr = AdapterManager()

# ensure queue started
asyncio.create_task(_inference_queue.start())

class InferRequest(BaseModel):
    prompt: str
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    adapter_ids: Optional[List[str]] = []
    meta: Optional[Dict] = {}

@router.post("/infer")
async def infer_endpoint(req: InferRequest):
    # Basic policy: block very long prompts to protect resources
    if len(req.prompt) > 50_000:
        raise HTTPException(400, "prompt too long")
    res = await _inference_queue.enqueue(req.prompt, max_tokens=req.max_tokens, temperature=req.temperature, top_p=req.top_p, adapter_ids=req.adapter_ids, meta=req.meta, timeout=60, max_retries=1)
    return res

@router.get("/queue_status")
async def queue_status():
    return {"queue_size": _inference_queue._queue.qsize(), "active_count": len(_inference_queue._active)}

@router.post("/adapters/register")
async def register_adapter(payload: Dict):
    """
    payload: {"adapter_id": "...", "metadata": {...}}
    """
    adapter_id = payload.get("adapter_id")
    metadata = payload.get("metadata", {})
    if not adapter_id:
        raise HTTPException(400, "adapter_id required")
    try:
        a = _adapter_mgr.add_adapter(adapter_id, metadata)
        sig = _adapter_mgr.sign_adapter(adapter_id)
        return {"adapter": a, "signature": sig}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/adapters/load/{adapter_id}")
async def load_adapter(adapter_id: str):
    try:
        r = await _adapter_mgr.load_adapter(adapter_id, _model_bridge)
        return r
    except Exception as e:
        raise HTTPException(400, str(e))