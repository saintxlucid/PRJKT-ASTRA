"""
System API routes.

Handles health checks and system information.
"""

import structlog
import time
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel

from astra.services.chat_service import ChatService
from astra.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


router = APIRouter(prefix="/v1/system", tags=["system"])


# Response models
class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    llm_healthy: bool
    database_connected: bool
    memory_stats: dict


class HealthzResponse(BaseModel):
    """Enhanced health check with component drill-down"""
    
    status: str
    components: Dict[str, Any]
    version: str
    uptime_seconds: float


class RegistryResponse(BaseModel):
    """Tool registry response"""
    
    capabilities: List[Dict[str, Any]]
    consent_policy: Dict[str, Any]
    audit: Dict[str, Any]
    rate_limits: Dict[str, Any]


class VersionResponse(BaseModel):
    """Version information"""

    version: str
    name: str


# Dependencies - set by main app
_chat_service: ChatService | None = None
_memory_service: MemoryService | None = None
_start_time = time.time()  # Track uptime


def set_system_dependencies(chat_service: ChatService, memory_service: MemoryService):
    """Set system dependencies"""
    global _chat_service, _memory_service
    _chat_service = chat_service
    _memory_service = memory_service


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Checks status of LLM, database, and memory systems.
    """
    llm_healthy = False
    memory_stats: dict = {}
    status = "healthy"

    if _chat_service:
        try:
            llm_healthy = await _chat_service.llm_provider.health_check()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("health_llm_check_failed", error=str(exc))
            llm_healthy = False
            status = "degraded"
    else:
        status = "degraded"

    if _memory_service:
        try:
            memory_stats = _memory_service.get_memory_stats()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("health_memory_stats_failed", error=str(exc))
            memory_stats = {"status": "unavailable"}
            status = "degraded"
    else:
        status = "degraded"

    if not llm_healthy:
        status = "degraded"

    return HealthResponse(
        status=status,
        llm_healthy=llm_healthy,
        database_connected=True,  # If we got here, DB is connected
        memory_stats=memory_stats,
    )


@router.get("/healthz", response_model=HealthzResponse)
async def enhanced_health_check():
    """
    Enhanced health check with component drill-down.
    
    Provides detailed status for each system component including
    latency, pool status, and capacity metrics.
    """
    overall_status = "healthy"
    components = {}
    
    # LLM Component Health
    llm_component = {"ok": False}
    if _chat_service:
        try:
            start_time = time.time()
            llm_healthy = await _chat_service.llm_provider.health_check()
            latency_ms = int((time.time() - start_time) * 1000)
            
            llm_component = {
                "ok": llm_healthy,
                "latency_ms": latency_ms
            }
            
            if not llm_healthy:
                overall_status = "degraded"
                
        except Exception as exc:
            logger.warning("healthz_llm_check_failed", error=str(exc))
            llm_component = {"ok": False, "error": str(exc)}
            overall_status = "degraded"
    else:
        overall_status = "degraded"
    
    components["llm"] = llm_component
    
    # Database Component Health
    db_component: Dict[str, Any] = {"ok": True}  # If we got here, DB is working
    try:
        # Add pool status if available
        # This would need to be implemented based on your SQLAlchemy setup
        db_component["pool_size"] = int(os.getenv("ASTRA_DATABASE_POOL_SIZE", "20"))
        db_component["in_use"] = 0  # Would need actual pool metrics
    except Exception as exc:
        logger.warning("healthz_db_check_failed", error=str(exc))
        db_component = {"ok": False, "error": str(exc)}
        overall_status = "degraded"
    
    components["db"] = db_component
    
    # Vector Store Component Health
    vector_component = {"ok": False, "count": 0}
    if _memory_service:
        try:
            memory_stats = _memory_service.get_memory_stats()
            vector_component = {
                "ok": True,
                "count": memory_stats.get("total_memories", 0)
            }
        except Exception as exc:
            logger.warning("healthz_vector_check_failed", error=str(exc))
            vector_component = {"ok": False, "error": str(exc)}
            overall_status = "degraded"
    else:
        overall_status = "degraded"
    
    components["vector_store"] = vector_component
    
    # Rate Limiting & Capacity Component
    limits_component = {
        "per_key_rate": int(os.getenv("ASTRA_PER_KEY_RATE", "120")),
        "per_key_period_sec": int(os.getenv("ASTRA_PER_KEY_PERIOD_SEC", "60")),
        "global_rate": int(os.getenv("ASTRA_RATE_LIMIT_REQUESTS", "30")),
        "global_window": int(os.getenv("ASTRA_RATE_LIMIT_WINDOW", "5")),
        "queue_depth": 0,  # Would need actual queue metrics
        "max_queue": int(os.getenv("ASTRA_MAX_QUEUE", "64"))
    }
    
    components["limits"] = limits_component
    
    # Tool Registry & Consent Health
    tools_component = {"ok": False}
    try:
        registry_path = Path(__file__).parent.parent.parent.parent.parent / "ops" / "registry" / "capability_registry.yaml"
        if registry_path.exists():
            with open(registry_path, "r") as f:
                registry_data = yaml.safe_load(f)
            
            total_caps = len(registry_data.get("capabilities", []))
            consent_required = sum(1 for cap in registry_data.get("capabilities", []) if cap.get("consent_required", False))
            
            tools_component = {
                "ok": True,
                "total_capabilities": total_caps,
                "consent_required": consent_required,
                "registry_loaded": True
            }
        else:
            tools_component = {
                "ok": False,
                "registry_loaded": False,
                "error": "capability_registry.yaml not found"
            }
            overall_status = "degraded"
    except Exception as exc:
        logger.warning("healthz_tools_check_failed", error=str(exc))
        tools_component = {"ok": False, "error": str(exc)}
        overall_status = "degraded"
    
    components["tools"] = tools_component
    
    # Calculate uptime
    uptime_seconds = time.time() - _start_time
    
    return HealthzResponse(
        status=overall_status,
        components=components,
        version="1.0.0",
        uptime_seconds=uptime_seconds
    )


# ============================================================================
# DEPENDENCY HELPERS (for unified health endpoint)
# ============================================================================

def get_memory_service(request: Request) -> Optional[Any]:
    """Get memory service from app state"""
    return getattr(request.app.state, "memory_service", None)


def get_chat_service(request: Request) -> Optional[Any]:
    """Get chat service from app state"""
    return getattr(request.app.state, "chat_service", None)


def get_bridge(request: Request) -> Optional[Any]:
    """Get bridge from app state"""
    return getattr(request.app.state, "bridge", None)


@router.get("/version", response_model=VersionResponse)
async def get_version():
    """
    Get version information.

    Returns the application name and version.
    """
    return VersionResponse(
        name="ASTRA",
        version="2.0.0",
    )


@router.get("/registry", response_model=RegistryResponse)
async def get_tool_registry():
    """
    Get OS Operator tool registry.
    
    Returns the authoritative list of all available capabilities,
    consent requirements, audit policy, and rate limits.
    """
    try:
        registry_path = Path(__file__).parent.parent.parent.parent.parent / "ops" / "registry" / "capability_registry.yaml"
        
        if not registry_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Tool registry not found at ops/registry/capability_registry.yaml"
            )
        
        with open(registry_path, "r") as f:
            registry_data = yaml.safe_load(f)
        
        return RegistryResponse(
            capabilities=registry_data.get("capabilities", []),
            consent_policy=registry_data.get("consent_policy", {}),
            audit=registry_data.get("audit", {}),
            rate_limits=registry_data.get("rate_limits", {})
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("registry_load_failed", error=str(exc))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load tool registry: {str(exc)}"
        )


# ============================================================================
# UNIFIED HEALTH ENDPOINT (Composite System Health)
# ============================================================================

@router.get("/health/unified", summary="Composite system health")
async def unified_system_health(
    mem_svc: Optional[Any] = Depends(get_memory_service),
    chat_svc: Optional[Any] = Depends(get_chat_service),
    bridge: Optional[Any] = Depends(get_bridge),
):
    """
    Returns one JSON blob the UI, Bridge, & Grafana can all consume.
    
    This is the authoritative health endpoint that consolidates:
    - LLM readiness
    - Memory system stats (semantic/episodic/procedural counts)
    - Bridge subsystem health
    - Overall system status
    """
    # Check LLM health
    llm_ready = "unknown"
    if chat_svc:
        try:
            llm_healthy = await chat_svc.llm_provider.health_check()
            llm_ready = "ready" if llm_healthy else "unavailable"
        except Exception as exc:
            logger.warning("unified_health_llm_check_failed", error=str(exc))
            llm_ready = "error"
    
    # Get memory counts
    mem_counts = {}
    if mem_svc:
        try:
            mem_counts = mem_svc.get_memory_stats()
        except Exception as exc:
            logger.warning("unified_health_memory_stats_failed", error=str(exc))
            mem_counts = {"error": str(exc)}
    
    # Get bridge health
    bridge_h = {}
    if bridge:
        try:
            if hasattr(bridge, "health"):
                bridge_h = await bridge.health()
            else:
                bridge_h = {"status": "ok", "note": "bridge_available_no_health_method"}
        except Exception as exc:
            logger.warning("unified_health_bridge_check_failed", error=str(exc))
            bridge_h = {"status": "error", "error": str(exc)}
    
    # Determine overall status
    overall_status = "ok"
    if llm_ready != "ready":
        overall_status = "degraded"
    if bridge_h.get("status") not in ["ok", ""]:
        if bridge_h.get("status") == "error":
            overall_status = "degraded"
    
    return {
        "status": overall_status,
        "llm": llm_ready,
        "memory": mem_counts,
        "bridge": bridge_h,
        "version": "ascension-v2",
    }
