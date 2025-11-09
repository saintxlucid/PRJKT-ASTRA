# src/astra/core/launcher.py
import asyncio
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Dict, Optional, AsyncGenerator, Any
from fastapi.responses import JSONResponse

from .initialization import CoreSystemsInitializer
from .inference_api import router as inference_router, stop_inference_subsystem
from astra.launcher.cleanup import CleanupManager
from astra.logging_setup import setup_logging
from astra.core.error_middleware import astra_error_guard

# Initialize structured logging
setup_logging()

# Global instances (single-source-of-truth)
initializer = CoreSystemsInitializer()  # config is now optional
cleanup = CleanupManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    app.state.draining = False
    # fire-and-forget start; if you prefer blocking, await initializer.start()
    asyncio.create_task(initializer.start())
    yield
    # SHUTDOWN (ordered, idempotent)
    app.state.draining = True
    # 1) stop inference (drain queue, close bridge)
    await stop_inference_subsystem()
    # 2) stop core systems (persist memory, etc.)
    await initializer.stop()
    
    # Log server exit
    logging.getLogger("astra").info(
        "server_exit",
        extra={
            "exit_status": {
                "reason": "lifespan_shutdown",
                "draining": True
            }
        }
    )
    
    # 3) run global cleanup last (temp files, subprocesses)
    try:
        await cleanup.cleanup()
    except Exception as e:
        # Log forced exit if cleanup fails
        children_left = len(cleanup.get_active_processes())
        logging.getLogger("astra").warning(
            "server_exit_forced",
            extra={
                "exit_status": {
                    "reason": "forced_kill",
                    "children_left": children_left
                }
            }
        )

app = FastAPI(title="ASTRA Core Launcher", version="0.1", lifespan=lifespan)

# Add global error handling middleware
app.middleware("http")(astra_error_guard)

# Development-only error testing route
if os.environ.get("ASTRA_DEV_BOOM", "0") == "1":
    @app.get("/boom")
    async def boom():
        raise RuntimeError("chaos-engine test")

# Health checks
@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok", 
        "service": "astra-core", 
        "draining": getattr(app.state, "draining", False)
    }

@app.get("/ready")
async def ready() -> Dict[str, bool]:
    # not ready when draining
    return {"ready": not getattr(app.state, "draining", False)}

@app.get("/astra/status")
async def astra_status() -> Dict[str, Any]:
    return initializer.status()

@app.post("/astra/start")
async def astra_start() -> Dict[str, Any]:
    if getattr(app.state, "draining", False):
        return {"error": "Service is draining, cannot start"}
    # Force a blocking start for manual triggers
    status = await initializer.start()
    return status

@app.post("/admin/drain")
async def admin_drain() -> Dict[str, Any]:
    app.state.draining = True
    return {"ok": True, "draining": True}

# Mount inference routes
app.include_router(inference_router)