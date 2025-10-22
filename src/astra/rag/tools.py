"""
ASTRA Multi-RAG Tool
Provides tool interface for Multi-RAG system.
"""
from typing import Dict, Any, List, Optional
import structlog
from dataclasses import dataclass

from astra.core.tools import BaseTool, ToolResult
from astra.core.memory import MemoryBridgeConnector
from astra.rag.multi_rag_core import MultiRAGRetriever
from astra.rag.modules.actions import MultiRAGActions

logger = structlog.get_logger()


@dataclass
class MultiRAGToolConfig:
    """Configuration for Multi-RAG tool."""
    default_k: int = 12
    default_policy: str = "default"


class MultiRAGTool(BaseTool):
    """Tool interface for Multi-RAG retrieval system."""
    
    tool_name = "multi_rag"
    description = "Multi-source retrieval augmented generation"
    
    def __init__(
        self,
        actions: MultiRAGActions,
        memory_bridge: Optional[MemoryBridgeConnector] = None,
        config: Optional[MultiRAGToolConfig] = None
    ):
        """
        Initialize Multi-RAG tool.
        
        Args:
            actions: Multi-RAG action registry
            memory_bridge: Optional memory bridge connector
            config: Tool configuration
        """
        self.actions = actions
        self.memory_bridge = memory_bridge
        self.config = config or MultiRAGToolConfig()
        
        logger.info("multi_rag_tool_initialized",
                   default_k=self.config.default_k,
                   default_policy=self.config.default_policy)
    
    async def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        policy: Optional[str] = None,
        categories: Optional[List[str]] = None
    ) -> ToolResult:
        """
        Execute retrieval action.
        
        Args:
            query: Query text
            k: Number of results to return
            policy: Retrieval policy to use
            categories: Categories to search in
            
        Returns:
            Tool result with retrieved documents
        """
        try:
            # Get handler for policy
            handler = self.actions.get_action_handler(policy or self.config.default_policy)
            if not handler:
                return ToolResult(
                    ok=False,
                    error=f"Unknown policy: {policy}"
                )
            
            # Execute retrieval
            results = await handler(
                query=query,
                k=k or self.config.default_k,
                categories=categories
            )
            
            return ToolResult(
                ok=True,
                data={
                    "documents": results.documents,
                    "metadata": {
                        "confidence": results.confidence,
                        "diversity": results.diversity,
                        "categories": results.categories_used
                    }
                }
            )
            
        except Exception as e:
            logger.exception("retrieval_failed",
                           query=query,
                           error=str(e))
            return ToolResult(
                ok=False,
                error=f"Retrieval failed: {str(e)}"
            )
    
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get list of available retrieval actions."""
        return self.actions.list_actions()
    
    def get_available_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get available retrieval policies."""
        return self.actions.list_policies()