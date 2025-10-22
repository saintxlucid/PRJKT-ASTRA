# ASTRA Core API Documentation

## Overview

ASTRA Core provides a comprehensive API for managing memory, identity, and system operations. This document details the available endpoints, their parameters, and expected responses.

## API Endpoints

### Memory Operations

#### 1. Store Memory
```http
POST /api/v1/memory/store
```

Store a new memory in the specified memory system.

**Request Body:**
```json
{
    "memory_type": "semantic|episodic|procedural",
    "content": string,
    "tags": string[],
    "metadata": object
}
```

**Response:**
```json
{
    "memory_id": string,
    "status": "success|error",
    "message": string
}
```

#### 2. Retrieve Memory
```http
GET /api/v1/memory/retrieve
```

Search and retrieve memories based on query.

**Query Parameters:**
- `query` (string): Search query
- `memory_type` (string, optional): Filter by memory type
- `max_results` (number, optional): Maximum results to return
- `include_metadata` (boolean, optional): Include memory metadata

**Response:**
```json
{
    "memories": [
        {
            "id": string,
            "content": string,
            "memory_type": string,
            "relevance_score": number,
            "metadata": object
        }
    ],
    "total_count": number
}
```

### Identity Management

#### 1. Get Identity
```http
GET /api/v1/identity
```

Retrieve ASTRA's current identity configuration.

**Response:**
```json
{
    "name": string,
    "full_name": string,
    "version": string,
    "creator": string,
    "project": string,
    "essence": string,
    "personality_traits": {
        "warmth": number,
        "precision": number,
        "creativity": number,
        "formality": number,
        "verbosity": number,
        "enthusiasm": number
    }
}
```

### System Operations

#### 1. System Health
```http
GET /api/v1/system/health
```

Get system health status and metrics.

**Response:**
```json
{
    "status": "healthy|degraded|error",
    "components": {
        "memory": {
            "status": string,
            "metrics": {
                "semantic_count": number,
                "episodic_count": number,
                "procedural_count": number,
                "cache_hit_ratio": number
            }
        },
        "identity": {
            "status": string
        },
        "neural_engine": {
            "status": string
        }
    },
    "memory_usage": {
        "total": number,
        "available": number,
        "percent": number
    }
}
```

#### 2. Batch Operations
```http
POST /api/v1/batch
```

Process multiple operations in a single request.

**Request Body:**
```json
{
    "operations": [
        {
            "type": "store|retrieve",
            "memory_type": string,
            "content": any,
            "metadata": object
        }
    ]
}
```

**Response:**
```json
{
    "results": [
        {
            "operation_id": string,
            "status": "success|error",
            "result": any
        }
    ]
}
```

## WebSocket API

### Real-time Updates
```
ws://localhost:8765/ws
```

Subscribe to real-time system updates and memory operations.

**Subscribe Message:**
```json
{
    "action": "subscribe",
    "channels": ["memory", "system", "identity"]
}
```

**Update Message Format:**
```json
{
    "channel": string,
    "event_type": string,
    "timestamp": string,
    "data": any
}
```

## Error Handling

All API endpoints use standard HTTP status codes and return error details in the response body:

```json
{
    "error": {
        "code": string,
        "message": string,
        "details": object
    }
}
```

Common error codes:
- 400: Bad Request
- 401: Unauthorized
- 404: Not Found
- 500: Internal Server Error

## Rate Limiting

API endpoints are rate-limited to ensure system stability:

- Memory operations: 100 requests per minute
- System operations: 60 requests per minute
- Batch operations: 10 requests per minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1635724800
```

## Authentication

API requests must include an authentication token in the header:

```http
Authorization: Bearer <token>
```

Tokens can be obtained through the authentication endpoint:
```http
POST /api/v1/auth/token
```

## Best Practices

1. **Memory Operations**
   - Use batch operations for multiple requests
   - Include relevant tags for better retrieval
   - Set appropriate TTL for temporary memories

2. **Performance**
   - Use pagination for large result sets
   - Cache frequently accessed memories
   - Monitor rate limits and adjust accordingly

3. **Error Handling**
   - Implement proper error handling
   - Use retry logic with exponential backoff
   - Log error responses for debugging

## SDK Examples

### Python SDK
```python
from astra_core import ASTRAClient

# Initialize client
client = ASTRAClient(token="your-token")

# Store memory
memory_id = await client.store_memory(
    memory_type="semantic",
    content="Important fact to remember",
    tags=["fact", "important"]
)

# Retrieve memories
memories = await client.search_memories(
    query="important fact",
    max_results=5
)

# Batch operations
results = await client.batch_operations([
    {
        "type": "store",
        "memory_type": "episodic",
        "content": "Event occurred"
    },
    {
        "type": "retrieve",
        "memory_type": "semantic",
        "query": "search term"
    }
])
```

### JavaScript SDK
```javascript
import { ASTRAClient } from '@astra/core';

// Initialize client
const client = new ASTRAClient({ token: 'your-token' });

// Store memory
const memoryId = await client.storeMemory({
    memoryType: 'semantic',
    content: 'Important fact to remember',
    tags: ['fact', 'important']
});

// Retrieve memories
const memories = await client.searchMemories({
    query: 'important fact',
    maxResults: 5
});

// WebSocket connection
const ws = client.connectWebSocket();
ws.subscribe(['memory', 'system']);
ws.on('update', (data) => {
    console.log('Received update:', data);
});
```

## API Versioning

The API uses semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

Current version: v1.0.0

## Support

For API support and issues:
- Documentation: `/docs`
- Issues: Create a ticket in the issue tracker
- Real-time help: Join the developer Discord server

## Changelog

### v1.0.0 (2025-10-21)
- Initial release of ASTRA Core API
- Memory operations support
- Identity management
- Real-time updates via WebSocket
- Authentication and rate limiting
- Batch operations support