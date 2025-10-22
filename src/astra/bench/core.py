"""
Benchmarking and tuning utilities for ASTRA.

This module provides tools for:
- Running fixed query benchmarks
- Collecting performance metrics
- Analyzing retrieval quality
- Parameter tuning
"""
import time
import json
import statistics
from typing import List, Dict, Any, Tuple, Set
from dataclasses import dataclass
import structlog
from pathlib import Path

import numpy as np
from tqdm import tqdm

from astra.rag.pipeline import MultiRAGPipeline
from astra.rag.documents import Document
from astra.telemetry.events import EventLogger

logger = structlog.get_logger()

@dataclass
class BenchmarkConfig:
    """Configuration for benchmark runs."""
    k_bm25: int = 20
    k_dense: int = 10
    fusion_method: str = "rrf"
    rrf_k: float = 60.0
    score_threshold: float = 0.6
    cache_ttl: int = 3600
    target_p95_ms: float = 300.0
    target_cache_rate: float = 0.7

@dataclass
class QueryResult:
    """Results from a single query."""
    query: str
    duration_ms: float
    num_results: int
    cache_hit: bool
    top_k_ids: List[str]

@dataclass
class BenchmarkResult:
    """Results from a complete benchmark run."""
    config: BenchmarkConfig
    queries: List[QueryResult]
    p50_ms: float
    p95_ms: float
    cache_hit_rate: float
    mean_overlap: float

class Benchmarker:
    """Runs benchmarks and tunes parameters."""
    
    # Standard test queries covering different aspects
    DEFAULT_QUERIES = [
        # Core functionality
        "What is ASTRA's architecture?",
        "How does the RAG pipeline work?",
        "Explain the memory bridge integration.",
        
        # Technical components
        "How does Qdrant integration work?",
        "Describe the PDF parsing process.",
        "What embeddings are used?",
        
        # Features
        "How does chunk merging work?",
        "Explain the telemetry system.",
        "What maintenance tasks run?",
        
        # Operations
        "How to install the ingestion service?",
        "What are the health check procedures?",
        "How to monitor the system?",
        
        # Edge cases
        "Handle large PDF documents",
        "Recovery from failures",
        "Performance optimization",
        
        # Specific details
        "BGE-M3 configuration options",
        "Windows service parameters",
        "Cache configuration settings",
        
        # Integration points
        "Memory bridge callbacks",
        "Event logging format"
    ]
    
    def __init__(
        self,
        pipeline: MultiRAGPipeline,
        event_logger: EventLogger,
        config: BenchmarkConfig = None
    ):
        """Initialize benchmarker.
        
        Args:
            pipeline: RAG pipeline to benchmark
            event_logger: Event logger for metrics
            config: Optional benchmark configuration
        """
        self.pipeline = pipeline
        self.event_logger = event_logger
        self.config = config or BenchmarkConfig()
        
    def _run_query(self, query: str) -> QueryResult:
        """Run a single query and collect metrics."""
        # Check cache state before query
        cache_size_before = len(self.pipeline.cache) if hasattr(self.pipeline, 'cache') else 0
        
        # Time the query
        start = time.perf_counter()
        results = self.pipeline.retrieve(query, self.config.k_dense)
        duration = (time.perf_counter() - start) * 1000  # ms
        
        # Check if cache was hit
        cache_size_after = len(self.pipeline.cache) if hasattr(self.pipeline, 'cache') else 0
        cache_hit = cache_size_after == cache_size_before
        
        return QueryResult(
            query=query,
            duration_ms=duration,
            num_results=len(results),
            cache_hit=cache_hit,
            top_k_ids=[r.id for r in results]
        )
        
    def _calculate_overlap(self, results: List[QueryResult]) -> float:
        """Calculate mean overlap between result sets."""
        overlaps = []
        for i, r1 in enumerate(results[:-1]):
            for r2 in results[i+1:]:
                if r1.query == r2.query:  # Only compare same query
                    s1 = set(r1.top_k_ids)
                    s2 = set(r2.top_k_ids)
                    if s1 and s2:  # Non-empty results
                        overlap = len(s1 & s2) / len(s1 | s2)
                        overlaps.append(overlap)
        return statistics.mean(overlaps) if overlaps else 0.0

    def run_benchmark(
        self,
        queries: List[str] = None,
        runs: int = 2
    ) -> BenchmarkResult:
        """Run complete benchmark.
        
        Args:
            queries: List of queries to run, defaults to standard set
            runs: Number of times to run each query
            
        Returns:
            Complete benchmark results
        """
        queries = queries or self.DEFAULT_QUERIES
        all_results: List[QueryResult] = []
        
        logger.info(
            "benchmark_started",
            queries=len(queries),
            runs=runs
        )
        
        # Run queries
        for _ in range(runs):
            for query in tqdm(queries, desc="Running queries"):
                result = self._run_query(query)
                all_results.append(result)
                
        # Calculate metrics
        durations = [r.duration_ms for r in all_results]
        durations.sort()
        
        p50_ms = np.percentile(durations, 50)
        p95_ms = np.percentile(durations, 95)
        
        cache_hits = sum(1 for r in all_results if r.cache_hit)
        cache_hit_rate = cache_hits / len(all_results)
        
        mean_overlap = self._calculate_overlap(all_results)
        
        logger.info(
            "benchmark_complete",
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            cache_hit_rate=cache_hit_rate,
            mean_overlap=mean_overlap
        )
        
        return BenchmarkResult(
            config=self.config,
            queries=all_results,
            p50_ms=p50_ms,
            p95_ms=p95_ms,
            cache_hit_rate=cache_hit_rate,
            mean_overlap=mean_overlap
        )
        
    def tune_parameters(
        self,
        results: BenchmarkResult
    ) -> BenchmarkConfig:
        """Suggest parameter tuning based on results.
        
        Args:
            results: Benchmark results to analyze
            
        Returns:
            Tuned configuration
        """
        config = self.config
        
        # Tune based on p95 latency
        if results.p95_ms > config.target_p95_ms:
            # Try reducing k values
            if config.k_dense > 5:
                config.k_dense = max(5, config.k_dense - 5)
            if config.k_bm25 > 10:
                config.k_bm25 = max(10, config.k_bm25 - 5)
                
        # Tune based on cache hit rate
        if results.cache_hit_rate < config.target_cache_rate:
            # Try increasing TTL
            config.cache_ttl = min(7200, config.cache_ttl * 2)
            
        # Tune fusion based on overlap
        if results.mean_overlap < 0.5:
            # Increase RRF k to favor higher ranks
            config.rrf_k = min(100.0, config.rrf_k * 1.5)
        elif results.mean_overlap > 0.8:
            # Decrease RRF k to consider more results
            config.rrf_k = max(20.0, config.rrf_k * 0.75)
            
        logger.info(
            "tuning_complete",
            k_dense=config.k_dense,
            k_bm25=config.k_bm25,
            cache_ttl=config.cache_ttl,
            rrf_k=config.rrf_k
        )
        
        return config
        
    def save_results(
        self,
        results: BenchmarkResult,
        path: str
    ) -> None:
        """Save benchmark results to file.
        
        Args:
            results: Benchmark results to save
            path: Path to save results file
        """
        output = {
            "config": vars(results.config),
            "summary": {
                "p50_ms": results.p50_ms,
                "p95_ms": results.p95_ms,
                "cache_hit_rate": results.cache_hit_rate,
                "mean_overlap": results.mean_overlap
            },
            "queries": [
                {
                    "query": r.query,
                    "duration_ms": r.duration_ms,
                    "num_results": r.num_results,
                    "cache_hit": r.cache_hit,
                    "top_k_ids": r.top_k_ids
                }
                for r in results.queries
            ]
        }
        
        with open(path, 'w') as f:
            json.dump(output, f, indent=2)
            
        logger.info("results_saved", path=path)