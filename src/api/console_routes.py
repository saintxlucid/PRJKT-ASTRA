"""
Operator Console API Endpoints - FastAPI routes for the console MVP.

Part of Week-3 Days 21-24: Operator Console MVP

Endpoints:
  - POST /console/plan/preview - Generate visual plan preview
  - POST /console/consent - Record consent decision
  - GET /console/consent/history - Get consent history
  - GET /console/memory/browse - Browse memories with filters
  - GET /console/events - Get event log with filters
  - GET /console/events/replay - Replay event sequence
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from src.services.plan_preview_service import (
    PlanPreviewService,
    ActionType,
    RiskLevel,
)
from src.services.consent_service import ConsentService, ConsentDecision


# Initialize services
plan_service = PlanPreviewService()
consent_service = ConsentService()

# Create router
router = APIRouter(prefix="/console", tags=["console"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ActionRequest(BaseModel):
    """Action in a plan"""
    type: str = Field(..., description="Action type: read, write, execute, network, memory, query")
    description: str = Field(..., description="Human-readable action description")
    resources: dict[str, str] = Field(default_factory=dict, description="Resource identifiers")
    dependencies: list[str] = Field(default_factory=list, description="IDs of prerequisite actions")


class PlanPreviewRequest(BaseModel):
    """Request to preview a plan"""
    plan_id: str = Field(..., description="Unique plan identifier")
    title: str = Field(..., description="Plan title")
    description: str = Field(..., description="Plan description")
    actions: list[ActionRequest] = Field(..., description="List of actions in the plan")


class ConsentRequest(BaseModel):
    """Request to record consent"""
    plan_id: str = Field(..., description="Plan identifier")
    action_id: str = Field(..., description="Action identifier")
    decision: str = Field(..., description="Decision: approved, denied, deferred")
    reason: str = Field(..., description="User's reason for decision")
    user: str = Field(default="operator", description="Username")
    expires_in_hours: Optional[int] = Field(None, description="Consent expiration time")


class MemoryBrowseRequest(BaseModel):
    """Request to browse memories"""
    query: Optional[str] = Field(None, description="Semantic search query")
    filter_type: Optional[str] = Field(None, description="Filter by memory type")
    filter_source: Optional[str] = Field(None, description="Filter by source file")
    limit: int = Field(10, description="Max results", ge=1, le=100)


# ============================================================================
# Plan Preview Endpoints
# ============================================================================


@router.post("/plan/preview")
async def preview_plan(request: PlanPreviewRequest) -> dict:
    """
    Generate a visual preview of an action plan.
    
    Returns:
        Dict with plan graph data (nodes, edges, metadata)
    
    Example:
        ```
        POST /console/plan/preview
        {
          "plan_id": "plan_001",
          "title": "Update Config",
          "description": "Modify nginx config",
          "actions": [
            {
              "type": "read",
              "description": "Read nginx config",
              "resources": {"file": "/etc/nginx/nginx.conf"},
              "dependencies": []
            }
          ]
        }
        ```
    """
    # Convert Pydantic models to dicts
    actions = [
        {
            "type": action.type,
            "description": action.description,
            "resources": action.resources,
            "dependencies": action.dependencies,
        }
        for action in request.actions
    ]
    
    # Generate plan preview
    try:
        plan = plan_service.create_plan_preview(
            plan_id=request.plan_id,
            title=request.title,
            description=request.description,
            actions=actions,
        )
        
        return plan_service.to_dict(plan)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create plan preview: {e}")


@router.get("/plan/{plan_id}")
async def get_plan(plan_id: str) -> dict:
    """
    Retrieve a previously created plan preview.
    
    Returns:
        Dict with plan graph data
    """
    plan = plan_service.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    
    return plan_service.to_dict(plan)


# ============================================================================
# Consent Management Endpoints
# ============================================================================


@router.post("/consent")
async def record_consent(request: ConsentRequest) -> dict:
    """
    Record a consent decision for an action.
    
    Returns:
        Dict with consent record
    
    Example:
        ```
        POST /console/consent
        {
          "plan_id": "plan_001",
          "action_id": "plan_001_action_2",
          "decision": "approved",
          "reason": "Necessary for config update",
          "user": "operator"
        }
        ```
    """
    try:
        decision = ConsentDecision(request.decision.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid decision: {request.decision}. Must be approved/denied/deferred",
        )
    
    try:
        record = consent_service.record_consent(
            plan_id=request.plan_id,
            action_id=request.action_id,
            decision=decision,
            reason=request.reason,
            user=request.user,
            expires_in_hours=request.expires_in_hours,
        )
        
        return {
            "plan_id": record.plan_id,
            "action_id": record.action_id,
            "decision": record.decision.value,
            "reason": record.reason,
            "timestamp": record.timestamp,
            "expires_at": record.expires_at,
            "user": record.user,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record consent: {e}")


@router.get("/consent/{plan_id}/{action_id}")
async def check_consent(plan_id: str, action_id: str) -> dict:
    """
    Check if an action has been consented to.
    
    Returns:
        Dict with has_consent (bool) and reason (if denied)
    """
    has_consent, reason = consent_service.check_consent(plan_id, action_id)
    
    return {
        "plan_id": plan_id,
        "action_id": action_id,
        "has_consent": has_consent,
        "reason": reason,
    }


@router.get("/consent/history")
async def get_consent_history(
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    limit: int = Query(100, description="Max results", ge=1, le=1000),
) -> dict:
    """
    Get consent history, optionally filtered by plan_id.
    
    Returns:
        Dict with list of consent records
    """
    records = consent_service.get_consent_history(plan_id=plan_id, limit=limit)
    
    return {
        "count": len(records),
        "records": [
            {
                "plan_id": r.plan_id,
                "action_id": r.action_id,
                "decision": r.decision.value,
                "reason": r.reason,
                "timestamp": r.timestamp,
                "expires_at": r.expires_at,
                "user": r.user,
            }
            for r in records
        ],
    }


# ============================================================================
# Memory Browser Endpoints
# ============================================================================


@router.get("/memory/browse")
async def browse_memories(
    query: Optional[str] = Query(None, description="Semantic search query"),
    filter_type: Optional[str] = Query(None, description="Filter by memory type"),
    filter_source: Optional[str] = Query(None, description="Filter by source file"),
    limit: int = Query(10, description="Max results", ge=1, le=100),
) -> dict:
    """
    Browse memories with semantic search and metadata filters.
    
    Returns:
        Dict with list of memories (id, text, source, timestamp)
    
    Example:
        ```
        GET /console/memory/browse?query=architecture&limit=5
        GET /console/memory/browse?filter_source=ARCH.md&limit=10
        ```
    """
    # This is a placeholder - will integrate with ChromaMemoryGatewayBGE
    # For now, return mock data
    return {
        "query": query,
        "filters": {
            "type": filter_type,
            "source": filter_source,
        },
        "count": 0,
        "memories": [],
        "message": "Memory browsing integration pending (ChromaMemoryGatewayBGE)",
    }


# ============================================================================
# Event Log Viewer Endpoints
# ============================================================================


@router.get("/events")
async def get_events(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    since: Optional[str] = Query(None, description="Filter by timestamp (ISO 8601)"),
    limit: int = Query(100, description="Max results", ge=1, le=1000),
) -> dict:
    """
    Get event log with filters.
    
    Returns:
        Dict with list of events
    
    Example:
        ```
        GET /console/events?limit=20
        GET /console/events?event_type=memory_searched&limit=10
        GET /console/events?since=2025-11-02T00:00:00Z&limit=50
        ```
    """
    # This is a placeholder - will integrate with EventStore
    # For now, return mock data
    return {
        "filters": {
            "event_type": event_type,
            "since": since,
        },
        "count": 0,
        "events": [],
        "message": "Event log integration pending (EventStore)",
    }


@router.get("/events/replay")
async def replay_events(
    start: str = Query(..., description="Start timestamp (ISO 8601)"),
    end: str = Query(..., description="End timestamp (ISO 8601)"),
) -> dict:
    """
    Replay event sequence between two timestamps.
    
    Useful for answering "Why did ASTRA do X?"
    
    Returns:
        Dict with list of events in chronological order
    
    Example:
        ```
        GET /console/events/replay?start=2025-11-02T10:00:00Z&end=2025-11-02T11:00:00Z
        ```
    """
    # This is a placeholder - will integrate with EventStore
    # For now, return mock data
    return {
        "start": start,
        "end": end,
        "count": 0,
        "events": [],
        "message": "Event replay integration pending (EventStore)",
    }


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def console_health() -> dict:
    """
    Health check for Operator Console API.
    
    Returns:
        Dict with status and service availability
    """
    return {
        "status": "operational",
        "services": {
            "plan_preview": "operational",
            "consent": "operational",
            "memory_browser": "pending_integration",
            "event_viewer": "pending_integration",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
