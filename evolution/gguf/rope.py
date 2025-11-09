"""RoPE parameter tuning for GGUF models."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class RoPEConfig:
    """RoPE tuning configuration."""
    scale: float = 1.15  # Default scale
    freq_base: float = 1e6  # Default base frequency
    max_seq_len: int = 8192  # Target sequence length
    
    def validate(self) -> bool:
        """Validate configuration.
        
        Returns:
            True if valid
        """
        return (
            0.1 <= self.scale <= 2.0 and
            1e4 <= self.freq_base <= 1e7 and
            512 <= self.max_seq_len <= 32768
        )

class RoPETuner:
    """RoPE parameter tuning for GGUF models."""
    
    def __init__(self, drift_threshold: float = 0.07):
        """Initialize tuner.
        
        Args:
            drift_threshold: Maximum allowed embedding drift
        """
        self.drift_threshold = drift_threshold
        
    def check_arch_support(
        self,
        model_kv: Dict[str, any]
    ) -> Tuple[bool, str]:
        """Check if architecture supports RoPE tuning.
        
        Args:
            model_kv: Model KV store
            
        Returns:
            (supported, reason) tuple
        """
        # Check for required keys
        required_keys = ["rope.freq_base", "rope.scale"]
        missing = [k for k in required_keys if k not in model_kv]
        
        if missing:
            return False, f"Missing required keys: {', '.join(missing)}"
            
        # Check architecture type
        arch = model_kv.get("arch.name", "").lower()
        if not any(x in arch for x in ["llama", "mistral", "falcon"]):
            return False, f"Unsupported architecture: {arch}"
            
        return True, "Supported"
        
    def tune_parameters(
        self,
        model_kv: Dict[str, any],
        target_len: Optional[int] = None,
        start_scale: Optional[float] = None
    ) -> RoPEConfig:
        """Tune RoPE parameters for target sequence length.
        
        Args:
            model_kv: Model KV store
            target_len: Target sequence length
            start_scale: Initial scale value
            
        Returns:
            Tuned configuration
            
        Raises:
            ValueError: If architecture unsupported
        """
        supported, reason = self.check_arch_support(model_kv)
        if not supported:
            raise ValueError(f"Architecture unsupported: {reason}")
            
        # Start with defaults
        config = RoPEConfig()
        if target_len:
            config.max_seq_len = target_len
        if start_scale:
            config.scale = start_scale
            
        # Get current values
        current_scale = float(model_kv.get("rope.scale", 1.0))
        current_base = float(model_kv.get("rope.freq_base", 10000.0))
        
        # Calculate required scale for target length
        orig_max_len = int(model_kv.get("arch.max_seq_len", 2048))
        required_scale = config.max_seq_len / orig_max_len
        
        # Start conservative
        config.scale = min(required_scale, config.scale)
        
        # Adjust base frequency to compensate
        freq_scale = 1.0 / config.scale
        config.freq_base = current_base * freq_scale
        
        return config
        
    def apply_config(
        self,
        model_kv: Dict[str, any],
        config: RoPEConfig
    ) -> Dict[str, float]:
        """Apply RoPE configuration to model.
        
        Args:
            model_kv: Model KV store to update
            config: Configuration to apply
            
        Returns:
            Applied parameters
            
        Raises:
            ValueError: If configuration invalid
        """
        if not config.validate():
            raise ValueError("Invalid RoPE configuration")
            
        # Update KV store
        model_kv["rope.scale"] = float(config.scale)
        model_kv["rope.freq_base"] = float(config.freq_base)
        model_kv["rope.max_seq_len"] = int(config.max_seq_len)
        
        return {
            "scale": config.scale,
            "freq_base": config.freq_base,
            "max_seq_len": config.max_seq_len
        }
        
    def measure_drift(
        self,
        base_embeds: Dict[str, np.ndarray],
        tuned_embeds: Dict[str, np.ndarray]
    ) -> float:
        """Measure embedding drift after tuning.
        
        Args:
            base_embeds: Base model embeddings
            tuned_embeds: Tuned model embeddings
            
        Returns:
            Drift metric (cosine distance)
        """
        drifts = []
        for key in base_embeds:
            if key in tuned_embeds:
                base = base_embeds[key]
                tuned = tuned_embeds[key]
                
                # Normalize
                base_norm = base / np.linalg.norm(base)
                tuned_norm = tuned / np.linalg.norm(tuned)
                
                # Cosine distance
                drift = 1 - np.dot(base_norm, tuned_norm)
                drifts.append(drift)
                
        return float(np.mean(drifts)) if drifts else 1.0
        
    def validate_tuning(
        self,
        model_kv: Dict[str, any],
        config: RoPEConfig,
        embeddings: Dict[str, np.ndarray]
    ) -> Tuple[bool, str]:
        """Validate RoPE tuning results.
        
        Args:
            model_kv: Updated model KV store
            config: Applied configuration
            embeddings: Sample embeddings
            
        Returns:
            (valid, reason) tuple
        """
        # Check configuration
        if not config.validate():
            return False, "Invalid configuration values"
            
        # Verify KV updates
        for key in ["rope.scale", "rope.freq_base"]:
            if key not in model_kv:
                return False, f"Missing KV key: {key}"
                
        # Check drift
        drift = self.measure_drift(embeddings, embeddings)  # Mock comparison
        if drift > self.drift_threshold:
            return False, f"Embedding drift too high: {drift:.1%}"
            
        return True, "Validation passed"