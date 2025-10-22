# Error Handling Guide

## Overview
This guide details the error handling patterns and best practices for the ASTRA Evolution API. Understanding these patterns is crucial for building robust applications that can gracefully handle failures and edge cases.

## Error Types

### 1. AdvancedFeatureError
Base exception for all advanced feature operations.

```python
try:
    quantizer = AutoQuantizer(target_size_mb=10)
    profile = quantizer.profile_tensors(tensor_data)
except AdvancedFeatureError as e:
    logger.error(f"Quantization error: {e}")
    # Handle quantization failure
```

### 2. Validation Errors

#### Invalid Parameters
```python
# Bad Request - 400
{
    "error": "Invalid parameters",
    "details": {
        "target_size_mb": "Must be positive number",
        "min_accuracy": "Must be between 0 and 1"
    }
}
```

#### Resource Not Found
```python
# Not Found - 404
{
    "error": "Resource not found",
    "details": {
        "model_path": "Model file does not exist"
    }
}
```

### 3. Processing Errors

#### Quantization Errors
```python
# Internal Server Error - 500
{
    "error": "Quantization failed",
    "details": {
        "tensor": "weight1",
        "reason": "Insufficient dynamic range for target bits"
    },
    "trace_id": "abc123"
}
```

#### Delta Analysis Errors
```python
# Internal Server Error - 500
{
    "error": "Delta analysis failed",
    "details": {
        "stage": "structural_analysis",
        "reason": "Incompatible tensor shapes"
    },
    "trace_id": "xyz789"
}
```

## Error Recovery Strategies

### 1. Quantization Recovery
```python
def safe_quantize(tensor_data, target_size_mb, min_accuracy=0.9):
    try:
        quantizer = AutoQuantizer(
            target_size_mb=target_size_mb,
            min_accuracy=min_accuracy
        )
        return quantizer.profile_tensors(tensor_data)
    except AdvancedFeatureError:
        # Fall back to conservative quantization
        return quantizer.profile_tensors(
            tensor_data,
            force_conservative=True
        )
```

### 2. Layout Optimization Recovery
```python
def resilient_layout_optimization(model_path, access_pattern):
    try:
        optimizer = DiskLayoutOptimizer()
        return optimizer.optimize_layout(model_path, access_pattern)
    except AdvancedFeatureError as e:
        if "fragmentation" in str(e):
            # Try with defragmentation first
            optimizer.defragment(model_path)
            return optimizer.optimize_layout(model_path, access_pattern)
        raise
```

### 3. Provenance Validation Recovery
```python
def verify_provenance_chain(model_path):
    tracker = BinaryProvenanceTracker()
    try:
        return tracker.validate_provenance(model_path)
    except AdvancedFeatureError as e:
        if "checksum mismatch" in str(e):
            # Attempt to rebuild provenance from logs
            tracker.rebuild_from_logs()
            return tracker.validate_provenance(model_path)
        raise
```

## Best Practices

1. Always catch specific exceptions rather than using bare except clauses
2. Include relevant context in error messages
3. Use structured error responses with error codes and details
4. Implement appropriate fallback mechanisms
5. Log errors with sufficient context for debugging
6. Maintain idempotency in error recovery operations

## Security Considerations

### 1. Input Validation
Always validate:
- File paths (prevent path traversal)
- Numeric parameters (range checks)
- Memory limits (prevent OOM)
- Access permissions

### 2. Resource Cleanup
```python
def safe_resource_handling():
    try:
        # Acquire resources
        return process_resources()
    except Exception:
        # Clean up resources
        cleanup_resources()
        raise
    finally:
        # Always release resources
        release_resources()
```

### 3. Rate Limiting
```python
# Rate limit headers in responses
{
    "X-RateLimit-Limit": "100",
    "X-RateLimit-Remaining": "95",
    "X-RateLimit-Reset": "1635529200"
}
```

## Monitoring and Debugging

### 1. Error Tracking
```python
def track_error(error, context):
    logger.error(
        "Operation failed",
        extra={
            "error_type": type(error).__name__,
            "operation": context.get("operation"),
            "model_path": context.get("model_path"),
            "trace_id": generate_trace_id()
        }
    )
```

### 2. Performance Monitoring
```python
def monitor_operation(operation_name):
    start_time = time.time()
    try:
        result = perform_operation()
        duration = time.time() - start_time
        record_metrics(operation_name, duration, success=True)
        return result
    except Exception as e:
        duration = time.time() - start_time
        record_metrics(operation_name, duration, success=False)
        raise
```

## Example Error Scenarios and Handling

### 1. Quantization Error Handling
```python
try:
    quantizer = AutoQuantizer(target_size_mb=10)
    profile = quantizer.profile_tensors(tensor_data)
except AdvancedFeatureError as e:
    if "memory" in str(e):
        # Try with reduced precision
        profile = quantizer.profile_tensors(
            tensor_data,
            max_bits=8
        )
    elif "accuracy" in str(e):
        # Try with relaxed constraints
        profile = quantizer.profile_tensors(
            tensor_data,
            min_accuracy=0.8
        )
    else:
        raise
```

### 2. Delta Analysis Error Recovery
```python
try:
    analyzer = DeltaAnalyzer()
    report = analyzer.analyze_deltas(original, modified)
except AdvancedFeatureError as e:
    if "structural" in str(e):
        # Fall back to basic analysis
        report = analyzer.analyze_deltas(
            original,
            modified,
            skip_structural=True
        )
    else:
        raise
```

### 3. Layout Optimization Error Handling
```python
try:
    optimizer = DiskLayoutOptimizer()
    new_path = optimizer.optimize_layout(model_path, access_pattern)
except AdvancedFeatureError as e:
    if "space" in str(e):
        # Try with temporary storage
        with TemporaryStorage() as temp:
            new_path = optimizer.optimize_layout(
                model_path,
                access_pattern,
                temp_dir=temp
            )
    else:
        raise
```