"""
TranscendentOS API routes.

Handles Phase 10 unified cognitive system management and monitoring.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from astra.services.transcendent_service import TranscendentService
from astra.utils.errors import AstraError

router = APIRouter(prefix="/v1/transcendent", tags=["transcendent"])


# Request/Response models
class CognitiveModeRequest(BaseModel):
    """Request to change cognitive mode"""
    
    mode: str = Field(
        ...,
        description="Cognitive mode: REACTIVE, PROACTIVE, REFLECTIVE, CREATIVE, COLLABORATIVE, TRANSCENDENT"
    )


class HealthResponse(BaseModel):
    """System health response"""
    
    available: bool
    overall_health: Optional[float] = None
    subsystems: Optional[dict] = None
    metrics: Optional[dict] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


class EmergentBehavior(BaseModel):
    """Emergent behavior"""
    
    name: str
    description: str
    utility_score: float
    phases_involved: list[str]
    emergence_count: int
    first_detected: str
    last_seen: str


class StatsResponse(BaseModel):
    """Unified stats response"""
    
    available: bool
    total_requests: Optional[int] = None
    successful_requests: Optional[int] = None
    failed_requests: Optional[int] = None
    avg_processing_time: Optional[float] = None
    current_mode: Optional[str] = None
    unification_level: Optional[str] = None
    generation: Optional[int] = None
    error: Optional[str] = None


class EvolutionResponse(BaseModel):
    """Evolution response"""
    
    available: bool
    generation: Optional[int] = None
    previous_generation: Optional[int] = None
    improvements: Optional[int] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


# Dependency injection - will be set by main app
_transcendent_service: Optional[TranscendentService] = None


def set_transcendent_service(service: TranscendentService):
    """Set the transcendent service instance"""
    global _transcendent_service
    _transcendent_service = service


def get_transcendent_service() -> TranscendentService:
    """Get transcendent service dependency"""
    if _transcendent_service is None:
        raise HTTPException(status_code=500, detail="Transcendent service not initialized")
    return _transcendent_service


@router.get("/health", response_model=HealthResponse)
async def get_health(
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Get comprehensive system health metrics.
    
    Returns health scores for all subsystems and performance metrics.
    """
    try:
        health = transcendent_service.get_system_health()
        return HealthResponse(**health)
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/behaviors", response_model=list[EmergentBehavior])
async def get_emergent_behaviors(
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Detect emergent behaviors from phase interactions.
    
    Returns list of behaviors with utility scores.
    """
    try:
        behaviors = transcendent_service.detect_emergent_behaviors()
        return [EmergentBehavior(**b) for b in behaviors]
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Get unified system statistics.
    
    Returns complete statistics including requests, timing, and generation.
    """
    try:
        stats = transcendent_service.get_unified_stats()
        return StatsResponse(**stats)
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/mode")
async def set_cognitive_mode(
    request: CognitiveModeRequest,
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Set cognitive mode for adaptive behavior.
    
    Modes:
    - REACTIVE: Fast reflexes (~50ms)
    - PROACTIVE: Planned responses (~200ms)
    - REFLECTIVE: Deep analysis (~1000ms)
    - CREATIVE: Novel solutions (~2000ms)
    - COLLABORATIVE: Multi-agent (~3000ms)
    - TRANSCENDENT: Full integration (~5000ms)
    """
    try:
        result = transcendent_service.set_cognitive_mode(request.mode)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("reason", "Mode change failed")
            )
        
        return result
    except HTTPException:
        raise
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/evolve", response_model=EvolutionResponse)
async def evolve_system(
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Trigger system evolution (generation advancement).
    
    Advances the system to next generation with improvements.
    """
    try:
        result = transcendent_service.evolve_system()
        return EvolutionResponse(**result)
    except AstraError as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/status")
async def get_status(
    transcendent_service: TranscendentService = Depends(get_transcendent_service),
):
    """
    Get TranscendentOS availability status.
    
    Returns whether the unified cognitive system is available and operational.
    """
    try:
        is_available = transcendent_service.is_available()
        
        status_info = {
            "available": is_available,
            "version": "2.5",
            "phases_integrated": 9 if is_available else 0,
        }
        
        if is_available:
            stats = transcendent_service.get_unified_stats()
            if stats.get("available"):
                status_info["current_mode"] = stats.get("current_mode")
                status_info["generation"] = stats.get("generation")
                status_info["total_requests"] = stats.get("total_requests")
        
        return status_info
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
        }
