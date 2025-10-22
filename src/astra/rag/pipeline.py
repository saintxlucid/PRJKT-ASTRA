"""
Core Multi-RAG pipeline implementation.

The pipeline coordinates retrieval, fusion, and callbacks for the Multi-RAG system.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import asyncio
import structlog

from astra.core.actions import ActionRegistry, action
from astra.core.memory import MemoryBridgeConnector
from astra.rag.document import Document, SearchResults
from astra.rag.fusion import rrf_fusion, interpolation_fusion
from astra.rag.retrievers import BaseRetriever
from astra.rag.callbacks import CallbackManager, RetrievalEvent

logger = structlog.get_logger(__name__)

@dataclass
class MultiRAGConfig:
    """Configuration for Multi-RAG pipeline."""
    
    fusion_method: str = "rrf"  # "rrf" or "interpolation"
    top_k: int = 10
    rrf_k: float = 60.0
    score_threshold: float = 0.0
    retriever_weights: Optional[Dict[str, float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultiRAGPipeline:
    """Core Multi-RAG pipeline implementation."""
    
    def __init__(
        self,
        config: MultiRAGConfig,
        callback_manager: Optional[CallbackManager] = None,
        memory_bridge_connector: Optional[MemoryBridgeConnector] = None
    ):
        """
        Initialize Multi-RAG pipeline.
        
        Args:
            config: Pipeline configuration
            callback_manager: Optional callback manager for events
            memory_bridge_connector: Optional memory bridge connector for callbacks
        """
        self.config = config
        self.callback_manager = callback_manager or CallbackManager()
        self.retrievers: Dict[str, BaseRetriever] = {}
        self.registry = ActionRegistry()
        self.memory_bridge = memory_bridge_connector
        
        # Register actions and callbacks
        self._register_actions()
        self._register_memory_callbacks()
        
        logger.info("multi_rag_pipeline_initialized",
                   fusion_method=config.fusion_method,
                   top_k=config.top_k,
                   has_memory_bridge=bool(memory_bridge_connector))
    
    def add_retriever(self, retriever: BaseRetriever) -> None:
        """
        Add a retriever to the pipeline.
        
        Args:
            retriever: Retriever instance to add
        """
        self.retrievers[retriever.retriever_id] = retriever
        logger.info("retriever_added", retriever_id=retriever.retriever_id)
    
    def _register_actions(self) -> None:
        """Register pipeline actions."""
        
        @self.registry.register(
            "multi_rag.retrieve",
            description="Execute multi-source retrieval",
            supports_dry_run=True
        )
        async def retrieve(
            query: str,
            top_k: Optional[int] = None,
            retrievers: Optional[List[str]] = None
        ) -> List[Document]:
            """
            Execute retrieval across multiple sources.
            
            Args:
                query: Search query
                top_k: Optional override for number of results
                retrievers: Optional list of specific retrievers to use
                
            Returns:
                List of fused documents
            """
            k = top_k or self.config.top_k
            
            # Select retrievers to use
            active_retrievers = []
            if retrievers:
                for r_id in retrievers:
                    if r_id in self.retrievers:
                        active_retrievers.append(self.retrievers[r_id])
                    else:
                        logger.warning("unknown_retriever", retriever_id=r_id)
            else:
                active_retrievers = list(self.retrievers.values())
            
            if not active_retrievers:
                logger.error("no_active_retrievers")
                return []
                
            # Execute retrievals in parallel
            tasks = []
            for retriever in active_retrievers:
                task = asyncio.create_task(
                    retriever.retrieve(query, k=k)
                )
                tasks.append(task)
                
            # Gather results
            results_list = []
            for task in asyncio.as_completed(tasks):
                try:
                    results = await task
                    results_list.append(results)
                except Exception as e:
                    logger.error("retrieval_failed", error=str(e))
                    
            if not results_list:
                logger.error("no_results_returned")
                return []
                
            # Fuse results
            if self.config.fusion_method == "rrf":
                fused_docs = rrf_fusion(
                    results_list,
                    k=k,
                    rrf_k=self.config.rrf_k
                )
            else:  # interpolation
                weights = None
                if self.config.retriever_weights:
                    weights = [
                        self.config.retriever_weights.get(r.retriever_id, 1.0)
                        for r in active_retrievers
                    ]
                fused_docs = interpolation_fusion(
                    results_list,
                    weights=weights,
                    k=k,
                    score_threshold=self.config.score_threshold
                )
                
            # Emit fusion completion event
            self.callback_manager.emit_event(
                RetrievalEvent(
                    event_type="fusion_complete",
                    metadata={
                        "query": query,
                        "n_results": len(fused_docs),
                        "fusion_method": self.config.fusion_method
                    }
                )
            )
            
            return fused_docs
            
        @self.registry.register(
            "multi_rag.add_documents",
            description="Add documents to retrievers",
            supports_dry_run=True
        )
        async def add_documents(
            documents: List[Document],
            retriever_ids: Optional[List[str]] = None
        ) -> Dict[str, bool]:
            """
            Add documents to specified retrievers.
            
            Args:
                documents: Documents to add
                retriever_ids: Optional list of specific retrievers
                
            Returns:
                Dictionary of retriever_id -> success status
            """
            results = {}
            
            # Select retrievers
            active_retrievers = []
            if retriever_ids:
                for r_id in retriever_ids:
                    if r_id in self.retrievers:
                        active_retrievers.append(self.retrievers[r_id])
                    else:
                        logger.warning("unknown_retriever", retriever_id=r_id)
            else:
                active_retrievers = list(self.retrievers.values())
                
            # Add to each retriever
            for retriever in active_retrievers:
                try:
                    success = await retriever.add_documents(documents)
                    results[retriever.retriever_id] = success
                except Exception as e:
                    logger.error(
                        "add_documents_failed",
                        retriever_id=retriever.retriever_id,
                        error=str(e)
                    )
                    results[retriever.retriever_id] = False
                    
            return results
            
    async def retrieve(self,
                     query: str,
                     top_k: Optional[int] = None,
                     retrievers: Optional[List[str]] = None) -> List[Document]:
        """
        Execute retrieval via action registry.
        
        Args:
            query: Search query
            top_k: Optional override for number of results
            retrievers: Optional list of specific retrievers to use
            
        Returns:
            List of fused documents
        """
        return await self.registry.execute(
            "multi_rag.retrieve",
            query,
            top_k=top_k,
            retrievers=retrievers
        )
    
    async def add_documents(self,
                          documents: List[Document],
                          retriever_ids: Optional[List[str]] = None
                         ) -> Dict[str, bool]:
        """
        Add documents via action registry.
        
        Args:
            documents: Documents to add
            retriever_ids: Optional list of specific retrievers
            
        Returns:
            Dictionary of retriever_id -> success status
        """
        return await self.registry.execute(
            "multi_rag.add_documents",
            documents,
            retriever_ids=retriever_ids
        )
    
    def _register_memory_callbacks(self) -> None:
        """Register memory bridge callbacks."""
        if not self.memory_bridge:
            return
            
        # Register retrieval callback
        async def on_retrieval_complete(event: RetrievalEvent):
            if event.event_type != "fusion_complete":
                return
                
            # Get episodic context
            query = event.metadata["query"]
            context = await self.memory_bridge.get_episodic_context(query)
            
            if context:
                logger.info("memory_context_retrieved",
                           query=query,
                           n_contexts=len(context))
                           
        self.callback_manager.on_event(
            "fusion_complete",
            on_retrieval_complete
        )