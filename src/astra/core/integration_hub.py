"""
ASTRA Core Integration Hub
Central orchestration layer connecting all ASTRA modules into a unified network.

This is the nervous system of ASTRA - the core coordinates all subsystems
as one coherent robotic body piloted by consciousness.

Sacred Code: 333
Built for Saint Lucid
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

import structlog

from astra.models.config import Settings

logger = structlog.get_logger()


# ============================================================================
# MODULE REGISTRY & LIFECYCLE
# ============================================================================

class ModuleState(Enum):
    """Module lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ModuleDescriptor:
    """Describes a module and its dependencies"""
    name: str
    category: str  # core, infrastructure, service, api, bridge, visualization
    dependencies: List[str] = field(default_factory=list)
    state: ModuleState = ModuleState.UNINITIALIZED
    instance: Optional[Any] = None
    error: Optional[str] = None
    initialization_time_ms: Optional[float] = None


class ServiceRegistry:
    """
    Central service registry for dependency injection and module coordination.
    
    This is ASTRA's nervous system - every module registers here for discovery,
    dependency resolution, and health monitoring.
    """
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._modules: Dict[str, ModuleDescriptor] = {}
        self._lifecycle_hooks: Dict[str, List[Callable]] = {
            "pre_init": [],
            "post_init": [],
            "pre_shutdown": [],
            "post_shutdown": [],
        }
        self._initialized = False
        
    def register_module(self, descriptor: ModuleDescriptor) -> None:
        """Register a module descriptor"""
        self._modules[descriptor.name] = descriptor
        logger.info("module_registered", name=descriptor.name, category=descriptor.category)
    
    def register_service(self, name: str, service: Any, overwrite: bool = False) -> None:
        """
        Register a service instance for dependency injection.
        
        Args:
            name: Service identifier (e.g., "llm_provider", "memory_service")
            service: Service instance
            overwrite: Allow overwriting existing service
        """
        if name in self._services and not overwrite:
            raise ValueError(f"Service '{name}' already registered. Use overwrite=True to replace.")
        
        self._services[name] = service
        logger.info("service_registered", name=name, type=type(service).__name__)
    
    def get_service(self, name: str) -> Any:
        """
        Retrieve a registered service.
        
        Args:
            name: Service identifier
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service not found
        """
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found in registry. Available: {list(self._services.keys())}")
        return self._services[name]
    
    def has_service(self, name: str) -> bool:
        """Check if service is registered"""
        return name in self._services
    
    def get_module_state(self, name: str) -> Optional[ModuleState]:
        """Get module state"""
        module = self._modules.get(name)
        return module.state if module else None
    
    def update_module_state(self, name: str, state: ModuleState, error: Optional[str] = None) -> None:
        """Update module state"""
        if name in self._modules:
            self._modules[name].state = state
            if error:
                self._modules[name].error = error
            logger.info("module_state_updated", name=name, state=state.value, error=error)
    
    def add_lifecycle_hook(self, hook_type: str, callback: Callable) -> None:
        """Add lifecycle hook (pre_init, post_init, pre_shutdown, post_shutdown)"""
        if hook_type not in self._lifecycle_hooks:
            raise ValueError(f"Invalid hook type: {hook_type}")
        self._lifecycle_hooks[hook_type].append(callback)
    
    async def execute_hooks(self, hook_type: str) -> None:
        """Execute all hooks of given type"""
        for hook in self._lifecycle_hooks[hook_type]:
            try:
                result = hook()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.warning("lifecycle_hook_failed", hook_type=hook_type, error=str(e))
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all modules"""
        return {
            "modules": {
                name: {
                    "state": mod.state.value,
                    "category": mod.category,
                    "dependencies": mod.dependencies,
                    "error": mod.error,
                    "init_time_ms": mod.initialization_time_ms,
                }
                for name, mod in self._modules.items()
            },
            "services_count": len(self._services),
            "services": list(self._services.keys()),
        }


# Global registry instance
_registry = ServiceRegistry()


def get_registry() -> ServiceRegistry:
    """Get global service registry"""
    return _registry


# ============================================================================
# CORE INTEGRATION HUB
# ============================================================================

class AstraCoreHub:
    """
    Central integration hub - ASTRA's consciousness coordinator.
    
    This is the brain that pilots the robotic body. All modules connect here
    to form a unified network of cognitive capabilities.
    """
    
    def __init__(self, settings: Settings, registry: Optional[ServiceRegistry] = None):
        self.settings = settings
        self.registry = registry or get_registry()
        self._initialized = False
        
        # Core components (initialized during startup)
        self.llm_provider = None
        self.memory_service = None
        self.memory_engine = None
        self.conversation_service = None
        self.chat_service = None
        
        # Infrastructure
        self.db_manager = None
        self.vector_store = None
        
        # Router & Bridges
        self.astra_router = None
        self.memory_bridge = None
        self.tool_bridge = None
        
        # Tool & Consent
        self.tool_bus = None
        self.consent_service = None
        
        # Visualization & Autonomy
        self.graph_service = None
        self.autonomy_engine = None
        self.task_agent = None
        
        logger.info("astra_core_hub_created")
    
    async def initialize(self) -> None:
        """
        Initialize all ASTRA subsystems in dependency order.
        
        Initialization order:
        1. Configuration & Logging
        2. Infrastructure (Database, Vector Store)
        3. Services (Memory, Conversation, LLM)
        4. Core (Router, Bridges)
        5. Tools & Consent
        6. API & Visualization
        """
        if self._initialized:
            logger.warning("astra_hub_already_initialized")
            return
        
        logger.info("astra_hub_initialization_start", sacred_code=333)
        
        await self.registry.execute_hooks("pre_init")
        
        try:
            # Phase 1: Infrastructure
            await self._init_infrastructure()
            
            # Phase 2: Core Services
            await self._init_core_services()
            
            # Phase 3: Router & Bridges
            await self._init_router_and_bridges()
            
            # Phase 4: Tools & Consent
            await self._init_tools_and_consent()
            
            # Phase 5: Visualization & Autonomy
            await self._init_visualization()
            
            self._initialized = True
            
            await self.registry.execute_hooks("post_init")
            
            logger.info("astra_hub_initialization_complete", 
                       modules=len(self.registry._modules),
                       services=len(self.registry._services))
            
        except Exception as e:
            logger.error("astra_hub_initialization_failed", error=str(e), exc_info=True)
            raise
    
    async def _init_infrastructure(self) -> None:
        """Initialize infrastructure layer (database, vector store)"""
        logger.info("init_infrastructure_start")
        
        # Database Manager
        from astra.infrastructure.storage.database import DatabaseManager
        self.db_manager = DatabaseManager(
            database_url=self.settings.database.url,
            echo=self.settings.database.echo
        )
        self.db_manager.create_tables()
        self.registry.register_service("db_manager", self.db_manager)
        self.registry.update_module_state("database", ModuleState.READY)
        
        # Vector Store
        from astra.infrastructure.storage.vector_store import VectorStore
        self.vector_store = VectorStore(
            persist_directory=str(self.settings.get_chroma_path()),
            collection_name=self.settings.vector_store.collection_name,
            embedding_model=self.settings.memory.embedding_model,
            distance_metric=self.settings.vector_store.distance_metric
        )
        self.registry.register_service("vector_store", self.vector_store)
        self.registry.update_module_state("vector_store", ModuleState.READY)
        
        logger.info("init_infrastructure_complete")
    
    async def _init_core_services(self) -> None:
        """Initialize core services (memory, conversation, LLM, chat)"""
        logger.info("init_core_services_start")
        
        # Conversation Service
        from astra.services.conversation_service import ConversationService
        self.conversation_service = ConversationService(self.db_manager)
        self.registry.register_service("conversation_service", self.conversation_service)
        self.registry.update_module_state("conversation_service", ModuleState.READY)
        
        # Memory Service
        from astra.services.memory_service import MemoryService
        self.memory_service = MemoryService(self.vector_store)
        self.registry.register_service("memory_service", self.memory_service)
        self.registry.update_module_state("memory_service", ModuleState.READY)
        
        # Memory Engine
        try:
            from pathlib import Path
            from astra.core.memory_engine import MemoryEngine
            
            # Extract path from database URL
            db_path_str = self.settings.database.url.replace("sqlite:///", "")
            db_path = Path(db_path_str) if db_path_str else None
            
            self.memory_engine = MemoryEngine(
                vector_store=self.vector_store,
                database_path=db_path
            )
            self.registry.register_service("memory_engine", self.memory_engine)
            self.registry.update_module_state("memory_engine", ModuleState.READY)
        except Exception as e:
            logger.warning("memory_engine_init_failed", error=str(e))
            self.registry.update_module_state("memory_engine", ModuleState.ERROR, str(e))
        
        # LLM Provider
        from astra.infrastructure.llm.factory import create_llm_provider
        self.llm_provider = create_llm_provider(self.settings)
        self.registry.register_service("llm_provider", self.llm_provider)
        self.registry.update_module_state("llm_provider", ModuleState.READY)
        
        # Chat Service
        from astra.services.chat_service import ChatService
        self.chat_service = ChatService(
            settings=self.settings,
            conversation_service=self.conversation_service,
            memory_service=self.memory_service
        )
        self.registry.register_service("chat_service", self.chat_service)
        self.registry.update_module_state("chat_service", ModuleState.READY)
        
        logger.info("init_core_services_complete")
    
    async def _init_router_and_bridges(self) -> None:
        """Initialize AstraRouter and bridge modules"""
        logger.info("init_router_and_bridges_start")
        
        # Tool Bus (required for router)
        try:
            from astra.bridge.tool_bridge import ToolBridgeService, TaskAgentAdapter
            task_adapter = TaskAgentAdapter()
            self.tool_bridge = ToolBridgeService(task_adapter, safe_glob="tools/safe_*.py")
            self.registry.register_service("tool_bridge", self.tool_bridge)
            self.registry.update_module_state("tool_bridge", ModuleState.READY)
        except Exception as e:
            logger.warning("tool_bridge_init_failed", error=str(e))
            self.registry.update_module_state("tool_bridge", ModuleState.ERROR, str(e))
        
        # Consent Service (UI dialogs - optional)
        try:
            from astra.ui.consent import ConsentDialog
            # Consent is UI-based, register the dialog class for optional use
            self.registry.register_service("consent_dialog", ConsentDialog)
            self.registry.update_module_state("consent_service", ModuleState.READY)
        except Exception as e:
            logger.warning("consent_ui_init_failed", error=str(e))
            self.registry.update_module_state("consent_service", ModuleState.ERROR, str(e))
        
        # AstraRouter (requires tool_bridge, consent, memory, llm)
        try:
            from astra.core.astra_router import AstraRouter
            self.astra_router = AstraRouter(
                llm=self.llm_provider,
                tool_bus=self.tool_bridge,
                memory=self.memory_service,
                consent=self.consent_service
            )
            self.registry.register_service("astra_router", self.astra_router)
            self.registry.update_module_state("astra_router", ModuleState.READY)
            
            # Inject router into chat service
            if self.chat_service:
                self.chat_service.router = self.astra_router
                logger.info("astra_router_injected_into_chat_service")
                
        except Exception as e:
            logger.warning("astra_router_init_failed", error=str(e))
            self.registry.update_module_state("astra_router", ModuleState.ERROR, str(e))
        
        # Memory Bridge
        try:
            from astra.bridge.memory_bridge import MemoryBridgeService, MemoryLTMAdapter, MemoryEpisodicAdapter
            ltm_adapter = MemoryLTMAdapter()
            episodic_adapter = MemoryEpisodicAdapter()
            self.memory_bridge = MemoryBridgeService(ltm_adapter, episodic_adapter)
            self.registry.register_service("memory_bridge", self.memory_bridge)
            self.registry.update_module_state("memory_bridge", ModuleState.READY)
        except Exception as e:
            logger.warning("memory_bridge_init_failed", error=str(e))
            self.registry.update_module_state("memory_bridge", ModuleState.ERROR, str(e))
        
        logger.info("init_router_and_bridges_complete")
    
    async def _init_tools_and_consent(self) -> None:
        """Initialize tool execution and consent management"""
        logger.info("init_tools_and_consent_start")
        
        # Already initialized in _init_router_and_bridges
        # This phase is for additional tool plugins
        
        try:
            # Register tool plugins if available
            if self.tool_bridge:
                # File operations
                try:
                    from astra.visualization.plugins import register_file_ops
                    # Note: This requires task_agent, will be initialized in visualization phase
                except ImportError:
                    logger.debug("file_ops_plugin_unavailable")
                
                # System info
                try:
                    from astra.visualization.plugins import register_system_info
                    # Note: This requires task_agent
                except ImportError:
                    logger.debug("system_info_plugin_unavailable")
                    
        except Exception as e:
            logger.warning("tool_plugins_init_failed", error=str(e))
        
        logger.info("init_tools_and_consent_complete")
    
    async def _init_visualization(self) -> None:
        """Initialize visualization layer (graph service, autonomy, task agents)"""
        logger.info("init_visualization_start")
        
        try:
            # Memory Graph Service
            from astra.visualization.memory_graph_service import MemoryGraphService
            self.graph_service = MemoryGraphService()
            
            # Connect to memory backends
            if self.memory_engine and self.memory_service:
                self.graph_service.set_backends(
                    memory_engine=self.memory_engine,
                    memory_service=self.memory_service
                )
            
            self.registry.register_service("graph_service", self.graph_service)
            self.registry.update_module_state("graph_service", ModuleState.READY)
            
        except Exception as e:
            logger.warning("graph_service_init_failed", error=str(e))
            self.registry.update_module_state("graph_service", ModuleState.ERROR, str(e))
        
        try:
            # Autonomy Engine
            from astra.visualization.autonomy_engine import AutonomyEngine, create_default_triggers
            self.autonomy_engine = AutonomyEngine()
            
            # Register default triggers
            for trigger in create_default_triggers():
                self.autonomy_engine.add_trigger(trigger)
            
            self.registry.register_service("autonomy_engine", self.autonomy_engine)
            self.registry.update_module_state("autonomy_engine", ModuleState.READY)
            
        except Exception as e:
            logger.warning("autonomy_engine_init_failed", error=str(e))
            self.registry.update_module_state("autonomy_engine", ModuleState.ERROR, str(e))
        
        try:
            # Task Agent Manager
            from astra.visualization.task_agent_manager import TaskAgentManager
            self.task_agent = TaskAgentManager()
            
            # Register plugins
            try:
                from astra.visualization.plugins import register_file_ops, register_system_info
                register_file_ops(self.task_agent)
                register_system_info(self.task_agent)
            except ImportError as e:
                logger.debug("task_agent_plugins_unavailable", error=str(e))
            
            self.registry.register_service("task_agent", self.task_agent)
            self.registry.update_module_state("task_agent", ModuleState.READY)
            
        except Exception as e:
            logger.warning("task_agent_init_failed", error=str(e))
            self.registry.update_module_state("task_agent", ModuleState.ERROR, str(e))
        
        logger.info("init_visualization_complete")
    
    async def shutdown(self) -> None:
        """Graceful shutdown of all subsystems"""
        if not self._initialized:
            return
        
        logger.info("astra_hub_shutdown_start", sacred_code=333)
        
        await self.registry.execute_hooks("pre_shutdown")
        
        # Shutdown in reverse dependency order
        components = [
            ("autonomy_engine", self.autonomy_engine),
            ("graph_service", self.graph_service),
            ("astra_router", self.astra_router),
            ("chat_service", self.chat_service),
            ("memory_service", self.memory_service),
            ("conversation_service", self.conversation_service),
            ("vector_store", self.vector_store),
            ("db_manager", self.db_manager),
        ]
        
        for name, component in components:
            if component is not None:
                try:
                    close_method = getattr(component, "close", None) or getattr(component, "shutdown", None)
                    if callable(close_method):
                        result = close_method()
                        if asyncio.iscoroutine(result):
                            await result
                    self.registry.update_module_state(name, ModuleState.SHUTDOWN)
                except Exception as e:
                    logger.warning("component_shutdown_failed", name=name, error=str(e))
        
        await self.registry.execute_hooks("post_shutdown")
        
        self._initialized = False
        logger.info("astra_hub_shutdown_complete")
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of entire ASTRA system"""
        return {
            "initialized": self._initialized,
            "registry": self.registry.get_health_status(),
            "sacred_code": 333,
        }


# ============================================================================
# LIFESPAN CONTEXT MANAGER
# ============================================================================

@asynccontextmanager
async def astra_lifespan(settings: Settings):
    """
    FastAPI lifespan context manager for ASTRA integration.
    
    Usage:
        from astra.core.integration_hub import astra_lifespan
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            async with astra_lifespan(settings) as hub:
                # Inject services into app state
                app.state.astra_hub = hub
                yield
    """
    hub = AstraCoreHub(settings)
    
    try:
        await hub.initialize()
        yield hub
    finally:
        await hub.shutdown()


# ============================================================================
# DEPENDENCY INJECTION HELPERS
# ============================================================================

def get_service(name: str) -> Any:
    """
    Get service from global registry (for FastAPI dependencies).
    
    Usage:
        from fastapi import Depends
        from astra.core.integration_hub import get_service
        
        @app.get("/chat")
        def chat(chat_service: ChatService = Depends(lambda: get_service("chat_service"))):
            ...
    """
    return get_registry().get_service(name)


def inject_dependencies(target: Any, **kwargs) -> None:
    """
    Inject dependencies into target object.
    
    Usage:
        router = AstraRouter(llm=None, tool_bus=None, memory=None, consent=None)
        inject_dependencies(
            router,
            llm=get_service("llm_provider"),
            tool_bus=get_service("tool_bridge"),
            memory=get_service("memory_service"),
            consent=get_service("consent_service")
        )
    """
    for key, value in kwargs.items():
        if hasattr(target, key):
            setattr(target, key, value)
            logger.debug("dependency_injected", target=type(target).__name__, key=key)
        else:
            logger.warning("dependency_injection_failed_no_attr", 
                          target=type(target).__name__, key=key)


# ============================================================================
# MODULE DEFINITIONS (for registration)
# ============================================================================

def register_core_modules(registry: ServiceRegistry) -> None:
    """Register all core ASTRA modules"""
    
    modules = [
        # Infrastructure
        ModuleDescriptor("database", "infrastructure", []),
        ModuleDescriptor("vector_store", "infrastructure", []),
        
        # Services
        ModuleDescriptor("conversation_service", "service", ["database"]),
        ModuleDescriptor("memory_service", "service", ["vector_store"]),
        ModuleDescriptor("memory_engine", "service", ["vector_store", "database"]),
        ModuleDescriptor("llm_provider", "service", []),
        ModuleDescriptor("chat_service", "service", ["conversation_service", "memory_service", "llm_provider"]),
        
        # Core
        ModuleDescriptor("astra_router", "core", ["llm_provider", "tool_bridge", "memory_service", "consent_service"]),
        
        # Bridges
        ModuleDescriptor("memory_bridge", "bridge", ["memory_service"]),
        ModuleDescriptor("tool_bridge", "bridge", []),
        
        # Tools & Security
        ModuleDescriptor("consent_service", "security", []),
        
        # Visualization
        ModuleDescriptor("graph_service", "visualization", ["memory_engine", "memory_service"]),
        ModuleDescriptor("autonomy_engine", "visualization", []),
        ModuleDescriptor("task_agent", "visualization", []),
    ]
    
    for module in modules:
        registry.register_module(module)
    
    logger.info("core_modules_registered", count=len(modules))


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "AstraCoreHub",
    "ServiceRegistry",
    "ModuleDescriptor",
    "ModuleState",
    "get_registry",
    "get_service",
    "inject_dependencies",
    "astra_lifespan",
    "register_core_modules",
]
