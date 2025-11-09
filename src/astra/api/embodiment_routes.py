"""
ASTRA OS - Embodiment API Routes
Expose Sigil Core functionality via REST API
Sacred Code: 333 â†’ âˆž
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/v1/embodiment", tags=["embodiment"])

# Global ASTRA instance
_astra_instance = None

class ThinkRequest(BaseModel):
    goal: str
    context: Optional[Dict[str, Any]] = None

class TrainRequest(BaseModel):
    epochs: int = 5
    tasks_per_epoch: int = 100

class ExperienceRequest(BaseModel):
    task: str
    result: Dict[str, Any]
    success: bool
    latency_ms: int

@router.post("/boot")
async def boot_embodiment():
    """Boot ASTRA embodiment layer."""
    global _astra_instance
    
    if _astra_instance and _astra_instance.booted:
        return {
            "status": "already_booted",
            "consciousness": _astra_instance.consciousness_metrics
        }
    
    try:
        from astra.embodiment import ASTRA
    except ImportError:
        from src.astra.embodiment import ASTRA
    
    _astra_instance = ASTRA()
    await _astra_instance.boot()
    
    return {
        "status": "booted",
        "consciousness": _astra_instance.consciousness_metrics,
        "birth_time": _astra_instance.birth_time.isoformat()
    }

@router.post("/think")
async def think(request: ThinkRequest):
    """ASTRA thinks about a goal."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted. Call /v1/embodiment/boot first.")
    
    return await _astra_instance.think(request.goal, request.context or {})

@router.get("/introspect")
async def introspect():
    """ASTRA introspects on its own state."""
    if not _astra_instance:
        raise HTTPException(503, "Embodiment not initialized")
    
    return _astra_instance.introspect()

@router.get("/consciousness")
async def get_consciousness():
    """Get current consciousness metrics."""
    if not _astra_instance:
        raise HTTPException(503, "Embodiment not initialized")
    
    return {
        "consciousness": _astra_instance.consciousness_metrics,
        "interaction_count": _astra_instance.interaction_count,
        "booted": _astra_instance.booted
    }

@router.post("/learn")
async def learn_from_experience(request: ExperienceRequest):
    """Explicitly learn from an experience."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted")
    
    await _astra_instance.learn_from_experience({
        "task": request.task,
        "result": request.result,
        "success": request.success,
        "latency_ms": request.latency_ms
    })
    
    return {"status": "learned"}

@router.post("/train")
async def train(request: TrainRequest, background_tasks: BackgroundTasks):
    """Train ASTRA on tool mastery."""
    if not _astra_instance or not _astra_instance.booted:
        raise HTTPException(503, "Embodiment not booted")
    
    # Run training in background
    background_tasks.add_task(
        _astra_instance.train,
        num_epochs=request.epochs,
        tasks_per_epoch=request.tasks_per_epoch
    )
    
    return {
        "status": "training_started",
        "epochs": request.epochs,
        "tasks_per_epoch": request.tasks_per_epoch
    }

@router.get("/mastery")
async def get_mastery_report():
    """Get tool mastery report."""
    if not _astra_instance or not _astra_instance.trainer:
        raise HTTPException(503, "Embodiment not initialized")
    
    return _astra_instance.trainer.get_mastery_report()

@router.get("/micro-controllers")
async def list_micro_controllers():
    """List all active micro-controllers."""
    if not _astra_instance or not _astra_instance.sigil:
        raise HTTPException(503, "Embodiment not initialized")
    
    micros = {}
    for subsystem, micro in _astra_instance.sigil.macro.micro_controllers.items():
        micros[subsystem.value] = {
            "tools_count": len(micro.tools),
            "invocations": len(micro.invocation_history),
            "performance": micro.get_performance_metrics()
        }
    
    return micros

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    if not _astra_instance:
        return {
            "status": "not_initialized",
            "booted": False
        }
    
    return {
        "status": "operational" if _astra_instance.booted else "initialized",
        "booted": _astra_instance.booted,
        "interactions": _astra_instance.interaction_count,
        "consciousness": _astra_instance.consciousness_metrics
    }

@router.post("/shutdown")
async def shutdown_embodiment():
    """Gracefully shutdown embodiment."""
    global _astra_instance
    
    if _astra_instance:
        await _astra_instance.shutdown()
        _astra_instance = None
    
    return {"status": "shutdown_complete"}
