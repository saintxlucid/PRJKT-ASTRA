"""ASTRA Tier-0: FastAPI Server

Provides REST API for voice-controlled desktop actions.

Endpoints:
- GET  /health - Health check
- POST /desktop/focus - Focus window
- POST /desktop/launch - Launch application
- POST /desktop/tile - Tile window
- POST /desktop/type - Type text
- POST /desktop/hotkey - Send hotkey
- GET  /desktop/screenshot - Capture screenshot
- POST /desktop/close - Close window
- GET  /voice/status - Voice service status
- POST /voice/start - Start voice monitoring
- POST /voice/stop - Stop voice monitoring

Created: October 18, 2025
"""

import os
import threading
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.security.capabilities import Capability, CapabilityGuard
from ..services.desktop.win_control import WinDesktop
from ..voice_engine.wake_service import WakeService


# ---- Mini logger ----
class _Logger:
    def info(self, msg: str) -> None:
        print(f"[ASTRA][api] {msg}")
    
    def error(self, msg: str) -> None:
        print(f"[ASTRA][api][ERR] {msg}")


logger = _Logger()


# ---- Request/Response Models ----

class FocusRequest(BaseModel):
    title_contains: str


class LaunchRequest(BaseModel):
    exe_path: str
    args: str = ""


class TileRequest(BaseModel):
    side: str


class TypeRequest(BaseModel):
    text: str


class HotkeyRequest(BaseModel):
    keys: list[str]


class CloseRequest(BaseModel):
    title_contains: str


class HealthResponse(BaseModel):
    status: str
    voice_running: bool
    capabilities_enabled: dict


class VoiceStatusResponse(BaseModel):
    running: bool
    model_size: str
    wake_words: list[str]


# ---- Global State ----

_guard = CapabilityGuard()
_desktop = WinDesktop(_guard)
_voice_service: WakeService | None = None
_voice_lock = threading.Lock()


def _on_wake(word: str) -> None:
    """Callback when wake word detected"""
    logger.info(f"Wake word '{word}' detected - desktop is ready for commands")


def _on_transcript(text: str) -> None:
    """Callback for all transcription"""
    logger.info(f"Transcribed: {text}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown handler"""
    logger.info("ASTRA Tier-0 API starting...")
    yield
    logger.info("ASTRA Tier-0 API shutting down...")
    if _voice_service:
        _voice_service.stop()


# ---- FastAPI App ----

app = FastAPI(
    title="ASTRA Tier-0 API",
    description="Voice-controlled Windows desktop",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- Health Check ----

@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        voice_running=_voice_service and _voice_service.running or False,
        capabilities_enabled={
            "focus": _guard.is_allowed(Capability.FOCUS),
            "launch": _guard.is_allowed(Capability.LAUNCH),
            "tile": _guard.is_allowed(Capability.TILE),
            "type": _guard.is_allowed(Capability.TYPE),
            "hotkey": _guard.is_allowed(Capability.HOTKEY),
            "screenshot": _guard.is_allowed(Capability.SCREENSHOT),
            "close": _guard.is_allowed(Capability.CLOSE),
        },
    )


# ---- Desktop Control Endpoints ----

@app.post("/desktop/focus")
async def desktop_focus(req: FocusRequest) -> dict:
    """Focus window by title"""
    try:
        result = _desktop.focus(req.title_contains)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/desktop/launch")
async def desktop_launch(req: LaunchRequest) -> dict:
    """Launch application"""
    try:
        result = _desktop.launch(req.exe_path, req.args or None)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/desktop/tile")
async def desktop_tile(req: TileRequest) -> dict:
    """Tile window to screen side"""
    try:
        result = _desktop.tile(req.side)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/desktop/type")
async def desktop_type(req: TypeRequest) -> dict:
    """Type text into focused window"""
    try:
        result = _desktop.type_text(req.text)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/desktop/hotkey")
async def desktop_hotkey(req: HotkeyRequest) -> dict:
    """Send hotkey sequence"""
    try:
        result = _desktop.hotkey(*req.keys)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/desktop/screenshot")
async def desktop_screenshot() -> dict:
    """Capture screenshot"""
    try:
        path = _desktop.screenshot()
        return {"path": path}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/desktop/close")
async def desktop_close(req: CloseRequest) -> dict:
    """Close window by title"""
    try:
        result = _desktop.close(req.title_contains)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---- Voice Control Endpoints ----

@app.get("/voice/status")
async def voice_status() -> VoiceStatusResponse:
    """Get voice service status"""
    with _voice_lock:
        if _voice_service is None:
            return VoiceStatusResponse(
                running=False,
                model_size="not_initialized",
                wake_words=[],
            )
        return VoiceStatusResponse(
            running=_voice_service.running,
            model_size=_voice_service.model_size,
            wake_words=_voice_service.wake_words,
        )


@app.post("/voice/start")
async def voice_start() -> dict:
    """Start voice service"""
    global _voice_service
    
    with _voice_lock:
        if _voice_service is None:
            _voice_service = WakeService(
                model_size="small",
                on_wake=_on_wake,
                on_transcript=_on_transcript,
            )
        
        if _voice_service.running:
            return {"status": "already_running"}
        
        try:
            _voice_service.start()
            logger.info("Voice service started")
            return {"status": "started"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@app.post("/voice/stop")
async def voice_stop() -> dict:
    """Stop voice service"""
    with _voice_lock:
        if _voice_service is None:
            return {"status": "not_running"}
        
        _voice_service.stop()
        logger.info("Voice service stopped")
        return {"status": "stopped"}


# ---- Startup ----

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("ASTRA_API_HOST", "127.0.0.1")
    port = int(os.getenv("ASTRA_API_PORT", "8000"))
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
