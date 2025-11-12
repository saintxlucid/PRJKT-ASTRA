"""Routing helpers for web console (Phase 3 scaffold).

Add additional sub-routers (agents, memory, observability) here.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def ping():
    return {"ok": True}
