"""RoPE tuning integration for model evolution.

Provides high-level integration of RoPE analysis and tuning within the
model evolution pipeline.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import torch
import logging
from .rope import (
    RoPEAnalyzer,
    RoPEConfig,
    RoPEMetrics,
    RoPETuner,
    TuningResult
)
from .core.advanced import DeltaAnalyzer
from .core.validators import validate_tensor_integrity
from .core.instrumentation import ModelInstrumentationData


@dataclass
class RoPETuningMetrics:
    """Combined metrics from RoPE tuning."""
    original_metrics: RoPEMetrics
    tuned_metrics: RoPEMetrics
    relative_improvement: float  # % improvement in effective context
    locality_preservation: float  # % preservation of local patterns
    stability_score: float  # 0-1 score for numerical stability


class RoPEEvolutionManager:
    """Manages RoPE tuning within model evolution pipeline."""
    
    # Logger for tuning operations
    logger = logging.getLogger("rope_evolution")
    
    def __init__(self, workspace_path: Path):
        """Initialize RoPE evolution manager.
        
        Args:
            workspace_path: Path to model workspace
        """
        self.workspace = Path(workspace_path)
        self.tuners: Dict[str, RoPETuner] = {}
        
    def configure_tuning(
        self,
        model_id: str,
        config: RoPEConfig
    ) -> None:
        """Configure RoPE tuning for a model.
        
        Args:
            model_id: Unique model identifier
            config: RoPE tuning configuration
        """
        model_path = self.workspace / f"{model_id}.bin"
        self.tuners[model_id] = RoPETuner(model_path)
        self.logger.info(
            f"Configured RoPE tuning for {model_id} "
            f"with scale={config.target_scale}"
        )
        
    def analyze_model(
        self,
        model_id: str,
        tensors: Dict[str, torch.Tensor]
    ) -> RoPEMetrics:
        """Analyze RoPE parameters of a model.
        
        Args:
            model_id: Model identifier
            tensors: Model tensors
            
        Returns:
            Analysis metrics
        """
        tuner = self._get_tuner(model_id)
        return tuner.analyzer.analyze_rope_tensors(tensors)
        
    def tune_model(
        self,
        model_id: str,
        tensors: Dict[str, torch.Tensor],
        instrumentation: Optional[ModelInstrumentationData] = None
    ) -> Tuple[Dict[str, torch.Tensor], RoPETuningMetrics]:
        """Tune RoPE parameters for a model.
        
        Args:
            model_id: Model identifier
            tensors: Model tensors
            instrumentation: Optional model instrumentation data
            
        Returns:
            (modified tensors, tuning metrics)
        """
        tuner = self._get_tuner(model_id)
        
        # Get original metrics
        orig_metrics = tuner.analyzer.analyze_rope_tensors(tensors)
        
        # Apply tuning
        result = tuner.tune_model(tensors, tuner.analyzer.config, dry_run=False)
        
        if not result.success:
            raise ValueError(f"RoPE tuning failed: {result.message}")
            
        # Get tuned metrics
        tuned_metrics = result.metrics
        
        # Calculate improvement metrics
        rel_improvement = (
            (tuned_metrics.max_effective_context -
             orig_metrics.max_effective_context) /
            orig_metrics.max_effective_context
        )
        
        locality_preservation = (
            tuned_metrics.locality_score /
            orig_metrics.locality_score
        )
        
        # Calculate stability from instrumentation if available
        if instrumentation:
            stability = self._compute_stability_score(
                instrumentation,
                result.modified_tensors
            )
        else:
            stability = 1.0  # Assume stable if no instrumentation
            
        # Combine metrics
        metrics = RoPETuningMetrics(
            original_metrics=orig_metrics,
            tuned_metrics=tuned_metrics,
            relative_improvement=rel_improvement,
            locality_preservation=locality_preservation,
            stability_score=stability
        )
        
        self.logger.info(
            f"Tuned {model_id} RoPE parameters: "
            f"ctx +{rel_improvement*100:.1f}%, "
            f"locality {locality_preservation*100:.1f}%, "
            f"stability {stability:.3f}"
        )
        
        return result.modified_tensors, metrics
        
    def validate_tuning(
        self,
        model_id: str,
        tensors: Dict[str, torch.Tensor],
        metrics: RoPETuningMetrics
    ) -> bool:
        """Validate RoPE tuning results.
        
        Args:
            model_id: Model identifier
            tensors: Tuned tensors
            metrics: Tuning metrics
            
        Returns:
            True if valid, False otherwise
        """
        # Check improvement threshold
        if metrics.relative_improvement < 0.1:  # At least 10% improvement
            self.logger.warning(
                f"Insufficient context improvement for {model_id}: "
                f"{metrics.relative_improvement*100:.1f}%"
            )
            return False
            
        # Check locality preservation
        if metrics.locality_preservation < 0.8:  # At most 20% degradation
            self.logger.warning(
                f"Excessive locality degradation for {model_id}: "
                f"{metrics.locality_preservation*100:.1f}%"
            )
            return False
            
        # Check stability
        if metrics.stability_score < 0.9:  # At least 0.9 stability
            self.logger.warning(
                f"Insufficient stability for {model_id}: "
                f"{metrics.stability_score:.3f}"
            )
            return False
            
        # Validate tensor integrity
        try:
            validate_tensor_integrity(tensors)
        except Exception as e:
            self.logger.error(f"Tensor integrity check failed for {model_id}: {e}")
            return False
            
        self.logger.info(f"Validated RoPE tuning for {model_id}")
        return True
        
    def _get_tuner(self, model_id: str) -> RoPETuner:
        """Get tuner for model, raising if not configured."""
        try:
            return self.tuners[model_id]
        except KeyError:
            raise ValueError(f"RoPE tuning not configured for {model_id}")
            
    def _compute_stability_score(
        self,
        instrumentation: ModelInstrumentationData,
        tuned_tensors: Dict[str, torch.Tensor]
    ) -> float:
        """Compute numerical stability score from instrumentation data."""
        # Get gradient stats
        grad_mean = torch.stack([
            t.grad.abs().mean() 
            for t in instrumentation.param_stats.values()
            if t.grad is not None
        ]).mean().item()
        
        # Get activation stats  
        act_mean = torch.stack([
            t.abs().mean()
            for t in instrumentation.activation_stats.values()
        ]).mean().item()
        
        # Score based on reasonable ranges for gradients/activations
        grad_score = 1.0 / (1.0 + grad_mean)  # Lower grads = higher score
        act_score = 1.0 / (1.0 + abs(1.0 - act_mean))  # Act mean near 1 = high score
        
        return min(grad_score, act_score)