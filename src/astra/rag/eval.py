"""
ASTRA Multi-RAG Evaluator
Evaluation metrics and regression detection for RAG pipeline.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path
import numpy as np
import structlog
from datetime import datetime

logger = structlog.get_logger()

@dataclass
class EvalMetrics:
    """Evaluation metrics for RAG pipeline."""
    hit_at_k: float  # Hit rate at k
    mrr_at_k: float  # Mean Reciprocal Rank at k
    context_tokens: int  # Avg tokens in context
    diversity: float  # Unique sources / total sources
    category_coverage: Dict[str, float]  # Per-category hit rates
    latency_p95: float  # 95th percentile latency
    confidence_mean: float  # Mean answer confidence

class RAGEvaluator:
    """Evaluates RAG pipeline quality and detects regressions."""
    
    def __init__(
        self,
        baseline_path: Optional[Path] = None,
        regression_threshold: float = -0.05  # 5% degradation
    ):
        self.baseline_path = baseline_path
        self.regression_threshold = regression_threshold
        self.baseline_metrics = self._load_baseline()
        
    def _load_baseline(self) -> Optional[Dict[str, float]]:
        """Load baseline metrics from file."""
        if not self.baseline_path or not self.baseline_path.exists():
            return None
            
        try:
            with open(self.baseline_path) as f:
                return json.load(f)
        except Exception as e:
            logger.warning("baseline_load_failed", error=str(e))
            return None
            
    def compute_metrics(
        self,
        results: List[Dict[str, Any]],
        ground_truth: Optional[List[str]] = None
    ) -> EvalMetrics:
        """
        Compute evaluation metrics for a batch of results.
        
        Args:
            results: List of retrieval/answer results
            ground_truth: Optional list of expected doc IDs
            
        Returns:
            EvalMetrics with computed scores
        """
        # Initialize counters
        total_tokens = 0
        unique_sources = set()
        total_sources = 0
        category_hits: Dict[str, int] = {}
        category_total: Dict[str, int] = {}
        latencies = []
        confidences = []
        
        # Track hits and MRR
        hits_at_k = 0
        mrr_sum = 0.0
        
        for result in results:
            # Context stats
            if "context" in result:
                total_tokens += len(result["context"].split())
            
            # Source diversity
            if "docs" in result:
                for doc in result["docs"]:
                    source = doc.get("source", "unknown")
                    unique_sources.add(source)
                    total_sources += 1
                    
                    # Category coverage
                    category = doc.get("category", "unknown")
                    category_hits[category] = category_hits.get(category, 0) + 1
                    category_total[category] = category_total.get(category, 0) + 1
            
            # Latency
            if "latency_ms" in result:
                latencies.append(result["latency_ms"] / 1000.0)  # Convert to seconds
                
            # Confidence
            if "confidence" in result:
                confidences.append(result["confidence"])
                
            # Ground truth evaluation
            if ground_truth and "docs" in result:
                retrieved_ids = [d["id"] for d in result["docs"]]
                
                # Hit@k
                if any(rid in ground_truth for rid in retrieved_ids):
                    hits_at_k += 1
                    
                # MRR@k
                for rank, rid in enumerate(retrieved_ids, 1):
                    if rid in ground_truth:
                        mrr_sum += 1.0 / rank
                        break
        
        # Compute final metrics
        n = len(results)
        metrics = EvalMetrics(
            hit_at_k=hits_at_k / n if ground_truth and n > 0 else -1,
            mrr_at_k=mrr_sum / n if ground_truth and n > 0 else -1,
            context_tokens=total_tokens // n if n > 0 else 0,
            diversity=len(unique_sources) / max(1, total_sources),
            category_coverage={
                cat: hits / max(1, category_total[cat])
                for cat, hits in category_hits.items()
            },
            latency_p95=np.percentile(latencies, 95) if latencies else -1,
            confidence_mean=np.mean(confidences) if confidences else -1
        )
        
        return metrics
        
    def detect_regression(self, current_metrics: EvalMetrics) -> Optional[Dict[str, float]]:
        """
        Detect significant regressions from baseline.
        
        Returns:
            Dict of metrics that degraded beyond threshold, or None if no regression
        """
        if not self.baseline_metrics:
            return None
            
        # Convert metrics to flat dict for comparison
        current = {
            "hit_at_k": current_metrics.hit_at_k,
            "mrr_at_k": current_metrics.mrr_at_k,
            "context_tokens": current_metrics.context_tokens,
            "diversity": current_metrics.diversity,
            "latency_p95": current_metrics.latency_p95,
            "confidence_mean": current_metrics.confidence_mean
        }
        
        # Check for regressions
        regressions = {}
        for metric, value in current.items():
            if metric in self.baseline_metrics:
                baseline = self.baseline_metrics[metric]
                if baseline > 0:  # Avoid div by zero
                    relative_change = (value - baseline) / baseline
                    if relative_change < self.regression_threshold:
                        regressions[metric] = relative_change
                        
        return regressions if regressions else None
        
    def save_baseline(self, metrics: EvalMetrics, path: Optional[Path] = None) -> None:
        """Save current metrics as new baseline."""
        save_path = path or self.baseline_path
        if not save_path:
            return
            
        metrics_dict = {
            "hit_at_k": metrics.hit_at_k,
            "mrr_at_k": metrics.mrr_at_k,
            "context_tokens": metrics.context_tokens,
            "diversity": metrics.diversity,
            "latency_p95": metrics.latency_p95,
            "confidence_mean": metrics.confidence_mean,
            "timestamp": datetime.now().isoformat(),
            "category_coverage": metrics.category_coverage
        }
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(metrics_dict, f, indent=2)