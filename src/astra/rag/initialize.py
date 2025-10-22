"""
ASTRA Multi-RAG Initialization
Central initialization and wiring of Multi-RAG components.
"""
from typing import Optional, Dict, Any
import structlog
import yaml
from pathlib import Path

from astra.core.memory import MemoryBridgeConnector
from astra.rag.multi_rag_core import (
    MultiRAGRetriever,
    FusionLayer,
    ContextComposer
)
from astra.rag.modules.actions import MultiRAGActions
from astra.rag.modules.bridges import MemoryBridge
from astra.rag.modules.events import EventBus
from astra.rag.pipeline import MultiRAGPipeline, MultiRAGConfig
from astra.rag.integration import register_multi_rag_actions 
from astra.rag.tools import MultiRAGToolConfig

logger = structlog.get_logger()


def init_multi_rag(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Initialize Multi-RAG system with all components."""
    # Load config
    if config_path:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    else:
        config = {} # Use defaults
        
    # Initialize event bus
    event_bus = EventBus()
    logger.info("event_bus_initialized")
    
    # Initialize core components
    retriever = MultiRAGRetriever(
        event_bus=event_bus,
        **config.get("retriever", {})
    )
    fusion = FusionLayer(
        event_bus=event_bus,
        **config.get("fusion", {})
    )
    composer = ContextComposer(
        event_bus=event_bus,
        **config.get("composer", {})
    )
    logger.info("core_components_initialized")
    
    # Initialize memory bridge and connector
    memory = MemoryBridge(
        event_bus=event_bus,
        retriever=retriever,
        **config.get("memory", {})
    )
    memory_connector = MemoryBridgeConnector()
    logger.info("memory_bridge_initialized")
    
    # Initialize pipeline
    pipeline = MultiRAGPipeline(
        config=MultiRAGConfig(**config.get("pipeline", {})),
        memory_bridge_connector=memory_connector
    )
    pipeline.add_retriever(retriever)
    logger.info("pipeline_initialized")
    
    # Initialize actions
    actions = MultiRAGActions(
        retriever=retriever,
        fusion=fusion,
        composer=composer
    )
    logger.info("actions_initialized")
    
    # Register with orchestrator
    register_multi_rag_actions(
        actions=actions,
        memory_bridge=memory_connector,
        config=MultiRAGToolConfig(**config.get("tool", {}))
    )
    logger.info("actions_registered_with_orchestrator")
    
    # Return initialized components
    return {
        "event_bus": event_bus,
        "retriever": retriever,
        "fusion": fusion,
        "composer": composer,
        "memory": memory,
        "actions": actions,
        "pipeline": pipeline,
        "config": config
    }