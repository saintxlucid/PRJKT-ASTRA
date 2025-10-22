"""Tests for specialized validators with performance optimization."""

import pytest
import numpy as np
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List

from evolution.core.validators import (
    validate_quantization,
    validate_lora_compatibility,
    validate_rope_params,
    validate_tensor_integrity
)

def test_parallel_quantization_validation(tensor_cache: Path,
                                       parallel_validator,
                                       performance_monitor):
    """Test parallel validation of tensor quantization."""
    
    def quantization_check(tensor_name: str) -> Dict[str, Any]:
        # Load tensor from cache
        tensor_path = tensor_cache / "mapped" / f"{tensor_name}.bin"
        with open(tensor_path, "rb") as f:
            tensor = np.fromfile(f, dtype=np.float32).reshape(-1, 1024)
            
        # Test different quantization targets
        results = {}
        dtypes = [np.float16, np.int8, np.int4]
        
        for dtype in dtypes:
            with performance_monitor.measure(f"quantize_{dtype}"):
                result = validate_quantization(tensor, dtype)
                results[str(dtype)] = result
                
        return {
            "passed": all(r["passed"] for r in results.values()),
            "metrics": results
        }
    
    # Run parallel validation
    tensor_names = [f"tensor_{i}" for i in range(3)]
    
    with performance_monitor.measure("parallel_quant_validation"):
        results = parallel_validator.validate_batch(
            tensor_names,
            quantization_check,
            aggregate=True
        )
    
    # Verify performance
    stats = performance_monitor.get_stats("parallel_quant_validation")
    assert stats["avg_duration"] < len(tensor_names)  # Should be faster than sequential
    assert results.passed  # All validations should pass

def test_lora_compatibility_performance(tensor_cache: Path,
                                     parallel_validator,
                                     performance_monitor):
    """Test LoRA compatibility validation performance."""
    
    def create_test_tensors() -> tuple:
        # Create base model tensors
        base_model = {}
        lora_model = {}
        
        shapes = [(1024, 1024), (2048, 512), (512, 2048)]
        for i, shape in enumerate(shapes):
            base_tensor = np.random.randn(*shape).astype(np.float32)
            lora_tensor = np.random.randn(*shape).astype(np.float16)
            
            base_model[f"layer_{i}"] = base_tensor
            lora_model[f"layer_{i}"] = lora_tensor
            
        return base_model, lora_model
    
    # Create test data
    with performance_monitor.measure("tensor_creation"):
        base_model, lora_model = create_test_tensors()
    
    # Run compatibility check with performance monitoring
    with performance_monitor.measure("lora_compatibility"):
        result = validate_lora_compatibility(base_model, lora_model)
    
    # Verify results and performance
    stats = performance_monitor.get_stats("lora_compatibility")
    assert stats["avg_duration"] < 1.0  # Should be fast
    assert result["passed"]
    assert result["shape_matches"] == len(base_model)

def test_rope_validation_gates(parallel_validator,
                             performance_monitor):
    """Test RoPE parameter validation with gates."""
    
    def create_test_configs() -> List[Dict[str, Any]]:
        configs = []
        
        # Valid config
        configs.append({
            "rope": {
                "dim": 128,
                "max_position": 4096,
                "alpha": 1.0
            },
            "tensor_shapes": {
                "rope_embeddings": (4096, 128),
                "pos_emb": (2048, 128)
            }
        })
        
        # Invalid dimension
        configs.append({
            "rope": {
                "dim": 256,
                "max_position": 4096,
                "alpha": 1.0
            },
            "tensor_shapes": {
                "rope_embeddings": (4096, 128)  # Mismatched dimension
            }
        })
        
        return configs
    
    configs = create_test_configs()
    
    def validation_gate(config: Dict) -> Dict[str, Any]:
        return validate_rope_params(
            config,
            config["tensor_shapes"]
        )
    
    # Run validations with gates
    with performance_monitor.measure("rope_validation"):
        results = parallel_validator.validate_batch(
            configs,
            validation_gate
        )
    
    # Check results
    assert len(results) == len(configs)
    assert results[0].passed  # First config should pass
    assert not results[1].passed  # Second config should fail
    
    # Verify performance
    stats = performance_monitor.get_stats("rope_validation")
    assert stats["avg_duration"] < 0.5  # Should be very fast

def test_tensor_integrity_streaming(tensor_cache: Path,
                                 parallel_validator,
                                 performance_monitor):
    """Test tensor integrity validation with streaming."""
    
    # Create test cases with metadata
    test_cases = []
    for i in range(3):
        tensor_path = tensor_cache / "mapped" / f"tensor_{i}.bin"
        with open(tensor_cache / "meta" / "cache.json", 'r') as f:
            metadata = json.load(f)
            tensor_info = metadata["tensors"][f"tensor_{i}"]
            
        test_cases.append({
            "path": tensor_path,
            "expected": {
                "shape": tensor_info["shape"],
                "dtype": tensor_info["dtype"],
                "value_range": [-5.0, 5.0]  # Example range
            }
        })
    
    def streaming_validation(case: Dict) -> Dict[str, Any]:
        # Load tensor in chunks
        with open(case["path"], "rb") as f:
            tensor = np.fromfile(f, dtype=np.dtype(case["expected"]["dtype"]))
            tensor = tensor.reshape(case["expected"]["shape"])
            
        return validate_tensor_integrity(tensor, case["expected"])
    
    # Run parallel validation
    with performance_monitor.measure("integrity_validation"):
        results = parallel_validator.validate_batch(
            test_cases,
            streaming_validation,
            aggregate=True
        )
    
    # Verify results
    assert results.passed
    
    # Check performance metrics
    stats = performance_monitor.get_stats("integrity_validation")
    memory_per_tensor = sum(
        np.prod(case["expected"]["shape"]) * 4  # Assuming float32
        for case in test_cases
    )
    
    # Verify memory efficiency
    assert stats["max_memory"] < memory_per_tensor * 1.5  # Should use less than 1.5x memory

def test_validator_stress_test(tensor_cache: Path,
                             parallel_validator,
                             performance_monitor):
    """Stress test the validation system."""
    
    # Create large test dataset
    num_tensors = 10
    shapes = [(1024, 1024), (2048, 512), (512, 2048)] * 4
    
    def create_test_tensor(shape: tuple) -> np.ndarray:
        return np.random.randn(*shape).astype(np.float32)
    
    # Create tensors in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        tensors = list(executor.map(create_test_tensor, shapes[:num_tensors]))
    
    def stress_validation(tensor: np.ndarray) -> Dict[str, Any]:
        # Run multiple validations
        results = {}
        
        # Quantization check
        results["quant"] = validate_quantization(tensor, np.float16)
        
        # Integrity check
        results["integrity"] = validate_tensor_integrity(tensor, {
            "shape": tensor.shape,
            "dtype": str(tensor.dtype),
            "value_range": [-10, 10]
        })
        
        return {
            "passed": all(r["passed"] for r in results.values()),
            "metrics": results
        }
    
    # Run stress test with progress tracking
    progress = {"completed": 0}
    
    def progress_callback(completed: int, total: int) -> None:
        progress["completed"] = completed
    
    with performance_monitor.measure("stress_test"):
        results = parallel_validator.validate_with_progress(
            tensors,
            stress_validation,
            progress_callback=progress_callback
        )
    
    # Verify results
    assert len(results) == num_tensors
    assert progress["completed"] == num_tensors
    
    # Check performance metrics
    stats = performance_monitor.get_stats("stress_test")
    assert stats["avg_duration"] / num_tensors < 1.0  # Average time per tensor
    
    # Memory efficiency check
    max_tensor_size = max(tensor.nbytes for tensor in tensors)
    assert stats["max_memory"] < max_tensor_size * parallel_validator.max_workers * 2