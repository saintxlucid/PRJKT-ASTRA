"""RoPE (Rotary Position Embedding) Analysis and Tuning.

Provides tools for:
- RoPE scale validation (1.1-1.3)
- Position encoding analysis
- Attention locality preservation
- Drift monitoring
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import torch
from pathlib import Path
from ..core.advanced import DeltaAnalyzer
from ..core.validators import validate_tensor_integrity


@dataclass
class RoPEMetrics:
    """Metrics for RoPE analysis."""
    locality_score: float  # 0-1 score for attention locality preservation
    position_drift: float  # Average drift in position encodings
    attention_entropy: float  # Entropy in attention patterns
    max_effective_context: int  # Estimated max effective context length


@dataclass
class RoPEConfig:
    """Configuration for RoPE tuning."""
    target_scale: float  # Target scaling factor (1.1-1.3)
    max_position: Optional[int] = None  # Maximum position to analyze
    base_frequency: float = 10000.0  # Base frequency for rotary embeddings
    num_probe_tokens: int = 1000  # Number of tokens to use in probing
    locality_threshold: float = 0.8  # Minimum locality preservation score


class RoPEAnalyzer:
    """Analyzes and validates RoPE modifications."""
    
    # Conservative bounds for RoPE scaling
    MIN_SCALE = 1.1
    MAX_SCALE = 1.3
    
    def __init__(self, model_path: Path):
        """Initialize RoPE analyzer.
        
        Args:
            model_path: Path to GGUF model
        """
        self.model_path = Path(model_path)
        self.analyzer = DeltaAnalyzer()
        
    def analyze_rope_tensors(
        self, 
        tensors: Dict[str, torch.Tensor]
    ) -> RoPEMetrics:
        """Analyze RoPE tensors for position encoding properties.
        
        Args:
            tensors: Model tensors
            
        Returns:
            RoPE analysis metrics
        """
        # Extract position embedding tensors
        pos_emb = self._extract_position_embeddings(tensors)
        if pos_emb is None:
            raise ValueError("Could not find position embedding tensors")
            
        # Calculate locality score
        locality = self._compute_locality_score(pos_emb)
        
        # Calculate position encoding drift
        drift = self._compute_position_drift(pos_emb)
        
        # Calculate attention entropy
        entropy = self._compute_attention_entropy(tensors)
        
        # Estimate effective context
        max_ctx = self._estimate_effective_context(pos_emb, locality)
        
        return RoPEMetrics(
            locality_score=locality,
            position_drift=drift,
            attention_entropy=entropy,
            max_effective_context=max_ctx
        )
        
    def validate_scale_factor(self, scale: float) -> bool:
        """Validate RoPE scale factor is within safe bounds.
        
        Args:
            scale: Proposed scaling factor
            
        Returns:
            True if scale is valid, False otherwise
        """
        return self.MIN_SCALE <= scale <= self.MAX_SCALE
        
    def _extract_position_embeddings(
        self,
        tensors: Dict[str, torch.Tensor]
    ) -> Optional[torch.Tensor]:
        """Extract position embedding tensors."""
        # Look for common RoPE tensor names
        rope_patterns = [
            "rope_freqs",
            "rope.freqs",
            "rotary_emb",
            "position_embeddings"
        ]
        
        for pattern in rope_patterns:
            for name, tensor in tensors.items():
                if pattern in name.lower():
                    return tensor
                    
        return None
        
    def _compute_locality_score(self, pos_emb: torch.Tensor) -> float:
        """Compute attention locality preservation score (0-1).
        
        Higher score = better preservation of local attention patterns.
        """
        # Calculate pairwise distances in embedding space
        distances = torch.cdist(pos_emb, pos_emb)
        
        # Get rank correlation between position differences and embedding distances
        pos_diffs = torch.arange(pos_emb.shape[0]).unsqueeze(1) - \
                    torch.arange(pos_emb.shape[0]).unsqueeze(0)
        pos_diffs = pos_diffs.abs().float()
        
        rank_corr = self._compute_rank_correlation(
            distances.flatten(),
            pos_diffs.flatten()
        )
        
        # Scale to 0-1
        return (rank_corr + 1) / 2
        
    def _compute_position_drift(self, pos_emb: torch.Tensor) -> float:
        """Compute average drift in position encodings."""
        # Get evenly spaced reference positions
        ref_positions = torch.linspace(0, pos_emb.shape[0]-1, 100)
        ref_embeddings = pos_emb[ref_positions.long()]
        
        # Calculate average displacement
        displacements = []
        for i in range(len(ref_positions)-1):
            delta = ref_embeddings[i+1] - ref_embeddings[i]
            displacement = torch.norm(delta).item()
            displacements.append(displacement)
            
        return np.mean(displacements)
        
    def _compute_attention_entropy(
        self,
        tensors: Dict[str, torch.Tensor]
    ) -> float:
        """Compute entropy in attention patterns."""
        # Extract attention tensors
        attn_tensors = []
        for name, tensor in tensors.items():
            if any(p in name.lower() for p in ["attn", "attention"]):
                attn_tensors.append(tensor)
                
        if not attn_tensors:
            return 0.0
            
        # Calculate average attention entropy
        entropies = []
        for attn in attn_tensors:
            if len(attn.shape) >= 2:
                # Normalize attention weights
                attn_probs = torch.softmax(attn.float(), dim=-1)
                
                # Calculate entropy
                entropy = -torch.sum(
                    attn_probs * torch.log(attn_probs + 1e-10),
                    dim=-1
                ).mean().item()
                
                entropies.append(entropy)
                
        return np.mean(entropies) if entropies else 0.0
        
    def _estimate_effective_context(
        self,
        pos_emb: torch.Tensor,
        locality_score: float
    ) -> int:
        """Estimate maximum effective context length."""
        # Base estimate on embedding dimensionality and locality
        base_estimate = pos_emb.shape[0]
        
        # Scale based on locality preservation
        effective_length = int(base_estimate * locality_score)
        
        # Round to nearest power of 2
        return 2 ** int(np.log2(effective_length))
        
    def _compute_rank_correlation(
        self,
        x: torch.Tensor,
        y: torch.Tensor
    ) -> float:
        """Compute Spearman rank correlation coefficient."""
        # Get ranks
        x_rank = torch.argsort(torch.argsort(x))
        y_rank = torch.argsort(torch.argsort(y))
        
        # Calculate correlation
        n = x.shape[0]
        xy_cov = torch.sum((x_rank - x_rank.mean()) * (y_rank - y_rank.mean()))
        x_std = torch.sqrt(torch.sum((x_rank - x_rank.mean())**2))
        y_std = torch.sqrt(torch.sum((y_rank - y_rank.mean())**2))
        
        return (xy_cov / (x_std * y_std)).item()
        
    def analyze_rope_modification(
        self,
        base_tensors: Dict[str, torch.Tensor],
        modified_tensors: Dict[str, torch.Tensor],
        config: RoPEConfig
    ) -> Tuple[bool, str]:
        """Analyze impact of RoPE modifications.
        
        Args:
            base_tensors: Original model tensors
            modified_tensors: Modified model tensors
            config: RoPE configuration
            
        Returns:
            (success, message) tuple
        """
        # Validate scale factor
        if not self.validate_scale_factor(config.target_scale):
            return False, f"Invalid scale factor: {config.target_scale}"
            
        # Analyze base model
        try:
            base_metrics = self.analyze_rope_tensors(base_tensors)
        except Exception as e:
            return False, f"Failed to analyze base model: {str(e)}"
            
        # Analyze modified model
        try:
            mod_metrics = self.analyze_rope_tensors(modified_tensors)
        except Exception as e:
            return False, f"Failed to analyze modified model: {str(e)}"
            
        # Check locality preservation
        if mod_metrics.locality_score < config.locality_threshold:
            return False, (
                f"Locality score too low: {mod_metrics.locality_score:.3f} "
                f"< {config.locality_threshold}"
            )
            
        # Check position drift
        drift_increase = mod_metrics.position_drift / base_metrics.position_drift
        if drift_increase > 1.5:  # Allow up to 50% increase
            return False, f"Excessive position drift increase: {drift_increase:.2f}x"
            
        # Check attention entropy
        entropy_increase = mod_metrics.attention_entropy / base_metrics.attention_entropy
        if entropy_increase > 1.3:  # Allow up to 30% increase
            return False, f"Excessive attention entropy increase: {entropy_increase:.2f}x"
            
        # Successful validation
        return True, "RoPE modification validated successfully"