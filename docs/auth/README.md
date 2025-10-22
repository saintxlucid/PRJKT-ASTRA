# Authentication & Multi-User System Documentation

## Overview

The ASTRA authentication and multi-user system provides secure, isolated environments for each user with features including:

- JWT-based session management
- Role-based access control (RBAC)
- Per-user memory isolation
- Memory quotas and rate limiting
- Persistent storage with SQLite
- Comprehensive metrics and monitoring

## Configuration

### Environment Variables

```env
# Memory Quotas
ASTRA_MAX_KEYS_PER_USER=1000        # Maximum number of memory keys per user
ASTRA_MAX_VALUE_SIZE_BYTES=1048576   # Maximum size of a single value (1MB)
ASTRA_MAX_TOTAL_SIZE_BYTES=10485760  # Maximum total memory per user (10MB)

# Database
ASTRA_MEMORY_DB_PATH=data/memory.db  # Path to SQLite database
```

### Default Values

If environment variables are not set, the system uses these defaults:

- Max keys per user: 1,000
- Max value size: 1MB
- Max total size per user: 10MB
- Database path: "data/memory.db"

## Architecture

### Core Components

1. Memory Isolation (`isolation.py`)
   - In-memory cache with SQLite persistence
   - Per-user memory segregation
   - Thread-safe operations with locks
   - Lazy loading of user data
   - Metrics for all operations

2. Quota Management (`quota.py`)
   - Key count limits
   - Value size limits
   - Total memory limits
   - Usage tracking
   - Quota violation metrics

3. Persistence Layer (`persistence.py`)
   - SQLite-based storage
   - Async operations
   - Transaction support
   - Automatic schema management
   - Operation metrics

4. FastAPI Middleware (`middleware.py`)
   - Automatic user context injection
   - Memory isolation integration
   - JWT token extraction
   - Custom extractor support

### Security Features

1. Memory Isolation
   - Complete separation of user memory spaces
   - No cross-user access possible
   - Quota enforcement per user

2. Resource Protection
   - Memory quotas prevent DoS
   - Rate limiting per user
   - Value size restrictions

3. Access Control
   - JWT token validation
   - Role-based permissions
   - Scope-based access

## Usage Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from astra.auth.middleware import MemoryIsolationMiddleware
from astra.auth.isolation import memory_isolation

app = FastAPI()
app.add_middleware(MemoryIsolationMiddleware)

@app.post("/memory/{key}")
async def store_memory(key: str, value: dict, user_id: str):
    await memory_isolation.set_user_memory(user_id, key, value)
    return {"status": "success"}
```

### Custom User ID Extraction

```python
def custom_user_extractor(request: Request) -> str:
    # Extract user ID from custom header
    user_id = request.headers.get("X-Custom-User")
    if not user_id:
        raise ValueError("No user ID found")
    return user_id

app.add_middleware(
    MemoryIsolationMiddleware,
    user_id_extractor=custom_user_extractor
)
```

## Metrics & Monitoring

### Prometheus Metrics

1. Memory Operations
   - `astra_memory_isolation_errors_total`: Error count by type
   - `astra_memory_access_latency_seconds`: Operation latency histogram

2. Quota Tracking
   - `astra_memory_quota_exceeded_total`: Quota violations by user
   - `astra_memory_usage_bytes`: Current memory usage per user

3. Persistence
   - `astra_memory_persistence_errors_total`: Storage errors by type
   - `astra_memory_persistence_latency_seconds`: Storage operation latency

### Logging

Structured logging with `structlog` provides:

- Operation timestamps
- User context
- Error details
- Performance metrics

## Database Schema

```sql
CREATE TABLE user_memory (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, key)
);

CREATE INDEX idx_user_memory_user ON user_memory(user_id);
```

## Performance Considerations

1. Memory Management
   - Lazy loading reduces startup time
   - In-memory cache for fast access
   - Write-through caching for persistence

2. Database Optimization
   - Indexed queries for fast lookups
   - Connection pooling
   - Async operations

3. Concurrency
   - Per-user locks prevent race conditions
   - Granular locking for better throughput
   - Transaction support for data integrity

## Testing

### Unit Tests

- `test_quota.py`: Quota management tests
- `test_persistence.py`: Storage layer tests
- `test_memory_isolation_e2e.py`: End-to-end tests

### Integration Tests

Tests cover:

- CRUD operations
- Concurrent access
- Error handling
- Quota enforcement
- User isolation

## Best Practices

1. Memory Management
   - Always use quotas to prevent abuse
   - Clear user memory when sessions end
   - Monitor usage patterns

2. Error Handling
   - Handle quota violations gracefully
   - Provide clear error messages
   - Log all errors with context

3. Performance
   - Use lazy loading when possible
   - Monitor operation latencies
   - Set appropriate quota limits

4. Security
   - Validate user tokens
   - Check permissions
   - Enforce rate limits

## Common Issues

### Quota Exceeded

```python
try:
    await memory_isolation.set_user_memory(user_id, key, value)
except ValueError as e:
    if "quota exceeded" in str(e):
        # Handle quota violation
```

### Database Initialization

```python
# Ensure database is initialized
await memory_isolation.ensure_initialized()
```

### Race Conditions

```python
async with memory_isolation._get_user_lock(user_id):
    # Perform atomic operations
```

## Future Enhancements

Planned improvements:

1. Backup/recovery system
2. Memory cleanup jobs
3. Quota adjustment API
4. Enhanced monitoring
5. Performance optimizations
