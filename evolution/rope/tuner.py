"""RoPE (Rotary Position Embedding) Tuning System.

Provides functionality for:
- Scaling RoPE parameters
- Interpolating position embeddings
- Validating modifications
- Applying optimized changes
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import torch
from .analyzer import RoPEAnalyzer, RoPEConfig, RoPEMetrics
from ..core.validators import validate_tensor_integrity


@dataclass
class TuningResult:
    """Results from RoPE tuning."""
    success: bool
    message: str
    metrics: Optional[RoPEMetrics] = None
    modified_tensors: Optional[Dict[str, torch.Tensor]] = None


class RoPETuner:
    """System for tuning RoPE parameters."""
    
    def __init__(self, model_path: Path):
        """Initialize RoPE tuner.
        
        Args:
            model_path: Path to GGUF model
        """
        self.model_path = Path(model_path)
        self.analyzer = RoPEAnalyzer(model_path)
        
    def tune_model(
        self,
        tensors: Dict[str, torch.Tensor],
        config: RoPEConfig,
        dry_run: bool = True
    ) -> TuningResult:
        """Tune RoPE parameters for the model.
        
        Args:
            tensors: Model tensors to tune
            config: RoPE tuning configuration
            dry_run: If True, validate but don't modify tensors
            
        Returns:
            Tuning results
        """
        # Copy tensors to avoid modifying originals
        modified = {k: v.clone() for k, v in tensors.items()}
        
        try:
            # Apply scaling
            modified = self._scale_rope_tensors(modified, config.target_scale)
            
            # Validate changes
            success, message = self.analyzer.analyze_rope_modification(
                tensors,
                modified,
                config
            )
            
            if not success:
                return TuningResult(False, message)
                
            # Get metrics for modified model
            metrics = self.analyzer.analyze_rope_tensors(modified)
            
            # Return results
            return TuningResult(
                success=True,
                message="RoPE tuning successful",
                metrics=metrics,
                modified_tensors=modified if not dry_run else None
            )
            
        except Exception as e:
            return TuningResult(False, f"Tuning failed: {str(e)}")
            
    def _scale_rope_tensors(
        self,
        tensors: Dict[str, torch.Tensor],
        scale: float
    ) -> Dict[str, torch.Tensor]:
        """Scale RoPE tensors by the given factor."""
        # Common RoPE tensor patterns
        rope_patterns = [
            "rope_freqs",
            "rope.freqs",
            "rotary_emb",
            "position_embeddings"
        ]
        
        # Track if we found any RoPE tensors
        found_rope = False
        
        # Scale matching tensors
        for name, tensor in tensors.items():
            if any(pattern in name.lower() for pattern in rope_patterns):
                found_rope = True
                
                # Scale the frequencies/positions
                if "freq" in name.lower():
                    # For frequency tensors, divide by scale
                    tensors[name] = tensor / scale
                else:
                    # For position embeddings, multiply by scale
                    tensors[name] = tensor * scale
                    
        if not found_rope:
            raise ValueError("No RoPE tensors found in model")
            
        return tensors
        
    def interpolate_rope(
        self,
        tensors: Dict[str, torch.Tensor],
        target_ctx: int
    ) -> Dict[str, torch.Tensor]:
        """Interpolate RoPE tensors to support longer context.
        
        Args:
            tensors: Model tensors
            target_ctx: Target context length
            
        Returns:
            Modified tensors
        """
        # Get original context length
        orig_ctx = self._get_max_position(tensors)
        
        if orig_ctx >= target_ctx:
            return tensors
            
        # Copy tensors
        modified = {k: v.clone() for k, v in tensors.items()}
        
        # Interpolate relevant tensors
        for name, tensor in modified.items():
            if self._is_rope_tensor(name):
                if len(tensor.shape) >= 1:
                    # Calculate new positions
                    orig_pos = torch.arange(tensor.shape[0])
                    new_pos = torch.linspace(0, orig_ctx-1, target_ctx)
                    
                    # Interpolate
                    modified[name] = torch.nn.functional.interpolate(
                        tensor.unsqueeze(0),
                        size=target_ctx,
                        mode='linear',
                        align_corners=True
                    ).squeeze(0)
                    
        return modified
        
    def _get_max_position(self, tensors: Dict[str, torch.Tensor]) -> int:
        """Get maximum position represented in RoPE tensors."""
        max_pos = 0
        
        for name, tensor in tensors.items():
            if self._is_rope_tensor(name):
                if len(tensor.shape) >= 1:
                    max_pos = max(max_pos, tensor.shape[0])
                    
        return max_pos
        
    def _is_rope_tensor(self, name: str) -> bool:
        """Check if tensor name matches RoPE patterns."""
        patterns = [
            "rope_freqs",
            "rope.freqs",
            "rotary_emb",
            "position_embeddings"
        ]
        return any(pattern in name.lower() for pattern in patterns)