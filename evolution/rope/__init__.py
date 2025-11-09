"""RoPE (Rotary Position Embedding) adjustment package.

Provides tools for analyzing and tuning RoPE parameters in language models to:
- Validate position encoding behavior
- Monitor attention patterns
- Adjust scaling factors
- Extend context windows
"""

from .analyzer import RoPEAnalyzer, RoPEConfig, RoPEMetrics
from .tuner import RoPETuner, TuningResult

__all__ = [
    'RoPEAnalyzer',
    'RoPEConfig',
    'RoPEMetrics',
    'RoPETuner',
    'TuningResult'
]