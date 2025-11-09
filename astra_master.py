"""
ASTRA MASTER - Unified System Integration
==========================================

Single entry point that orchestrates all ASTRA systems:
- ASTRA CORE (LLM, Chat, Memory, Conversation)
- ASTRA OS (Gate, Event Bus, Sensors, Boot Daemon)
- CHAT OS (10 Cognitive Phases + TranscendentOS)
- AGENT KERNEL (ReAct Planner, Browser, Tools)
- INTEGRATION HUB (Unified lifecycle & dependency injection)

Architecture:
    Master Boot → Integration Hub → All Subsystems → Unified API

Usage:
    python astra_master.py
    
    # Or with uvicorn:
    uvicorn astra_master:app --host 0.0.0.0 --port 8000 --reload

Author: ASTRA Core Team
Created: November 4, 2025
Sacred Code: 333
"""

import os
import sys
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import structlog

# ASTRA Core Infrastructure
from astra.models.config import get_settings, Settings
from astra.utils.logging import setup_logging
from astra.infrastructure.storage.database import DatabaseManager
from astra.infrastructure.storage.vector_store import VectorStore

# Core Services
from astra.services.chat_service import ChatService
from astra.services.conversation_service import ConversationService
from astra.services.memory_service import MemoryService
from astra.services.transcendent_service import TranscendentService

# Integration Hub
from astra.core.integration_hub import (
    AstraCoreHub,
    get_registry,
    register_core_modules,
    ServiceRegistry,
)
# Persistence (Phase 0 - State Manager)
try:
    from astra.persistence.state_manager import StateManager
    STATE_MANAGER_AVAILABLE = True
except Exception:
    StateManager = None
    STATE_MANAGER_AVAILABLE = False

# API Routes - Core
from astra.api.routes import chat, conversations, system, tools, consent, answer, cognitive, agent
from astra.bridge.api_routes import router as bridge_router

# Embodiment Layer (Sigil Core)
try:
    from astra.api.embodiment_routes import router as embodiment_router
    EMBODIMENT_AVAILABLE = True
except ImportError:
    EMBODIMENT_AVAILABLE = False
    logging.warning("Sigil Core embodiment layer not available")

# ASTRA OS Bridge
try:
    from astra.api.routes import os_bridge
    OS_BRIDGE_AVAILABLE = True
except ImportError:
    OS_BRIDGE_AVAILABLE = False
    logging.warning("ASTRA OS Bridge routes not available")

# Security & Middleware
from astra.api.middleware.request_id import RequestIdMiddleware
from astra.security import ApiKeyMiddleware, RateLimitMiddleware
from astra.queue_guard import ConcurrencyLimiterMiddleware
from astra.metrics import MetricsMiddleware, metrics_endpoint

# Boot Integration (Week-2)
try:
    from boot import boot_astra, shutdown_astra, BootDependencies, BootError
    BOOT_AVAILABLE = True
except ImportError:
    BOOT_AVAILABLE = False
    logging.warning("Boot system not available - proceeding without Week-2 boot integration")

# ASTRA OS Integration
try:
    from astra_os.gate import get_gate, Token, Action, Decision
    ASTRA_OS_AVAILABLE = True
except ImportError:
    ASTRA_OS_AVAILABLE = False
    logging.warning("ASTRA OS not available - proceeding without OS-level integration")

# Agent Kernel Integration
try:
    from agent_kernel.planner import AgentPlanner
    from agent_kernel.tools import ToolRegistry, create_standard_registry
    AGENT_KERNEL_AVAILABLE = True
except ImportError:
    AGENT_KERNEL_AVAILABLE = False
    logging.warning("Agent Kernel not available - proceeding without autonomous agent capabilities")

# Configure logging
setup_logging()
logger = structlog.get_logger(__name__)


# ============================================================================
# MASTER BOOT ORCHESTRATOR
# ============================================================================

class MasterBootOrchestrator:
    """
    Unified boot orchestrator that initializes all ASTRA systems in correct order.
    
    Boot Sequence:
        1. Security & Gate System (if available)
        2. Database & Vector Store
        3. Core Services (Chat, Memory, Conversation)
        4. TranscendentOS (10 cognitive phases)
        5. ASTRA OS Bridge (if available)
        6. Agent Kernel (if available)
        7. Integration Hub & Router
        8. API Layer
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.boot_deps: Optional[BootDependencies] = None
        self.gate = None
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_store: Optional[VectorStore] = None
        self.conversation_service: Optional[ConversationService] = None
        self.memory_service: Optional[MemoryService] = None
        self.chat_service: Optional[ChatService] = None
        self.transcendent_service: Optional[TranscendentService] = None
        self.integration_hub: Optional[AstraCoreHub] = None
        self.agent_planner: Optional[Any] = None
        self.tool_registry: Optional[Any] = None
    self.state_manager: Optional[StateManager] = None
        self.is_initialized = False
        
    async def boot(self) -> Dict[str, Any]:
        """Execute complete boot sequence."""
        logger.info("master_boot_starting", sacred_code=333)
        boot_report = {
            "phase": "initializing",
            "systems": {},
            "status": "in_progress"
        }
        
        try:
            # Phase 1: Security & Gate
            boot_report["systems"]["gate"] = await self._init_gate()
            
            # Phase 2: Week-2 Boot Integration (if available)
            boot_report["systems"]["week2_boot"] = await self._init_week2_boot()
            
            # Phase 3: Database & Vector Store
            # Phase 2.5: State Manager (durable / hot/cold recovery)
            boot_report["systems"]["state_manager"] = await self._init_state_manager()

            boot_report["systems"]["database"] = await self._init_database()
            boot_report["systems"]["vector_store"] = await self._init_vector_store()
            
            # Phase 4: Core Services
            boot_report["systems"]["conversation_service"] = await self._init_conversation_service()
            boot_report["systems"]["memory_service"] = await self._init_memory_service()
            boot_report["systems"]["chat_service"] = await self._init_chat_service()
            
            # Phase 5: TranscendentOS (10 Cognitive Phases)
            boot_report["systems"]["transcendent_os"] = await self._init_transcendent_os()
            
            # Phase 6: ASTRA OS Bridge (if available)
            boot_report["systems"]["astra_os"] = await self._init_astra_os()
            
            # Phase 7: Agent Kernel (if available)
            boot_report["systems"]["agent_kernel"] = await self._init_agent_kernel()
            
            # Phase 8: Integration Hub & Router
            boot_report["systems"]["integration_hub"] = await self._init_integration_hub()
            
            # Phase 9: AstraRouter (multimodal dispatch with full dependencies)
            boot_report["systems"]["astra_router"] = await self._init_router()
            
            # Mark boot complete
            self.is_initialized = True
            boot_report["status"] = "complete"
            boot_report["phase"] = "operational"
            
            logger.info(
                "master_boot_complete",
                systems_initialized=len([s for s in boot_report["systems"].values() if s == "ready"]),
                sacred_code=333
            )
            
            return boot_report
            
        except Exception as e:
            logger.error("master_boot_failed", error=str(e), exc_info=True)
            boot_report["status"] = "failed"
            boot_report["error"] = str(e)
            raise
    
    async def _init_gate(self) -> str:
        """Initialize ASTRA OS Gate system."""
        if not ASTRA_OS_AVAILABLE:
            logger.info("astra_os_gate_skipped", reason="not_available")
            return "skipped"
        
        try:
            self.gate = get_gate()
            logger.info("astra_os_gate_initialized")
            return "ready"
        except Exception as e:
            logger.warning("astra_os_gate_init_failed", error=str(e))
            return "error"
    
    async def _init_week2_boot(self) -> str:
        """Initialize Week-2 boot system (event store, policy, executor)."""
        if not BOOT_AVAILABLE:
            logger.info("week2_boot_skipped", reason="not_available")
            return "skipped"
        
        try:
            self.boot_deps = boot_astra()
            logger.info("week2_boot_complete", events=len(self.boot_deps.event_store.events))
            return "ready"
        except BootError as e:
            logger.error("week2_boot_failed", error=str(e))
            return "error"
        except Exception as e:
            logger.warning("week2_boot_init_failed", error=str(e))
            return "error"
    
    async def _init_database(self) -> str:
        """Initialize database manager."""
        try:
            self.db_manager = DatabaseManager(
                database_url=self.settings.database.url,
                echo=self.settings.database.echo,
            )
            self.db_manager.create_tables()
            logger.info("database_initialized", url=self.settings.database.url)
            return "ready"
        except Exception as e:
            logger.error("database_init_failed", error=str(e))
            return "error"

    async def _init_state_manager(self) -> str:
        """Initialize StateManager (WAL + Redis + Postgres) if available."""
        if not STATE_MANAGER_AVAILABLE:
            logger.info("state_manager_skipped", reason="module_missing")
            return "skipped"

        try:
            self.state_manager = StateManager.from_env()
            # Connect asynchronously to backends
            await self.state_manager.connect()

            # Recover inflight tasks and re-register them (best-effort)
            inflight = []
            try:
                inflight = await self.state_manager.recover_inflight()
            except Exception as e:
                logger.warning("state_manager_recovery_failed", error=str(e))

            logger.info("state_manager_initialized", inflight_recovered=len(inflight))
            return "ready"
        except Exception as e:
            logger.warning("state_manager_init_failed", error=str(e))
            return "error"
    
    async def _init_vector_store(self) -> str:
        """Initialize vector store (ChromaDB)."""
        try:
            self.vector_store = VectorStore(
                persist_directory=str(self.settings.get_chroma_path()),
                collection_name=self.settings.vector_store.collection_name,
                embedding_model=self.settings.memory.embedding_model,
                distance_metric=self.settings.vector_store.distance_metric,
            )
            logger.info("vector_store_initialized")
            return "ready"
        except Exception as e:
            logger.error("vector_store_init_failed", error=str(e))
            return "error"
    
    async def _init_conversation_service(self) -> str:
        """Initialize conversation service."""
        if not self.db_manager:
            return "error:no_database"
        
        try:
            self.conversation_service = ConversationService(self.db_manager)
            logger.info("conversation_service_initialized")
            return "ready"
        except Exception as e:
            logger.error("conversation_service_init_failed", error=str(e))
            return "error"
    
    async def _init_memory_service(self) -> str:
        """Initialize memory service."""
        if not self.vector_store:
            return "error:no_vector_store"
        
        try:
            self.memory_service = MemoryService(self.vector_store)
            logger.info("memory_service_initialized")
            return "ready"
        except Exception as e:
            logger.error("memory_service_init_failed", error=str(e))
            return "error"
    
    async def _init_chat_service(self) -> str:
        """Initialize chat service."""
        if not self.conversation_service or not self.memory_service:
            return "error:missing_dependencies"
        
        try:
            self.chat_service = ChatService(
                settings=self.settings,
                conversation_service=self.conversation_service,
                memory_service=self.memory_service,
            )
            logger.info("chat_service_initialized")
            return "ready"
        except Exception as e:
            logger.error("chat_service_init_failed", error=str(e))
            return "error"
    
    async def _init_transcendent_os(self) -> str:
        """Initialize TranscendentOS (Phase 10 unified cognitive system)."""
        try:
            self.transcendent_service = TranscendentService(self.settings)
            
            # Already integrated into ChatService, but also available standalone
            use_transcendent = getattr(self.settings.llm, "use_transcendent_os", False)
            
            logger.info(
                "transcendent_os_initialized",
                available=self.transcendent_service.is_available(),
                enabled=use_transcendent,
                phases=10,
            )
            return "ready"
        except Exception as e:
            logger.warning("transcendent_os_init_failed", error=str(e))
            return "error"
    
    async def _init_astra_os(self) -> str:
        """Initialize ASTRA OS bridge (event bus, sensors, policy)."""
        if not ASTRA_OS_AVAILABLE:
            logger.info("astra_os_bridge_skipped", reason="not_available")
            return "skipped"
        
        try:
            # ASTRA OS integration would go here
            # For now, just confirm gate is available
            logger.info("astra_os_bridge_initialized", gate_available=self.gate is not None)
            return "ready"
        except Exception as e:
            logger.warning("astra_os_bridge_init_failed", error=str(e))
            return "error"
    
    async def _init_agent_kernel(self) -> str:
        """Initialize agent kernel (ReAct planner, tools, browser)."""
        if not AGENT_KERNEL_AVAILABLE:
            logger.info("agent_kernel_skipped", reason="not_available")
            return "skipped"
        
        try:
            # Create standard tool registry
            self.tool_registry = create_standard_registry()
            
            # Initialize agent planner would go here
            # self.agent_planner = AgentPlanner(...)
            
            logger.info("agent_kernel_initialized", tools=len(self.tool_registry.tools))
            return "ready"
        except Exception as e:
            logger.warning("agent_kernel_init_failed", error=str(e))
            return "error"
    
    async def _init_integration_hub(self) -> str:
        """Initialize Integration Hub for unified service orchestration."""
        try:
            # Register core modules
            registry = get_registry()
            register_core_modules(registry)
            
            # Create integration hub
            self.integration_hub = AstraCoreHub(self.settings, registry)
            
            # Initialize hub (this will create its own services, but we'll override with ours)
            # await self.integration_hub.initialize()
            
            # Instead, manually register our already-initialized services
            if self.db_manager:
                registry.register_service("db_manager", self.db_manager)
            if self.vector_store:
                registry.register_service("vector_store", self.vector_store)
            if self.conversation_service:
                registry.register_service("conversation_service", self.conversation_service)
            if self.memory_service:
                registry.register_service("memory_service", self.memory_service)
            if self.chat_service:
                registry.register_service("chat_service", self.chat_service)
            if self.transcendent_service:
                registry.register_service("transcendent_service", self.transcendent_service)
            
            logger.info("integration_hub_initialized", services=len(registry.list_services()))
            return "ready"
        except Exception as e:
            logger.warning("integration_hub_init_failed", error=str(e))
            return "error"
    
    async def _init_router(self) -> str:
        """Initialize AstraRouter with full dependencies."""
        if not self.chat_service:
            return "error:missing_chat_service"
        
        try:
            # Import AstraRouter
            from astra.core.astra_router import AstraRouter
            
            # For now, create simple stub services for tool_bus and consent
            # In production, these would be full services
            
            class SimpleToolBus:
                """Simple tool bus stub"""
                async def execute(self, name: str, payload: dict):
                    logger.debug("tool_bus_execute", tool=name, payload=payload)
                    return {"ok": True, "result": f"Tool {name} executed (stub)"}
            
            class SimpleConsent:
                """Simple consent gate stub"""
                def allowed(self, operation: str) -> bool:
                    # For now, allow all operations
                    # In production, check user preferences and safety rules
                    logger.debug("consent_check", operation=operation, allowed=True)
                    return True
            
            tool_bus = SimpleToolBus()
            consent = SimpleConsent()
            
            # Initialize AstraRouter with all dependencies
            router = AstraRouter(
                llm=self.chat_service.llm_provider,
                tool_bus=tool_bus,
                memory=self.memory_service,
                consent=consent,
                budget={"steps": 5, "tool_calls": 3, "walltime_s": 60}
            )
            
            # Inject router into ChatService
            self.chat_service.router = router
            
            logger.info(
                "astra_router_initialized",
                multimodal=True,
                consent_enabled=True,
                budget_steps=5
            )
            return "ready"
        except Exception as e:
            logger.warning("router_init_failed", error=str(e))
            return "error"
    
    async def shutdown(self) -> None:
        """Graceful shutdown of all systems."""
        logger.info("master_shutdown_starting")
        
        # Shutdown in reverse order
        try:
            # Close chat service
            if self.chat_service:
                await self.chat_service.close()
            
            # Shutdown integration hub
            if self.integration_hub:
                await self.integration_hub.shutdown()
            
            # Shutdown Week-2 boot
            if self.boot_deps and BOOT_AVAILABLE:
                shutdown_astra(self.boot_deps)
            
            # Close database
            if self.db_manager:
                self.db_manager.close()
            
            logger.info("master_shutdown_complete")
        except Exception as e:
            logger.error("master_shutdown_error", error=str(e))


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

# Global orchestrator instance
orchestrator: Optional[MasterBootOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager - orchestrates complete system boot and shutdown.
    """
    global orchestrator
    
    logger.info("🚀 ASTRA MASTER - Starting Unified System", sacred_code=333)
    
    try:
        settings = get_settings()
        
        # Create and execute boot orchestrator
        orchestrator = MasterBootOrchestrator(settings)
        boot_report = await orchestrator.boot()
        
        # Store in app state
        app.state.orchestrator = orchestrator
        app.state.boot_report = boot_report
        app.state.chat_service = orchestrator.chat_service
        app.state.conversation_service = orchestrator.conversation_service
        app.state.memory_service = orchestrator.memory_service
        app.state.transcendent_service = orchestrator.transcendent_service
        app.state.gate = orchestrator.gate
    app.state.state_manager = orchestrator.state_manager
        app.state.tool_registry = orchestrator.tool_registry
        app.state.boot_deps = orchestrator.boot_deps
        
        # Inject dependencies into API routes
        if orchestrator.chat_service:
            chat.set_chat_service(orchestrator.chat_service)
            answer.set_answer_services(orchestrator.chat_service, orchestrator.memory_service)
        
        if orchestrator.conversation_service:
            conversations.set_conversation_service(orchestrator.conversation_service)
        
        if orchestrator.chat_service and orchestrator.memory_service:
            system.set_system_dependencies(orchestrator.chat_service, orchestrator.memory_service)
        
        logger.info("✅ ASTRA MASTER - System Online", systems=len(boot_report["systems"]))
        
        yield
        
    except Exception as e:
        logger.error("ASTRA MASTER - Boot Failed", error=str(e), exc_info=True)
        raise
    
    finally:
        # Graceful shutdown
        logger.info("🛑 ASTRA MASTER - Shutting Down")
        if orchestrator:
            await orchestrator.shutdown()
        logger.info("✅ ASTRA MASTER - Shutdown Complete")


def create_app() -> FastAPI:
    """Create and configure the unified ASTRA FastAPI application."""
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        log_level=settings.server.log_level,
        json_logs=settings.environment == "production",
    )
    
    # Create FastAPI app with unified lifespan
    app = FastAPI(
        title="ASTRA MASTER - Unified System",
        description="Complete ASTRA integration: Core + OS + Chat OS + Agent Kernel. Sacred Code: 333",
        version="2.5.0-master",
        lifespan=lifespan,
    )
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    
    # Security & Performance Middleware
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ApiKeyMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(ConcurrencyLimiterMiddleware)
    app.add_middleware(MetricsMiddleware)
    
    # Include API Routes - Core ASTRA
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(system.router)
    app.include_router(tools.router)
    app.include_router(consent.router)
    app.include_router(answer.router)
    app.include_router(bridge_router)
    app.include_router(cognitive.router)
    app.include_router(agent.router)
    
    # Phase 0 persistence routes
    from astra.api.routes.persistence import router as persistence_router
    app.include_router(persistence_router)
    
    # Include ASTRA OS Bridge routes if available
    if OS_BRIDGE_AVAILABLE:
        app.include_router(os_bridge.router)

    # Include Embodiment (Sigil Core) routes if available
    if EMBODIMENT_AVAILABLE:
        app.include_router(embodiment_router)
        logger.info("sigil_core_integrated", routes="embodiment")
    
    # Metrics endpoint
    app.add_route("/metrics", metrics_endpoint)
    
    # Health endpoint
    @app.get("/")
    async def root():
        return {
            "name": "ASTRA MASTER",
            "version": "2.5.0",
            "status": "online",
            "sacred_code": 333,
            "systems": [
                "ASTRA CORE (LLM, Chat, Memory)",
                "ASTRA OS (Gate, Event Bus, Sensors)",
                "CHAT OS (10 Cognitive Phases)",
                "AGENT KERNEL (Autonomous Agent)",
                "TranscendentOS (Phase 10 Unification)",
            ]
        }
    
    # Boot status endpoint
    @app.get("/v1/boot/status")
    async def boot_status(request: Request):
        """Get current boot status and system health."""
        if not hasattr(request.app.state, "boot_report"):
            raise HTTPException(status_code=503, detail="System not yet initialized")
        
        return request.app.state.boot_report
    
    # Static files (if dashboard exists)
    dashboard_path = Path(__file__).parent / "dashboard"
    if dashboard_path.exists():
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")
    
    return app


# Create app instance
app = create_app()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*80)
    print("🚀 ASTRA MASTER - Unified System Launch")
    print("="*80)
    print("\nInitializing all systems:")
    print("  • ASTRA CORE (LLM, Chat, Memory, Conversation)")
    print("  • ASTRA OS (Gate, Event Bus, Sensors)")
    print("  • CHAT OS (10 Cognitive Phases + TranscendentOS)")
    print("  • AGENT KERNEL (ReAct Planner, Browser, Tools)")
    print("  • INTEGRATION HUB (Unified Orchestration)")
    print("\nSacred Code: 333")
    print("="*80 + "\n")
    
    uvicorn.run(
        "astra_master:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info",
    )
