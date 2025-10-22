"""
Advanced Multi-RAG pipeline with adaptive routing and fusion.

This module implements an intelligent retrieval pipeline that:
1. Routes queries to optimal retrieval strategies
2. Performs hybrid retrieval with auto-tuned fusion
3. Applies diversity-aware reranking
4. Tracks performance metrics for continuous improvement
"""
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from pathlib import Path
import structlog
import json
import time
from concurrent.futures import ThreadPoolExecutor

from astra.rag.routing.router import QueryRouter, Route
from astra.rag.fusion.auto_fusion import AutoFusion, FusionConfig
from astra.rag.indexes import DenseIndex
from astra.embed.bge import BGEM3Embedder
from astra.rag.telemetry import TelemetryEmitter

logger = structlog.get_logger(__name__)

@dataclass
class MultiRAGConfig:
    """Configuration for multi-RAG pipeline."""
    # Retrieval params
    dense_batch_size: int = 32
    max_concurrent: int = 4
    rerank_cutoff: int = 50
    max_results: int = 10
    
    # Layout-aware scoring
    heading_bonus: float = 0.2
    section_bonus: float = 0.1
    length_bonus: float = 0.05
    layout_weight: float = 0.3
    
    # Fusion params 
    fusion_method: str = "rrf"
    rrf_k: float = 60.0
    consent_required: bool = True
    
    # Cache settings
    cache_ttl: int = 3600
    
    # Auto-tuning
    learning_rate: float = 0.01
    min_feedback: int = 25
    eval_frequency: int = 100

class MultiRAGPipeline:
    """
    Advanced retrieval pipeline with routing and fusion.
    """
    
    def __init__(
        self,
        config_path: str,
        golden_set_path: Optional[str] = None,
        telemetry_dir: Optional[str] = None
    ):
        """Initialize pipeline components."""
        self.logger = logger.bind(component="multi_rag")
        
        # Load config
        with open(config_path) as f:
            config = json.load(f)
        self.config = MultiRAGConfig(**config.get("multi_rag", {}))
        
        # Initialize components
        self.router = QueryRouter(config_path)
        self.fusion = AutoFusion(
            config=FusionConfig(**config.get("fusion", {})),
            golden_set_path=golden_set_path
        )
        
        # Initialize retrievers and rerankers
        self.dense_index = DenseIndex.from_config(config)
        self.embedder = BGEM3Embedder()
        self.reranker = CrossEncoderReranker(
            config=RerankerConfig(
                heading_bonus=self.config.heading_bonus,
                section_bonus=self.config.section_bonus,
                length_bonus=self.config.length_bonus,
                layout_weight=self.config.layout_weight
            )
        )
        
        # Initialize text processor for layout parsing
        self.text_processor = LayoutParser()
        
        # Initialize telemetry
        self.telemetry = TelemetryEmitter(telemetry_dir) if telemetry_dir else None
        
        # Initialize thread pool for parallel retrievals
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.config.max_concurrent
        )
        
        # Cache for layout-enhanced results
        self._layout_cache = {}
        self._layout_cache_ttl = self.config.cache_ttl
        
        self.logger.info("pipeline_initialized",
                        config_path=config_path,
                        golden_set=bool(golden_set_path))
                        
    async def retrieve(
        self,
        query: str,
        k: int = 10,
        context: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results using adaptive routing and fusion.
        
        Args:
            query: Search query
            k: Number of results to return
            context: Optional request context
            
        Returns:
            List of retrieved and reranked results
        """
        start_time = time.time()
        request_id = context.get("request_id") if context else None
        
        try:
            # 1. Route query
            route = self.router.route(query)
            self.logger.debug("query_routed",
                            intent=route.intent,
                            strategy=route.strategy)
            
            # 2. Parallel retrieval
            dense_task = None
            bm25_task = None
            
            if route.use_dense:
                # Embed query
                query_vector = self.embedder.embed_documents([query])[0]
                
                # Start dense search
                dense_task = asyncio.create_task(
                    self.dense_index.search(
                        query_vector=query_vector,
                        collection="documents",
                        k=self.config.rerank_cutoff
                    )
                )
                
            if route.use_bm25:
                # Placeholder for BM25 implementation
                # Will add BM25 index integration later
                bm25_results = []
            else:
                bm25_results = []
                
            # Wait for dense results if used
            dense_results = []
            if dense_task:
                try:
                    dense_results = await dense_task
                except Exception as e:
                    self.logger.error("dense_search_failed",
                                    error=str(e))
                    
            # 3. Fuse initial results
            cache_key = f"{query}_{route.strategy}_{k}"
            if cache_key in self._layout_cache:
                cached = self._layout_cache[cache_key]
                if time.time() - cached["timestamp"] < self._layout_cache_ttl:
                    return cached["results"][:k]

            fused = self.fusion.interpolate(
                bm25_results=bm25_results,
                dense_results=dense_results,
                alpha=route.alpha
            )
            
            # 4. Layout-aware reranking
            chunks = []
            for result in fused:
                # Convert to layout chunks
                chunk = self.text_processor.convert_to_chunk(
                    text=result["text"],
                    metadata=result["metadata"]
                )
                chunks.append(chunk)
                
            # Apply layout-aware scoring
            scores = self.reranker.rerank(
                query=query,
                chunks=chunks,
                intent=route.intent
            )
            
            # Update result scores
            for result, score in zip(fused, scores):
                result["score"] = float(score)
                
            # 5. Apply context stitching for adjacent content
            stitched = []
            prev_chunk = None
            
            for i, result in enumerate(sorted(fused, key=lambda x: x["score"], reverse=True)):
                chunk = chunks[i]
                
                if prev_chunk and self.text_processor.are_adjacent(prev_chunk, chunk):
                    # Merge with previous
                    merged = self.text_processor.merge_chunks(prev_chunk, chunk)
                    stitched[-1]["text"] = merged.text
                    stitched[-1]["metadata"].update(chunk.metadata)
                    stitched[-1]["score"] += result["score"] * self.config.layout_weight
                else:
                    stitched.append(result)
                    prev_chunk = chunk
                    
            fused = stitched
            
            # 6. Filter by consent
            if self.config.consent_required:
                fused = [
                    r for r in fused 
                    if r.get("metadata", {}).get("consent", True)
                ]
                
            # 7. Update weights and cache
            self.fusion.update_weights(query, route.intent, fused)
            
            self._layout_cache[cache_key] = {
                "results": fused,
                "timestamp": time.time()
            }
            
            # 8. Emit telemetry with layout metrics
            duration = time.time() - start_time
            if self.telemetry:
                emit_data = {
                    "request_id": request_id,
                    "intent": route.intent, 
                    "strategy": route.strategy,
                    "results": len(fused),
                    "duration": duration,
                    "layout_enhanced": True,
                    "context_stitching": True,
                    "cache_hit": False,
                    "layout_metrics": {
                        "heading_matches": len([c for c in chunks if c.heading]),
                        "section_diversity": len({c.section_id for c in chunks if c.section_id}),
                        "avg_context_length": sum(len(c.text.split()) for c in chunks) / len(chunks)
                    }
                }
                self.telemetry.emit_event("retrieval", emit_data)
                
            return fused[:k]
            
        except Exception as e:
            self.logger.error("retrieval_failed",
                            query=query,
                            error=str(e))
            if self.telemetry:
                self.telemetry.emit("retrieval_error", {
                    "request_id": request_id,
                    "error": str(e)
                })
            return []
        
    def save_state(self, state_dir: str) -> None:
        """Save pipeline state for analysis/reload."""
        state_dir = Path(state_dir)
        state_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save router analytics
            router_path = state_dir / "router_state.json"
            with open(router_path, 'w') as f:
                json.dump(self.router.get_analytics(), f, indent=2)
                
            # Save fusion state
            fusion_path = state_dir / "fusion_state.json"
            self.fusion.save_state(str(fusion_path))
            
            self.logger.info("state_saved", directory=str(state_dir))
            
        except Exception as e:
            self.logger.error("state_save_failed",
                            directory=str(state_dir),
                            error=str(e))
            
    async def run_evaluation(
        self,
        queries: List[str],
        k: int = 10
    ) -> Dict[str, Any]:
        """
        Run evaluation on a set of queries.
        
        Args:
            queries: List of queries to evaluate
            k: Number of results per query
            
        Returns:
            Evaluation metrics
        """
        metrics = {
            "queries": len(queries),
            "mean_latency": 0.0,
            "hit_rate": 0.0,
            "mrr": 0.0,
            "intent_dist": {},
            "errors": 0
        }
        
        total_time = 0.0
        total_hits = 0
        mrr_sum = 0.0
        
        for query in queries:
            try:
                start = time.time()
                results = await self.retrieve(query, k=k)
                duration = time.time() - start
                
                total_time += duration
                
                # Calculate metrics if golden set exists
                if (self.fusion.golden_set and 
                    query in self.fusion.golden_set):
                    expected = set(
                        self.fusion.golden_set[query]["relevant_ids"]
                    )
                    retrieved = set(r["id"] for r in results)
                    
                    # Hit rate
                    hits = len(expected & retrieved)
                    total_hits += hits
                    
                    # MRR
                    for i, r in enumerate(results, 1):
                        if r["id"] in expected:
                            mrr_sum += 1.0 / i
                            break
                            
            except Exception as e:
                self.logger.error("eval_query_failed",
                                query=query,
                                error=str(e))
                metrics["errors"] += 1
                
        # Compute final metrics
        queries_completed = len(queries) - metrics["errors"]
        if queries_completed > 0:
            metrics["mean_latency"] = total_time / queries_completed
            metrics["hit_rate"] = total_hits / queries_completed
            metrics["mrr"] = mrr_sum / queries_completed
            
        # Get intent distribution
        metrics["intent_dist"] = self.router.get_analytics()["intent_dist"]
        
        return metrics