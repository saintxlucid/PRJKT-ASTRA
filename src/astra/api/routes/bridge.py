"""
ASTRA Bridge API Routes
FastAPI endpoints for bridge ingestion, registry view, and health checks.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from time import time
from typing import Optional
import structlog

from ...bridge.config import BridgeConfig
from ...bridge.schemas import BridgeEvent, BridgeRouteResult
from ...bridge.interpreter import interpret
from ...bridge.registry import BridgeRegistry
from ...bridge.memory_bridge import MemoryBridgeService
from ...bridge.tool_bridge import ToolBridgeService
from ...bridge.router import route

logger = structlog.get_logger()

router = APIRouter(prefix="/v1/bridge", tags=["bridge"])

# Module-level singletons (can be replaced with dependency injection)
CFG = BridgeConfig()
REG = BridgeRegistry()
MEM = MemoryBridgeService()
TOOLS = ToolBridgeService()


class IngestBody(BaseModel):
    """Request body for bridge ingestion."""
    text: str
    quote_raw: bool = False
    request_id: Optional[str] = None
    channel: str = "text"
    source: str = "local"


@router.post("/ingest", response_model=BridgeRouteResult)
def ingest(body: IngestBody):
    """
    Ingest raw text through the bridge pipeline.
    
    Pipeline:
    1. Safety prefilter (redaction)
    2. Pattern matching
    3. Optional LLM abstraction
    4. Routing to Memory/Tools/Dialogue
    
    Returns:
        BridgeRouteResult with writes, tool_calls, reply, metrics
    """
    if not CFG.enabled:
        raise HTTPException(status_code=503, detail="Bridge disabled by config.")
    
    logger.info("bridge_ingest_request", source=body.source, channel=body.channel, length=len(body.text))
    
    # Create bridge event
    ev = BridgeEvent(
        text=body.text,
        quote_raw=body.quote_raw,
        request_id=body.request_id,
        channel=body.channel,
        source=body.source,
        ts=time()
    )
    
    # Interpret
    payload = interpret(ev, CFG)
    
    # Store raw quote if requested
    if body.quote_raw:
        REG.add_raw(ev.text, ev.request_id)
    
    # Route
    res = route(payload, CFG, MEM, TOOLS)
    
    logger.info("bridge_ingest_complete", writes=len(res.writes), tool_calls=len(res.tool_calls))
    
    return res


@router.get("/registry")
def registry_view():
    """
    View recent facts and raw quotes from the bridge registry.
    
    Returns last 500 facts and 200 raw quotes.
    """
    logger.info("bridge_registry_view_request")
    return REG.all()


@router.get("/healthz")
def healthz():
    """
    Health check endpoint.
    
    Returns bridge configuration and status.
    """
    return {
        "enabled": CFG.enabled,
        "threshold": CFG.interpret_conf_threshold,
        "max_toolcalls": CFG.max_toolcalls_per_req,
        "ok": True,
        "version": "1.0.0"
    }


@router.post("/config")
def update_config(enabled: Optional[bool] = None,
                  threshold: Optional[float] = None,
                  max_toolcalls: Optional[int] = None):
    """
    Update bridge configuration at runtime.
    
    Use sparingly - most config should be via environment variables.
    """
    global CFG
    
    if enabled is not None:
        CFG.enabled = enabled
    if threshold is not None:
        CFG.interpret_conf_threshold = threshold
    if max_toolcalls is not None:
        CFG.max_toolcalls_per_req = max_toolcalls
    
    logger.info("bridge_config_updated", enabled=CFG.enabled, threshold=CFG.interpret_conf_threshold)
    
    return {
        "enabled": CFG.enabled,
        "threshold": CFG.interpret_conf_threshold,
        "max_toolcalls": CFG.max_toolcalls_per_req
    }
