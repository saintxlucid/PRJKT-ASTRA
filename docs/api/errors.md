# Error Handling Guide

## Overview

This document describes error handling patterns and best practices for the ASTRA Evolution API.

## Error Format

All API errors follow a consistent format:

```json
{
  "code": "error_code",
  "message": "Human readable error description",
  "details": {
    "context": "Additional error context",
    "suggestion": "Suggested fix if applicable"
  }
}
```

## Standard Error Codes

### Request Validation (4xx)

- `invalid_request` (400)
  - Malformed request body/parameters
  - Missing required fields
  - Invalid field values

- `unauthorized` (401)
  - Missing API key
  - Invalid API key
  - Expired API key

- `forbidden` (403)
  - Insufficient permissions
  - Rate limit exceeded
  - Operation not allowed

- `not_found` (404)
  - Resource does not exist
  - Model/snapshot not found
  - Invalid endpoint

### Operation Failures (4xx)

- `validation_failed` (422)
  - Model validation errors
  - Format validation errors
  - Threshold validation errors

- `operation_failed` (424)
  - Quantization failed
  - LoRA merge failed
  - Snapshot creation failed

### System Errors (5xx)

- `internal_error` (500)
  - Unexpected server errors
  - Database errors
  - File system errors

- `service_unavailable` (503)
  - System overloaded
  - Maintenance mode
  - Dependency failure

## Error Handling Best Practices

### Client-Side

1. Always check response status codes
2. Parse error response body
3. Handle specific error codes appropriately
4. Implement retry logic with backoff
5. Log errors for debugging

### Example Client Error Handling:

```python
import requests
from typing import Dict, Any

class ModelAPIError(Exception):
    def __init__(self, code: str, message: str, details: Dict[str, Any]):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

def handle_api_error(response: requests.Response) -> None:
    """Handle API error responses."""
    try:
        error = response.json()
        raise ModelAPIError(
            error.get('code', 'unknown'),
            error.get('message', 'Unknown error'),
            error.get('details', {})
        )
    except ValueError:
        raise ModelAPIError(
            'parse_error',
            'Failed to parse error response',
            {'status_code': response.status_code}
        )

def api_request(method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
    """Make API request with error handling."""
    try:
        response = requests.request(method, endpoint, **kwargs)
        if response.status_code >= 400:
            handle_api_error(response)
        return response.json()
    except requests.exceptions.RequestException as e:
        raise ModelAPIError(
            'network_error',
            'Network error occurred',
            {'error': str(e)}
        )
```

### Server-Side

1. Validation:
```python
def validate_quantization_request(config: Dict[str, Any]) -> None:
    """Validate quantization configuration."""
    if 'format' not in config:
        raise ValidationError('invalid_request', 'Missing quantization format')
        
    valid_formats = {'Q4_K_M', 'Q5_K_M', 'Q6_K', 'Q8_0'}
    if config['format'] not in valid_formats:
        raise ValidationError(
            'invalid_request',
            f'Invalid quantization format. Must be one of: {valid_formats}'
        )
```

2. Operation Errors:
```python
def quantize_model(model_id: str, config: Dict[str, Any]) -> None:
    """Quantize model with error handling."""
    try:
        model = load_model(model_id)
        validate_quantization_request(config)
        create_snapshot(model)  # Backup first
        
        result = perform_quantization(model, config)
        if not validate_result(result):
            rollback_to_snapshot()
            raise OperationError(
                'validation_failed',
                'Quantized model failed validation'
            )
            
    except ModelNotFoundError:
        raise NotFoundError('not_found', f'Model {model_id} not found')
    except ResourceExhaustedError:
        raise SystemError(
            'service_unavailable',
            'System resources exhausted'
        )
```

3. System Errors:
```python
def handle_system_error(error: Exception) -> Dict[str, Any]:
    """Handle unexpected system errors."""
    error_id = log_error(error)  # Log for debugging
    
    if isinstance(error, DatabaseError):
        return {
            'code': 'internal_error',
            'message': 'Database operation failed',
            'details': {
                'error_id': error_id,
                'retry_after': 30
            }
        }
        
    return {
        'code': 'internal_error',
        'message': 'An unexpected error occurred',
        'details': {
            'error_id': error_id
        }
    }
```

## Error Recovery

### Retry Strategy

1. Implement exponential backoff:
```python
def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry operation with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except ModelAPIError as e:
            if not is_retryable(e) or attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

2. Define retryable errors:
```python
def is_retryable(error: ModelAPIError) -> bool:
    """Check if error is retryable."""
    retryable_codes = {
        'service_unavailable',
        'rate_limit_exceeded',
        'network_error'
    }
    return error.code in retryable_codes
```

### Rollback Procedures

1. Snapshot-based rollback:
```python
def safe_operation(model_id: str, operation: Callable) -> Any:
    """Perform operation with automatic rollback."""
    snapshot = create_snapshot(model_id)
    try:
        result = operation()
        validate_result(result)
        return result
    except Exception as e:
        rollback_to_snapshot(snapshot.id)
        raise OperationError(
            'operation_failed',
            f'Operation failed: {str(e)}'
        )
```

2. Transaction-like operations:
```python
def atomic_model_update(model_id: str, updates: List[Callable]) -> None:
    """Perform multiple updates atomically."""
    snapshot = create_snapshot(model_id)
    results = []
    
    try:
        for update in updates:
            result = update()
            results.append(result)
            
        if not all(validate_result(r) for r in results):
            raise ValidationError('validation_failed')
            
    except Exception as e:
        rollback_to_snapshot(snapshot.id)
        raise OperationError(
            'operation_failed',
            'Atomic update failed'
        )
```

## Monitoring and Debugging

### Error Tracking

1. Log error patterns:
```python
def log_error(error: Exception) -> str:
    """Log error with context for debugging."""
    error_id = str(uuid.uuid4())
    
    error_context = {
        'error_id': error_id,
        'timestamp': datetime.utcnow().isoformat(),
        'error_type': type(error).__name__,
        'message': str(error),
        'stack_trace': traceback.format_exc()
    }
    
    logger.error('API Error', extra=error_context)
    return error_id
```

2. Monitor error rates:
```python
def track_error_metrics(error: ModelAPIError) -> None:
    """Track error metrics for monitoring."""
    metrics.increment(f'errors.{error.code}')
    if error.code == 'validation_failed':
        metrics.increment('validation.failures')
    elif error.code.startswith('internal_'):
        metrics.increment('system.errors')
```

### Debugging Support

1. Include request context:
```python
def enrich_error_context(error: Dict[str, Any],
                        request: Any,
                        include_request_body: bool = False) -> Dict[str, Any]:
    """Add request context to error details."""
    error['details'].update({
        'request_id': request.id,
        'endpoint': request.path,
        'method': request.method,
        'client_id': request.headers.get('X-Client-ID')
    })
    
    if include_request_body and request.is_json:
        error['details']['request_body'] = request.get_json()
        
    return error
```

2. Debug mode support:
```python
def get_error_response(error: ModelAPIError, debug: bool = False) -> Dict[str, Any]:
    """Generate error response with optional debug info."""
    response = {
        'code': error.code,
        'message': error.message,
        'details': error.details
    }
    
    if debug:
        response['debug'] = {
            'stack_trace': error.stack_trace,
            'error_id': error.error_id,
            'system_info': get_system_info()
        }
        
    return response
```