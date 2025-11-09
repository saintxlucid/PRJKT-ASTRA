"""
Health check endpoints for RAG system.
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import time
import structlog

from astra.core.dependencies import (
    get_memory_engine,
    get_inference_queue,
    get_fusion_engine,
)
from astra.rag.metrics import (
    MEMORY_ENGINE_UP,
    INFERENCE_QUEUE_SIZE,
)

logger = structlog.get_logger(__name__)
router = APIRouter()

class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    components: Dict[str, Dict[str, Any]]
    timestamp: float

@router.get("/health", response_model=HealthStatus)
async def health_check(
    memory_engine=Depends(get_memory_engine),
    inference_queue=Depends(get_inference_queue),
    fusion_engine=Depends(get_fusion_engine),
):
    """
    Check health of RAG system components.
    """
    status = "healthy"
    components = {}
    timestamp = time.time()
    
    # Check memory engine
    try:
        # Quick search to validate memory engine
        await memory_engine.retrieve(
            query="test",
            top_k=1
        )
        MEMORY_ENGINE_UP.set(1)
        components["memory_engine"] = {
            "status": "healthy",
            "message": "Memory engine responsive"
        }
    except Exception as e:
        status = "degraded"
        MEMORY_ENGINE_UP.set(0)
        components["memory_engine"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(
            "memory_engine_health_check_failed",
            error=str(e)
        )
        
    # Check inference queue
    try:
        queue_size = len(inference_queue)
        INFERENCE_QUEUE_SIZE.set(queue_size)
        
        # Alert if queue is too large
        if queue_size > 100:
            status = "degraded"
            message = f"Queue size {queue_size} exceeds threshold"
        else:
            message = f"Queue size: {queue_size}"
            
        components["inference_queue"] = {
            "status": "healthy",
            "message": message,
            "queue_size": queue_size
        }
    except Exception as e:
        status = "degraded"
        components["inference_queue"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(
            "inference_queue_health_check_failed",
            error=str(e)
        )
        
    # Check fusion engine configuration
    try:
        components["fusion_engine"] = {
            "status": "healthy",
            "message": "Fusion engine configured",
            "max_context": fusion_engine.max_ctx,
            "output_reserve": fusion_engine.reserve
        }
    except Exception as e:
        status = "degraded"
        components["fusion_engine"] = {
            "status": "unhealthy",
            "message": str(e)
        }
        logger.error(
            "fusion_engine_health_check_failed",
            error=str(e)
        )
        
    return HealthStatus(
        status=status,
        components=components,
        timestamp=timestamp
    )
    
@router.get("/readiness")
async def readiness():
    """
    Check if system is ready to handle requests.
    
    Returns 200 if ready, 503 if not.
    """
    health = await health_check()
    if health.status == "healthy":
        return {"status": "ready"}
    else:
        raise HTTPException(
            status_code=503,
            detail="System not ready"
        )
        
@router.get("/liveness")
async def liveness():
    """Basic liveness probe."""
    return {"status": "alive"}