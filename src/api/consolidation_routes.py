# Memory Consolidation API Routes
# SPDX-License-Identifier: MIT
"""
FastAPI routes for memory consolidation control.

Endpoints:
- POST /consolidation/run - Run consolidation now (manual trigger)
- GET /consolidation/status - Get scheduler status
- GET /consolidation/history - Get job history
- POST /consolidation/config - Update consolidation config
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/consolidation", tags=["memory_consolidation"])


# Global scheduler instance (set by boot.py)
_scheduler = None


def set_scheduler(scheduler):
    """Set global scheduler instance (called by boot.py)."""
    global _scheduler
    _scheduler = scheduler


class ConsolidationRunResponse(BaseModel):
    """Response for manual consolidation run."""
    status: str
    events_count: int
    clusters_count: int
    summaries_stored: int
    duration_seconds: float


class ConsolidationStatusResponse(BaseModel):
    """Response for consolidation status."""
    enabled: bool
    schedule: str
    next_run_time: str | None
    is_running: bool


class ConsolidationHistoryItem(BaseModel):
    """Single consolidation job history item."""
    timestamp: str
    status: str
    events_count: int
    clusters_count: int
    duration_seconds: float
    error: str | None = None


class ConsolidationHistoryResponse(BaseModel):
    """Response for consolidation history."""
    total_runs: int
    recent_runs: list[ConsolidationHistoryItem]


@router.post("/run", response_model=ConsolidationRunResponse)
async def run_consolidation_now(
    mode: str = "live",
    since: str | None = None,
    limit: int = 0
):
    """
    Run memory consolidation immediately.
    
    Modes:
    - live: Normal consolidation with writes (default)
    - dry: Test run without writes (compute metrics only)
    - backfill: Process historical events (with watermark)
    
    Args:
        mode: Consolidation mode (live|dry|backfill)
        since: ISO timestamp for backfill mode (optional)
        limit: Max events to process (0 = use config default)
    
    Returns:
        ConsolidationRunResponse with job statistics
    
    Examples:
        ```bash
        # Live run (default)
        curl -X POST "http://localhost:8000/consolidation/run"
        
        # Dry run (no writes)
        curl -X POST "http://localhost:8000/consolidation/run?mode=dry&limit=50"
        
        # Backfill (historical)
        curl -X POST "http://localhost:8000/consolidation/run?mode=backfill&since=2025-10-01T00:00:00Z"
        ```
    """
    if not _scheduler:
        raise HTTPException(
            status_code=503,
            detail="Consolidation scheduler not initialized"
        )
    
    # Try to pass mode/since/limit to scheduler; fallback if not supported
    try:
        result = _scheduler.run_now(mode=mode, since=since, limit=limit)
    except TypeError:
        # Older scheduler signature: no args
        result = _scheduler.run_now()
    
    return ConsolidationRunResponse(
        status=result["status"],
        events_count=result["events_count"],
        clusters_count=result["clusters_count"],
        summaries_stored=result.get("summaries_stored", result["clusters_count"]),
        duration_seconds=result["duration_seconds"]
    )


@router.get("/status", response_model=ConsolidationStatusResponse)
async def get_consolidation_status():
    """
    Get memory consolidation scheduler status.
    
    Returns:
        ConsolidationStatusResponse with scheduler state
    
    Example:
        ```bash
        curl http://localhost:8000/consolidation/status
        ```
    """
    if not _scheduler:
        raise HTTPException(
            status_code=503,
            detail="Consolidation scheduler not initialized"
        )
    
    return ConsolidationStatusResponse(
        enabled=_scheduler.enabled,
        schedule=_scheduler.schedule,
        next_run_time=_scheduler.get_next_run_time(),
        is_running=_scheduler.is_running
    )


@router.get("/history", response_model=ConsolidationHistoryResponse)
async def get_consolidation_history(limit: int = 10):
    """
    Get recent consolidation job history.
    
    Args:
        limit: Number of recent jobs to return (default: 10)
    
    Returns:
        ConsolidationHistoryResponse with job history
    
    Example:
        ```bash
        curl http://localhost:8000/consolidation/history?limit=5
        ```
    """
    if not _scheduler:
        raise HTTPException(
            status_code=503,
            detail="Consolidation scheduler not initialized"
        )
    
    history = _scheduler.get_job_history(limit=limit)
    
    return ConsolidationHistoryResponse(
        total_runs=len(_scheduler.job_history),
        recent_runs=[
            ConsolidationHistoryItem(**run)
            for run in history
        ]
    )


@router.get("/health")
async def consolidation_health_check():
    """
    Health check for consolidation service.
    
    Returns:
        {"status": "ok"} if service is available
    """
    if not _scheduler:
        return {
            "status": "unavailable",
            "message": "Consolidation scheduler not initialized"
        }
    
    return {
        "status": "ok",
        "enabled": _scheduler.enabled,
        "is_running": _scheduler.is_running
    }
