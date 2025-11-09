"""
ASTRA Week-2 Server - Boot Integration
=======================================

FastAPI server with integrated boot sequence, event logging, and policy enforcement.

Usage:
    python launch_server.py

Endpoints:
    GET  /health              - Health check (logged)
    POST /chat                - Chat with ASTRA (plan approval + event logging)
    POST /tool/execute        - Execute tool (policy check + event logging)
    GET  /memory/search       - Search memories (event logging)
    GET  /events              - View event log
    GET  /events/replay       - Replay session events
    GET  /metrics             - Prometheus metrics

Architecture:
    Boot → Dependencies → FastAPI Lifespan → Endpoints → Shutdown

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Days 7-8)
"""

import os
import sys
import inspect
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from boot import boot_astra, shutdown_astra, BootDependencies, BootError
from src.astra.core.circuit_breaker import CircuitBreaker, CircuitOpenError

# ASTRA Identity & Role System v2.5
from src.astra.core.identity.astra_roles import ROLE_SPECS, resolve_role
from src.astra.core.identity.role_context import role_scope, get_current_role

# Import modules_v2 to register universal functions
import src.astra.core.functions.modules_v2  # noqa: F401

# Dashboard integration
from src.astra.core.functions.simple_registry import get_function, list_all_functions


def tag_event_with_role(text: str, role: str) -> str:
    """Tag text with role for memory encoding."""
    return f"[{role}] {text}"


# Logger
logger = logging.getLogger("astra.launch_server")
logging.basicConfig(level=logging.INFO)


# ---- Request/Response Models ----

class ChatRequest(BaseModel):
    """Chat request with message."""
    message: str
    temperature: float = 0.7
    max_tokens: int = 512


class ChatResponse(BaseModel):
    """Chat response with generated text."""
    response: str
    event_id: str  # Event log reference


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""
    tool_name: str
    arguments: dict


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""
    status: int
    output: str
    error: str | None
    event_id: str  # Event log reference


class MemorySearchRequest(BaseModel):
    """Memory search request."""
    query: str
    limit: int = 5


class MemorySearchResponse(BaseModel):
    """Memory search response."""
    results: list[dict]
    event_id: str  # Event log reference


class EventResponse(BaseModel):
    """Event log entry."""
    id: str
    ts: str
    typ: str
    payload: dict
    identity: dict
    prev_hash: str
    hash: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    event_store_count: int
    policy_count: int
    executor_type: str


class RoleSwitchRequest(BaseModel):
    """Role switch request."""
    role: str


class InvokeRequest(BaseModel):
    """Function invocation request."""
    args: dict = {}


# ---- Global Dependencies ----

_deps: BootDependencies | None = None
_current_role: str = "ASTRA"  # Runtime role state for dashboard

# ---- Circuit Breakers for Fault Tolerance ----

_llm_breaker = CircuitBreaker(failure_threshold=5, timeout=60, name="llm")
_memory_breaker = CircuitBreaker(failure_threshold=5, timeout=30, name="memory")


def _ensure_ready() -> BootDependencies:
    """Return boot dependencies or raise 503 HTTPException.

    This centralizes the readiness check and keeps endpoints concise.
    """
    if not _deps:
        logger.warning("Request received while server not ready")
        raise HTTPException(status_code=503, detail="Server not ready (boot incomplete)")
    return _deps


def _safe_append_event(event_type: str, payload: dict[str, Any]) -> str:
    """Append to event store if available. Returns event id or 'unknown'.

    Swallows internal event-store errors but logs them; avoids crashing endpoints.
    """
    try:
        deps = _ensure_ready()
        ev_id = deps.event_store.append(event_type, payload, deps.identity_snapshot)
        return ev_id
    except HTTPException:
        # re-raise readiness errors
        raise
    except Exception as e:
        logger.exception("Failed to append event '%s': %s", event_type, e)
        return "unknown"


async def _maybe_await(obj):
    """Await object if awaitable; otherwise return directly."""
    if inspect.isawaitable(obj):
        return await obj
    return obj


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan: Boot on startup, shutdown on teardown.
    """
    global _deps
    
    print("\n" + "="*80)
    print("🚀 ASTRA SERVER STARTING (Week-2 Architecture)")
    print("="*80 + "\n")
    
    try:
        # Execute boot sequence
        _deps = boot_astra()
        
        print("\n✅ Server ready for requests\n")
        
        yield
        
    except BootError as e:
        print(f"\n❌ Boot failed: {e}\n")
        raise
        
    finally:
        # Graceful shutdown
        if _deps:
            print("\n🛑 Server shutting down...\n")
            shutdown_astra(_deps)
            print("✅ Shutdown complete\n")


# ---- FastAPI App ----

app = FastAPI(
    title="ASTRA Unified Server",
    description="Integrated server with Boot, LLM, Memory, Identity & Dashboard",
    version="2.5.0",
    lifespan=lifespan,
)

# CORS - Allow all origins for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Operator Console routes (Week-3 Days 21-24)
try:
    from api.console_routes import router as console_router
    app.include_router(console_router)
    print("✅ Operator Console routes loaded (/console/*)")
except ImportError as e:
    print(f"⚠️  Operator Console routes not available: {e}")

# Include Memory Consolidation routes (Week-3 Days 25-28)
try:
    from api.consolidation_routes import router as consolidation_router
    app.include_router(consolidation_router)
    print("✅ Memory Consolidation routes loaded (/consolidation/*)")
except ImportError as e:
    print(f"⚠️  Memory Consolidation routes not available: {e}")

# Mount static dashboard files
try:
    app.mount("/dashboard", StaticFiles(directory="app/static", html=True), name="dashboard")
    print("✅ Dashboard mounted at /dashboard")
except RuntimeError as e:
    print(f"⚠️  Dashboard static files not available: {e}")


# ---- Endpoints ----

@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check with boot status.
    """
    deps = _ensure_ready()

    # Log health check (best-effort)
    _safe_append_event("health_check", {"endpoint": "/health"})

    return HealthResponse(
        status="operational",
        event_store_count=deps.event_store.count(),
        policy_count=len(deps.plan_verifier.policies),
        executor_type=type(deps.action_executor).__name__
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    Chat with ASTRA (prompt guard + Multi-Model Router + event logging).
    
    Flow:
    1. Prompt guard evaluation (3-layer defense)
    2. Log chat_requested event
    3. Route to optimal model via ModelRouter (intelligent selection)
    4. Check policy approval for response
    5. Log chat_completed event (with tokens, cost, latency, selected_model)
    6. Return response
    
    NEW: Multi-model orchestration with intelligent routing:
    - Complex reasoning → DeepSeek-V3.1 (128K context)
    - Vision tasks → Llama-3.2-Vision-11B
    - Fast responses → Phi-4-mini (60 tok/s)
    - Audio transcription → Whisper-large-v3
    """
    deps = _ensure_ready()

    # Layer 1-3: Prompt Guard evaluation (best-effort)
    guard_passed = False
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path("src").absolute()))
        from security import prompt_guard as PG

        guard_result = PG.evaluate(req.message, context={"signed_plan": None})
        if not guard_result.get("allow"):
            _safe_append_event(
                "chat_blocked_by_guard",
                {"reasons": guard_result.get("reasons", []), "original_message": req.message},
            )
            raise HTTPException(
                status_code=400,
                detail=f"Prompt blocked: {', '.join(guard_result.get('reasons', []))}"
            )

        safe_message = guard_result.get("transformed_text", req.message)
        guard_passed = True
    except Exception as e:
        logger.debug("Prompt guard unavailable or failed: %s", e)
        safe_message = req.message

    # 🌟 ASTRA v2.5: Detect role activation phrases
    detected_role = "ASTRA"  # Default role
    for role_key, role_spec in ROLE_SPECS.items():
        activation = role_spec.get("activation_phrase", "").lower()
        if activation and activation in safe_message.lower():
            detected_role = role_key
            logger.info(f"🪽 Role activated: {role_key} (phrase: {activation})")
            break

    # Tag message with role for memory encoding
    role_tagged_message = tag_event_with_role(safe_message, detected_role)

    # Log request (best-effort) with role information
    request_event_id = _safe_append_event(
        "chat_requested",
        {
            "message": role_tagged_message,
            "original_message": safe_message,
            "detected_role": detected_role,
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "guard_passed": guard_passed,
        },
    )

    # Check policy (deny destructive actions without plan)
    approved, errors = deps.plan_verifier.check(
        {"action": "chat_response", "message": safe_message},
        {}
    )
    
    if not approved:
        _deps.event_store.append(
            "chat_rejected",
            {"reason": errors},
            _deps.identity_snapshot
        )
        raise HTTPException(status_code=403, detail=f"Policy denied: {errors}")
    
    # Generate LLM response with multi-model routing (circuit breaker protected)
    # 🪽 ASTRA v2.5: Execute within role scope for identity-aware generation
    try:
        async def _generate_response():
            """Internal helper for circuit-breaker-protected LLM generation."""
            # Apply role scope for entire generation
            with role_scope(detected_role):
                current_role = get_current_role()
                logger.info(f"🎭 Generating response in role: {current_role}")

                from services.model_router import build_router_from_config, RoutingRequest, TaskType, Modality

                # Try to use ModelRouter for intelligent model selection
                try:
                    # Initialize router (will be cached in production via _deps)
                    router = build_router_from_config(Path("config/model_router.yaml"))
                    await router.initialize()

                    # Intelligent routing based on message complexity
                    routing_request = RoutingRequest(
                        prompt=safe_message,
                        modality=Modality.TEXT,  # TODO: Detect images/audio
                        task_type=TaskType.REASONING if len(safe_message) > 200 else TaskType.FAST_CHAT,
                        temperature=req.temperature,
                        max_tokens=req.max_tokens
                    )

                    # Route and generate
                    result = await router.generate(routing_request)

                    return {
                        "content": result["content"],
                        "tokens_used": result["usage"]["total_tokens"],
                        "cost_usd": 0.0,  # Local models, no cost
                        "latency_seconds": result["latency"]
                    }

                except (ImportError, FileNotFoundError):
                    # Fallback to traditional LLMService if router unavailable
                    from services.llm_service import LLMService

                    llm = LLMService(
                        provider=os.getenv("LLM_PROVIDER", "openai"),
                        model=os.getenv("LLM_MODEL", "gpt-4-turbo-preview"),
                        temperature=req.temperature,
                        system_prompt=f"You are {current_role}, an angelic intelligence in the ASTRA ecosystem. You embody: {ROLE_SPECS.get(current_role, {}).get('desc', 'helpful assistance')}."
                    )

                    llm_response = llm.generate(
                        prompt=safe_message,
                        max_tokens=req.max_tokens,
                        temperature=req.temperature
                    )

                    return {
                        "content": llm_response.text,
                        "tokens_used": llm_response.tokens_used,
                        "cost_usd": llm_response.cost_usd,
                        "latency_seconds": llm_response.latency_seconds
                    }
        
        # Execute with circuit breaker protection
        result = await _llm_breaker.call(_generate_response)
        response_text = result["content"]
        tokens_used = result["tokens_used"]
        cost_usd = result["cost_usd"]
        latency_seconds = result["latency_seconds"]
        
    except CircuitOpenError as e:
        # Circuit breaker open - LLM service is down
        logger.warning("LLM circuit breaker open: %s", e)
        _safe_append_event("chat_circuit_open", {"retry_after": e.retry_after, "message": safe_message})
        raise HTTPException(
            status_code=503,
            detail=f"LLM service temporarily unavailable. Retry after {e.retry_after}s"
        )
    except Exception as e:
        # Fallback to echo if everything fails
        logger.error("All LLM fallbacks exhausted: %s", e)
        response_text = f"[LLM UNAVAILABLE: {str(e)}] Echo: {safe_message}"
        tokens_used = 0
        cost_usd = 0.0
        latency_seconds = 0.0
    
    # Log completion
    completion_event_id = _deps.event_store.append(
        "chat_completed",
        {
            "request_event_id": request_event_id,
            "response": response_text,
            "tokens_used": tokens_used,
            "cost_usd": cost_usd,
            "latency_seconds": latency_seconds,
            "model": os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
        },
        _deps.identity_snapshot
    )
    
    return ChatResponse(
        response=response_text,
        event_id=completion_event_id
    )


@app.post("/tool/execute", response_model=ToolExecuteResponse)
async def tool_execute(req: ToolExecuteRequest):
    """
    Execute tool with policy enforcement + event logging.
    
    Flow:
    1. Check policy approval
    2. Execute tool via action_executor
    3. Log tool_executed event
    4. Return result
    """
    deps = _ensure_ready()

    # Check policy
    approved, errors = deps.plan_verifier.check({"action": req.tool_name, **req.arguments}, {})
    if not approved:
        _safe_append_event("tool_rejected", {"tool": req.tool_name, "reason": errors})
        raise HTTPException(status_code=403, detail=f"Policy denied: {errors}")

    # Execute tool (sync or async)
    try:
        result = await _maybe_await(deps.action_executor.run(req.tool_name, req.arguments))
    except Exception as e:
        logger.exception("Tool execution failed: %s", e)
        result = {"status": -1, "output": "", "error": str(e)}

    # Log execution (best-effort)
    event_id = _safe_append_event(
        "tool_executed",
        {
            "tool": req.tool_name,
            "arguments": req.arguments,
            "status": result.get("status"),
            "success": result.get("status") == 0,
        },
    )

    return ToolExecuteResponse(
        status=result.get("status", -1),
        output=result.get("output", ""),
        error=result.get("error"),
        event_id=event_id,
    )


@app.post("/memory/search", response_model=MemorySearchResponse)
async def memory_search(req: MemorySearchRequest):
    """
    Search memories with semantic search + signature verification (circuit breaker protected).
    
    Uses ChromaMemoryGateway for vector search with tamper detection.
    """
    deps = _ensure_ready()

    if not deps.memory_gateway:
        # Log warning and return empty results
        event_id = _safe_append_event(
            "memory_search_failed", {"query": req.query, "reason": "Memory gateway not available"}
        )
        return MemorySearchResponse(results=[], event_id=event_id)
    
    # Perform semantic search with circuit breaker protection
    try:
        async def _search_memories():
            """Internal helper for circuit-breaker-protected memory search."""
            # Note: memory_gateway.search is synchronous, not async
            results = list(
                deps.memory_gateway.search(query=req.query, limit=req.limit, filters=None)  # TODO: Add conversation_id filtering
            )
            return results
        
        # Execute with circuit breaker (await the coroutine)
        results = await _memory_breaker.call(_search_memories)

        # Log successful search
        event_id = _safe_append_event(
            "memory_searched",
            {
                "query": req.query,
                "limit": req.limit,
                "results_count": len(results),
                "tamper_detected": any(
                    not r.get("metadata", {}).get("signature_valid", True) for r in results
                ),
            },
        )

        return MemorySearchResponse(results=results, event_id=event_id)

    except CircuitOpenError as e:
        # Circuit breaker open - memory service is down
        logger.warning("Memory circuit breaker open: %s", e)
        event_id = _safe_append_event(
            "memory_search_circuit_open", 
            {"query": req.query, "retry_after": e.retry_after}
        )
        raise HTTPException(
            status_code=503,
            detail=f"Memory service temporarily unavailable. Retry after {e.retry_after}s"
        ) from e
    except Exception as e:
        # Log error
        _safe_append_event("memory_search_error", {"query": req.query, "error": str(e)})
        raise HTTPException(status_code=500, detail=f"Memory search failed: {e}") from e


@app.get("/events", response_model=list[EventResponse])
async def get_events(limit: int = 50):
    """
    Get recent events from event log.
    """
    deps = _ensure_ready()

    events = list(deps.event_store.replay())[-limit:]
    
    return [
        EventResponse(
            id=ev.id,
            ts=ev.ts,
            typ=ev.typ,
            payload=ev.payload,
            identity=ev.identity,
            prev_hash=ev.prev_hash,
            hash=ev.hash
        )
        for ev in events
    ]


@app.get("/events/replay")
async def replay_events(event_type: str | None = None):
    """
    Replay events by type.
    """
    deps = _ensure_ready()

    if event_type:
        events = list(deps.event_store.get_by_type(event_type))
    else:
        events = list(deps.event_store.replay())
    
    return {
        "count": len(events),
        "events": [
            {
                "id": ev.id,
                "ts": ev.ts,
                "typ": ev.typ,
                "payload": ev.payload,
                "hash": ev.hash[:16] + "..."
            }
            for ev in events
        ]
    }


@app.get("/metrics")
async def metrics():
    """
    Prometheus-style metrics with circuit breaker status.
    """
    deps = _ensure_ready()

    return {
        "event_store_count": deps.event_store.count(),
        "policy_count": len(deps.plan_verifier.policies),
        "executor_type": type(deps.action_executor).__name__,
        "boot_event_id": getattr(deps, "boot_event_id", None),
        "circuit_breakers": {
            "llm": _llm_breaker.metrics,
            "memory": _memory_breaker.metrics,
        },
    }


# ====================================================================================
# DASHBOARD API ENDPOINTS (Role Management, Function Invocation, Traces)
# ====================================================================================

@app.get("/api/health")
def api_health() -> dict[str, Any]:
    """Dashboard health check endpoint."""
    global _current_role
    return {"ok": True, "role": _current_role, "version": app.version}


@app.get("/api/roles")
def api_roles() -> dict[str, Any]:
    """List available roles and current role."""
    global _current_role
    return {
        "current": _current_role,
        "available": {
            k: {"token": v.token, "desc": v.description}
            for k, v in ROLE_SPECS.items()
        },
    }


@app.post("/api/role/switch")
def api_switch_role(req: RoleSwitchRequest) -> dict[str, Any]:
    """Switch active role."""
    global _current_role
    
    target = resolve_role(req.role)
    if target not in ROLE_SPECS:
        raise HTTPException(status_code=400, detail=f"Unknown role: {target}")

    _current_role = target
    
    # Log role switch event
    _safe_append_event("role.switch", {"to": target, "from": _current_role})
    
    return {"ok": True, "role": _current_role}


@app.get("/api/functions")
def api_list_functions() -> dict[str, Any]:
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
async def api_invoke(code: str, req: InvokeRequest) -> dict[str, Any]:
    """Invoke a universal function."""
    global _current_role
    
    func_data = get_function(code)
    if not func_data:
        raise HTTPException(status_code=404, detail=f"Unknown function: {code}")

    impl = func_data["instance"]
    meta = func_data["metadata"]

    # Enter role scope using hint OR current runtime role
    chosen_role = meta["role_hint"] or _current_role

    with role_scope(chosen_role):
        _safe_append_event("function.invoke", {"code": code, "role": chosen_role, "args": req.args})
        
        try:
            result = await impl.invoke(**(req.args or {}))
            _safe_append_event("function.result", {"code": code, "ok": True})
            return {"ok": True, "result": result}
        except Exception as e:
            _safe_append_event("function.error", {"code": code, "error": str(e)})
            raise HTTPException(status_code=500, detail=f"Invocation failed: {e}")


@app.get("/api/traces")
def api_get_traces() -> dict[str, Any]:
    """Get last 100 trace events from event store."""
    deps = _ensure_ready()
    
    events = list(deps.event_store.replay())[-100:]
    
    return {
        "events": [
            {
                "ts": ev.ts,
                "kind": ev.typ,
                "payload": ev.payload,
            }
            for ev in events
        ]
    }


# ---- Main ----

if __name__ == "__main__":
    import uvicorn

    print("\n" + "="*80)
    print("🌌 ASTRA UNIFIED SERVER")
    print("="*80)
    print("📡 Main API:    http://0.0.0.0:8000")
    print("🎨 Dashboard:   http://0.0.0.0:8000/dashboard")
    print("🔍 Health:      http://0.0.0.0:8000/api/health")
    print("📊 Metrics:     http://0.0.0.0:8000/metrics")
    print("="*80 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
