"""
Sampling Configuration Presets for LLM Providers

Provides conservative, battle-tested sampling parameters to prevent gibberish output.
Includes preset configurations, stop token management, and parameter validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SamplingPreset(str, Enum):
    """Predefined sampling parameter presets"""

    VERY_CONSERVATIVE = "very_conservative"
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    CREATIVE = "creative"
    LONG_CONTEXT = "long_context"
    HIGH_QUALITY = "high_quality"
    GPTOSS_STRICT = "gptoss-strict"


@dataclass
class SamplingParameters:
    """
    Sampling parameters for LLM generation.
    
    These parameters control the randomness and creativity of model outputs.
    Conservative settings prevent gibberish and maintain coherence.
    """
    # Core sampling
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    
    # Repetition control
    repetition_penalty: float = 1.1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Advanced sampling (usually off for stability)
    min_p: float = 0.0
    typical_p: float = 1.0
    
    # Mirostat (adaptive sampling - off by default)
    mirostat: int = 0
    mirostat_tau: float = 5.0
    mirostat_eta: float = 0.1
    
    # Generation limits
    max_tokens: int = 2048
    stop: List[str] = field(default_factory=list)
    
    # Context management
    context_length: int = 8192
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API requests"""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repetition_penalty,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "min_p": self.min_p,
            "typical_p": self.typical_p,
            "mirostat": self.mirostat,
            "mirostat_tau": self.mirostat_tau,
            "mirostat_eta": self.mirostat_eta,
            "n_predict": self.max_tokens,
            "stop": self.stop,
        }

    def to_llamacpp_kwargs(self) -> Dict:
        """Return llama.cpp compatible generation arguments."""
        kwargs = self.to_dict().copy()
        kwargs["max_tokens"] = self.max_tokens
        return kwargs


class SamplingConfigFactory:
    """Factory for creating sampling configurations"""

    DEFAULT_PRESET = SamplingPreset.GPTOSS_STRICT

    # Preset configurations tested for quality and coherence
    PRESETS = {
        SamplingPreset.VERY_CONSERVATIVE: SamplingParameters(
            temperature=0.5,
            top_p=0.85,
            top_k=30,
            repetition_penalty=1.05,
            max_tokens=2048,
        ),
        SamplingPreset.CONSERVATIVE: SamplingParameters(
            temperature=0.6,
            top_p=0.9,
            top_k=40,
            repetition_penalty=1.1,
            max_tokens=2048,
        ),
        SamplingPreset.BALANCED: SamplingParameters(
            temperature=0.7,
            top_p=0.9,
            top_k=80,
            repetition_penalty=1.15,
            max_tokens=2048,
        ),
        SamplingPreset.CREATIVE: SamplingParameters(
            temperature=0.8,
            top_p=0.95,
            top_k=100,
            repetition_penalty=1.2,
            max_tokens=2048,
        ),
        SamplingPreset.LONG_CONTEXT: SamplingParameters(
            temperature=0.6,
            top_p=0.88,
            top_k=50,
            repetition_penalty=1.12,
            max_tokens=4096,
            context_length=16384,
        ),
        SamplingPreset.HIGH_QUALITY: SamplingParameters(
            temperature=0.7,
            top_p=0.92,
            top_k=60,
            repetition_penalty=1.15,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            max_tokens=2048,
        ),
        SamplingPreset.GPTOSS_STRICT: SamplingParameters(
            temperature=0.2,
            top_p=0.8,
            top_k=20,
            repetition_penalty=1.25,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            min_p=0.10,
            typical_p=1.0,
            mirostat=0,
            max_tokens=1024,
            stop=[
                "<|start_header_id|>",
                "<|end_header_id|>",
                "<|channel|>analysis<|message|>",
                "<|channel|>final<|message|>",
                "<|end|>",
                "</s>",
                "<|eot_id|>",
                "<|end_of_text|>",
            ],
            context_length=4096,
        ),
    }

    ALIASES = {
        "safe-balanced": SamplingPreset.CONSERVATIVE,
        "safe_balanced": SamplingPreset.CONSERVATIVE,
        "balanced": SamplingPreset.BALANCED,
        "strict": SamplingPreset.GPTOSS_STRICT,
        "gptoss-strict": SamplingPreset.GPTOSS_STRICT,
        "gpt_oss_strict": SamplingPreset.GPTOSS_STRICT,
    }

    @classmethod
    def _normalize_preset(cls, preset: Optional[object]) -> SamplingPreset:
        """Normalize string aliases into SamplingPreset values."""

        if isinstance(preset, SamplingPreset):
            return preset

        if isinstance(preset, str):
            normalized = preset.strip().lower().replace("_", "-")
            if normalized in cls.ALIASES:
                return cls.ALIASES[normalized]

            try:
                return SamplingPreset(normalized)
            except ValueError as exc:
                raise KeyError(f"Unknown sampling preset: {preset}") from exc

        if preset is None:
            return cls.DEFAULT_PRESET

        raise TypeError(
            f"Preset must be SamplingPreset or str, got {type(preset).__name__}"
        )

    @classmethod
    def for_preset(cls, name: str) -> SamplingParameters:
        """Return sampling parameters for preset name or raise."""
        try:
            preset = cls._normalize_preset(name)
        except Exception as exc:
            raise ValueError(f"Unknown sampling preset: {name}") from exc
        return cls.PRESETS[preset]

    @classmethod
    def create(
        cls,
        preset: Optional[object] = None,
        **overrides,
    ) -> SamplingParameters:
        """
        Create sampling parameters from preset with optional overrides.

        Args:
            preset: Predefined preset to use
            **overrides: Override specific parameters

        Returns:
            SamplingParameters instance

        Example:
            >>> params = SamplingConfigFactory.create(
            ...     preset=SamplingPreset.CONSERVATIVE,
            ...     temperature=0.65
            ... )
        """
        resolved_preset = cls._normalize_preset(preset)
        base_params = cls.PRESETS[resolved_preset]

        # Apply overrides
        params_dict = {
            "temperature": base_params.temperature,
            "top_p": base_params.top_p,
            "top_k": base_params.top_k,
            "repetition_penalty": base_params.repetition_penalty,
            "frequency_penalty": base_params.frequency_penalty,
            "presence_penalty": base_params.presence_penalty,
            "min_p": base_params.min_p,
            "typical_p": base_params.typical_p,
            "mirostat": base_params.mirostat,
            "mirostat_tau": base_params.mirostat_tau,
            "mirostat_eta": base_params.mirostat_eta,
            "max_tokens": base_params.max_tokens,
            "stop": base_params.stop.copy(),
            "context_length": base_params.context_length,
        }

        params_dict.update(overrides)

        return SamplingParameters(**params_dict)
    
    @classmethod
    def for_reasoning_mode(cls, mode: str) -> SamplingParameters:
        """
        Get sampling parameters for reasoning mode.
        
        Args:
            mode: Reasoning mode (low, medium, high)
            
        Returns:
            SamplingParameters for the mode
        """
        mode_map = {
            "low": SamplingPreset.GPTOSS_STRICT,
            "medium": SamplingPreset.GPTOSS_STRICT,
            "high": SamplingPreset.CREATIVE,
        }
        
        preset = mode_map.get(mode.lower(), cls.DEFAULT_PRESET)
        return cls.create(preset)


class StopTokenManager:
    """Manages stop tokens for different chat formats"""
    
    # Common stop tokens across formats
    COMMON_STOP_TOKENS = [
        "</s>",                      # Standard EOS
        "<|end_of_text|>",           # GPT-4 style
        "<|eot_id|>",                # Llama 3 style
    ]
    
    # Harmony format stop tokens
    HARMONY_STOP_TOKENS = [
        "<|start_header_id|>",       # Prevent continuing to next header
        "<|end_header_id|>",         # Prevent malformed headers
        "</s>",
        "<|eot_id|>",
        "<|end_of_text|>",
    ]
    
    # Simple chat format stop tokens
    SIMPLE_STOP_TOKENS = [
        "</s>",
        "\nUser:",                   # Prevent model from continuing conversation
        "\nSystem:",                 # Prevent system impersonation
        "\n\nUser:",                 # With whitespace variants
        "\n\nSystem:",
    ]
    
    # Channel-specific stop tokens (for Harmony)
    CHANNEL_STOP_TOKENS = {
        "analysis": [
            "<|start_header_id|>assistant|final<|end_header_id|>",
            "<|channel|>final<|message|>",
        ],
        "final": [
            "<|start_header_id|>user<|end_header_id|>",
            "<|start_header_id|>assistant|analysis<|end_header_id|>",
        ],
    }
    
    @classmethod
    def get_stop_tokens(
        cls,
        format_type: str = "harmony",
        channel: Optional[str] = None,
        additional: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get appropriate stop tokens for format and channel.
        
        Args:
            format_type: "harmony", "simple", or "common"
            channel: Optional channel name for Harmony format
            additional: Additional stop tokens to include
            
        Returns:
            List of stop tokens
        """
        if format_type == "harmony":
            tokens = cls.HARMONY_STOP_TOKENS.copy()
            if channel and channel in cls.CHANNEL_STOP_TOKENS:
                tokens.extend(cls.CHANNEL_STOP_TOKENS[channel])
        elif format_type == "simple":
            tokens = cls.SIMPLE_STOP_TOKENS.copy()
        else:
            tokens = cls.COMMON_STOP_TOKENS.copy()
        
        if additional:
            tokens.extend(additional)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        
        return unique_tokens

    @classmethod
    def harmony_stops(cls) -> List[str]:
        """Return default Harmony stop tokens."""
        return cls.get_stop_tokens("harmony")
    
    @classmethod
    def validate_stop_tokens(cls, tokens: List[str]) -> bool:
        """
        Validate stop token list.
        
        Args:
            tokens: List of stop tokens
            
        Returns:
            True if valid, False otherwise
        """
        if not tokens:
            return False
        
        # Check for common issues
        for token in tokens:
            # Empty strings
            if not token or not token.strip():
                return False
            
            # Tokens that are too short (likely mistakes)
            if len(token) < 2:
                return False
        
        return True


class ParameterValidator:
    """Validates sampling parameters"""
    
    @staticmethod
    def validate_temperature(temp: float) -> None:
        """Validate temperature parameter"""
        if not 0.0 <= temp <= 2.0:
            raise ValueError(f"Temperature must be between 0.0 and 2.0, got {temp}")
        
        if temp > 1.2:
            import warnings
            warnings.warn(
                f"Temperature {temp} is very high and may produce gibberish. "
                "Consider values between 0.6-0.9 for quality."
            )
    
    @staticmethod
    def validate_top_p(top_p: float) -> None:
        """Validate top_p parameter"""
        if not 0.0 <= top_p <= 1.0:
            raise ValueError(f"top_p must be between 0.0 and 1.0, got {top_p}")
    
    @staticmethod
    def validate_top_k(top_k: int) -> None:
        """Validate top_k parameter"""
        if top_k < 0:
            raise ValueError(f"top_k must be non-negative, got {top_k}")
        
        if top_k > 200:
            import warnings
            warnings.warn(
                f"top_k {top_k} is very high. "
                "Consider values between 40-100 for better quality."
            )
    
    @staticmethod
    def validate_repetition_penalty(penalty: float) -> None:
        """Validate repetition penalty"""
        if not 1.0 <= penalty <= 2.0:
            raise ValueError(
                f"repetition_penalty should be between 1.0 and 2.0, got {penalty}"
            )
    
    @classmethod
    def validate_all(cls, params: SamplingParameters) -> None:
        """Validate all parameters"""
        cls.validate_temperature(params.temperature)
        cls.validate_top_p(params.top_p)
        cls.validate_top_k(params.top_k)
        cls.validate_repetition_penalty(params.repetition_penalty)
        
        # Validate stop tokens
        if params.stop and not StopTokenManager.validate_stop_tokens(params.stop):
            raise ValueError("Invalid stop tokens")


# Export preset recommendations
RECOMMENDED_PRESETS = {
    "default": SamplingPreset.GPTOSS_STRICT,
    "chat": SamplingPreset.GPTOSS_STRICT,
    "creative_writing": SamplingPreset.CREATIVE,
    "code_generation": SamplingPreset.VERY_CONSERVATIVE,
    "long_documents": SamplingPreset.LONG_CONTEXT,
    "high_stakes": SamplingPreset.HIGH_QUALITY,
}


def get_recommended_preset(use_case: str) -> SamplingPreset:
    """
    Get recommended preset for use case.
    
    Args:
        use_case: Use case name
        
    Returns:
        Recommended SamplingPreset
    """
    return RECOMMENDED_PRESETS.get(
        use_case.lower(),
        SamplingPreset.BALANCED
    )
