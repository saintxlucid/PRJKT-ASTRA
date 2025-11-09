"""
CLI tool for running ASTRA benchmarks.

This script provides a command-line interface for:
- Running performance benchmarks
- Collecting metrics
- Tuning parameters
- Saving results
"""
import os
import sys
import time
import argparse
from pathlib import Path
import yaml
import structlog
from typing import Dict, Any

from astra.bench.core import Benchmarker, BenchmarkConfig
from astra.rag.pipeline import MultiRAGPipeline
from astra.telemetry.events import EventLogger

logger = structlog.get_logger()

def load_config(path: str) -> Dict[str, Any]:
    """Load YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f)

def create_benchmark_config(config: Dict[str, Any]) -> BenchmarkConfig:
    """Create benchmark config from YAML."""
    return BenchmarkConfig(
        k_bm25=config["pipeline"].get("k_bm25", 20),
        k_dense=config["pipeline"].get("k_dense", 10),
        fusion_method=config["pipeline"].get("fusion_method", "rrf"),
        rrf_k=config["pipeline"].get("rrf_k", 60.0),
        score_threshold=config["pipeline"].get("score_threshold", 0.6),
        cache_ttl=config["retriever"].get("cache_ttl", 3600),
        target_p95_ms=config["maintenance"].get("target_p95_ms", 300.0),
        target_cache_rate=config["maintenance"].get("target_cache_rate", 0.7)
    )

def main():
    parser = argparse.ArgumentParser(
        description="Run ASTRA benchmarks"
    )
    parser.add_argument(
        "--config",
        default="config/rag.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--queries",
        help="Path to custom queries file"
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of runs per query"
    )
    parser.add_argument(
        "--output",
        default="bench_results.json",
        help="Output file path"
    )
    parser.add_argument(
        "--tune",
        action="store_true",
        help="Tune parameters based on results"
    )
    args = parser.parse_args()

    try:
        # Load config
        config = load_config(args.config)
        bench_config = create_benchmark_config(config)
        
        # Set up components
        logger.info("initializing_components")
        pipeline = MultiRAGPipeline.from_config(config)
        
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        event_logger = EventLogger(
            log_dir=str(log_dir),
            rotation_bytes=1048576,
            max_files=5
        )
        
        # Create benchmarker
        benchmarker = Benchmarker(
            pipeline=pipeline,
            event_logger=event_logger,
            config=bench_config
        )
        
        # Load custom queries if specified
        queries = None
        if args.queries:
            with open(args.queries) as f:
                queries = [q.strip() for q in f]
        
        # Run benchmark
        logger.info(
            "starting_benchmark",
            runs=args.runs,
            queries=len(queries) if queries else "default"
        )
        results = benchmarker.run_benchmark(
            queries=queries,
            runs=args.runs
        )
        
        # Save results
        benchmarker.save_results(results, args.output)
        
        # Tune if requested
        if args.tune:
            logger.info("tuning_parameters")
            new_config = benchmarker.tune_parameters(results)
            
            # Save tuned config
            config_path = Path(args.config)
            tuned_path = config_path.parent / f"tuned_{config_path.name}"
            
            # Update config with tuned values
            config["pipeline"]["k_bm25"] = new_config.k_bm25
            config["pipeline"]["k_dense"] = new_config.k_dense
            config["pipeline"]["rrf_k"] = new_config.rrf_k
            config["retriever"]["cache_ttl"] = new_config.cache_ttl
            
            with open(tuned_path, 'w') as f:
                yaml.dump(config, f)
            
            logger.info("tuned_config_saved", path=str(tuned_path))
            
        return 0
        
    except Exception as e:
        logger.error("benchmark_failed", error=str(e))
        return 1

if __name__ == "__main__":
    sys.exit(main())