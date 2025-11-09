"""
ASTRA Inference API implementation.
"""

import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

# Global state
_inference_queue = None
_model_bridge = None

# Request models
class InferenceRequest(BaseModel):
    prompt: str = Field(..., description="The input prompt")
    max_tokens: int = Field(256, description="Maximum tokens to generate")
    temperature: float = Field(0.7, description="Sampling temperature")
    top_p: float = Field(0.95, description="Top-p sampling parameter")
    adapter_ids: Optional[list[str]] = Field(None, description="Optional adapter IDs")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")

@router.post("/v1/infer")
async def infer(request: InferenceRequest):
    """Submit inference request to queue"""
    if not _inference_queue:
        return {"error": "Inference subsystem not initialized"}
    
    result = await _inference_queue.infer(
        prompt=request.prompt,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        adapter_ids=request.adapter_ids,
        meta=request.meta
    )
    return result

async def stop_inference_subsystem():
    """
    Drain queue and stop workers (idempotent).
    """
    try:
        if _inference_queue:
            await _inference_queue.stop()
    except Exception:
        pass
    try:
        if _model_bridge:
            await _model_bridge.aclose()
    except Exception:
        pass