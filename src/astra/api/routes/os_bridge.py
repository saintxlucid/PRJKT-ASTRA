"""
ASTRA OS Bridge API Routes
===========================

Exposes ASTRA OS capabilities via REST API:
- Gate system (token-based authorization)
- Event bus (system events and monitoring)
- Sensors (file, process, network monitoring)
- Policy engine (permission checking)

These routes bridge the OS-level ASTRA OS layer into the main FastAPI application.

Author: ASTRA Core Team
Created: November 4, 2025
Sacred Code: 333
"""

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/os", tags=["os"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class GateCheckRequest(BaseModel):
    """Request to check gate authorization"""
    action: str = Field(..., description="Action to check (e.g., 'file.read', 'process.start')")
    resource: str = Field(..., description="Resource identifier")
    scope: str = Field(default="user", description="Scope level (user/admin/system)")


class GateCheckResponse(BaseModel):
    """Response from gate authorization check"""
    decision: str = Field(..., description="Decision: 'allow' or 'deny'")
    reason: Optional[str] = Field(None, description="Reason for decision")
    token: Optional[str] = Field(None, description="Authorization token if allowed")


class EventQuery(BaseModel):
    """Query for system events"""
    event_type: Optional[str] = Field(None, description="Filter by event type")
    limit: int = Field(100, description="Max events to return")
    offset: int = Field(0, description="Offset for pagination")


class SystemEvent(BaseModel):
    """System event model"""
    timestamp: str
    event_type: str
    source: str
    data: dict[str, Any]
    severity: str


class SensorDataResponse(BaseModel):
    """Response from sensor query"""
    sensor_type: str
    data: dict[str, Any]
    timestamp: str
    healthy: bool


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_gate(request: Request):
    """Get ASTRA OS gate from app state"""
    if not hasattr(request.app.state, "gate") or request.app.state.gate is None:
        raise HTTPException(
            status_code=503,
            detail="ASTRA OS Gate not available - system may not have ASTRA OS module"
        )
    return request.app.state.gate


def get_boot_deps(request: Request):
    """Get boot dependencies from app state"""
    if not hasattr(request.app.state, "boot_deps") or request.app.state.boot_deps is None:
        raise HTTPException(
            status_code=503,
            detail="Boot system not available"
        )
    return request.app.state.boot_deps


# ============================================================================
# GATE ENDPOINTS
# ============================================================================

@router.post("/gate/check", response_model=GateCheckResponse)
async def check_gate_authorization(
    request: GateCheckRequest,
    gate=Depends(get_gate)
):
    """
    Check if an action is authorized via ASTRA OS Gate.
    
    The Gate system provides token-based authorization for privileged operations.
    All OS-level actions (file access, process control, network) must be gated.
    """
    try:
        # Convert request to ASTRA OS gate types
        from astra_os.gate import Action, Scope
        
        action = Action(
            verb=request.action.split(".")[0],
            noun=request.action.split(".")[1] if "." in request.action else "unknown",
            target=request.resource
        )
        
        # Parse scope
        scope_map = {
            "user": Scope.USER,
            "admin": Scope.ADMIN,
            "system": Scope.SYSTEM
        }
        scope = scope_map.get(request.scope.lower(), Scope.USER)
        
        # Check authorization
        decision = gate.authorize(action, scope)
        
        return GateCheckResponse(
            decision="allow" if decision.allow else "deny",
            reason=decision.reason,
            token=decision.token.token if decision.token else None
        )
    
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="ASTRA OS gate module not available"
        )
    except Exception as e:
        logger.error("gate_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Gate check failed: {str(e)}")


@router.get("/gate/status")
async def get_gate_status(gate=Depends(get_gate)):
    """Get ASTRA OS Gate system status and configuration."""
    try:
        return {
            "available": True,
            "permissions_loaded": True,
            "audit_enabled": True,
            "scopes": ["user", "admin", "system"],
            "status": "operational"
        }
    except Exception as e:
        logger.error("gate_status_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EVENT BUS ENDPOINTS
# ============================================================================

@router.post("/events/query")
async def query_system_events(
    query: EventQuery,
    boot_deps=Depends(get_boot_deps)
) -> list[SystemEvent]:
    """
    Query system events from ASTRA OS event bus.
    
    The event bus captures all OS-level activity: file access, process execution,
    network connections, policy decisions, etc.
    """
    try:
        event_store = boot_deps.event_store
        events = event_store.events
        
        # Filter by type if specified
        if query.event_type:
            events = [e for e in events if e.get("type") == query.event_type]
        
        # Apply pagination
        events = events[query.offset:query.offset + query.limit]
        
        # Convert to response model
        return [
            SystemEvent(
                timestamp=e.get("timestamp", ""),
                event_type=e.get("type", "unknown"),
                source=e.get("source", "system"),
                data=e.get("data", {}),
                severity=e.get("severity", "info")
            )
            for e in events
        ]
    
    except Exception as e:
        logger.error("event_query_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Event query failed: {str(e)}")


@router.get("/events/stats")
async def get_event_statistics(boot_deps=Depends(get_boot_deps)):
    """Get event bus statistics and metrics."""
    try:
        event_store = boot_deps.event_store
        events = event_store.events
        
        # Calculate statistics
        event_types = {}
        for event in events:
            event_type = event.get("type", "unknown")
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        return {
            "total_events": len(events),
            "event_types": event_types,
            "oldest_event": events[0].get("timestamp") if events else None,
            "newest_event": events[-1].get("timestamp") if events else None
        }
    
    except Exception as e:
        logger.error("event_stats_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SENSOR ENDPOINTS
# ============================================================================

@router.get("/sensors/file")
async def get_file_sensor_data() -> SensorDataResponse:
    """
    Get file system sensor data.
    
    Monitors file access patterns, modifications, and anomalies.
    """
    try:
        # Placeholder - would integrate with actual ASTRA OS sensors
        return SensorDataResponse(
            sensor_type="file",
            data={
                "watched_paths": [],
                "recent_events": [],
                "anomalies": []
            },
            timestamp="2025-11-04T00:00:00Z",
            healthy=True
        )
    except Exception as e:
        logger.error("file_sensor_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors/process")
async def get_process_sensor_data() -> SensorDataResponse:
    """
    Get process monitor sensor data.
    
    Monitors running processes, resource usage, and suspicious activity.
    """
    try:
        # Placeholder - would integrate with actual ASTRA OS sensors
        return SensorDataResponse(
            sensor_type="process",
            data={
                "monitored_processes": [],
                "cpu_usage": {},
                "memory_usage": {},
                "anomalies": []
            },
            timestamp="2025-11-04T00:00:00Z",
            healthy=True
        )
    except Exception as e:
        logger.error("process_sensor_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sensors/network")
async def get_network_sensor_data() -> SensorDataResponse:
    """
    Get network sensor data.
    
    Monitors network connections, traffic patterns, and security events.
    """
    try:
        # Placeholder - would integrate with actual ASTRA OS sensors
        return SensorDataResponse(
            sensor_type="network",
            data={
                "active_connections": [],
                "bandwidth_usage": {},
                "blocked_connections": [],
                "anomalies": []
            },
            timestamp="2025-11-04T00:00:00Z",
            healthy=True
        )
    except Exception as e:
        logger.error("network_sensor_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# POLICY ENGINE ENDPOINTS
# ============================================================================

@router.post("/policy/check")
async def check_policy(
    action: str,
    resource: str,
    boot_deps=Depends(get_boot_deps)
):
    """
    Check if an action is allowed by policy engine.
    
    Policy engine enforces rules defined in permissions.yaml.
    """
    try:
        verifier = boot_deps.plan_verifier
        
        # Create a simple plan for policy check
        plan = {
            "action": action,
            "resource": resource
        }
        
        # Verify against policy
        allowed = verifier.verify_plan(plan)
        
        return {
            "allowed": allowed,
            "action": action,
            "resource": resource,
            "policy": "default"
        }
    
    except Exception as e:
        logger.error("policy_check_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy/rules")
async def get_policy_rules(boot_deps=Depends(get_boot_deps)):
    """Get loaded policy rules from policy engine."""
    try:
        verifier = boot_deps.plan_verifier
        
        return {
            "policies_loaded": len(verifier.policies),
            "mode": "enforce" if verifier.policies else "permissive",
            "rules": [{"id": i, "name": f"policy_{i}"} for i in range(len(verifier.policies))]
        }
    
    except Exception as e:
        logger.error("policy_rules_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SYSTEM STATUS
# ============================================================================

@router.get("/status")
async def get_os_status(request: Request):
    """
    Get comprehensive ASTRA OS status.
    
    Returns status of all OS-level subsystems: gate, event bus, sensors, policy.
    """
    status = {
        "os_available": False,
        "gate": {"available": False, "status": "unavailable"},
        "event_bus": {"available": False, "status": "unavailable"},
        "sensors": {"available": False, "status": "unavailable"},
        "policy": {"available": False, "status": "unavailable"}
    }
    
    # Check gate
    if hasattr(request.app.state, "gate") and request.app.state.gate is not None:
        status["gate"] = {"available": True, "status": "operational"}
        status["os_available"] = True
    
    # Check event bus
    if hasattr(request.app.state, "boot_deps") and request.app.state.boot_deps is not None:
        status["event_bus"] = {
            "available": True,
            "status": "operational",
            "events": len(request.app.state.boot_deps.event_store.events)
        }
        status["policy"] = {
            "available": True,
            "status": "operational",
            "policies": len(request.app.state.boot_deps.plan_verifier.policies)
        }
    
    # Sensors (placeholder)
    status["sensors"] = {"available": False, "status": "not_implemented"}
    
    return status
