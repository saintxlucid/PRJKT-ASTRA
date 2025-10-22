"""
ASTRA Multi-RAG Orchestrator Integration
Registers Multi-RAG actions with the Runtime Orchestrator.
"""
from typing import Optional, Dict, Any
import structlog

from astra.core.actions import action, ActionRegistry, get_action_registry
from astra.core.memory import MemoryBridgeConnector
from astra.rag.modules.actions import MultiRAGActions
from astra.rag.tools import MultiRAGTool, MultiRAGToolConfig

logger = structlog.get_logger()


def register_multi_rag_actions(
    actions: MultiRAGActions,
    memory_bridge: Optional[MemoryBridgeConnector] = None,
    config: Optional[MultiRAGToolConfig] = None,
    registry: Optional[ActionRegistry] = None
) -> None:
    """
    Register Multi-RAG actions with the orchestrator.
    
    Args:
        actions: Multi-RAG action registry
        memory_bridge: Optional memory bridge connector
        config: Optional tool configuration
        registry: Optional action registry (uses default if None)
    """
    # Initialize tool
    tool = MultiRAGTool(
        actions=actions,
        memory_bridge=memory_bridge,
        config=config
    )
    
    # Get registry
    registry = registry or get_action_registry()
    
    @action("multi_rag.retrieve", registry=registry)
    async def act_retrieve(
        query: str,
        k: Optional[int] = None,
        policy: Optional[str] = None,
        categories: Optional[list[str]] = None,
        ctx: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute Multi-RAG retrieval."""
        result = await tool.retrieve(
            query=query,
            k=k,
            policy=policy,
            categories=categories
        )
        if not result.ok:
            raise ValueError(result.error)
        return result.data
    
    @action("multi_rag.list_actions", registry=registry)
    def act_list_actions() -> List[Dict[str, Any]]:
        """List available Multi-RAG actions."""
        return tool.get_available_actions()
    
    @action("multi_rag.list_policies", registry=registry)
    def act_list_policies() -> Dict[str, Dict[str, Any]]:
        """List available retrieval policies."""
        return tool.get_available_policies()
    
    logger.info("multi_rag_actions_registered")