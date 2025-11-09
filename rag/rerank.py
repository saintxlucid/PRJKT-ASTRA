"""
RAG Fusion reranking module with MMR and recency-weighted scoring
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging
from dataclasses import dataclass
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)

@dataclass
class RetrievedChunk:
    """Retrieved context chunk with metadata"""
    text: str
    source: str
    embedding: np.ndarray
    score: float
    timestamp: datetime
    energy: float
    tags: List[str]
    chunk_id: str
    token_count: int

@dataclass
class RerankResult:
    """Result of reranking with diagnostics"""
    chunks: List[RetrievedChunk]
    scores: List[float]
    mmr_diversity: float
    recency_boost: float
    budget_tokens: int
    truncation_reason: Optional[str] = None

class MMRReranker:
    """Maximum Marginal Relevance reranker with recency weighting"""
    
    def __init__(
        self,
        lambda_param: float = 0.5,  # MMR diversity weight
        recency_weight: float = 0.3,  # Timestamp recency weight
        max_tokens: int = 2000,  # Token budget
        min_chunks: int = 3,  # Minimum chunks to return
        energy_threshold: float = 0.5  # Minimum energy score
    ):
        self.lambda_param = lambda_param
        self.recency_weight = recency_weight
        self.max_tokens = max_tokens
        self.min_chunks = min_chunks
        self.energy_threshold = energy_threshold
        
    def _compute_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between vectors"""
        return float(F.cosine_similarity(
            torch.tensor(a).unsqueeze(0),
            torch.tensor(b).unsqueeze(0)
        ))
        
    def _compute_recency_score(self, timestamp: datetime, reference: datetime) -> float:
        """Compute recency score based on time difference"""
        age = (reference - timestamp).total_seconds()
        # Decay over 30 days
        decay_factor = np.exp(-age / (30 * 24 * 3600))
        return float(decay_factor)
        
    def _filter_low_energy(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """Filter out chunks below energy threshold"""
        return [
            chunk for chunk in chunks
            if chunk.energy >= self.energy_threshold
        ]
        
    def rerank(
        self,
        query_embedding: np.ndarray,
        chunks: List[RetrievedChunk],
        reference_time: Optional[datetime] = None
    ) -> RerankResult:
        """
        Rerank chunks using MMR with recency weighting
        
        Args:
            query_embedding: Query vector
            chunks: List of retrieved chunks with metadata
            reference_time: Time to use for recency calculation
            
        Returns:
            RerankResult with reranked chunks and diagnostics
        """
        if not chunks:
            return RerankResult(
                chunks=[],
                scores=[],
                mmr_diversity=0.0,
                recency_boost=0.0,
                budget_tokens=0,
                truncation_reason="No chunks provided"
            )
            
        # Filter low energy chunks
        chunks = self._filter_low_energy(chunks)
        if not chunks:
            return RerankResult(
                chunks=[],
                scores=[],
                mmr_diversity=0.0,
                recency_boost=0.0,
                budget_tokens=0,
                truncation_reason="All chunks below energy threshold"
            )
            
        reference_time = reference_time or datetime.utcnow()
        
        # Track selected chunks and scores
        selected: List[RetrievedChunk] = []
        scores: List[float] = []
        remaining = chunks.copy()
        total_tokens = 0
        mmr_diversity = 0.0
        recency_boost = 0.0
        
        while remaining and (
            len(selected) < self.min_chunks or
            (total_tokens < self.max_tokens and remaining)
        ):
            # Compute scores for remaining chunks
            chunk_scores = []
            for chunk in remaining:
                # Relevance score (cosine similarity)
                rel_score = self._compute_similarity(
                    query_embedding,
                    chunk.embedding
                )
                
                # Diversity penalty
                if selected:
                    diversity_penalty = max(
                        self._compute_similarity(
                            chunk.embedding,
                            selected_chunk.embedding
                        )
                        for selected_chunk in selected
                    )
                else:
                    diversity_penalty = 0.0
                    
                # Recency score
                recency = self._compute_recency_score(
                    chunk.timestamp,
                    reference_time
                )
                
                # Combined MMR score with recency
                mmr_score = (
                    self.lambda_param * rel_score -
                    (1 - self.lambda_param) * diversity_penalty +
                    self.recency_weight * recency
                )
                
                chunk_scores.append((chunk, mmr_score))
                
            # Select chunk with highest score
            selected_chunk, score = max(chunk_scores, key=lambda x: x[1])
            
            # Check token budget
            new_total = total_tokens + selected_chunk.token_count
            if new_total > self.max_tokens and len(selected) >= self.min_chunks:
                truncation_reason = (
                    f"Token budget exceeded: {new_total} > {self.max_tokens}"
                )
                break
                
            # Add selected chunk
            selected.append(selected_chunk)
            scores.append(score)
            remaining.remove(selected_chunk)
            total_tokens += selected_chunk.token_count
            
            # Update diversity metric
            if len(selected) > 1:
                mmr_diversity = np.mean([
                    1 - self._compute_similarity(
                        a.embedding,
                        b.embedding
                    )
                    for i, a in enumerate(selected)
                    for b in selected[i+1:]
                ])
                
            # Update recency metric
            recency_boost = np.mean([
                self._compute_recency_score(chunk.timestamp, reference_time)
                for chunk in selected
            ])
            
        return RerankResult(
            chunks=selected,
            scores=scores,
            mmr_diversity=mmr_diversity,
            recency_boost=recency_boost,
            budget_tokens=total_tokens,
            truncation_reason=(
                f"Token budget exceeded: {total_tokens} > {self.max_tokens}"
                if remaining and total_tokens >= self.max_tokens
                else None
            )
        )