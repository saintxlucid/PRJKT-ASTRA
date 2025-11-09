"""
RAG Fusion v2 main implementation
"""
from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime
import logging
import json
from pathlib import Path

from .rerank import MMRReranker, RetrievedChunk, RerankResult
from .planner import RAGPlanner, ResponsePlan
from .telemetry import token_monitor
from .citations import CitationManager

logger = logging.getLogger(__name__)

class RAGFusion:
    """Main RAG implementation with MMR and recency-based reranking"""
    
    def __init__(
        self,
        rerank_config: Optional[Dict[str, Any]] = None,
        planner_config: Optional[Dict[str, Any]] = None,
        export_path: Optional[str] = None
    ):
        # Initialize components
        self.reranker = MMRReranker(**(rerank_config or {}))
        self.planner = RAGPlanner(**(planner_config or {}))
        self.citations = CitationManager()
        self.export_path = export_path
        
    def process_query(
        self,
        query_embedding: np.ndarray,
        chunks: List[RetrievedChunk],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ResponsePlan:
        """
        Process query and retrieved chunks
        
        Args:
            query_embedding: Query vector
            chunks: Retrieved context chunks
            metadata: Additional processing context
            
        Returns:
            Structured response plan
        """
        token_monitor.start_request()
        
        try:
            # Track initial chunks
            token_monitor.record_usage(
                "initial_chunks",
                sum(c.token_count for c in chunks),
                sum(c.token_count for c in chunks),
                {"num_chunks": len(chunks)}
            )
            
            # Rerank chunks
            rerank_result = self.reranker.rerank(
                query_embedding,
                chunks
            )
            
            token_monitor.record_usage(
                "reranked_chunks",
                self.reranker.max_tokens,
                rerank_result.budget_tokens,
                {
                    "num_chunks": len(rerank_result.chunks),
                    "mmr_diversity": rerank_result.mmr_diversity
                }
            )
            
            # Add citations
            for chunk in rerank_result.chunks:
                citation = self.citations.add_citation(
                    text=chunk.text,
                    source=chunk.source,
                    chunk_id=chunk.chunk_id,
                    relevance_score=chunk.score,
                    timestamp=chunk.timestamp,
                    metadata={"tags": chunk.tags}
                )
                self.citations.mark_used(citation.citation_id)
                
            # Generate response plan
            plan = self.planner.plan_response(
                rerank_result,
                query_embedding,
                metadata
            )
            
            token_monitor.record_usage(
                "response_plan",
                self.planner.max_total_tokens,
                plan.total_tokens,
                {
                    "query_type": plan.query_type,
                    "num_clusters": len(plan.clusters)
                }
            )
            
            # Export artifacts if path provided
            if self.export_path:
                self._export_artifacts()
                
            return plan
            
        except Exception as e:
            logger.error(
                "Error processing query",
                error=str(e),
                exc_info=True
            )
            raise
            
    def _export_artifacts(self):
        """Export processing artifacts"""
        if not self.export_path:
            return
            
        # Create export directory
        export_dir = Path(self.export_path)
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export telemetry
        token_monitor.export_metrics(
            export_dir / "token_metrics.json"
        )
        
        # Export citations
        self.citations.export_citations(
            export_dir / "citations.json"
        )
        
    def get_citations(self) -> str:
        """Get formatted citation block"""
        return self.citations.format_citations()