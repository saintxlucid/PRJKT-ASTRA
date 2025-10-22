# ASTRA Evolution API Examples

This document provides practical examples of using the ASTRA Evolution API for common model transformation and analysis tasks.

## Auto-Quantization Examples

### Basic Quantization

Simple example of auto-tuning quantization parameters:

```python
from astra.evolution.backend.advanced import AutoQuantizer
import torch

# Load your model tensors
model_tensors = {
    "weight1": torch.randn(256, 1024),
    "weight2": torch.randn(1024, 4096)
}

# Create quantizer with target size
quantizer = AutoQuantizer(
    target_size_mb=10,
    min_accuracy=0.95
)

# Profile tensors
profile = quantizer.profile_tensors(model_tensors)

print(f"Estimated size: {profile.estimated_size_mb:.2f} MB")
print(f"Estimated accuracy: {profile.estimated_accuracy:.2%}")
print("\nBit width assignments:")
for tensor_name, bits in profile.bit_widths.items():
    print(f"{tensor_name}: {bits} bits")
```

### Advanced Quantization

Example with calibration data and sensitivity analysis:

```python
# Create calibration dataset
calibration_data = torch.randn(100, 256)  # Input samples

# Initialize quantizer with calibration
quantizer = AutoQuantizer(
    target_size_mb=10,
    min_accuracy=0.95,
    calibration_data=calibration_data
)

# Analyze tensor sensitivities
sensitivities = quantizer.analyze_sensitivities(model_tensors)

# Search for optimal profiles
profiles = quantizer.search_profiles(
    model_tensors,
    max_iterations=5
)

# Print results
print("\nQuantization profiles:")
for i, profile in enumerate(profiles):
    print(f"\nProfile {i + 1}:")
    print(f"Size: {profile.estimated_size_mb:.2f} MB")
    print(f"Accuracy: {profile.estimated_accuracy:.2%}")
```

## Delta Analysis Examples

### Basic Delta Analysis

Compare two versions of a model:

```python
from astra.evolution.backend.advanced import DeltaAnalyzer

# Original and modified tensors
original_tensors = {
    "weight1": torch.randn(256, 1024),
    "bias1": torch.randn(1024)
}

modified_tensors = {
    "weight1": original_tensors["weight1"] + 0.1 * torch.randn_like(original_tensors["weight1"]),
    "bias1": original_tensors["bias1"] * 1.5
}

# Create analyzer and analyze changes
analyzer = DeltaAnalyzer()
report = analyzer.analyze_deltas(
    original_tensors,
    modified_tensors,
    analyze_impacts=True
)

# Print report
print("\nDelta Analysis Report:")
print(f"Timestamp: {report.timestamp}")
print(f"Breaking changes: {'Yes' if report.has_breaking_changes else 'No'}")

print("\nTensor changes:")
for name, change in report.tensor_changes.items():
    print(f"{name}: {change:.2%} change")
    if name in report.impact_assessment:
        print(f"Impact: {report.impact_assessment[name]}")
```

### Advanced Delta Analysis

Detailed analysis with explanations:

```python
# Analyze with detailed explanation
report = analyzer.analyze_deltas(
    original_tensors,
    modified_tensors,
    analyze_impacts=True
)

explanations = report.generate_explanations()

print("\nDetailed Change Analysis:")
for name, explanation in explanations.items():
    print(f"\n{name}:")
    print(f"Explanation: {explanation}")
    if name in report.significant_changes:
        print(f"Significant: {'Yes' if report.significant_changes[name] else 'No'}")
```

## Layout Optimization Examples

### Basic Layout Optimization

Optimize model file layout:

```python
from astra.evolution.backend.advanced import DiskLayoutOptimizer
from pathlib import Path

# Initialize optimizer
optimizer = DiskLayoutOptimizer()

# Profile current layout
model_path = Path("path/to/model.bin")
profile = optimizer.profile_layout(model_path)

print("\nCurrent Layout Profile:")
print(f"Number of tensors: {profile.num_tensors}")
print(f"Fragmentation score: {profile.fragmentation_score:.2f}")
print(f"Estimated access time: {profile.estimated_access_time:.3f}s")
```

### Streaming Optimization

Optimize for streaming access:

```python
# Define access pattern
access_pattern = {
    "weight1": 0.5,  # Access frequency
    "weight2": 0.3,
    "bias1": 0.2
}

# Optimize layout
new_path = optimizer.optimize_layout(
    model_path,
    access_pattern
)

# Check new layout
new_profile = optimizer.profile_layout(new_path)
print("\nOptimized Layout Profile:")
print(f"Fragmentation score: {new_profile.fragmentation_score:.2f}")
print(f"Estimated access time: {new_profile.estimated_access_time:.3f}s")

# Optimize for streaming
streaming_path = optimizer.optimize_for_streaming(
    model_path,
    chunk_size_mb=1
)

streaming_profile = optimizer.profile_layout(streaming_path)
print("\nStreaming-Optimized Profile:")
print(f"Chunk-aligned: {'Yes' if streaming_profile.is_chunk_aligned else 'No'}")
print(f"Chunk size: {streaming_profile.chunk_size_mb} MB")
```

## Provenance Tracking Examples

### Basic Provenance Recording

Track model transformations:

```python
from astra.evolution.backend.advanced import BinaryProvenanceTracker

# Initialize tracker
tracker = BinaryProvenanceTracker()

# Record operations
model_path = Path("path/to/model.bin")

# Record quantization operation
record = tracker.record_operation(
    model_path=model_path,
    operation="quantize",
    params={"bits": 8}
)

print("\nProvenance Record:")
print(f"Operation: {record.operation}")
print(f"Timestamp: {record.timestamp}")
print(f"Output path: {record.output_path}")
```

### Provenance Chain Validation

Validate operation chain:

```python
# Get full provenance chain
chain = tracker.get_provenance_chain(record.output_path)

print("\nProvenance Chain:")
for r in chain:
    print(f"\nOperation: {r.operation}")
    print(f"Timestamp: {r.timestamp}")
    print(f"Parameters: {r.params}")

# Validate specific operation
is_valid = tracker.validate_provenance(
    record.output_path,
    expected_operation="quantize"
)

print(f"\nValid quantization: {'Yes' if is_valid else 'No'}")

# Query recent operations
recent_ops = tracker.query_operations(
    operation_type="quantize",
    time_range_hours=24
)

print(f"\nRecent operations: {len(recent_ops)}")
```

## Complete Workflow Example

Combining multiple features:

```python
from astra.evolution.backend.advanced import (
    AutoQuantizer,
    DeltaAnalyzer,
    DiskLayoutOptimizer,
    BinaryProvenanceTracker
)

def optimize_model(model_path: Path, target_size_mb: float):
    """Complete model optimization workflow."""
    
    # 1. Load model tensors
    model_tensors = load_tensors(model_path)
    
    # 2. Auto-quantization
    quantizer = AutoQuantizer(target_size_mb=target_size_mb)
    profile = quantizer.profile_tensors(model_tensors)
    
    # 3. Apply quantization
    quantized_tensors = apply_quantization(model_tensors, profile)
    
    # 4. Analyze changes
    analyzer = DeltaAnalyzer()
    report = analyzer.analyze_deltas(
        model_tensors,
        quantized_tensors,
        analyze_impacts=True
    )
    
    if report.has_breaking_changes:
        raise ValueError("Detected breaking changes")
        
    # 5. Optimize layout
    optimizer = DiskLayoutOptimizer()
    access_pattern = analyze_access_pattern(model_path)
    optimized_path = optimizer.optimize_layout(
        model_path,
        access_pattern
    )
    
    # 6. Record provenance
    tracker = BinaryProvenanceTracker()
    record = tracker.record_operation(
        model_path=model_path,
        operation="optimize",
        params={
            "target_size_mb": target_size_mb,
            "quantization_profile": profile,
            "layout_optimization": True
        }
    )
    
    return optimized_path, record

# Use the workflow
try:
    result_path, record = optimize_model(
        Path("model.bin"),
        target_size_mb=10
    )
    print(f"Optimization complete: {result_path}")
except Exception as e:
    print(f"Optimization failed: {e}")
```

## Security Best Practices

Always follow these security practices:

1. Validate paths and prevent path traversal:
```python
from pathlib import Path
import os

def safe_path_join(base_dir: Path, *parts):
    """Safely join paths preventing traversal."""
    path = base_dir.joinpath(*parts)
    if not str(path.resolve()).startswith(str(base_dir.resolve())):
        raise ValueError("Path traversal detected")
    return path
```

2. Handle sensitive data securely:
```python
def secure_operation(model_path: Path, api_key: str):
    """Example of secure operation handling."""
    try:
        # Validate inputs
        if not model_path.is_file():
            raise ValueError("Invalid model path")
            
        # Clear sensitive data after use
        try:
            result = perform_operation(model_path, api_key)
        finally:
            api_key = None  # Clear sensitive data
            
        return result
    except Exception:
        # Avoid leaking sensitive info in errors
        raise ValueError("Operation failed")
```

3. Use secure file operations:
```python
def safe_file_operation(path: Path):
    """Example of secure file handling."""
    import tempfile
    import shutil
    
    # Use temporary file for atomic operations
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        try:
            # Perform operations on temporary file
            process_file(tmp.name)
            
            # Atomic move to final location
            shutil.move(tmp.name, path)
        except Exception:
            # Clean up on failure
            os.unlink(tmp.name)
            raise
```

Remember to always handle errors gracefully and maintain secure coding practices throughout your implementation.