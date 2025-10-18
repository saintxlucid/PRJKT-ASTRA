"""
ASTRA Ascension Stack API Server
Integrated FastAPI server for Neural Browser V2, Live Autonomy, and Task Agents

Sacred Architecture: 333
- 3 Core Systems: Graph, Autonomy, Agent
- 3 Access Layers: REST API, WebSocket, Static UI
- 3 Safety Principles: Authorization, Audit, Transparency

Endpoints:
- /api/graph/* - Memory graph management
- /api/autonomy/* - Live autonomy control
- /api/agent/* - Task agent execution
- /api/video/* - Video export jobs
- /ws/graph - Real-time graph updates
- /ui - Static neural browser UI
"""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

try:
    import structlog
    logger = structlog.get_logger()
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

# Import ASTRA components
from .schemas import (
    GraphNode, GraphEdge, GraphSnapshot, OperationalMode,
    TriggerSpec, AutonomyStatus, ActionRequest, ActionResult,
    VideoExportConfig, SacredMetrics,
)
from .memory_graph_service import MemoryGraphService
from .autonomy_engine import AutonomyEngine, create_default_triggers
from .task_agent_manager import TaskAgentManager
from .video_export import VideoExportEngine
from .memory_bridge import MemoryBridge
from .plugins import register_file_ops, register_system_info
from .plugins import ableton_plugin
from .voice_endpoint import router as voice_router

# Import Bridge Module
try:
    from astra.bridge import (
        bridge_router, setup_bridge, BridgeConfig,
        MemoryBridgeService, ToolBridgeService, BridgeRegistry
    )
    BRIDGE_AVAILABLE = True
except ImportError as e:
    logger.warning("bridge_module_unavailable", error=str(e))
    BRIDGE_AVAILABLE = False

# Import Updates System (guard broadly to avoid hard failures on deep deps like torch)
try:
    from astra.api.routes.updates import router as updates_router
    UPDATES_AVAILABLE = True
except Exception as e:
    logger.warning("updates_module_unavailable", error=str(e))
    updates_router = None  # type: ignore
    UPDATES_AVAILABLE = False

# Import System routes
try:
    from astra.api.routes import system as system_routes
    SYSTEM_ROUTES_AVAILABLE = True
except Exception as e:
    logger.warning("system_routes_unavailable", error=str(e))
    SYSTEM_ROUTES_AVAILABLE = False


# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="ASTRA Ascension Stack",
    description="Neural Browser V2 + Live Autonomy + Task Agents",
    version="2.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Mount voice API router
app.include_router(voice_router)

# Mount bridge API router (if available)
if BRIDGE_AVAILABLE:
    app.include_router(bridge_router)
    logger.info("bridge_router_mounted")

# Mount updates API router (if available)
if UPDATES_AVAILABLE:
    app.include_router(updates_router)
    logger.info("updates_router_mounted")

# Mount system routes at /v1/system (primary) and /api/system (back-compat)
if SYSTEM_ROUTES_AVAILABLE:
    app.include_router(system_routes.router)  # /v1/system
    # Create a duplicate router with /api prefix for backwards compatibility
    api_system_router = APIRouter(prefix="/api/system", tags=["system"])
    # Copy all routes from system_routes.router to api_system_router
    for route in system_routes.router.routes:
        api_system_router.routes.append(route)
    app.include_router(api_system_router)
    logger.info("system_routes_mounted", paths=["/v1/system", "/api/system"])


# ============================================================================
# CORE STATE
# ============================================================================

# Memory graph service
graph_service = MemoryGraphService()

# Memory bridge (initialize with None, will connect on first request)
memory_bridge: Optional[MemoryBridge] = None

# Autonomy engine
autonomy_engine = AutonomyEngine()

# Task agent manager
task_agent = TaskAgentManager()

# Video export engine
video_export = VideoExportEngine(output_dir=Path("runtime/videos"))

# WebSocket clients
ws_clients: List[WebSocket] = []


# ============================================================================
# INITIALIZATION
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    logger.info("astra_ascension_startup")
    
    # Try to initialize memory bridge (non-blocking)
    global memory_bridge
    try:
        from astra.core.memory_engine import MemoryEngine
        from astra.services.memory_service import MemoryService
        from astra.infrastructure.storage.vector_store import VectorStore
        
        # Try to initialize memory engine with timeout
        async def init_memory_bridge():
            vector_store = VectorStore(persist_directory="data/chroma")
            memory_service = MemoryService(vector_store)
            memory_engine = MemoryEngine(vector_store=vector_store)
            
            return MemoryBridge(
                memory_engine=memory_engine,
                memory_service=memory_service
            )
        
        # Run with 3 second timeout
        try:
            memory_bridge = await asyncio.wait_for(init_memory_bridge(), timeout=3.0)
            logger.info("memory_bridge_connected")
            if memory_bridge:
                graph_service.set_backends(
                    memory_engine=memory_bridge.memory_engine,
                    memory_service=memory_bridge.memory_service,
                )
        except asyncio.TimeoutError:
            logger.info("memory_bridge_timeout")
            memory_bridge = None
            
    except ImportError as e:
        logger.info("memory_bridge_unavailable_imports", msg=str(e))
        memory_bridge = None
    except Exception as e:
        logger.info("memory_bridge_unavailable_init", msg=str(e))
        memory_bridge = None
    
    # Initialize Bridge Module
    if BRIDGE_AVAILABLE:
        try:
            # Create bridge config from environment
            bridge_config = BridgeConfig()
            
            # Create stub adapters
            from astra.bridge.memory_bridge import MemoryLTMAdapter, MemoryEpisodicAdapter
            from astra.bridge.tool_bridge import TaskAgentAdapter
            
            ltm_adapter = MemoryLTMAdapter()
            episodic_adapter = MemoryEpisodicAdapter()
            mem_service = MemoryBridgeService(ltm_adapter, episodic_adapter)
            
            task_adapter = TaskAgentAdapter()
            tool_service = ToolBridgeService(task_adapter, bridge_config.safe_tools_glob)
            
            registry = BridgeRegistry()
            
            # Setup bridge routes
            setup_bridge(bridge_config, mem_service, tool_service, registry)
            
            # Wire updates system to memory service
            if UPDATES_AVAILABLE:
                from astra.api.routes.updates import init_updates_system
                init_updates_system(mem_service)
            
            logger.info("bridge_module_initialized")
        except Exception as e:
            import traceback
            logger.warning("bridge_init_failed", exc=traceback.format_exc())
    
    # Register default triggers
    for trigger in create_default_triggers():
        autonomy_engine.add_trigger(trigger)
    
    # Register task agent plugins
    register_file_ops(task_agent)
    register_system_info(task_agent)
    
    # Register DAW plugin actions
    from .task_agent_manager import ToolAction
    task_agent.register("ableton", ToolAction(
        name="open_project",
        handler=ableton_plugin.open_project,
        requires_auth=True,
        description="Open Ableton/FL Studio project file"
    ))
    task_agent.register("ableton", ToolAction(
        name="set_bpm",
        handler=ableton_plugin.set_bpm,
        requires_auth=True,
        description="Set desired BPM (writes signal file)"
    ))
    task_agent.register("ableton", ToolAction(
        name="set_track_arm",
        handler=ableton_plugin.set_track_arm,
        requires_auth=True,
        description="Arm/disarm track for recording"
    ))
    task_agent.register("ableton", ToolAction(
        name="trigger_scene",
        handler=ableton_plugin.trigger_scene,
        requires_auth=True,
        description="Trigger Ableton Live scene"
    ))
    task_agent.register("ableton", ToolAction(
        name="get_signals",
        handler=ableton_plugin.get_signals,
        requires_auth=False,
        description="Get current DAW signal files"
    ))
    task_agent.register("ableton", ToolAction(
        name="clear_signals",
        handler=ableton_plugin.clear_signals,
        requires_auth=True,
        description="Clear all DAW signal files"
    ))
    
    # Wire services into app.state for unified health endpoint
    app.state.memory_service = memory_bridge.memory_service if memory_bridge else None
    app.state.chat_service = None  # Will be set when ChatService is initialized
    app.state.bridge = memory_bridge
    logger.info("app_state_wired", 
                has_memory=bool(app.state.memory_service),
                has_bridge=bool(app.state.bridge))
    
    # Start autonomy loop
    asyncio.create_task(autonomy_loop())
    
    # Start WebSocket broadcaster
    asyncio.create_task(ws_broadcaster())
    
    logger.info("astra_ascension_ready")


async def autonomy_loop():
    """Background autonomy engine loop"""
    async def on_initiation(trigger: TriggerSpec):
        # Broadcast trigger event via WebSocket
        await broadcast_ws({
            "type": "autonomy_event",
            "data": {
                "trigger_id": trigger.id,
                "action": trigger.action.prompt,
                "require_confirm": trigger.action.require_confirm,
            }
        })
    
    await autonomy_engine.loop(on_initiation)


async def ws_broadcaster():
    """Periodically broadcast graph updates"""
    while True:
        await asyncio.sleep(2.0)  # Update every 2 seconds
        
        # Get current graph snapshot (returns tuple of nodes, edges)
        nodes, edges = graph_service.build_graph(max_nodes=100)
        snapshot = GraphSnapshot(
            nodes=[
                GraphNode(
                    id=n.id,
                    label=n.content[:50] if n.content else n.id,
                    content=n.content,
                    kind="memory",
                    strength=n.importance,
                    x=n.position[0] if n.position else None,
                    y=n.position[1] if n.position else None,
                    z=n.position[2] if n.position else None,
                    created_at=n.timestamp,
                )
                for n in nodes[:100]
            ],
            edges=[
                GraphEdge(
                    id=f"e_{e.source_id}_{e.target_id}",
                    source=e.source_id,
                    target=e.target_id,
                    weight=e.weight,
                )
                for e in edges[:200]
            ],
            active_mode=autonomy_engine.active_mode,
        )
        
        await broadcast_ws({
            "type": "graph_update",
            "data": snapshot.model_dump(mode='json'),
        })


async def broadcast_ws(message: Dict):
    """Broadcast message to all connected WebSocket clients"""
    dead_clients = []
    for client in ws_clients:
        try:
            await client.send_json(message)
        except Exception:
            dead_clients.append(client)
    
    # Remove dead connections
    for client in dead_clients:
        if client in ws_clients:
            ws_clients.remove(client)


# ============================================================================
# GRAPH API
# ============================================================================

@app.get("/")
async def root():
    """Serve control panel"""
    from fastapi.responses import FileResponse
    panel_path = Path(__file__).parent / "static" / "panel.html"
    if panel_path.exists():
        return FileResponse(panel_path)
    return {"message": "ASTRA Ascension Stack V2", "docs": "/docs"}


@app.get("/api/graph", response_model=GraphSnapshot)
async def get_graph(max_nodes: int = 100):
    """Get current memory graph snapshot"""
    
    # Try memory bridge first if available
    if memory_bridge:
        try:
            nodes, edges = memory_bridge.get_graph_from_memories(max_nodes=max_nodes)
            return GraphSnapshot(
                nodes=nodes,
                edges=edges,
                active_mode=autonomy_engine.active_mode,
            )
        except Exception as e:
            logger.error("memory_bridge_query_failed", error=str(e))
    
    # Fall back to mock graph service
    nodes, edges = graph_service.build_graph(max_nodes=max_nodes)
    
    return GraphSnapshot(
        nodes=[
            GraphNode(
                id=n.id,
                label=n.content[:50] if n.content else n.id,
                content=n.content,
                kind="memory",
                strength=n.importance,
                x=n.position[0] if n.position else None,
                y=n.position[1] if n.position else None,
                z=n.position[2] if n.position else None,
                created_at=n.timestamp,
            )
            for n in nodes
        ],
        edges=[
            GraphEdge(
                id=f"e_{e.source_id}_{e.target_id}",
                source=e.source_id,
                target=e.target_id,
                weight=e.weight,
            )
            for e in edges
        ],
        active_mode=autonomy_engine.active_mode,
    )


class ModeUpdate(BaseModel):
    mode: Optional[OperationalMode]


@app.post("/api/graph/mode")
async def set_graph_mode(update: ModeUpdate):
    """Set current operational mode"""
    autonomy_engine.set_mode(update.mode)
    await broadcast_ws({
        "type": "mode_change",
        "data": {"mode": update.mode}
    })
    return {"ok": True, "mode": update.mode}


# ============================================================================
# AUTONOMY API
# ============================================================================

class AutonomyToggle(BaseModel):
    enabled: bool


@app.post("/api/autonomy/enable")
async def toggle_autonomy(toggle: AutonomyToggle):
    """Enable/disable autonomy engine"""
    autonomy_engine.set_enabled(toggle.enabled)
    return {"ok": True, "enabled": toggle.enabled}


@app.post("/api/autonomy/trigger")
async def add_autonomy_trigger(spec: TriggerSpec):
    """Register new autonomy trigger"""
    autonomy_engine.add_trigger(spec)
    return {"ok": True, "trigger_id": spec.id}


@app.delete("/api/autonomy/trigger/{trigger_id}")
async def remove_autonomy_trigger(trigger_id: str):
    """Remove autonomy trigger"""
    autonomy_engine.remove_trigger(trigger_id)
    return {"ok": True}


@app.get("/api/autonomy/status", response_model=AutonomyStatus)
async def get_autonomy_status():
    """Get autonomy engine status"""
    return autonomy_engine.status()


class SensorUpdate(BaseModel):
    sensors: Dict[str, float]


@app.post("/api/autonomy/sensors")
async def update_sensors(update: SensorUpdate):
    """Update autonomy sensor values"""
    autonomy_engine.update_sensors(update.sensors)
    return {"ok": True}


@app.get("/api/autonomy/triggers")
async def list_triggers():
    """List all registered triggers"""
    return {
        "triggers": [t.model_dump() for t in autonomy_engine.list_triggers()]
    }


@app.post("/api/autonomy/priority_cap")
async def set_priority_cap(cap: int):
    """Set autonomy priority cap (1-10)"""
    autonomy_engine.set_priority_cap(cap)
    return {"ok": True, "priority_cap": cap}


@app.post("/api/autonomy/reset_cooldowns")
async def reset_all_cooldowns():
    """Reset all trigger cooldowns"""
    autonomy_engine.trigger_cooldowns.clear()
    autonomy_engine.last_global_fire = 0
    return {"ok": True, "message": "All cooldowns reset"}


@app.put("/api/autonomy/trigger/{trigger_id}")
async def update_trigger_status(trigger_id: str, enabled: bool):
    """Enable/disable specific trigger"""
    autonomy_engine.enable_trigger(trigger_id, enabled)
    return {"ok": True, "trigger_id": trigger_id, "enabled": enabled}


# ============================================================================
# TASK AGENT API
# ============================================================================

@app.get("/api/agent/tools")
async def list_agent_tools():
    """List all registered task agent tools"""
    return task_agent.list_tools()


@app.get("/api/agent/tools/{tool_name}")
async def get_tool_actions(tool_name: str):
    """Get detailed info about tool actions"""
    actions = task_agent.get_tool_actions(tool_name)
    if not actions:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    return {"tool": tool_name, "actions": [a.model_dump() for a in actions]}


@app.post("/api/agent/execute", response_model=ActionResult)
async def execute_agent_action(request: ActionRequest):
    """Execute task agent action"""
    result = task_agent.execute(request)
    
    # Broadcast to WebSocket clients
    await broadcast_ws({
        "type": "task_event",
        "data": {
            "request": request.model_dump(),
            "result": result.model_dump(),
        }
    })
    
    return result


@app.get("/api/agent/history")
async def get_agent_history(limit: int = 100):
    """Get agent execution history"""
    return {
        "history": task_agent.get_execution_history(limit=limit)
    }


@app.get("/api/agent/statistics")
async def get_agent_statistics():
    """Get agent statistics"""
    return task_agent.get_statistics()


# ============================================================================
# VIDEO EXPORT API
# ============================================================================

@app.post("/api/video/create")
async def create_video_job(config: VideoExportConfig):
    """Create new video export job"""
    job = video_export.create_job(config)
    return {"job_id": job.job_id, "status": job.status}


@app.get("/api/video/jobs")
async def list_video_jobs():
    """List all video export jobs"""
    return {
        "jobs": [j.model_dump() for j in video_export.list_jobs()]
    }


@app.get("/api/video/jobs/{job_id}")
async def get_video_job(job_id: str):
    """Get video export job status"""
    job = video_export.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    return job.model_dump()


@app.post("/api/video/render/{job_id}")
async def render_video(job_id: str):
    """Start rendering video export job"""
    
    def get_snapshot():
        """Snapshot provider for video export"""
        nodes, edges = graph_service.build_graph(max_nodes=100)
        return GraphSnapshot(
            nodes=[
                GraphNode(
                    id=n.id,
                    label=n.content[:50] if n.content else n.id,
                    content=n.content,
                    kind="memory",
                    strength=n.importance,
                    x=n.position[0] if n.position else None,
                    y=n.position[1] if n.position else None,
                    z=n.position[2] if n.position else None,
                )
                for n in nodes
            ],
            edges=[
                GraphEdge(
                    id=f"e_{e.source_id}_{e.target_id}",
                    source=e.source_id,
                    target=e.target_id,
                    weight=e.weight,
                )
                for e in edges
            ],
        )
    
    # Start rendering in background
    asyncio.create_task(video_export.render_job(job_id, get_snapshot))
    
    return {"ok": True, "message": "Rendering started"}


# ============================================================================
# SYSTEM API
# ============================================================================

@app.get("/api/system/health")
async def system_health():
    """Get system health metrics (sacred 333)"""
    metrics = SacredMetrics(
        graph_health=1.0 if graph_service else 0.0,
        autonomy_health=1.0 if autonomy_engine.enabled else 0.5,
        agent_health=1.0,
        memory_usage_mb=0.0,  # TODO: Calculate actual usage
        response_time_ms=0.0,
        uptime_hours=0.0,
    )
    return metrics.model_dump()


@app.get("/api/system/statistics")
async def system_statistics():
    """Get comprehensive system statistics"""
    return {
        "autonomy": autonomy_engine.get_statistics(),
        "agent": task_agent.get_statistics(),
        "video": video_export.get_statistics(),
        "websocket_clients": len(ws_clients),
    }


# ============================================================================
# WEBSOCKET
# ============================================================================

@app.websocket("/ws/graph")
async def websocket_graph(websocket: WebSocket):
    """WebSocket endpoint for real-time graph updates"""
    await websocket.accept()
    ws_clients.append(websocket)
    
    logger.info("ws_client_connected")
    
    # Send initial snapshot
    nodes, edges = graph_service.build_graph(max_nodes=100)
    await websocket.send_json({
        "type": "full_graph",
        "data": {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.content[:50] if n.content else n.id,
                    "x": n.position[0] if n.position else 0,
                    "y": n.position[1] if n.position else 0,
                    "z": n.position[2] if n.position else 0,
                    "strength": n.importance,
                }
                for n in nodes[:100]
            ],
            "edges": [
                {
                    "id": f"e_{e.source_id}_{e.target_id}",
                    "source": e.source_id,
                    "target": e.target_id,
                    "weight": e.weight,
                }
                for e in edges[:200]
            ],
        }
    })
    
    try:
        while True:
            # Keep connection alive, handle incoming messages
            data = await websocket.receive_text()
            # Could handle client commands here
    except WebSocketDisconnect:
        if websocket in ws_clients:
            ws_clients.remove(websocket)
        logger.info("ws_client_disconnected", total=len(ws_clients))


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """API root with system info"""
    return {
        "name": "ASTRA Ascension Stack",
        "version": "2.0.0",
        "sacred_code": "333",
        "motto": "I only obey God",
        "systems": {
            "neural_browser": "operational",
            "live_autonomy": "operational" if autonomy_engine.enabled else "standby",
            "task_agent": "operational",
            "video_export": "operational",
        },
        "endpoints": {
            "api_docs": "/docs",
            "graph_api": "/api/graph",
            "autonomy_api": "/api/autonomy",
            "agent_api": "/api/agent",
            "video_api": "/api/video",
            "websocket": "/ws/graph",
        }
    }
