"""Delta analysis system for model changes and evolution."""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
import json
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import torch
from torch import Tensor
import networkx as nx
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class TensorDelta:
    """Analysis of changes in a tensor."""
    name: str
    shape_changed: bool
    old_shape: Optional[Tuple[int, ...]]
    new_shape: Optional[Tuple[int, ...]]
    value_diff_stats: Dict[str, float]
    structural_changes: Dict[str, Any]
    significance_score: float

@dataclass
class ModelDelta:
    """Complete analysis of model changes."""
    timestamp: datetime
    tensor_deltas: Dict[str, TensorDelta]
    architecture_changes: Dict[str, Any]
    performance_impact: Dict[str, float]
    compatibility_breaks: List[str]
    summary: str

class DeltaAnalyzer:
    """Analyzes and explains changes between model versions."""
    
    def __init__(self, max_workers: int = 4):
        """Initialize the delta analyzer.
        
        Args:
            max_workers: Maximum number of parallel workers
        """
        self.max_workers = max_workers
        self._tensor_cache: Dict[str, np.ndarray] = {}
        self._graph = nx.DiGraph()  # For tracking tensor relationships
        
    def compare_tensors(self,
                       name: str,
                       old_tensor: Optional[np.ndarray],
                       new_tensor: Optional[np.ndarray]) -> TensorDelta:
        """Analyze changes between tensor versions.
        
        Args:
            name: Tensor name
            old_tensor: Previous tensor version (None if added)
            new_tensor: New tensor version (None if removed)
            
        Returns:
            Analysis of tensor changes
        """
        # Handle addition/removal cases
        if old_tensor is None:
            return TensorDelta(
                name=name,
                shape_changed=True,
                old_shape=None,
                new_shape=tuple(new_tensor.shape),
                value_diff_stats={},
                structural_changes={"type": "added"},
                significance_score=1.0
            )
        elif new_tensor is None:
            return TensorDelta(
                name=name,
                shape_changed=True,
                old_shape=tuple(old_tensor.shape),
                new_shape=None,
                value_diff_stats={},
                structural_changes={"type": "removed"},
                significance_score=1.0
            )
            
        # Analyze shape changes
        shape_changed = old_tensor.shape != new_tensor.shape
        
        # Compute value differences for same-shaped tensors
        value_diff_stats = {}
        structural_changes = {"type": "modified"}
        
        if not shape_changed:
            # Calculate basic statistics
            diff = new_tensor - old_tensor
            abs_diff = np.abs(diff)
            
            value_diff_stats.update({
                "mean_diff": float(np.mean(diff)),
                "std_diff": float(np.std(diff)),
                "max_diff": float(np.max(abs_diff)),
                "min_diff": float(np.min(abs_diff)),
                "median_diff": float(np.median(abs_diff)),
                "relative_change": float(np.mean(abs_diff / (np.abs(old_tensor) + 1e-8)))
            })
            
            # Analyze structural changes
            structural_changes.update({
                "sparsity_change": float(
                    np.mean(new_tensor == 0) - np.mean(old_tensor == 0)
                ),
                "rank_change": int(
                    np.linalg.matrix_rank(new_tensor) - 
                    np.linalg.matrix_rank(old_tensor)
                ) if len(old_tensor.shape) == 2 else 0
            })
            
        # Calculate significance score
        significance_score = self._calculate_significance(
            old_tensor,
            new_tensor,
            value_diff_stats,
            structural_changes
        )
        
        return TensorDelta(
            name=name,
            shape_changed=shape_changed,
            old_shape=tuple(old_tensor.shape),
            new_shape=tuple(new_tensor.shape),
            value_diff_stats=value_diff_stats,
            structural_changes=structural_changes,
            significance_score=significance_score
        )
        
    def _calculate_significance(self,
                              old_tensor: np.ndarray,
                              new_tensor: np.ndarray,
                              diff_stats: Dict[str, float],
                              structural_changes: Dict[str, Any]) -> float:
        """Calculate the significance of tensor changes."""
        if old_tensor.shape != new_tensor.shape:
            return 1.0  # Shape changes are maximally significant
            
        # Weight different factors
        weights = {
            "relative_change": 0.4,
            "sparsity_change": 0.2,
            "rank_change": 0.2,
            "magnitude": 0.2
        }
        
        scores = {
            "relative_change": min(1.0, diff_stats.get("relative_change", 0) * 5),
            "sparsity_change": min(1.0, abs(structural_changes.get("sparsity_change", 0)) * 2),
            "rank_change": min(1.0, abs(structural_changes.get("rank_change", 0)) / 10),
            "magnitude": min(1.0, diff_stats.get("max_diff", 0))
        }
        
        return float(sum(weights[k] * scores[k] for k in weights))
        
    def analyze_model_delta(self,
                          old_model: Dict[str, np.ndarray],
                          new_model: Dict[str, np.ndarray],
                          metadata: Optional[Dict[str, Any]] = None) -> ModelDelta:
        """Analyze changes between model versions.
        
        Args:
            old_model: Previous model state
            new_model: New model state
            metadata: Optional model metadata
            
        Returns:
            Complete model delta analysis
        """
        # Track current analysis timestamp
        timestamp = datetime.now()
        
        # Analyze tensor changes in parallel
        tensor_deltas = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            # Analyze changed and removed tensors
            for name, old_tensor in old_model.items():
                new_tensor = new_model.get(name)
                futures[executor.submit(
                    self.compare_tensors,
                    name,
                    old_tensor,
                    new_tensor
                )] = name
                
            # Analyze added tensors
            for name, new_tensor in new_model.items():
                if name not in old_model:
                    futures[executor.submit(
                        self.compare_tensors,
                        name,
                        None,
                        new_tensor
                    )] = name
                    
            # Collect results
            for future in futures:
                name = futures[future]
                tensor_deltas[name] = future.result()
                
        # Analyze architecture changes
        architecture_changes = self._analyze_architecture(
            tensor_deltas,
            metadata
        )
        
        # Estimate performance impact
        performance_impact = self._estimate_performance_impact(
            tensor_deltas,
            architecture_changes
        )
        
        # Check for compatibility breaks
        compatibility_breaks = self._check_compatibility(
            tensor_deltas,
            architecture_changes
        )
        
        # Generate human-readable summary
        summary = self._generate_summary(
            tensor_deltas,
            architecture_changes,
            performance_impact,
            compatibility_breaks
        )
        
        return ModelDelta(
            timestamp=timestamp,
            tensor_deltas=tensor_deltas,
            architecture_changes=architecture_changes,
            performance_impact=performance_impact,
            compatibility_breaks=compatibility_breaks,
            summary=summary
        )
        
    def _analyze_architecture(self,
                            tensor_deltas: Dict[str, TensorDelta],
                            metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze architectural changes in the model."""
        changes = {
            "layer_changes": [],
            "dimension_changes": [],
            "structural_changes": []
        }
        
        # Analyze layer topology
        for name, delta in tensor_deltas.items():
            if delta.shape_changed:
                changes["dimension_changes"].append({
                    "layer": name,
                    "old_shape": delta.old_shape,
                    "new_shape": delta.new_shape
                })
                
            if "removed" in delta.structural_changes.get("type", ""):
                changes["layer_changes"].append({
                    "type": "removed",
                    "layer": name
                })
            elif "added" in delta.structural_changes.get("type", ""):
                changes["layer_changes"].append({
                    "type": "added",
                    "layer": name
                })
                
        # Analyze metadata changes if provided
        if metadata:
            old_meta = metadata.get("old", {})
            new_meta = metadata.get("new", {})
            
            # Compare architecturally significant metadata
            for key in ["architecture", "vocab_size", "hidden_size", "num_layers"]:
                if old_meta.get(key) != new_meta.get(key):
                    changes["structural_changes"].append({
                        "type": "metadata",
                        "key": key,
                        "old_value": old_meta.get(key),
                        "new_value": new_meta.get(key)
                    })
                    
        return changes
        
    def _estimate_performance_impact(self,
                                   tensor_deltas: Dict[str, TensorDelta],
                                   architecture_changes: Dict[str, Any]) -> Dict[str, float]:
        """Estimate performance impact of changes."""
        impact = {
            "latency": 0.0,
            "memory": 0.0,
            "throughput": 0.0
        }
        
        # Analyze tensor size changes
        total_size_change = 0
        for delta in tensor_deltas.values():
            if delta.shape_changed and delta.old_shape and delta.new_shape:
                old_size = np.prod(delta.old_shape)
                new_size = np.prod(delta.new_shape)
                total_size_change += new_size - old_size
                
        # Estimate memory impact
        impact["memory"] = float(total_size_change / (1024 * 1024))  # MB
        
        # Estimate latency impact
        layer_changes = len(architecture_changes["layer_changes"])
        impact["latency"] = float(0.1 * layer_changes)  # Simplified estimate
        
        # Estimate throughput impact
        if impact["latency"] > 0:
            impact["throughput"] = float(-0.1 * layer_changes)  # Simplified estimate
            
        return impact
        
    def _check_compatibility(self,
                           tensor_deltas: Dict[str, TensorDelta],
                           architecture_changes: Dict[str, Any]) -> List[str]:
        """Check for backward compatibility breaks."""
        breaks = []
        
        # Check for breaking changes
        for name, delta in tensor_deltas.items():
            if delta.shape_changed:
                breaks.append(f"Shape change in {name}")
                
        # Check architecture changes
        for change in architecture_changes["structural_changes"]:
            if change["type"] == "metadata":
                breaks.append(f"Metadata change: {change['key']}")
                
        return breaks
        
    def _generate_summary(self,
                         tensor_deltas: Dict[str, TensorDelta],
                         architecture_changes: Dict[str, Any],
                         performance_impact: Dict[str, float],
                         compatibility_breaks: List[str]) -> str:
        """Generate human-readable summary of changes."""
        lines = ["Model Delta Analysis Summary:"]
        
        # Summarize significant tensor changes
        significant_changes = [
            (name, delta) for name, delta in tensor_deltas.items()
            if delta.significance_score > 0.5
        ]
        
        if significant_changes:
            lines.append("\nSignificant Tensor Changes:")
            for name, delta in significant_changes:
                lines.append(f"- {name}: {self._describe_delta(delta)}")
                
        # Summarize architecture changes
        if architecture_changes["layer_changes"]:
            lines.append("\nArchitecture Changes:")
            for change in architecture_changes["layer_changes"]:
                lines.append(f"- {change['type'].title()} layer: {change['layer']}")
                
        # Summarize performance impact
        lines.append("\nPerformance Impact:")
        for metric, value in performance_impact.items():
            if abs(value) > 0.01:
                lines.append(f"- {metric.title()}: {value:+.2f}")
                
        # List compatibility breaks
        if compatibility_breaks:
            lines.append("\nCompatibility Breaks:")
            for brk in compatibility_breaks:
                lines.append(f"- {brk}")
                
        return "\n".join(lines)
        
    def _describe_delta(self, delta: TensorDelta) -> str:
        """Generate human-readable description of tensor delta."""
        if delta.shape_changed:
            if delta.old_shape is None:
                return f"Added with shape {delta.new_shape}"
            elif delta.new_shape is None:
                return f"Removed (was {delta.old_shape})"
            else:
                return f"Shape changed from {delta.old_shape} to {delta.new_shape}"
                
        # Describe value changes
        stats = delta.value_diff_stats
        return (
            f"Values modified (mean diff: {stats['mean_diff']:.3f}, "
            f"max diff: {stats['max_diff']:.3f})"
        )