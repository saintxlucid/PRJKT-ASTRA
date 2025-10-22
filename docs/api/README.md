# ASTRA Evolution API Documentation

## Overview

This document provides detailed information about using the ASTRA Evolution API for model transformation and management operations.

## Authentication

All API endpoints require authentication using an API key. Include the key in the `X-API-Key` header:

```http
X-API-Key: your-api-key-here
```

## Error Handling

All errors follow a consistent format:

```json
{
  "code": "error_code",
  "message": "Human readable error message",
  "details": {
    // Additional error context
  }
}
```

Common error codes:
- `invalid_request`: Malformed request
- `validation_failed`: Model validation failed
- `operation_failed`: Operation could not be completed
- `not_found`: Resource not found
- `unauthorized`: Invalid or missing API key

## Models

### List Models

```http
GET /api/v1/models
```

Returns a list of available models.

### Upload Model

```http
POST /api/v1/models
Content-Type: multipart/form-data

file=@model.bin
name=my-model
description=Model description
```

Upload a new model file.

### Get Model Details

```http
GET /api/v1/models/{model_id}
```

Retrieve detailed information about a specific model.

## Model Operations

### Quantization

```http
POST /api/v1/models/{model_id}/quantize
Content-Type: application/json

{
  "format": "Q4_K_M",
  "bits": 4,
  "compute_dtype": "float16",
  "strict": true
}
```

Quantize a model to a specified format.

Supported formats:
- Q4_K_M (4-bit)
- Q5_K_M (5-bit)
- Q6_K (6-bit)
- Q8_0 (8-bit)

### LoRA Merging

```http
POST /api/v1/models/{model_id}/merge-lora
Content-Type: application/json

{
  "adapter_path": "path/to/lora.bin",
  "alpha": 0.7,
  "target_modules": ["q_proj", "v_proj"]
}
```

Merge a LoRA adapter into the base model.

### Model Validation

```http
POST /api/v1/models/{model_id}/validate
Content-Type: application/json

{
  "tasks": ["perplexity", "accuracy", "drift"],
  "thresholds": {
    "perplexity_max": 10.0,
    "accuracy_min": 0.85,
    "drift_max": 0.1
  }
}
```

Validate model performance across multiple metrics.

## Snapshots

### List Snapshots

```http
GET /api/v1/models/{model_id}/snapshots
```

List all snapshots for a model.

### Rollback

```http
POST /api/v1/models/{model_id}/rollback
Content-Type: application/json

{
  "snapshot_id": "snapshot-uuid"
}
```

Rollback to a previous snapshot.

## Security Guidelines

1. API Keys:
   - Store securely
   - Rotate regularly
   - Use environment variables

2. Model Files:
   - Verify signatures
   - Check file integrity
   - Scan for malware

3. Operations:
   - Validate inputs
   - Set resource limits
   - Monitor usage

## Rate Limits

- 100 requests per minute per API key
- 10 concurrent operations per model
- Max file size: 100GB
- Max snapshot retention: 30 days

## Example Workflows

### Quantization Pipeline

1. Upload base model:
```http
POST /api/v1/models
```

2. Create pre-quantization snapshot:
```http
POST /api/v1/models/{model_id}/snapshots
```

3. Quantize model:
```http
POST /api/v1/models/{model_id}/quantize
```

4. Validate results:
```http
POST /api/v1/models/{model_id}/validate
```

5. Rollback if needed:
```http
POST /api/v1/models/{model_id}/rollback
```

### LoRA Integration

1. Upload base model
2. Validate base performance
3. Merge LoRA adapter
4. Validate merged model
5. Create snapshot if successful

## Best Practices

1. Model Management:
   - Always validate after operations
   - Keep snapshots for critical changes
   - Document model lineage

2. Performance:
   - Use appropriate batch sizes
   - Monitor resource usage
   - Cache frequent operations

3. Security:
   - Verify file signatures
   - Use secure connections
   - Follow least privilege principle

## Troubleshooting

Common issues and solutions:

1. Validation Failures:
   - Check input formats
   - Verify thresholds
   - Review error details

2. Performance Issues:
   - Monitor resource usage
   - Check operation logs
   - Review batch sizes

3. Operation Failures:
   - Verify file integrity
   - Check dependencies
   - Review error logs

## Support

For additional support:
- File issues on GitHub
- Check documentation updates
- Contact support team