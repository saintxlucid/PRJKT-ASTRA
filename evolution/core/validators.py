"""Specialized validators for model operations."""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import torch
from torch import Tensor
import json

def validate_quantization(tensor: np.ndarray,
                        target_dtype: np.dtype,
                        tolerance: float = 0.1) -> Dict[str, Any]:
    """Validate tensor quantization quality.
    
    Args:
        tensor: Original tensor
        target_dtype: Target dtype for quantization
        tolerance: Maximum allowed error
        
    Returns:
        Validation metrics
    """
    # Quantize tensor
    quantized = tensor.astype(target_dtype)
    dequantized = quantized.astype(tensor.dtype)
    
    # Compute error metrics
    mse = np.mean((tensor - dequantized) ** 2)
    mae = np.mean(np.abs(tensor - dequantized))
    max_error = np.max(np.abs(tensor - dequantized))
    
    # Compute dynamic range preservation
    orig_range = np.max(tensor) - np.min(tensor)
    quant_range = np.max(quantized) - np.min(quantized)
    range_ratio = quant_range / orig_range if orig_range != 0 else 1.0
    
    metrics = {
        "mse": float(mse),
        "mae": float(mae),
        "max_error": float(max_error),
        "range_ratio": float(range_ratio),
        "passed": mse <= tolerance
    }
    
    return metrics

def validate_lora_compatibility(
    base_model: Dict[str, np.ndarray],
    lora_model: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """Validate LoRA adapter compatibility with base model.
    
    Args:
        base_model: Base model tensors
        lora_model: LoRA model tensors
        
    Returns:
        Validation metrics
    """
    metrics = {
        "shape_matches": 0,
        "total_checks": 0,
        "missing_keys": [],
        "shape_mismatches": []
    }
    
    # Check each LoRA tensor
    for key, lora_tensor in lora_model.items():
        metrics["total_checks"] += 1
        
        if key not in base_model:
            metrics["missing_keys"].append(key)
            continue
            
        base_tensor = base_model[key]
        
        # Check shape compatibility
        if lora_tensor.shape == base_tensor.shape:
            metrics["shape_matches"] += 1
        else:
            metrics["shape_mismatches"].append({
                "key": key,
                "base_shape": base_tensor.shape,
                "lora_shape": lora_tensor.shape
            })
            
    # Compute overall compatibility
    compatibility_score = metrics["shape_matches"] / metrics["total_checks"]
    metrics["compatibility_score"] = float(compatibility_score)
    metrics["passed"] = len(metrics["missing_keys"]) == 0 and len(metrics["shape_mismatches"]) == 0
    
    return metrics

def validate_rope_params(
    config: Dict[str, Any],
    tensor_shapes: Dict[str, Tuple[int, ...]]) -> Dict[str, Any]:
    """Validate RoPE parameter configuration.
    
    Args:
        config: Model configuration
        tensor_shapes: Dictionary of tensor shapes
        
    Returns:
        Validation metrics
    """
    metrics = {
        "checks": [],
        "warnings": []
    }
    
    # Extract RoPE parameters
    rope_params = config.get("rope", {})
    dim = rope_params.get("dim", 0)
    max_position = rope_params.get("max_position", 0)
    alpha = rope_params.get("alpha", 1.0)
    
    # Validate dimensions
    for key, shape in tensor_shapes.items():
        if "rope" in key.lower() or "pos_emb" in key.lower():
            if len(shape) < 2:
                metrics["checks"].append({
                    "tensor": key,
                    "check": "dimension_count",
                    "passed": False,
                    "message": f"Expected at least 2D tensor, got {len(shape)}D"
                })
                continue
                
            # Check embedding dimension
            if shape[-1] != dim and dim != 0:
                metrics["warnings"].append(
                    f"Tensor {key} has dimension {shape[-1]}, expected {dim}"
                )
                
            # Check maximum position
            if shape[0] > max_position and max_position != 0:
                metrics["warnings"].append(
                    f"Tensor {key} has {shape[0]} positions, max_position is {max_position}"
                )
                
            metrics["checks"].append({
                "tensor": key,
                "check": "basic_compatibility",
                "passed": True
            })
            
    # Validate alpha scaling
    if alpha != 1.0:
        if alpha <= 0:
            metrics["checks"].append({
                "check": "alpha_value",
                "passed": False,
                "message": f"Invalid alpha value: {alpha}"
            })
        else:
            metrics["checks"].append({
                "check": "alpha_value",
                "passed": True
            })
            
    # Compute overall status
    failed_checks = sum(1 for c in metrics["checks"] if not c["passed"])
    metrics["passed"] = failed_checks == 0
    metrics["score"] = float(1.0 - (failed_checks / len(metrics["checks"]))) if metrics["checks"] else 0.0
    
    return metrics

def validate_tensor_integrity(
    tensor: np.ndarray,
    expected_metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Validate tensor integrity and characteristics.
    
    Args:
        tensor: Tensor to validate
        expected_metadata: Optional expected tensor properties
        
    Returns:
        Validation metrics
    """
    metrics = {
        "checks": [],
        "properties": {
            "shape": tensor.shape,
            "dtype": str(tensor.dtype),
            "has_nans": np.isnan(tensor).any(),
            "has_infs": np.isinf(tensor).any(),
            "min_value": float(np.min(tensor)),
            "max_value": float(np.max(tensor)),
            "mean": float(np.mean(tensor)),
            "std": float(np.std(tensor))
        }
    }
    
    # Basic integrity checks
    metrics["checks"].append({
        "check": "finite_values",
        "passed": not (metrics["properties"]["has_nans"] or metrics["properties"]["has_infs"])
    })
    
    # Check against expected metadata
    if expected_metadata:
        if "shape" in expected_metadata:
            metrics["checks"].append({
                "check": "shape_match",
                "passed": tensor.shape == tuple(expected_metadata["shape"]),
                "expected": expected_metadata["shape"],
                "actual": tensor.shape
            })
            
        if "dtype" in expected_metadata:
            metrics["checks"].append({
                "check": "dtype_match",
                "passed": str(tensor.dtype) == expected_metadata["dtype"],
                "expected": expected_metadata["dtype"],
                "actual": str(tensor.dtype)
            })
            
        if "value_range" in expected_metadata:
            min_val, max_val = expected_metadata["value_range"]
            metrics["checks"].append({
                "check": "value_range",
                "passed": (
                    metrics["properties"]["min_value"] >= min_val and
                    metrics["properties"]["max_value"] <= max_val
                ),
                "expected": expected_metadata["value_range"],
                "actual": [
                    metrics["properties"]["min_value"],
                    metrics["properties"]["max_value"]
                ]
            })
            
    # Compute overall status
    failed_checks = sum(1 for c in metrics["checks"] if not c["passed"])
    metrics["passed"] = failed_checks == 0
    metrics["score"] = float(1.0 - (failed_checks / len(metrics["checks"]))) if metrics["checks"] else 0.0
    
    return metrics