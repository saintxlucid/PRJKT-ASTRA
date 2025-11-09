"""
Persistence API routes for Phase 0.

Provides health checks and basic state manager status endpoints.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter(prefix="/v1/persistence", tags=["persistence"])


class PersistenceHealthResponse(BaseModel):
    """Persistence health check response"""
    wal: bool
    redis: bool
    postgres: bool
    overall_healthy: bool


@router.get("/health", response_model=PersistenceHealthResponse)
async def persistence_health(request: Request):
    """
    Check health of all persistence layers (WAL, Redis, Postgres).
    
    Returns:
        - wal: True if write-ahead log is enabled
        - redis: True if Redis connection is healthy
        - postgres: True if Postgres connection is healthy
        - overall_healthy: True if all enabled backends are healthy
    """
    state_manager = getattr(request.app.state, "state_manager", None)
    
    if not state_manager:
        raise HTTPException(
            status_code=503,
            detail="State manager not initialized (persistence disabled)"
        )
    
    try:
        health = await state_manager.health_check()
        overall = all(health.values())
        
        return PersistenceHealthResponse(
            wal=health.get("wal", False),
            redis=health.get("redis", False),
            postgres=health.get("postgres", False),
            overall_healthy=overall
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/inflight")
async def get_inflight_tasks(request: Request):
    """
    Get list of in-flight tasks (planning or executing state).
    
    Returns tasks that would be recovered on restart.
    """
    state_manager = getattr(request.app.state, "state_manager", None)
    
    if not state_manager:
        raise HTTPException(
            status_code=503,
            detail="State manager not initialized"
        )
    
    try:
        tasks = await state_manager.recover_inflight()
        return {
            "count": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "identity": t.identity,
                    "state": t.state,
                    "goal": t.goal,
                    "updated_at": t.updated_at
                }
                for t in tasks
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve inflight tasks: {str(e)}"
        )
