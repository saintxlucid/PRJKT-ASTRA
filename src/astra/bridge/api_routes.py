"""
ASTRA Bridge FastAPI Routes
REST endpoints for cryptic input transformation.

Endpoints:
- POST /v1/bridge/ingest - Transform cryptic text into intents/facts
- GET /v1/bridge/healthz - Health check with subcomponents
- GET /v1/bridge/registry - View stored facts
- POST /v1/bridge/hydrate - Load memory graph
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import structlog

from .config import BridgeConfig
from .schemas import BridgeEvent, BridgeRouteResult
from .interpreter import interpret
from .router import route
from .memory_bridge import MemoryBridgeService
from .tool_bridge import ToolBridgeService
from .registry import BridgeRegistry

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/v1/bridge", tags=["bridge"])

# Global instances (initialized by setup_bridge)
_config: Optional[BridgeConfig] = None
_mem_service: Optional[MemoryBridgeService] = None
_tool_service: Optional[ToolBridgeService] = None
_registry: Optional[BridgeRegistry] = None


def setup_bridge(
    config: BridgeConfig,
    mem_service: MemoryBridgeService,
    tool_service: ToolBridgeService,
    registry: BridgeRegistry
):
    """Initialize bridge services (call from app startup)"""
    global _config, _mem_service, _tool_service, _registry
    _config = config
    _mem_service = mem_service
    _tool_service = tool_service
    _registry = registry
    logger.info("bridge_api_initialized")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class IngestRequest(BaseModel):
    """Request to ingest cryptic text"""
    text: str = Field(..., description="Cryptic input text to process")
    quote_raw: bool = Field(False, description="Bypass interpretation, treat as quote")
    rid: Optional[str] = Field(None, description="Request ID for tracking")


class IngestResponse(BaseModel):
    """Response from ingest endpoint"""
    rid: str
    intents: list
    facts: list
    route_result: dict
    safe_text: str
    redactions: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    enabled: bool
    subcomponents: dict


class HydrateRequest(BaseModel):
    """Request to hydrate memory graph"""
    chroma_path: Optional[str] = Field(None, description="Path to Chroma collection")
    sqlite_ep_path: Optional[str] = Field(None, description="Path to episodic SQLite DB")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest) -> IngestResponse:
    """
    Transform cryptic input into structured intents/facts.
    Routes to Memory/Tools/Dialogue based on interpretation.
    """
    if not _config or not _mem_service or not _tool_service:
        raise HTTPException(status_code=503, detail="Bridge not initialized")
    
    if not _config.enabled:
        raise HTTPException(status_code=503, detail="Bridge disabled via config")
    
    try:
        # Create event with current timestamp
        import time
        event = BridgeEvent(
            text=req.text,
            quote_raw=req.quote_raw,
            rid=req.rid,
            ts=time.time()
        )
        
        # Interpret
        payload = interpret(event, _config)
        
        # Route
        result = route(payload, _config, _mem_service, _tool_service)
        
        # Register facts
        if _registry:
            for fact in payload.get("facts", []):
                _registry.register(fact)
        
        logger.info(
            "bridge_ingest_complete",
            rid=event.rid,
            intents=len(payload.get("intents", [])),
            facts=len(payload.get("facts", [])),
            writes=len(result.writes),
            tool_calls=len(result.tool_calls)
        )
        
        return IngestResponse(
            rid=event.rid,
            intents=payload.get("intents", []),
            facts=payload.get("facts", []),
            route_result={
                "writes": result.writes,
                "tool_calls": result.tool_calls,
                "reply": result.reply,
                "discarded": result.discarded,
                "metrics": result.metrics
            },
            safe_text=payload.get("safe_text", req.text),
            redactions=payload.get("redactions", 0)
        )
        
    except Exception as e:
        logger.error("bridge_ingest_error", error=str(e), rid=req.rid)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Health check with subcomponent status"""
    if not _config:
        return HealthResponse(
            status="uninitialized",
            enabled=False,
            subcomponents={}
        )
    
    subcomponents = {
        "config": "ok" if _config else "missing",
        "memory_service": "ok" if _mem_service else "missing",
        "tool_service": "ok" if _tool_service else "missing",
        "registry": "ok" if _registry else "missing",
    }
    
    all_ok = all(v == "ok" for v in subcomponents.values())
    
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        enabled=_config.enabled if _config else False,
        subcomponents=subcomponents
    )


@router.get("/registry")
async def get_registry():
    """View stored bridge facts"""
    if not _registry:
        raise HTTPException(status_code=503, detail="Registry not initialized")
    
    try:
        facts = _registry.get_all()
        return {
            "facts": [
                {
                    "subject": f.subject,
                    "predicate": f.predicate,
                    "object": f.object,
                    "tags": f.tags,
                    "provenance": f.provenance,
                    "confidence": f.confidence
                }
                for f in facts
            ],
            "count": len(facts)
        }
    except Exception as e:
        logger.error("bridge_registry_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/hydrate")
async def hydrate(req: HydrateRequest):
    """Load memory graph paths (configure LTM/Episodic connections)"""
    if not _mem_service:
        raise HTTPException(status_code=503, detail="Memory service not initialized")
    
    try:
        result = {
            "chroma_configured": bool(req.chroma_path),
            "sqlite_configured": bool(req.sqlite_ep_path)
        }
        
        # Note: Actual hydration logic would update adapters here
        # For now, just acknowledge the paths
        
        logger.info(
            "bridge_hydrate",
            chroma=req.chroma_path,
            sqlite=req.sqlite_ep_path
        )
        
        return result
        
    except Exception as e:
        logger.error("bridge_hydrate_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
