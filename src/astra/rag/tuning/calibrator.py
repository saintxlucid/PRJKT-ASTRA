"""
Auto-tuning pipeline for RAG system weight calibration and configuration management.
Handles:
1. Weight optimization using golden set
2. Versioned configuration management
3. A/B testing framework
4. Rollback support
"""

import asyncio
import datetime
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize
from prometheus_client import Gauge, Counter

from astra.rag.eval.metrics import compute_ndcg, compute_mrr
from astra.rag.store.config import RagConfig
from astra.rag.multi_rag import MultiRagFusion
from astra.utils.async_utils import gather_with_concurrency

logger = logging.getLogger(__name__)

# Prometheus metrics
calibration_score = Gauge("rag_calibration_score", "Current calibration score (nDCG@10)")
config_version = Gauge("rag_config_version", "Active configuration version")
rollback_count = Counter("rag_rollback_count", "Number of configuration rollbacks")

@dataclass
class CalibrationResult:
    """Results from a calibration run."""
    weights: Dict[str, float]
    ndcg: float
    mrr: float
    timestamp: datetime.datetime
    version: int

class RagCalibrator:
    """Manages RAG system weight calibration and configuration versioning."""
    
    def __init__(
        self,
        rag_fusion: MultiRagFusion,
        golden_set_path: Path,
        config_dir: Path,
        max_versions: int = 5,
        concurrent_queries: int = 3
    ):
        self.rag_fusion = rag_fusion
        self.golden_set_path = golden_set_path
        self.config_dir = config_dir
        self.max_versions = max_versions
        self.concurrent_queries = concurrent_queries
        
        # Create config directory if needed
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load golden set
        with open(golden_set_path) as f:
            self.golden_set = json.load(f)
            
        # Track current version
        self._current_version = self._get_latest_version()
        config_version.set(self._current_version)

    async def calibrate(self) -> CalibrationResult:
        """Run calibration using golden set to optimize weights."""
        logger.info("Starting RAG weight calibration")
        
        # Get initial weights
        initial_weights = self.rag_fusion.get_weights()
        
        # Optimize weights using scipy
        bounds = [(0.1, 1.0) for _ in range(len(initial_weights))]
        result = minimize(
            fun=lambda w: -1 * asyncio.run(self._evaluate_weights(dict(zip(initial_weights.keys(), w)))),
            x0=list(initial_weights.values()),
            bounds=bounds,
            method="L-BFGS-B"
        )
        
        optimized_weights = dict(zip(initial_weights.keys(), result.x))
        
        # Evaluate final performance
        ndcg = await self._compute_ndcg(optimized_weights)
        mrr = await self._compute_mrr(optimized_weights)
        
        # Save new configuration
        calibration = CalibrationResult(
            weights=optimized_weights,
            ndcg=ndcg,
            mrr=mrr,
            timestamp=datetime.datetime.now(),
            version=self._current_version + 1
        )
        await self._save_config(calibration)
        
        # Update metrics
        calibration_score.set(ndcg)
        config_version.set(calibration.version)
        
        logger.info(f"Calibration complete - nDCG: {ndcg:.3f}, MRR: {mrr:.3f}")
        return calibration

    async def _evaluate_weights(self, weights: Dict[str, float]) -> float:
        """Evaluate a set of weights using the golden set."""
        return await self._compute_ndcg(weights)
    
    async def _compute_ndcg(self, weights: Dict[str, float]) -> float:
        """Compute nDCG@10 for given weights using golden set."""
        self.rag_fusion.set_weights(weights)
        
        async def process_query(item):
            query = item["query"]
            relevant_docs = item["relevant_docs"]
            results = await self.rag_fusion.retrieve(query, limit=10)
            return compute_ndcg(
                [r.doc_id for r in results],
                relevant_docs,
                k=10
            )
            
        scores = await gather_with_concurrency(
            self.concurrent_queries,
            *[process_query(item) for item in self.golden_set]
        )
        return np.mean(scores)
    
    async def _compute_mrr(self, weights: Dict[str, float]) -> float:
        """Compute MRR for given weights using golden set."""
        self.rag_fusion.set_weights(weights)
        
        async def process_query(item):
            query = item["query"]
            relevant_docs = item["relevant_docs"]
            results = await self.rag_fusion.retrieve(query, limit=10)
            return compute_mrr(
                [r.doc_id for r in results],
                relevant_docs
            )
            
        scores = await gather_with_concurrency(
            self.concurrent_queries,
            *[process_query(item) for item in self.golden_set]
        )
        return np.mean(scores)

    async def _save_config(self, result: CalibrationResult):
        """Save calibration results as new config version."""
        config_path = self.config_dir / f"rag_config_v{result.version}.json"
        config = {
            "version": result.version,
            "timestamp": result.timestamp.isoformat(),
            "weights": result.weights,
            "metrics": {
                "ndcg": result.ndcg,
                "mrr": result.mrr
            }
        }
        
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
            
        # Update current version
        self._current_version = result.version
        
        # Cleanup old versions
        self._cleanup_old_versions()
        
    def _cleanup_old_versions(self):
        """Remove old config versions beyond max_versions."""
        versions = sorted([
            int(p.stem.split("_v")[1])
            for p in self.config_dir.glob("rag_config_v*.json")
        ])
        
        for v in versions[:-self.max_versions]:
            config_path = self.config_dir / f"rag_config_v{v}.json"
            config_path.unlink()
            
    def _get_latest_version(self) -> int:
        """Get latest config version number."""
        versions = [
            int(p.stem.split("_v")[1])
            for p in self.config_dir.glob("rag_config_v*.json")
        ]
        return max(versions) if versions else 0
    
    async def rollback(self, version: Optional[int] = None) -> bool:
        """Rollback to specified or previous version."""
        if version is None:
            version = self._current_version - 1
            
        config_path = self.config_dir / f"rag_config_v{version}.json"
        if not config_path.exists():
            logger.error(f"Cannot rollback - version {version} not found")
            return False
            
        with open(config_path) as f:
            config = json.load(f)
            
        # Apply weights
        self.rag_fusion.set_weights(config["weights"])
        self._current_version = version
        
        # Update metrics
        config_version.set(version)
        rollback_count.inc()
        
        logger.info(f"Rolled back to version {version}")
        return True
        
    async def start_ab_test(
        self,
        test_weights: Dict[str, float],
        duration_hours: int = 24
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Run A/B test comparing current weights vs test weights.
        Returns metrics for both variants.
        """
        logger.info("Starting A/B test")
        
        # Store current weights
        control_weights = self.rag_fusion.get_weights()
        
        # Evaluate both variants
        control_ndcg = await self._compute_ndcg(control_weights)
        control_mrr = await self._compute_mrr(control_weights)
        
        test_ndcg = await self._compute_ndcg(test_weights)
        test_mrr = await self._compute_mrr(test_weights)
        
        return (
            {"ndcg": control_ndcg, "mrr": control_mrr},
            {"ndcg": test_ndcg, "mrr": test_mrr}
        )