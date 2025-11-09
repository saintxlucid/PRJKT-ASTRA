"""
RAG planner for token budgeting and response structuring
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sklearn.cluster import AgglomerativeClustering
import logging
from datetime import datetime

from .rerank import RetrievedChunk, RerankResult

logger = logging.getLogger(__name__)

@dataclass
class ChunkCluster:
    """Group of related chunks with aggregate metrics"""
    chunks: List[RetrievedChunk]
    centroid: np.ndarray
    total_tokens: int
    avg_score: float
    theme_words: List[str]
    cluster_id: str

@dataclass 
class ResponsePlan:
    """Structured plan for response generation"""
    clusters: List[ChunkCluster]
    total_tokens: int
    token_budget: Dict[str, int]
    query_type: str
    suggested_format: str
    metadata: Dict[str, Any]

class RAGPlanner:
    """Plans response structure and budgets tokens"""
    
    def __init__(
        self,
        max_total_tokens: int = 4000,
        max_context_tokens: int = 2000,
        max_completion_tokens: int = 1000,
        min_cluster_size: int = 2,
        clustering_threshold: float = 0.7
    ):
        self.max_total_tokens = max_total_tokens
        self.max_context_tokens = max_context_tokens  
        self.max_completion_tokens = max_completion_tokens
        self.min_cluster_size = min_cluster_size
        self.clustering_threshold = clustering_threshold
        
    def _cluster_chunks(
        self,
        chunks: List[RetrievedChunk]
    ) -> List[ChunkCluster]:
        """Cluster chunks by semantic similarity"""
        if not chunks:
            return []
            
        # Extract embeddings
        embeddings = np.vstack([c.embedding for c in chunks])
        
        # Run hierarchical clustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.clustering_threshold,
            linkage='average',
            metric='cosine'
        )
        labels = clustering.fit_predict(embeddings)
        
        # Group chunks by cluster
        clusters: Dict[int, List[RetrievedChunk]] = {}
        for chunk, label in zip(chunks, labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(chunk)
            
        # Create ChunkCluster objects
        chunk_clusters = []
        for i, cluster_chunks in clusters.items():
            if len(cluster_chunks) < self.min_cluster_size:
                continue
                
            # Compute centroid
            centroid = np.mean([c.embedding for c in cluster_chunks], axis=0)
            
            # Aggregate metrics
            total_tokens = sum(c.token_count for c in cluster_chunks)
            avg_score = np.mean([c.score for c in cluster_chunks])
            
            # Extract theme words (placeholder)
            theme_words = []  # TODO: implement theme extraction
            
            cluster = ChunkCluster(
                chunks=cluster_chunks,
                centroid=centroid,
                total_tokens=total_tokens,
                avg_score=avg_score,
                theme_words=theme_words,
                cluster_id=f"cluster_{i}"
            )
            chunk_clusters.append(cluster)
            
        return chunk_clusters
        
    def _estimate_query_type(
        self,
        clusters: List[ChunkCluster],
        query_embedding: np.ndarray
    ) -> Tuple[str, str]:
        """Estimate query type and suggested response format"""
        # TODO: implement more sophisticated query type detection
        
        if not clusters:
            return "unknown", "direct_answer"
            
        total_chunks = sum(len(c.chunks) for c in clusters)
        
        if total_chunks >= 10:
            return "complex_analytical", "structured_analysis"
        elif len(clusters) >= 3:
            return "multi_faceted", "bullet_points"
        else:
            return "focused", "direct_answer"
            
    def _allocate_token_budget(
        self,
        clusters: List[ChunkCluster],
        query_type: str
    ) -> Dict[str, int]:
        """Allocate tokens across response components"""
        total_cluster_tokens = sum(c.total_tokens for c in clusters)
        
        # Base allocations
        budget = {
            "context": min(total_cluster_tokens, self.max_context_tokens),
            "completion": self.max_completion_tokens,
            "citations": 200,
            "metadata": 100
        }
        
        # Adjust based on query type
        if query_type == "complex_analytical":
            budget["completion"] = int(budget["completion"] * 1.2)
            budget["citations"] = 300
        elif query_type == "multi_faceted":
            budget["citations"] = 250
            
        # Ensure total budget compliance
        total = sum(budget.values())
        if total > self.max_total_tokens:
            # Scale down proportionally
            scale = self.max_total_tokens / total
            budget = {k: int(v * scale) for k, v in budget.items()}
            
        return budget
        
    def plan_response(
        self,
        rerank_result: RerankResult,
        query_embedding: np.ndarray,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ResponsePlan:
        """
        Generate response plan from reranked chunks
        
        Args:
            rerank_result: Output from reranking
            query_embedding: Original query embedding
            metadata: Optional additional planning context
            
        Returns:
            ResponsePlan with structure and budgets
        """
        metadata = metadata or {}
        
        # Cluster chunks
        clusters = self._cluster_chunks(rerank_result.chunks)
        
        # Determine query type
        query_type, suggested_format = self._estimate_query_type(
            clusters,
            query_embedding
        )
        
        # Allocate token budget
        token_budget = self._allocate_token_budget(clusters, query_type)
        
        # Construct plan
        plan = ResponsePlan(
            clusters=clusters,
            total_tokens=sum(c.total_tokens for c in clusters),
            token_budget=token_budget,
            query_type=query_type,
            suggested_format=suggested_format,
            metadata={
                "mmr_diversity": rerank_result.mmr_diversity,
                "recency_boost": rerank_result.recency_boost,
                "truncation_reason": rerank_result.truncation_reason,
                **metadata
            }
        )
        
        return plan