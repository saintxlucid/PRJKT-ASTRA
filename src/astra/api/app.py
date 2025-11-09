"""
Main FastAPI application.

This module creates and configures the FastAPI application with all routes,
middleware, and dependency injection.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from astra.api.middleware.request_id import RequestIdMiddleware
from astra.api.routes import chat, conversations, system, tools, consent, answer
from astra.infrastructure.storage.database import DatabaseManager
from astra.infrastructure.storage.vector_store import VectorStore

# Bridge Module
from astra.bridge.api_routes import router as bridge_router

# Tool Bus Components
from astra.core.tool_bus import initialize_registry
from astra.security.policy_engine import initialize_policy_engine

# Upgrade Pack v2.0 - Metrics and Security
from astra.metrics import (
    MetricsMiddleware, 
    metrics_endpoint,
    RequestMetrics
)
from astra.models.config import get_settings
from astra.queue_guard import ConcurrencyLimiterMiddleware
from astra.security import ApiKeyMiddleware, RateLimitMiddleware
from astra.services.chat_service import ChatService
from astra.services.conversation_service import ConversationService
from astra.services.memory_service import MemoryService
from astra.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


# Global service instances
chat_service: ChatService | None = None
conversation_service: ConversationService | None = None
memory_service: MemoryService | None = None
db_manager: DatabaseManager | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown logic.
    """
    global chat_service, conversation_service, memory_service, db_manager

    # Startup
    logger.info("application_starting")
    settings = get_settings()

    # Initialize database
    logger.info("initializing_database")
    db_manager = DatabaseManager(
        database_url=settings.database.url,
        echo=settings.database.echo,
    )
    db_manager.create_tables()

    # Initialize vector store
    logger.info("initializing_vector_store")
    vector_store = VectorStore(
        persist_directory=str(settings.get_chroma_path()),
        collection_name=settings.vector_store.collection_name,
        embedding_model=settings.memory.embedding_model,
        distance_metric=settings.vector_store.distance_metric,
    )

    # Initialize services
    logger.info("initializing_services")
    conversation_service = ConversationService(db_manager)
    memory_service = MemoryService(vector_store)
    chat_service = ChatService(settings, conversation_service, memory_service)

    # Inject dependencies into routes
    chat.set_chat_service(chat_service)
    conversations.set_conversation_service(conversation_service)
    system.set_system_dependencies(chat_service, memory_service)
    answer.set_answer_services(chat_service, memory_service)

    logger.info("application_started")

    yield

    # Shutdown
    logger.info("application_shutting_down")
    if chat_service:
        await chat_service.close()
    if db_manager:
        db_manager.close()
    logger.info("application_shutdown_complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    # Setup logging
    setup_logging(
        log_level=settings.server.log_level,
        json_logs=settings.environment == "production",
    )

    # Create FastAPI app
    app = FastAPI(
        title="ASTRA API",
        description="AI assistant with semantic memory and conversation management",
        version="2.0.0",
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

    # Initialize Tool Bus components
    initialize_registry()
    initialize_policy_engine()

    # Include routers
    app.include_router(chat.router)
    app.include_router(conversations.router)
    app.include_router(system.router)
    app.include_router(answer.router)  # New non-streaming answer endpoint
    app.include_router(bridge_router)  # Bridge module for LLM function calling
    app.include_router(tools.router)  # Tool Bus endpoints
    app.include_router(consent.router)  # Consent management
    
    # Add health check endpoints
    from astra.api.health import router as health_router
    app.include_router(health_router)

    # Upgrade Pack v2.0 - Expose Prometheus metrics endpoint
    app.add_route("/metrics", metrics_endpoint)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "name": "ASTRA API",
            "version": "2.0.0",
            "status": "running",
        }

    logger.info("fastapi_app_created")
    return app


# Create app instance
app = create_app()
