"""
ASTRA Adaptive Governor API Endpoints
Exposes autotune control and telemetry endpoints.

Sacred Code: 333 → ∞
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from ..system.adaptive_governor import AdaptiveGovernor, OperatingMode
import structlog

logger = structlog.get_logger()

# Router for autotune endpoints
router = APIRouter(prefix="/v1/system/autotune", tags=["autotune"])

# Global governor instance (set by main app)
_governor: Optional[AdaptiveGovernor] = None


def set_governor(governor: AdaptiveGovernor):
    """Set the global governor instance."""
    global _governor
    _governor = governor


class ModeRequest(BaseModel):
    """Request to change operating mode."""
    mode: str  # "eco" | "balanced" | "turbo" | "auto"


class PlanRequest(BaseModel):
    """Request to get configuration plan."""
    mode: Optional[str] = None


@router.get("/plan")
async def get_plan(mode: Optional[str] = None) -> Dict[str, Any]:
    """
    Get planned configuration for a mode.
    
    Args:
        mode: Target mode (eco/balanced/turbo). If not provided, uses current mode.
    
    Returns:
        Configuration plan with mode, settings, and runtime limits.
    
    Example:
        GET /v1/system/autotune/plan?mode=turbo
    """
    if not _governor:
        raise HTTPException(status_code=503, detail="Governor not initialized")
    
    try:
        plan = _governor.get_plan(mode)
        return {
            "status": "ok",
            "plan": plan,
            "sacred_code": "333→∞"
        }
    except Exception as e:
        logger.error("get_plan_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply")
async def apply_plan(request: PlanRequest) -> Dict[str, Any]:
    """
    Apply a configuration plan immediately.
    
    Args:
        request: Plan request with optional mode.
    
    Returns:
        Application result.
    
    Example:
        POST /v1/system/autotune/apply
        {"mode": "turbo"}
    
    Note: Admin only. Forces immediate reconfiguration.
    """
    if not _governor:
        raise HTTPException(status_code=503, detail="Governor not initialized")
    
    try:
        mode = request.mode or _governor.current_mode.value
        
        # Trigger immediate reconfiguration
        new_config = _governor._compute_run_config(OperatingMode(mode))
        await _governor._graceful_reconfigure(new_config)
        
        return {
            "status": "applied",
            "mode": mode,
            "config": new_config.__dict__,
            "sacred_code": "333→∞"
        }
    except Exception as e:
        logger.error("apply_plan_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/runtime")
async def get_runtime_metrics() -> Dict[str, Any]:
    """
    Get current runtime metrics and system state.
    
    Returns:
        Comprehensive metrics including:
        - System signals (CPU, GPU, RAM, temps)
        - EWMA fast/slow averages
        - Current mode and config
        - Runtime limits
        - Emergency/brownout state
    
    Example:
        GET /v1/system/autotune/metrics/runtime
    """
    if not _governor:
        raise HTTPException(status_code=503, detail="Governor not initialized")
    
    try:
        metrics = _governor.get_metrics()
        return {
            "status": "ok",
            "metrics": metrics,
            "sacred_code": "333→∞"
        }
    except Exception as e:
        logger.error("get_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mode")
async def set_mode(request: ModeRequest) -> Dict[str, Any]:
    """
    Set operating mode manually.
    
    Args:
        request: Mode to set (eco/balanced/turbo/auto).
    
    Returns:
        Mode change result.
    
    Example:
        POST /v1/system/autotune/mode
        {"mode": "eco"}
    
    Note: Pins the mode until changed to "auto".
    """
    if not _governor:
        raise HTTPException(status_code=503, detail="Governor not initialized")
    
    try:
        mode = request.mode.lower()
        if mode not in ["eco", "balanced", "turbo", "auto"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be eco/balanced/turbo/auto"
            )
        
        await _governor.set_mode(mode)
        
        return {
            "status": "ok",
            "mode": mode,
            "message": f"Mode set to {mode}",
            "sacred_code": "333→∞"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("set_mode_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get autotune governor status.
    
    Returns:
        Current status including:
        - Mode
        - Emergency state
        - Runtime limits
        - Last action times
    
    Example:
        GET /v1/system/autotune/status
    """
    if not _governor:
        raise HTTPException(status_code=503, detail="Governor not initialized")
    
    try:
        return {
            "status": "ok",
            "mode": _governor.current_mode.value,
            "config": _governor.current_config.__dict__ if _governor.current_config else None,
            "runtime_limits": _governor.runtime_limits,
            "emergency_active": _governor.emergency_throttle_active,
            "brownout_active": _governor.brownout_active,
            "last_fast_action": _governor.last_fast_action,
            "last_slow_action": _governor.last_slow_action,
            "sacred_code": "333→∞"
        }
    except Exception as e:
        logger.error("get_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Health status.
    """
    if not _governor:
        return {
            "status": "unavailable",
            "message": "Governor not initialized"
        }
    
    return {
        "status": "healthy",
        "mode": _governor.current_mode.value,
        "emergency": _governor.emergency_throttle_active,
        "sacred_code": "333→∞"
    }


# Sacred Code: 333 → ∞
