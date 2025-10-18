"""
ASTRA Module Connectors
Auto-discovery and registration connectors for all ASTRA modules.

Each connector knows how to:
1. Discover its dependencies from the service registry
2. Initialize its module with proper dependency injection
3. Register its services for other modules to use
4. Report health status and handle graceful shutdown

Sacred Code: 333
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

import structlog

from astra.core.integration_hub import ModuleDescriptor, ModuleState, ServiceRegistry
from astra.models.config import Settings

logger = structlog.get_logger()


# ============================================================================
# CONNECTOR PROTOCOL
# ============================================================================

class ModuleConnector(Protocol):
    """Protocol for module connectors"""
    
    def connect(self, registry: ServiceRegistry, settings: Settings) -> Any:
        """
        Initialize module and connect to dependencies.
        
        Returns:
            Initialized module instance
        """
        ...
    
    def disconnect(self, instance: Any) -> None:
        """Gracefully shutdown module"""
        ...


# ============================================================================
# INFRASTRUCTURE CONNECTORS
# ============================================================================

class DatabaseConnector:
    """Connector for database infrastructure"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize database manager"""
        from astra.infrastructure.storage.database import DatabaseManager
        
        db_manager = DatabaseManager(
            database_url=settings.database.url,
            echo=settings.database.echo
        )
        db_manager.create_tables()
        
        registry.register_service("db_manager", db_manager)
        registry.update_module_state("database", ModuleState.READY)
        
        logger.info("database_connector_initialized", url=settings.database.url)
        return db_manager
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Close database connections"""
        close_method = getattr(instance, "close", None)
        if callable(close_method):
            close_method()
        logger.info("database_connector_shutdown")


class VectorStoreConnector:
    """Connector for vector store infrastructure"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize vector store"""
        from astra.infrastructure.storage.vector_store import VectorStore
        
        vector_store = VectorStore(
            persist_directory=str(settings.get_chroma_path()),
            collection_name=settings.vector_store.collection_name,
            embedding_model=settings.memory.embedding_model,
            distance_metric=settings.vector_store.distance_metric
        )
        
        registry.register_service("vector_store", vector_store)
        registry.update_module_state("vector_store", ModuleState.READY)
        
        logger.info("vector_store_connector_initialized", path=str(settings.get_chroma_path()))
        return vector_store
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Cleanup vector store"""
        logger.info("vector_store_connector_shutdown")


# ============================================================================
# SERVICE CONNECTORS
# ============================================================================

class ConversationServiceConnector:
    """Connector for conversation service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize conversation service"""
        from astra.services.conversation_service import ConversationService
        
        db_manager = registry.get_service("db_manager")
        conversation_service = ConversationService(db_manager)
        
        registry.register_service("conversation_service", conversation_service)
        registry.update_module_state("conversation_service", ModuleState.READY)
        
        logger.info("conversation_service_connector_initialized")
        return conversation_service
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown conversation service"""
        logger.info("conversation_service_connector_shutdown")


class MemoryServiceConnector:
    """Connector for memory service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize memory service"""
        from astra.services.memory_service import MemoryService
        
        vector_store = registry.get_service("vector_store")
        memory_service = MemoryService(vector_store)
        
        registry.register_service("memory_service", memory_service)
        registry.update_module_state("memory_service", ModuleState.READY)
        
        logger.info("memory_service_connector_initialized")
        return memory_service
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown memory service"""
        logger.info("memory_service_connector_shutdown")


class MemoryEngineConnector:
    """Connector for memory engine"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize memory engine"""
        try:
            from pathlib import Path
            from astra.core.memory_engine import MemoryEngine
            
            vector_store = registry.get_service("vector_store")
            
            # Extract path from database URL
            db_path_str = settings.database.url.replace("sqlite:///", "")
            db_path = Path(db_path_str) if db_path_str else None
            
            memory_engine = MemoryEngine(
                vector_store=vector_store,
                database_path=db_path
            )
            
            registry.register_service("memory_engine", memory_engine)
            registry.update_module_state("memory_engine", ModuleState.READY)
            
            logger.info("memory_engine_connector_initialized")
            return memory_engine
            
        except ImportError as e:
            logger.warning("memory_engine_connector_unavailable", error=str(e))
            registry.update_module_state("memory_engine", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown memory engine"""
        if instance:
            logger.info("memory_engine_connector_shutdown")


class LLMProviderConnector:
    """Connector for LLM provider"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize LLM provider"""
        from astra.infrastructure.llm.factory import create_llm_provider
        
        llm_provider = create_llm_provider(settings)
        
        registry.register_service("llm_provider", llm_provider)
        registry.update_module_state("llm_provider", ModuleState.READY)
        
        logger.info("llm_provider_connector_initialized", 
                   model=settings.llm.model_name if hasattr(settings.llm, 'model_name') else 'unknown')
        return llm_provider
    
    @staticmethod
    async def disconnect(instance: Any) -> None:
        """Shutdown LLM provider"""
        close_method = getattr(instance, "close", None)
        if callable(close_method):
            import asyncio
            result = close_method()
            if asyncio.iscoroutine(result):
                await result
        logger.info("llm_provider_connector_shutdown")


class ChatServiceConnector:
    """Connector for chat service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize chat service"""
        from astra.services.chat_service import ChatService
        
        conversation_service = registry.get_service("conversation_service")
        memory_service = registry.get_service("memory_service")
        
        chat_service = ChatService(
            settings=settings,
            conversation_service=conversation_service,
            memory_service=memory_service
        )
        
        registry.register_service("chat_service", chat_service)
        registry.update_module_state("chat_service", ModuleState.READY)
        
        logger.info("chat_service_connector_initialized")
        return chat_service
    
    @staticmethod
    async def disconnect(instance: Any) -> None:
        """Shutdown chat service"""
        if hasattr(instance, "close"):
            import asyncio
            result = instance.close()
            if asyncio.iscoroutine(result):
                await result
        logger.info("chat_service_connector_shutdown")


# ============================================================================
# CORE CONNECTORS (Router & Bridges)
# ============================================================================

class ToolBridgeConnector:
    """Connector for tool bridge service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize tool bridge"""
        try:
            from astra.bridge.tool_bridge import ToolBridgeService, TaskAgentAdapter
            
            task_adapter = TaskAgentAdapter()
            tool_bridge = ToolBridgeService(task_adapter, safe_glob="tools/safe_*.py")
            
            registry.register_service("tool_bridge", tool_bridge)
            registry.update_module_state("tool_bridge", ModuleState.READY)
            
            logger.info("tool_bridge_connector_initialized")
            return tool_bridge
            
        except ImportError as e:
            logger.warning("tool_bridge_connector_unavailable", error=str(e))
            registry.update_module_state("tool_bridge", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown tool bridge"""
        if instance:
            logger.info("tool_bridge_connector_shutdown")


class ConsentServiceConnector:
    """Connector for consent service (UI dialogs)"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize consent UI - optional component"""
        try:
            from astra.ui.consent import ConsentDialog
            
            # Consent is UI-based, register the dialog class for optional use
            registry.register_service("consent_dialog", ConsentDialog)
            registry.update_module_state("consent_service", ModuleState.READY)
            
            logger.info("consent_ui_connector_initialized")
            return ConsentDialog
            
        except ImportError as e:
            logger.warning("consent_ui_connector_unavailable", error=str(e))
            registry.update_module_state("consent_service", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown consent service"""
        if instance:
            logger.info("consent_service_connector_shutdown")


class AstraRouterConnector:
    """Connector for ASTRA multimodal router"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize ASTRA router"""
        try:
            from astra.core.astra_router import AstraRouter
            
            # Get dependencies
            llm_provider = registry.get_service("llm_provider")
            memory_service = registry.get_service("memory_service")
            
            # Optional dependencies
            tool_bridge = registry.get_service("tool_bridge") if registry.has_service("tool_bridge") else None
            consent_service = registry.get_service("consent_service") if registry.has_service("consent_service") else None
            
            router = AstraRouter(
                llm=llm_provider,
                tool_bus=tool_bridge,
                memory=memory_service,
                consent=consent_service
            )
            
            registry.register_service("astra_router", router)
            registry.update_module_state("astra_router", ModuleState.READY)
            
            # Inject into chat service if available
            if registry.has_service("chat_service"):
                chat_service = registry.get_service("chat_service")
                chat_service.router = router
                logger.info("astra_router_injected_into_chat_service")
            
            logger.info("astra_router_connector_initialized")
            return router
            
        except Exception as e:
            logger.warning("astra_router_connector_failed", error=str(e))
            registry.update_module_state("astra_router", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown ASTRA router"""
        if instance:
            logger.info("astra_router_connector_shutdown")


class MemoryBridgeConnector:
    """Connector for memory bridge service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize memory bridge"""
        try:
            from astra.bridge.memory_bridge import MemoryBridgeService, MemoryLTMAdapter, MemoryEpisodicAdapter
            
            ltm_adapter = MemoryLTMAdapter()
            episodic_adapter = MemoryEpisodicAdapter()
            memory_bridge = MemoryBridgeService(ltm_adapter, episodic_adapter)
            
            registry.register_service("memory_bridge", memory_bridge)
            registry.update_module_state("memory_bridge", ModuleState.READY)
            
            logger.info("memory_bridge_connector_initialized")
            return memory_bridge
            
        except ImportError as e:
            logger.warning("memory_bridge_connector_unavailable", error=str(e))
            registry.update_module_state("memory_bridge", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown memory bridge"""
        if instance:
            logger.info("memory_bridge_connector_shutdown")


# ============================================================================
# VISUALIZATION CONNECTORS
# ============================================================================

class GraphServiceConnector:
    """Connector for memory graph visualization service"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize graph service"""
        try:
            from astra.visualization.memory_graph_service import MemoryGraphService
            
            graph_service = MemoryGraphService()
            
            # Connect to memory backends if available
            if registry.has_service("memory_engine") and registry.has_service("memory_service"):
                memory_engine = registry.get_service("memory_engine")
                memory_service = registry.get_service("memory_service")
                if memory_engine and memory_service:
                    graph_service.set_backends(
                        memory_engine=memory_engine,
                        memory_service=memory_service
                    )
            
            registry.register_service("graph_service", graph_service)
            registry.update_module_state("graph_service", ModuleState.READY)
            
            logger.info("graph_service_connector_initialized")
            return graph_service
            
        except ImportError as e:
            logger.warning("graph_service_connector_unavailable", error=str(e))
            registry.update_module_state("graph_service", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown graph service"""
        if instance:
            logger.info("graph_service_connector_shutdown")


class AutonomyEngineConnector:
    """Connector for autonomy engine"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize autonomy engine"""
        try:
            from astra.visualization.autonomy_engine import AutonomyEngine, create_default_triggers
            
            autonomy_engine = AutonomyEngine()
            
            # Register default triggers
            for trigger in create_default_triggers():
                autonomy_engine.add_trigger(trigger)
            
            registry.register_service("autonomy_engine", autonomy_engine)
            registry.update_module_state("autonomy_engine", ModuleState.READY)
            
            logger.info("autonomy_engine_connector_initialized")
            return autonomy_engine
            
        except ImportError as e:
            logger.warning("autonomy_engine_connector_unavailable", error=str(e))
            registry.update_module_state("autonomy_engine", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown autonomy engine"""
        if instance:
            logger.info("autonomy_engine_connector_shutdown")


class TaskAgentConnector:
    """Connector for task agent manager"""
    
    @staticmethod
    def connect(registry: ServiceRegistry, settings: Settings) -> Any:
        """Initialize task agent manager"""
        try:
            from astra.visualization.task_agent_manager import TaskAgentManager
            
            task_agent = TaskAgentManager()
            
            # Register plugins
            try:
                from astra.visualization.plugins import register_file_ops, register_system_info
                register_file_ops(task_agent)
                register_system_info(task_agent)
                logger.info("task_agent_plugins_registered")
            except ImportError as e:
                logger.debug("task_agent_plugins_unavailable", error=str(e))
            
            registry.register_service("task_agent", task_agent)
            registry.update_module_state("task_agent", ModuleState.READY)
            
            logger.info("task_agent_connector_initialized")
            return task_agent
            
        except ImportError as e:
            logger.warning("task_agent_connector_unavailable", error=str(e))
            registry.update_module_state("task_agent", ModuleState.ERROR, str(e))
            return None
    
    @staticmethod
    def disconnect(instance: Any) -> None:
        """Shutdown task agent"""
        if instance:
            logger.info("task_agent_connector_shutdown")


# ============================================================================
# CONNECTOR REGISTRY
# ============================================================================

CONNECTORS = {
    # Infrastructure
    "database": DatabaseConnector,
    "vector_store": VectorStoreConnector,
    
    # Services
    "conversation_service": ConversationServiceConnector,
    "memory_service": MemoryServiceConnector,
    "memory_engine": MemoryEngineConnector,
    "llm_provider": LLMProviderConnector,
    "chat_service": ChatServiceConnector,
    
    # Core & Bridges
    "tool_bridge": ToolBridgeConnector,
    "consent_service": ConsentServiceConnector,
    "astra_router": AstraRouterConnector,
    "memory_bridge": MemoryBridgeConnector,
    
    # Visualization
    "graph_service": GraphServiceConnector,
    "autonomy_engine": AutonomyEngineConnector,
    "task_agent": TaskAgentConnector,
}


def get_connector(module_name: str) -> Optional[type]:
    """Get connector class for module"""
    return CONNECTORS.get(module_name)


def auto_connect_module(module_name: str, registry: ServiceRegistry, settings: Settings) -> Any:
    """Auto-connect module using its registered connector"""
    connector = get_connector(module_name)
    if not connector:
        logger.warning("connector_not_found", module=module_name)
        return None
    
    try:
        registry.update_module_state(module_name, ModuleState.INITIALIZING)
        instance = connector.connect(registry, settings)
        return instance
    except Exception as e:
        logger.error("connector_failed", module=module_name, error=str(e), exc_info=True)
        registry.update_module_state(module_name, ModuleState.ERROR, str(e))
        return None


__all__ = [
    "ModuleConnector",
    "CONNECTORS",
    "get_connector",
    "auto_connect_module",
    # Individual connectors
    "DatabaseConnector",
    "VectorStoreConnector",
    "ConversationServiceConnector",
    "MemoryServiceConnector",
    "MemoryEngineConnector",
    "LLMProviderConnector",
    "ChatServiceConnector",
    "ToolBridgeConnector",
    "ConsentServiceConnector",
    "AstraRouterConnector",
    "MemoryBridgeConnector",
    "GraphServiceConnector",
    "AutonomyEngineConnector",
    "TaskAgentConnector",
]
