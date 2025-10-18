"""
ASTRA Bridge Module
Production-grade bridge layer for turning cryptic inputs into structured intents & facts.
Routes to Memory, Tools, or Dialogue with safety and observability.

Sacred Code: 333
Built for Saint Lucid
"""
from .config import BridgeConfig
from .schemas import BridgeEvent, BridgeIntent, BridgeFact, BridgeRouteResult, BridgeKind
from .interpreter import interpret, LLM_ABSTRACTOR
from .router import route
from .memory_bridge import MemoryBridgeService, MemoryLTMAdapter, MemoryEpisodicAdapter
from .tool_bridge import ToolBridgeService, TaskAgentAdapter
from .registry import BridgeRegistry
from .api_routes import router as bridge_router, setup_bridge

__all__ = [
    "BridgeConfig",
    "BridgeEvent",
    "BridgeIntent",
    "BridgeFact",
    "BridgeRouteResult",
    "BridgeKind",
    "interpret",
    "route",
    "MemoryBridgeService",
    "MemoryLTMAdapter",
    "MemoryEpisodicAdapter",
    "ToolBridgeService",
    "TaskAgentAdapter",
    "BridgeRegistry",
    "LLM_ABSTRACTOR",
    "bridge_router",
    "setup_bridge",
]
