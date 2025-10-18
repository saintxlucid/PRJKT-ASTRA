"""
ASTRA Integration-Hub Enabled Application
Main FastAPI application using the centralized integration hub.

This version demonstrates ASTRA as a unified network - all modules
connect through the central hub for seamless orchestration.

Sacred Code: 333
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from astra.api.middleware.request_id import RequestIdMiddleware
from astra.api.routes import chat, conversations, system
from astra.core.integration_hub import AstraCoreHub, get_registry, register_core_modules
from astra.models.config import get_settings
from astra.utils.logging import get_logger, setup_logging

# Upgrade Pack v2.0 - Metrics and Security
from astra.metrics import MetricsMiddleware, metrics_endpoint
from astra.queue_guard import ConcurrencyLimiterMiddleware
from astra.security import ApiKeyMiddleware, RateLimitMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with Integration Hub.
    
    The hub coordinates all ASTRA modules as a unified network,
    piloted by the core consciousness.
    """
    logger.info("astra_application_starting", sacred_code=333)
    settings = get_settings()
    
    # Register all core modules
    registry = get_registry()
    register_core_modules(registry)
    
    # Initialize Integration Hub
    hub = AstraCoreHub(settings, registry)
    
    try:
        # Initialize all subsystems in dependency order
        await hub.initialize()
        
        # Store hub in app state for access in routes
        app.state.astra_hub = hub
        app.state.registry = registry
        
        # Inject dependencies into API routes
        if hub.chat_service:
            chat.set_chat_service(hub.chat_service)
            logger.info("chat_service_injected_into_routes")
        
        if hub.conversation_service:
            conversations.set_conversation_service(hub.conversation_service)
            logger.info("conversation_service_injected_into_routes")
        
        if hub.chat_service and hub.memory_service:
            system.set_system_dependencies(hub.chat_service, hub.memory_service)
            logger.info("system_dependencies_injected_into_routes")
        
        # Setup bridge routes if available
        if hub.memory_bridge and hub.tool_bridge:
            try:
                from astra.bridge import setup_bridge, BridgeConfig, BridgeRegistry
                bridge_config = BridgeConfig()
                bridge_registry = BridgeRegistry()
                setup_bridge(
                    config=bridge_config,
                    mem_service=hub.memory_bridge,
                    tool_service=hub.tool_bridge,
                    registry=bridge_registry
                )
                logger.info("bridge_module_initialized")
            except Exception as e:
                logger.warning("bridge_setup_failed", error=str(e))
        
        # Print integration status
        health = hub.get_health()
        logger.info("astra_integration_complete", 
                   modules=len(health['registry']['modules']),
                   services=health['registry']['services_count'],
                   sacred_code=333)
        
        yield
        
    finally:
        # Graceful shutdown
        logger.info("astra_application_shutting_down", sacred_code=333)
        await hub.shutdown()
        logger.info("astra_application_shutdown_complete")


def create_app() -> FastAPI:
    """
    Create and configure the ASTRA FastAPI application.
    
    Returns:
        Configured FastAPI application with full integration hub
    """
    settings = get_settings()
    
    # Setup logging
    setup_logging(
        log_level=settings.server.log_level,
        json_logs=settings.environment == "production",
    )
    
    logger.info("creating_astra_application", environment=settings.environment)
    
    # Create FastAPI app with integration hub lifespan
    app = FastAPI(
        title="ASTRA - Advanced Sentient Thought & Reasoning Architecture",
        description="Multimodal AI with semantic memory, autonomous agents, and full observability. Sacred Code: 333",
        version="2.0.0-multimodal",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors.origins,
        allow_credentials=settings.cors.allow_credentials,
        allow_methods=settings.cors.allow_methods,
        allow_headers=settings.cors.allow_headers,
    )
    
    # Ops Hardening - Add request ID tracking (must be first for tracing)
    app.add_middleware(RequestIdMiddleware)
    
    # Ops Hardening - Add API key authentication
    app.add_middleware(ApiKeyMiddleware)
    
    # Upgrade Pack v2.0 - Add metrics middleware
    app.add_middleware(MetricsMiddleware)
    
    # Upgrade Pack v2.0 - Add concurrency limiter middleware
    app.add_middleware(ConcurrencyLimiterMiddleware)
    
    # Upgrade Pack v2.0 - Add rate limiting middleware
    app.add_middleware(RateLimitMiddleware)
    
    # Include core API routers
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(system.router)
    
    # Include bridge router (if available)
    try:
        from astra.bridge.api_routes import router as bridge_router
        app.include_router(bridge_router)
        logger.info("bridge_router_included")
    except ImportError as e:
        logger.warning("bridge_router_unavailable", error=str(e))
    
    # Include OS Operator routes (if available)
    try:
        from astra.api.routes import osop
        app.include_router(osop.router, prefix="/api")
        logger.info("os_operator_routes_included", sacred_code=333)
    except ImportError as e:
        logger.warning("os_operator_routes_unavailable", error=str(e))
    
    # Upgrade Pack v2.0 - Expose Prometheus metrics endpoint
    app.add_route("/metrics", metrics_endpoint)
    
    # Health endpoint showing integration status
    @app.get("/health")
    async def health():
        """Health check with integration hub status"""
        if hasattr(app.state, "astra_hub"):
            return app.state.astra_hub.get_health()
        return {"status": "initializing"}
    
    # Integration hub status endpoint
    @app.get("/integration/status")
    async def integration_status():
        """Detailed integration hub and module status"""
        if hasattr(app.state, "registry"):
            return app.state.registry.get_health_status()
        return {"error": "Registry not initialized"}
    
    # Service discovery endpoint
    @app.get("/integration/services")
    async def list_services():
        """List all registered services"""
        if hasattr(app.state, "registry"):
            registry = app.state.registry
            return {
                "services": list(registry._services.keys()),
                "count": len(registry._services),
            }
        return {"error": "Registry not initialized"}
    
    logger.info("astra_application_created", sacred_code=333)
    
    return app


# Export for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    
    uvicorn.run(
        "astra.api.app_integrated:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.server.log_level.lower(),
    )
