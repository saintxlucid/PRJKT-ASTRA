"""
ASTRA Multi-RAG System v2.0 Core Implementation
Category-aware retrieval with hierarchical ingestion and HRM planning.

Sacred Code: 333
Author: Saint Lucid ⚛️
Date: October 20, 2025
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
from pathlib import Path
from enum import Enum
import json
import hashlib
import logging
from collections import defaultdict

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger("astra.rag.multi_rag")


# ============================================================================
# DATA MODELS
# ============================================================================

class ConsentScope(str, Enum):
    """Consent scope for document access and retention."""
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


@dataclass
class DocumentMetadata:
    """Metadata for ingested documents."""
    doc_id: str
    uri: str
    category: str
    consent_scope: ConsentScope = ConsentScope.PRIVATE
    retention_days: int = 365
    pii_flag: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for vector store payload."""
        return {
            "doc_id": self.doc_id,
            "uri": self.uri,
            "category": self.category,
            "consent_scope": self.consent_scope.value,
            "retention_days": self.retention_days,
            "pii_flag": self.pii_flag,
            "created_at": self.created_at.isoformat(),
            "tags": self.tags
        }


@dataclass
class Chunk:
    """A text chunk with metadata and embeddings."""
    chunk_id: str  # section:para:window
    text: str
    abstract: Optional[str] = None
    hierarchical_path: Optional[str] = None  # doc > Section > Para
    doc_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    # Embeddings (for vector-sliding)
    embeddings: Optional[Dict[int, List[float]]] = None  # offset_id -> vector
    
    def __hash__(self):
        """Hash for deduplication."""
        return hash(self.text)


class RetrievalResult(BaseModel):
    """Result from retrieval pipeline."""
    chunk: Chunk
    score: float  # Hybrid or reranked score
    category: str
    source: str  # "sparse" | "dense" | "reranked" | "fused"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CitationRef(BaseModel):
    """Citation reference for answer."""
    doc_id: str
    uri: str
    chunk_id: str
    hierarchical_path: str
    text_span: str


class RAGAnswer(BaseModel):
    """Final RAG answer with citations."""
    answer: str
    citations: List[CitationRef] = Field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# ABSTRACT BASE CLASSES
# ============================================================================

class Chunker(ABC):
    """Base chunker interface."""
    
    @abstractmethod
    def chunk(self, text: str, metadata: Dict[str, Any]) -> List[Chunk]:
        """
        Chunk text into Chunk objects.
        
        Args:
            text: Raw document text
            metadata: Document metadata (doc_id, uri, etc.)
        
        Returns:
            List of Chunk objects with IDs, text, abstracts, paths
        """
        pass


class Embedder(ABC):
    """Base embedder interface."""
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Embed a text string into a vector.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding vector
        """
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass


class VectorStore(ABC):
    """Base vector store interface."""
    
    @abstractmethod
    async def upsert_vectors(
        self,
        vectors: List[Tuple[str, List[float], Dict]],
        collection: str
    ) -> int:
        """
        Upsert vectors to store.
        
        Args:
            vectors: List of (id, vector, metadata) tuples
            collection: Collection name
        
        Returns:
            Count of upserted vectors
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        collection: str,
        k: int = 10,
        filter_metadata: Optional[Dict] = None
    ) -> List[RetrievalResult]:
        """
        Search for nearest neighbors.
        
        Args:
            query_vector: Query embedding
            collection: Collection name
            k: Number of results
            filter_metadata: Metadata filters (e.g., consent_scope)
        
        Returns:
            List of RetrievalResult objects
        """
        pass


class Reranker(ABC):
    """Base reranker interface."""
    
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[str]
    ) -> List[Tuple[int, float]]:
        """
        Re-rank documents.
        
        Args:
            query: Query string
            documents: List of document texts
        
        Returns:
            List of (index, score) tuples sorted by score descending
        """
        pass


# ============================================================================
# CORE RETRIEVAL ORCHESTRATOR
# ============================================================================

class MultiRAGRetriever:
    """
    Multi-category retrieval orchestrator.
    Manages sparse + dense + cross-encoder reranking pipeline.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        vector_store: VectorStore,
        embedder: Embedder,
        reranker: Reranker,
        fts5_engine: Optional[Any] = None
    ):
        """
        Initialize retriever.
        
        Args:
            config: Configuration dict (from config.yaml)
            vector_store: Qdrant or similar vector store
            embedder: BGE-M3 or similar embedder
            reranker: BGE-Reranker or similar
            fts5_engine: SQLite FTS5 engine for sparse search
        """
        self.config = config
        self.vector_store = vector_store
        self.embedder = embedder
        self.reranker = reranker
        self.fts5_engine = fts5_engine
        logger.info("multi_rag_retriever_initialized")
    
    async def retrieve(
        self,
        query: str,
        categories: Optional[List[str]] = None,
        k: int = 12,
        policy: str = "default"
    ) -> Dict[str, List[RetrievalResult]]:
        """
        Full retrieval pipeline for query.
        
        Returns:
            {
                "ai_engineering": [RetrievalResult, ...],
                "music_film": [...],
                ...
            }
        """
        logger.info("retrieve_start", query=query, categories=categories)
        
        # Default to all categories
        if categories is None:
            categories = list(self.config["categories"].keys())
        
        candidates: Dict[str, List[RetrievalResult]] = {}
        
        # Per-category retrieval
        for category in categories:
            if category not in self.config["categories"]:
                logger.warning("unknown_category", category=category)
                continue
            
            cat_config = self.config["categories"][category]
            
            # Stage 1: Sparse search (FTS5)
            sparse_results = await self._sparse_search(
                query,
                category,
                cat_config["retrieval"]["bm25_k"]
            )
            logger.info("sparse_search_complete", category=category, count=len(sparse_results))
            
            # Stage 2: Dense search (ANN)
            dense_results = await self._dense_search(
                query,
                category,
                cat_config["retrieval"]["vec_k"]
            )
            logger.info("dense_search_complete", category=category, count=len(dense_results))
            
            # Stage 3: Hybrid mix
            mixed_results = self._hybrid_mix(
                sparse_results,
                dense_results,
                alpha=cat_config["retrieval"]["mix_alpha"]
            )
            logger.info("hybrid_mix_complete", category=category, count=len(mixed_results))
            
            # Stage 4: Cross-encoder reranking
            reranked_results = await self._rerank(
                query,
                mixed_results,
                cat_config,
                k=40  # Top 40 to reranker
            )
            logger.info("reranking_complete", category=category, count=len(reranked_results))
            
            # Stage 5: Post-retrieval optimization
            optimized_results = self._post_retrieval_optimize(
                reranked_results,
                category,
                cat_config
            )
            logger.info("post_optimization_complete", category=category, count=len(optimized_results))
            
            candidates[category] = optimized_results[:cat_config["retrieval"]["top_k"]]
        
        logger.info("retrieve_complete", categories=list(candidates.keys()))
        return candidates
    
    async def _sparse_search(
        self,
        query: str,
        category: str,
        k: int
    ) -> List[RetrievalResult]:
        """Full-text search on titles, abstracts, headers."""
        if self.fts5_engine is None:
            logger.warning("fts5_engine_not_available")
            return []
        
        try:
            results = self.fts5_engine.search(
                collection=category,
                query=query,
                top_k=k
            )
            
            return [
                RetrievalResult(
                    chunk=result["chunk"],
                    score=result["score"],
                    category=category,
                    source="sparse",
                    metadata={"bm25_score": result["score"]}
                )
                for result in results
            ]
        except Exception as e:
            logger.error("sparse_search_failed", category=category, error=str(e))
            return []
    
    async def _dense_search(
        self,
        query: str,
        category: str,
        k: int
    ) -> List[RetrievalResult]:
        """ANN search on vector embeddings with vector-sliding."""
        try:
            # Embed query
            query_vec = self.embedder.embed(query)
            
            # Search with consent filter
            cat_config = self.config["categories"][category]
            filter_metadata = {
                "must": [
                    {
                        "key": "consent_scope",
                        "match": {"any": ["private", "shared"]}
                    }
                ]
            }
            
            results = await self.vector_store.search(
                query_vector=query_vec,
                collection=cat_config["index"]["name"],
                k=k,
                filter_metadata=filter_metadata
            )
            
            # Apply vector-sliding deduplication
            deduplicated = self._deduplicate_by_vector_sliding(results, category)
            
            return deduplicated
        except Exception as e:
            logger.error("dense_search_failed", category=category, error=str(e))
            return []
    
    def _deduplicate_by_vector_sliding(
        self,
        results: List[RetrievalResult],
        category: str
    ) -> List[RetrievalResult]:
        """
        Apply vector-sliding deduplication:
        For each (doc_id, chunk_id), keep the one with max score across offsets.
        """
        best_per_chunk: Dict[Tuple[str, str], RetrievalResult] = {}
        
        for result in results:
            key = (result.chunk.doc_id, result.chunk.chunk_id)
            if key not in best_per_chunk or result.score > best_per_chunk[key].score:
                best_per_chunk[key] = result
        
        return sorted(best_per_chunk.values(), key=lambda x: -x.score)
    
    def _hybrid_mix(
        self,
        sparse_results: List[RetrievalResult],
        dense_results: List[RetrievalResult],
        alpha: float
    ) -> List[RetrievalResult]:
        """
        Combine sparse (BM25) and dense (vector) scores.
        score = alpha * dense_norm + (1 - alpha) * sparse_norm
        """
        # Normalize scores
        if sparse_results:
            max_sparse = max(r.score for r in sparse_results)
            for r in sparse_results:
                r.score = r.score / max_sparse if max_sparse > 0 else 0.0
        
        if dense_results:
            max_dense = max(r.score for r in dense_results)
            for r in dense_results:
                r.score = r.score / max_dense if max_dense > 0 else 0.0
        
        # Merge by chunk
        merged: Dict[Tuple[str, str], RetrievalResult] = {}
        
        for result in sparse_results:
            key = (result.chunk.doc_id, result.chunk.chunk_id)
            merged[key] = RetrievalResult(
                chunk=result.chunk,
                score=result.score,
                category=result.category,
                source="sparse",
                metadata={"sparse_score": result.score, "dense_score": 0.0}
            )
        
        for result in dense_results:
            key = (result.chunk.doc_id, result.chunk.chunk_id)
            if key in merged:
                # Hybrid score
                sparse_score = merged[key].metadata.get("sparse_score", 0.0)
                dense_score = result.score
                hybrid_score = alpha * dense_score + (1 - alpha) * sparse_score
                
                merged[key].score = hybrid_score
                merged[key].metadata["sparse_score"] = sparse_score
                merged[key].metadata["dense_score"] = dense_score
                merged[key].metadata["hybrid_score"] = hybrid_score
            else:
                # Dense-only
                merged[key] = RetrievalResult(
                    chunk=result.chunk,
                    score=alpha * result.score,
                    category=result.category,
                    source="dense",
                    metadata={"sparse_score": 0.0, "dense_score": result.score}
                )
        
        return sorted(merged.values(), key=lambda x: -x.score)
    
    async def _rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        cat_config: Dict,
        k: int = 40
    ) -> List[RetrievalResult]:
        """Cross-encoder reranking: top 40 → top 10-20."""
        if not candidates:
            return []
        
        # Prepare pairs for reranker
        pairs = [(query, result.chunk.text[:512]) for result in candidates[:k]]
        
        try:
            # Rerank
            scored_pairs = self.reranker.rerank(query, [text for _, text in pairs])
            
            # Re-sort candidates by reranker scores
            reranked = []
            for idx, score in scored_pairs:
                if idx < len(candidates):
                    result = candidates[idx]
                    result.score = score
                    result.source = "reranked"
                    reranked.append(result)
            
            return reranked
        except Exception as e:
            logger.error("reranking_failed", error=str(e))
            return candidates[:k]
    
    def _post_retrieval_optimize(
        self,
        reranked: List[RetrievalResult],
        category: str,
        cat_config: Dict
    ) -> List[RetrievalResult]:
        """
        Post-retrieval optimization:
        1. Adjacent packing
        2. Deduplication
        3. Diversity guard
        4. Hierarchical citation
        """
        optimizer = PostRetrievalOptimizer(cat_config)
        return optimizer.optimize(reranked, category)


# ============================================================================
# POST-RETRIEVAL OPTIMIZER
# ============================================================================

class PostRetrievalOptimizer:
    """Optimize retrieved results before passing to HRM planner."""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def optimize(
        self,
        reranked: List[RetrievalResult],
        category: str
    ) -> List[RetrievalResult]:
        """Run full optimization pipeline."""
        # 1. Adjacent packing
        packed = self._pack_adjacent(reranked)
        logger.info("adjacent_packing_complete", before=len(reranked), after=len(packed))
        
        # 2. Deduplication
        deduplicated = self._deduplicate(packed)
        logger.info("deduplication_complete", before=len(packed), after=len(deduplicated))
        
        # 3. Diversity guard
        diverse = self._apply_diversity_cap(deduplicated, category)
        logger.info("diversity_guard_complete", before=len(deduplicated), after=len(diverse))
        
        # 4. Hierarchical citation paths (already in chunk)
        return diverse
    
    def _pack_adjacent(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Merge adjacent chunks from same doc/section."""
        # Group by (doc_id, section_id)
        groups: Dict[Tuple, List[RetrievalResult]] = defaultdict(list)
        for result in results:
            key = (result.chunk.doc_id, getattr(result.chunk, "section_id", None))
            groups[key].append(result)
        
        packed = []
        for group in groups.values():
            # Check if contiguous by chunk_id
            if len(group) > 1:
                # Try to merge
                merged_text = "\n\n".join([r.chunk.text for r in group])
                merged_chunk = Chunk(
                    chunk_id=f"{group[0].chunk.chunk_id}–{group[-1].chunk.chunk_id}",
                    text=merged_text,
                    hierarchical_path=group[0].chunk.hierarchical_path,
                    doc_id=group[0].chunk.doc_id
                )
                merged_result = RetrievalResult(
                    chunk=merged_chunk,
                    score=group[0].score,
                    category=group[0].category,
                    source="packed"
                )
                packed.append(merged_result)
            else:
                packed.extend(group)
        
        return packed
    
    def _deduplicate(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Remove duplicates by text hash."""
        seen_hashes = set()
        deduplicated = []
        
        for result in results:
            h = hashlib.md5(result.chunk.text.encode()).hexdigest()
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduplicated.append(result)
        
        return deduplicated
    
    def _apply_diversity_cap(
        self,
        results: List[RetrievalResult],
        category: str
    ) -> List[RetrievalResult]:
        """Cap single doc at X% of result slots."""
        diversity_cap = self.config["retrieval"].get("diversity_cap", 0.4)
        max_from_doc = max(1, int(len(results) * diversity_cap))
        
        doc_counts: Dict[str, int] = defaultdict(int)
        diverse = []
        
        for result in results:
            doc_id = result.chunk.doc_id
            if doc_counts[doc_id] < max_from_doc:
                diverse.append(result)
                doc_counts[doc_id] += 1
        
        return diverse


# ============================================================================
# FUSION LAYER (Cross-Category)
# ============================================================================

class FusionLayer:
    """Fuse results across categories."""
    
    def __init__(self, config: Dict):
        self.config = config
        self.mode = config["fusion"]["mode"]
        logger.info("fusion_layer_initialized", mode=self.mode)
    
    def fuse(
        self,
        query: str,
        candidates: Dict[str, List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """Fuse across categories."""
        if self.mode == "weighted":
            return self._fusion_weighted(candidates)
        elif self.mode == "attention_gate":
            return self._fusion_attention_gate(query, candidates)
        else:
            raise ValueError(f"Unknown fusion mode: {self.mode}")
    
    def _fusion_weighted(
        self,
        candidates: Dict[str, List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """Static weighted fusion."""
        weights = self.config["fusion"]["weights"]
        merged = []
        
        for category, results in candidates.items():
            weight = weights.get(category, 1.0)
            for result in results:
                result.score = result.score * weight
                result.metadata["fusion_weight"] = weight
                merged.append(result)
        
        return sorted(merged, key=lambda x: -x.score)
    
    def _fusion_attention_gate(
        self,
        query: str,
        candidates: Dict[str, List[RetrievalResult]]
    ) -> List[RetrievalResult]:
        """
        Attention-gate fusion (learned).
        For now: mock implementation, can be trained later.
        """
        # TODO: Extract query features, run MLP, get per-category gates
        gates = self.config["fusion"]["weights"]  # Fallback to weights
        
        merged = []
        for category, results in candidates.items():
            gate = gates.get(category, 1.0)
            for result in results:
                result.score = result.score * gate
                result.metadata["fusion_gate"] = gate
                merged.append(result)
        
        return sorted(merged, key=lambda x: -x.score)


# ============================================================================
# INGESTION PIPELINE
# ============================================================================

class IngestionPipeline:
    """Ingest documents into Multi-RAG system."""
    
    def __init__(
        self,
        config: Dict,
        chunker: Chunker,
        embedder: Embedder,
        vector_store: VectorStore,
        fts5_engine: Optional[Any] = None
    ):
        self.config = config
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.fts5_engine = fts5_engine
        logger.info("ingestion_pipeline_initialized")
    
    async def ingest_document(
        self,
        path: str,
        category: str,
        consent: str = "private",
        pii: bool = False
    ) -> str:
        """
        Ingest a document.
        
        Returns:
            doc_id (SHA256 hash)
        """
        logger.info("ingest_document_start", path=path, category=category)
        
        # Read file
        file_path = Path(path)
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # Compute doc_id (SHA256 hash)
        doc_id = hashlib.sha256(text.encode()).hexdigest()[:16]
        
        # Create metadata
        metadata = DocumentMetadata(
            doc_id=doc_id,
            uri=str(file_path.absolute()),
            category=category,
            consent_scope=ConsentScope(consent),
            pii_flag=pii
        )
        
        # Chunk text
        chunks = self.chunker.chunk(text, asdict(metadata))
        logger.info("chunking_complete", count=len(chunks), doc_id=doc_id)
        
        # Embed and store
        vectors_to_upsert = []
        for chunk in chunks:
            # Embed chunk text
            vec = self.embedder.embed(chunk.text)
            
            # Prepare metadata
            chunk_metadata = metadata.to_dict()
            chunk_metadata["chunk_id"] = chunk.chunk_id
            chunk_metadata["hierarchical_path"] = chunk.hierarchical_path
            
            vectors_to_upsert.append((chunk.chunk_id, vec, chunk_metadata))
        
        # Upsert to vector store
        cat_config = self.config["categories"][category]
        collection = cat_config["index"]["name"]
        
        count = await self.vector_store.upsert_vectors(
            vectors=vectors_to_upsert,
            collection=collection
        )
        logger.info("vectors_upserted", count=count, collection=collection)
        
        # Index in FTS5 (optional)
        if self.fts5_engine:
            for chunk in chunks:
                self.fts5_engine.index(
                    collection=category,
                    doc_id=doc_id,
                    text=chunk.text,
                    abstract=chunk.abstract or chunk.text[:100],
                    title=chunk.hierarchical_path or f"Chunk {chunk.chunk_id}"
                )
        
        logger.info("ingest_document_complete", doc_id=doc_id)
        return doc_id


# ============================================================================
# CONTEXT COMPOSER
# ============================================================================

class ContextComposer:
    """Compose final context for LLM with token budgeting and diversity."""
    
    def __init__(self, max_tokens: int = 3500):
        self.max_tokens = max_tokens
    
    def compose(
        self,
        query: str,
        fused_results: List[RetrievalResult]
    ) -> Tuple[str, List[CitationRef]]:
        """
        Compose context with token budgeting and diversity.
        
        Returns:
            (composed_context_text, citations)
        """
        tokens_used = 0
        context_chunks = []
        citations = []
        
        doc_usage: Dict[str, int] = defaultdict(int)
        
        for result in fused_results:
            chunk_tokens = len(result.chunk.text.split())
            
            # Check token budget
            if tokens_used + chunk_tokens > self.max_tokens:
                break
            
            # Check diversity (cap 40% from single doc)
            doc_id = result.chunk.doc_id
            if doc_usage[doc_id] >= int(self.max_tokens * 0.4) / max(1, len(fused_results)):
                continue
            
            # Add chunk
            context_chunks.append(result.chunk.text)
            tokens_used += chunk_tokens
            doc_usage[doc_id] += 1
            
            # Add citation
            citations.append(
                CitationRef(
                    doc_id=result.chunk.doc_id or "",
                    uri=result.chunk.metadata.get("uri", "") if result.chunk.metadata else "",
                    chunk_id=result.chunk.chunk_id,
                    hierarchical_path=result.chunk.hierarchical_path or "",
                    text_span=result.chunk.text[:80] + "..."
                )
            )
        
        # Compose final context
        composed = "\n\n".join(context_chunks)
        
        return composed, citations


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    "MultiRAGRetriever",
    "PostRetrievalOptimizer",
    "FusionLayer",
    "IngestionPipeline",
    "ContextComposer",
    "RAGAnswer",
    "CitationRef",
    "RetrievalResult",
    "Chunk",
    "DocumentMetadata",
]
