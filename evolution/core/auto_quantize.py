"""Auto-quantization tuning system for optimal model compression."""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import json
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor
import torch
from torch import Tensor

logger = logging.getLogger(__name__)

@dataclass
class QuantizationProfile:
    """Profile for a specific quantization configuration."""
    dtype: str
    bits: int
    scale_factor: float
    zero_point: Optional[float]
    error_metrics: Dict[str, float]
    performance_impact: float
    memory_savings: float

@dataclass
class LayerProfile:
    """Analysis of a model layer for quantization."""
    name: str
    shape: Tuple[int, ...]
    sparsity: float
    dynamic_range: float
    importance_score: float
    recommended_bits: int

class AutoQuantizationTuner:
    """Automated system for finding optimal quantization parameters."""
    
    def __init__(self, 
                 target_size_mb: float,
                 accuracy_threshold: float = 0.98,
                 max_workers: int = 4):
        """Initialize the auto-tuner.
        
        Args:
            target_size_mb: Target model size in MB
            accuracy_threshold: Minimum acceptable accuracy (0-1)
            max_workers: Maximum number of parallel workers
        """
        self.target_size_mb = target_size_mb
        self.accuracy_threshold = accuracy_threshold
        self.max_workers = max_workers
        self._profiles: Dict[str, List[QuantizationProfile]] = {}
        self._layer_analysis: Dict[str, LayerProfile] = {}
        
    def analyze_layer(self, name: str, tensor: np.ndarray) -> LayerProfile:
        """Analyze a layer for quantization characteristics.
        
        Args:
            name: Layer name
            tensor: Layer weights/bias tensor
            
        Returns:
            Layer profile with recommendations
        """
        # Calculate basic statistics
        sparsity = np.mean(tensor == 0.0)
        dynamic_range = float(np.max(tensor) - np.min(tensor))
        
        # Calculate importance score based on tensor properties
        variance = np.var(tensor)
        mean_magnitude = np.mean(np.abs(tensor))
        importance = float(variance * mean_magnitude * (1 - sparsity))
        
        # Recommend bits based on characteristics
        recommended_bits = self._recommend_bits(
            sparsity,
            dynamic_range,
            importance,
            tensor.shape
        )
        
        profile = LayerProfile(
            name=name,
            shape=tensor.shape,
            sparsity=float(sparsity),
            dynamic_range=dynamic_range,
            importance_score=importance,
            recommended_bits=recommended_bits
        )
        
        self._layer_analysis[name] = profile
        return profile
        
    def _recommend_bits(self,
                       sparsity: float,
                       dynamic_range: float,
                       importance: float,
                       shape: Tuple[int, ...]) -> int:
        """Recommend number of bits for quantization."""
        if sparsity > 0.9:
            return 4  # Highly sparse -> aggressive quantization
        elif importance > 0.8:
            return 16  # Important layer -> preserve precision
        elif dynamic_range < 1.0:
            return 8  # Small range -> moderate quantization
        else:
            return 8  # Default case
            
    def profile_quantization(self,
                           name: str,
                           tensor: np.ndarray,
                           dtypes: Optional[List[str]] = None) -> List[QuantizationProfile]:
        """Profile different quantization options for a tensor.
        
        Args:
            name: Tensor name
            tensor: Input tensor
            dtypes: Optional list of dtypes to test
            
        Returns:
            List of quantization profiles
        """
        if dtypes is None:
            dtypes = ['float16', 'int8', 'int4']
            
        profiles = []
        
        def profile_dtype(dtype: str) -> QuantizationProfile:
            # Convert dtype string to numpy dtype
            np_dtype = np.dtype(dtype)
            bits = np_dtype.itemsize * 8
            
            # Quantize tensor
            if dtype.startswith('int'):
                # Calculate scale and zero point for integer quantization
                data_range = np.max(tensor) - np.min(tensor)
                scale = data_range / (2**bits - 1)
                zero_point = -np.min(tensor) / scale
                
                quantized = np.clip(
                    np.round(tensor / scale + zero_point),
                    0,
                    2**bits - 1
                ).astype(np_dtype)
                
                # Dequantize for error calculation
                dequantized = (quantized.astype(float) - zero_point) * scale
            else:
                # Floating point quantization
                quantized = tensor.astype(np_dtype)
                dequantized = quantized.astype(tensor.dtype)
                scale = 1.0
                zero_point = None
                
            # Calculate error metrics
            mse = float(np.mean((tensor - dequantized) ** 2))
            mae = float(np.mean(np.abs(tensor - dequantized)))
            max_error = float(np.max(np.abs(tensor - dequantized)))
            
            # Calculate memory impact
            original_size = tensor.nbytes
            quantized_size = quantized.nbytes
            memory_savings = 1.0 - (quantized_size / original_size)
            
            # Estimate performance impact (simplified)
            performance_impact = 1.0 if dtype == 'float32' else (
                0.8 if dtype == 'float16' else 0.6
            )
            
            return QuantizationProfile(
                dtype=dtype,
                bits=bits,
                scale_factor=float(scale),
                zero_point=float(zero_point) if zero_point is not None else None,
                error_metrics={
                    'mse': mse,
                    'mae': mae,
                    'max_error': max_error
                },
                performance_impact=performance_impact,
                memory_savings=float(memory_savings)
            )
            
        # Profile different dtypes in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            profiles = list(executor.map(profile_dtype, dtypes))
            
        self._profiles[name] = profiles
        return profiles
        
    def optimize_model_quantization(self,
                                  tensors: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Find optimal quantization strategy for entire model.
        
        Args:
            tensors: Dictionary of named tensors
            
        Returns:
            Quantization strategy for each tensor
        """
        # Analyze all layers
        layer_profiles = {}
        for name, tensor in tensors.items():
            layer_profiles[name] = self.analyze_layer(name, tensor)
            
        # Profile quantization options
        for name, tensor in tensors.items():
            self.profile_quantization(name, tensor)
            
        # Optimize global strategy
        strategy = self._optimize_global_strategy(tensors)
        
        return {
            'quantization_strategy': strategy,
            'layer_profiles': {
                name: {
                    'sparsity': profile.sparsity,
                    'importance': profile.importance_score,
                    'recommended_bits': profile.recommended_bits
                }
                for name, profile in layer_profiles.items()
            },
            'estimated_size_mb': self._estimate_final_size(tensors, strategy) / (1024 * 1024),
            'estimated_accuracy': self._estimate_accuracy(strategy)
        }
        
    def _optimize_global_strategy(self,
                                tensors: Dict[str, np.ndarray]) -> Dict[str, str]:
        """Optimize quantization strategy across all tensors."""
        strategy = {}
        current_size = sum(t.nbytes for t in tensors.values())
        target_size = self.target_size_mb * 1024 * 1024
        
        # Sort layers by importance
        sorted_layers = sorted(
            self._layer_analysis.items(),
            key=lambda x: x[1].importance_score,
            reverse=True
        )
        
        # Assign quantization based on importance and size constraints
        remaining_size = current_size
        for name, profile in sorted_layers:
            tensor = tensors[name]
            tensor_profiles = self._profiles[name]
            
            # Find best profile that meets accuracy requirements
            valid_profiles = [
                p for p in tensor_profiles
                if self._estimate_accuracy_impact(p) >= self.accuracy_threshold
            ]
            
            if not valid_profiles:
                strategy[name] = 'float32'  # Fallback
                continue
                
            # Choose most aggressive valid quantization
            best_profile = min(
                valid_profiles,
                key=lambda p: p.bits
            )
            
            strategy[name] = best_profile.dtype
            remaining_size -= tensor.nbytes * (1 - best_profile.memory_savings)
            
        return strategy
        
    def _estimate_final_size(self,
                           tensors: Dict[str, np.ndarray],
                           strategy: Dict[str, str]) -> float:
        """Estimate final model size with strategy."""
        total_size = 0
        for name, tensor in tensors.items():
            dtype = strategy[name]
            profile = next(p for p in self._profiles[name] if p.dtype == dtype)
            total_size += tensor.nbytes * (1 - profile.memory_savings)
        return total_size
        
    def _estimate_accuracy(self, strategy: Dict[str, str]) -> float:
        """Estimate model accuracy with quantization strategy."""
        # Simple estimation based on importance-weighted average
        accuracy = 0.0
        total_importance = 0.0
        
        for name, dtype in strategy.items():
            profile = next(p for p in self._profiles[name] if p.dtype == dtype)
            layer = self._layer_analysis[name]
            
            # Weight accuracy impact by layer importance
            accuracy_impact = self._estimate_accuracy_impact(profile)
            accuracy += accuracy_impact * layer.importance_score
            total_importance += layer.importance_score
            
        return float(accuracy / total_importance if total_importance > 0 else 1.0)
        
    def _estimate_accuracy_impact(self, profile: QuantizationProfile) -> float:
        """Estimate accuracy impact of a quantization profile."""
        # Simple estimation based on error metrics
        mse_impact = 1.0 - min(1.0, profile.error_metrics['mse'] * 10)
        return float(mse_impact * profile.performance_impact)