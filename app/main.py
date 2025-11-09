"""
ASTRA Role API
==============

FastAPI service for role switching, function invocation, and trace visualization.
"""

from __future__ import annotations

from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.identity_state import RoleRuntime
from app.models import InvokeRequest, RoleSwitchRequest
from app.traces import Tracer
from src.astra.core.functions.simple_registry import get_function, list_all_functions
from src.astra.core.identity.astra_roles import ROLE_SPECS, resolve_role
from src.astra.core.identity.role_context import role_scope

# Import modules_v2 to trigger function registration
import src.astra.core.functions.modules_v2  # noqa: F401

app = FastAPI(title="ASTRA Role API", version="2.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Runtime state
runtime = RoleRuntime()
tracer = Tracer()


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Health check endpoint."""
    return {"ok": True, "role": runtime.current_role, "version": app.version}


@app.get("/api/roles")
def roles() -> dict[str, Any]:
    """List available roles and current role."""
    return {
        "current": runtime.current_role,
        "available": {
            k: {"token": v.token, "desc": v.description}
            for k, v in ROLE_SPECS.items()
        },
    }


@app.post("/api/role/switch")
def switch_role(req: RoleSwitchRequest) -> dict[str, Any]:
    """Switch active role."""
    target = resolve_role(req.role)
    if target not in ROLE_SPECS:
        raise HTTPException(status_code=400, detail=f"Unknown role: {target}")

    runtime.set_role(target)
    tracer.log("role.switch", {"to": target})
    return {"ok": True, "role": runtime.current_role}


@app.get("/api/functions")
def list_functions() -> dict[str, Any]:
    """List all registered universal functions."""
    all_funcs = list_all_functions()
    return {
        "count": len(all_funcs),
        "items": [
            {
                "code": meta["code"],
                "role_hint": meta["role_hint"],
                "boundaries": [],  # Not stored in simple registry
                "description": meta["description"],
            }
            for meta in all_funcs
        ],
    }


@app.post("/api/functions/{code}/invoke")
async def invoke(code: str, req: InvokeRequest) -> dict[str, Any]:
    """Invoke a universal function."""
    func_data = get_function(code)
    if not func_data:
        raise HTTPException(status_code=404, detail=f"Unknown function: {code}")

    impl = func_data["instance"]
    meta = func_data["metadata"]

    # Enter role scope using hint OR current runtime role
    chosen_role = meta["role_hint"] or runtime.current_role

    with role_scope(chosen_role):
        tracer.log("function.invoke", {"code": code, "role": chosen_role, "args": req.args})
        try:
            result = await impl.invoke(**(req.args or {}))
            tracer.log("function.result", {"code": code, "ok": True})
            return {"ok": True, "result": result}
        except Exception as e:
            tracer.log("function.error", {"code": code, "error": str(e)})
            raise HTTPException(status_code=500, detail=f"Invocation failed: {e}")


@app.get("/api/traces")
def get_traces() -> dict[str, Any]:
    """Get last 100 trace events."""
    return tracer.tail()


# Mount static dashboard at root
try:
    app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
except RuntimeError:
    # Directory might not exist yet
    pass


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8787, reload=True)
