"""
ASTRA Multi-RAG Action Registry
Connects Multi-RAG capabilities to service registry.
"""
from typing import Dict, Any, List, Optional
import structlog
from dataclasses import dataclass

from astra.core.integration_hub import get_registry, ServiceRegistry
from astra.rag.multi_rag_core import (
    MultiRAGRetriever,
    RAGAnswer,
    FusionLayer,
    ContextComposer
)

logger = structlog.get_logger()


@dataclass
class RetrievalAction:
    """Retrieval action registration."""
    name: str
    description: str
    categories: List[str]
    k: int = 12
    policy: str = "default"


class MultiRAGActions:
    """Multi-RAG action registration and handlers."""
    
    def __init__(
        self,
        retriever: MultiRAGRetriever,
        fusion: FusionLayer,
        composer: ContextComposer
    ):
        self.retriever = retriever
        self.fusion = fusion
        self.composer = composer
        self.registry = get_registry()
        
        # Register standard actions
        self._register_standard_actions()
        logger.info("multi_rag_actions_initialized")
    
    def _register_standard_actions(self) -> None:
        """Register standard Multi-RAG retrieval actions."""
        # Default search across all categories
        self.register_retrieval_action(
            RetrievalAction(
                name="semantic_search",
                description="Search across all knowledge categories",
                categories=[],  # All categories
                k=12
            )
        )
        
        # AI/Engineering focused search
        self.register_retrieval_action(
            RetrievalAction(
                name="code_search",
                description="Search code, algorithms, and technical docs",
                categories=["ai_engineering"],
                k=8,
                policy="precise"
            )
        )
        
        # Media/Arts focused search
        self.register_retrieval_action(
            RetrievalAction(
                name="media_search", 
                description="Search music and film content",
                categories=["music_film"],
                k=8
            )
        )
        
        # Cognitive/Spiritual focused
        self.register_retrieval_action(
            RetrievalAction(
                name="cognitive_search",
                description="Search consciousness and philosophy",
                categories=["cognition_spirit"],
                k=8
            )
        )
        
        # Ops/Systems focused
        self.register_retrieval_action(
            RetrievalAction(
                name="ops_search",
                description="Search logs and system docs",
                categories=["operations_systems"],
                k=10,
                policy="fast"
            )
        )
        
        logger.info("standard_actions_registered")
    
    def register_retrieval_action(self, action: RetrievalAction) -> None:
        """Register a retrieval action with the service registry."""
        self.registry.register_service(
            f"rag_action_{action.name}",
            {
                "type": "retrieval",
                "handler": self._create_handler(action),
                "metadata": {
                    "name": action.name,
                    "description": action.description,
                    "categories": action.categories,
                    "k": action.k,
                    "policy": action.policy
                }
            },
            overwrite=True
        )
        logger.info("retrieval_action_registered", name=action.name)
    
    def _create_handler(self, action: RetrievalAction):
        """Create handler function for retrieval action."""
        
        async def handle_retrieval(query: str) -> RAGAnswer:
            # Stage 1: Multi-RAG retrieval
            candidates = await self.retriever.retrieve(
                query=query,
                categories=action.categories or None,
                k=action.k,
                policy=action.policy
            )
            
            # Stage 2: Cross-category fusion
            fused_results = self.fusion.fuse(query, candidates)
            
            # Stage 3: Context composition
            context, citations = self.composer.compose(query, fused_results)
            
            # Calculate metrics
            diversity = len({c.doc_id for c in citations}) / max(1, len(citations))
            margin = fused_results[0].score - fused_results[min(1, len(fused_results)-1)].score if fused_results else 0.0
            
            # Create answer
            answer = RAGAnswer(
                answer=context,
                citations=citations,
                confidence=(diversity * 0.5 + (margin / 0.15) * 0.5),
                metadata={
                    "diversity": diversity,
                    "margin": margin,
                    "categories": list(candidates.keys()),
                    "action": action.name,
                    "policy": action.policy
                }
            )
            
            return answer
        
        return handle_retrieval
    
    def get_action_handler(self, name: str):
        """Get handler for registered action."""
        service = self.registry.get_service(f"rag_action_{name}")
        return service["handler"]
    
    def list_actions(self) -> List[Dict[str, Any]]:
        """List all registered retrieval actions."""
        actions = []
        for name, service in self.registry._services.items():
            if name.startswith("rag_action_"):
                actions.append(service["metadata"])
        return actions
    
    def list_policies(self) -> Dict[str, Dict[str, Any]]:
        """Get available retrieval policies."""
        return {
            "default": {
                "description": "Balanced retrieval",
                "k": 12,
                "rerank_threshold": 0.5
            },
            "precise": {
                "description": "High-precision mode",
                "k": 8,
                "rerank_threshold": 0.6
            },
            "fast": {
                "description": "Low-latency mode",
                "k": 6,
                "rerank_threshold": 0.4
            }
        }