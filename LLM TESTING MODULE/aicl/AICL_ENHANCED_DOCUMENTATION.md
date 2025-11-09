# AICL - AI Interchange Chat Language (Enhanced Version)

## Overview

AICL is a lightweight, efficient communication protocol designed for LLM-to-LLM interactions. This enhanced version includes advanced features for production use including enhanced error handling, message persistence, advanced security, and comprehensive monitoring.

## Enhanced Features

### 1. Enhanced Error Handling

The enhanced AICL includes a comprehensive error handling system with standardized error codes and structured error reporting.

#### Key Components:
- `AICLError`: Base exception class with standardized error codes
- `AICLErrorCode`: Enum of standardized error codes
- `AICLValidationError`: Specific exception for validation errors
- `AICLSecurityError`: Specific exception for security-related errors
- `AICLNetworkError`: Specific exception for network-related errors
- `handle_exception`: Utility to convert standard exceptions to AICLError

#### Usage Example:
```python
from aicl import AICLError, AICLErrorCode, handle_exception

try:
    # Some operation that might fail
    process_message(msg)
except Exception as e:
    # Convert to standardized AICLError
    aicl_error = handle_exception(e)
    print(f"Error {aicl_error.code.value}: {aicl_error.message}")
```

### 2. Message Persistence and Recovery

The enhanced AICL includes robust message persistence with SQLite-based storage and recovery mechanisms.

#### Key Components:
- `MessageStore`: Persistent storage for AICL messages
- `MessageRecovery`: Recovery mechanisms for failed or lost messages

#### Features:
- SQLite-based persistent storage
- Message status tracking (pending, processed, failed)
- Retry mechanisms for failed messages
- Cleanup of old messages
- Statistics and monitoring

#### Usage Example:
```python
from aicl import MessageStore, MessageRecovery

# Create message store
store = MessageStore("messages.db")

# Store a message
store.store_message(msg)

# Update message status
store.update_message_status(msg_id, "processed")

# Get pending messages
pending = store.get_pending_messages("recipient")

# Create recovery mechanism
recovery = MessageRecovery(store)
retried = recovery.retry_failed_messages()
```

### 3. Advanced Security Features

The enhanced AICL includes comprehensive security features including message integrity, replay protection, rate limiting, and access control.

#### Key Components:
- `MessageIntegrity`: Message signing and verification utilities
- `ReplayProtection`: Protection against message replay attacks
- `RateLimiter`: Advanced rate limiting with multiple strategies
- `AccessControl`: Access control and authorization
- `SecurityManager`: Centralized security management

#### Features:
- HMAC-SHA256 message signing and verification
- Replay attack detection
- Multi-tier rate limiting (per-minute, per-hour)
- Access control lists
- Centralized security management

#### Usage Example:
```python
from aicl import SecurityManager

# Create security manager
security = SecurityManager(secret_key=b"my_secret_key")

# Sign a message
signed_msg = security.sign_message(msg)

# Validate a message
try:
    security.validate_message(msg)
    print("Message is valid")
except AICLSecurityError as e:
    print(f"Security error: {e.message}")
```

### 4. Monitoring and Observability

The enhanced AICL includes comprehensive monitoring and observability features for production environments.

#### Key Components:
- `MetricsCollector`: Collect and manage system metrics
- `HealthChecker`: System health monitoring
- `EventLogger`: Structured event logging
- `PerformanceMonitor`: System performance monitoring
- `AICLObserver`: Main observer combining all monitoring features

#### Features:
- Real-time metric collection
- Health checks with customizable checks
- Structured event logging with severity levels
- Performance monitoring with timing statistics
- Comprehensive system status reporting

#### Usage Example:
```python
from aicl import AICLObserver

# Create observer
observer = AICLObserver()

# Record message processing
observer.record_message_processed("ask", 15.2, True)

# Record connection event
observer.record_connection_event("established", "127.0.0.1:5555", True)

# Get system status
status = observer.get_system_status()
print(status)
```

## Module Structure

```
aicl/
├── __init__.py                 # Main package exports
├── core/                       # Core message handling
├── transport.py                # Network transport layer
├── aicl_logging.py             # Conversation logging and replay
├── guardrails.py               # Security and policy enforcement
├── config.py                   # Configuration management
├── streaming.py                # Streaming support for large payloads
├── routing.py                  # Message routing and broker system
├── compression.py              # Payload compression utilities
├── benchmark.py                # Performance benchmarking tools
├── async_transport.py          # Async version of transport layer
├── error_handling.py           # Enhanced error handling
├── persistence.py              # Message persistence and recovery
├── security.py                 # Advanced security features
├── monitoring.py               # Monitoring and observability
├── advanced_example.py         # Advanced features demonstration
├── comprehensive_example.py    # All features demonstration
└── examples.py                 # Basic usage examples
```

## API Reference

### Enhanced Error Handling
- `AICLError`: Base exception class with standardized error codes
- `AICLErrorCode`: Enum of standardized error codes
- `AICLValidationError`: Specific exception for validation errors
- `AICLSecurityError`: Specific exception for security-related errors
- `AICLNetworkError`: Specific exception for network-related errors
- `handle_exception`: Utility to convert standard exceptions to AICLError

### Message Persistence
- `MessageStore`: Persistent storage for AICL messages
  - `store_message(msg)`: Store a message
  - `update_message_status(msg_id, status)`: Update message status
  - `get_pending_messages(to_addr)`: Get pending messages for recipient
  - `get_message_by_id(msg_id)`: Get specific message by ID
  - `delete_message(msg_id)`: Delete a message
  - `get_message_stats()`: Get message statistics
  - `cleanup_old_messages(days_old)`: Delete old messages
- `MessageRecovery`: Recovery mechanisms for failed messages
  - `retry_failed_messages(max_retries)`: Retry failed messages
  - `recover_incomplete_conversations()`: Recover incomplete conversations

### Advanced Security
- `MessageIntegrity`: Message signing and verification
  - `create_signature(msg, secret_key)`: Create HMAC signature
  - `verify_signature(msg, secret_key)`: Verify message signature
- `ReplayProtection`: Replay attack protection
  - `is_replay(msg)`: Check if message is replay
- `RateLimiter`: Rate limiting
  - `is_allowed(sender_id, ...)`: Check if request is allowed
  - `get_current_usage(sender_id)`: Get current usage statistics
- `AccessControl`: Access control
  - `add_allowed_sender(sender_id)`: Add allowed sender
  - `add_allowed_receiver(receiver_id)`: Add allowed receiver
  - `set_sender_permissions(sender_id, permissions)`: Set sender permissions
  - `is_authorized(msg)`: Check if message is authorized
- `SecurityManager`: Centralized security management
  - `validate_message(msg, policy)`: Validate message
  - `sign_message(msg)`: Sign message with HMAC

### Monitoring and Observability
- `MetricsCollector`: Metric collection
  - `record_metric(name, value, tags)`: Record a metric
  - `get_metrics(name)`: Get metrics
  - `get_metrics_summary()`: Get metrics summary
- `HealthChecker`: Health monitoring
  - `register_health_check(name, check_func)`: Register health check
  - `run_health_checks()`: Run all health checks
  - `get_system_health()`: Get system health
- `EventLogger`: Event logging
  - `log_event(event_type, message, severity, details)`: Log event
  - `get_events(event_type, severity)`: Get events
  - `get_recent_events(count)`: Get recent events
- `PerformanceMonitor`: Performance monitoring
  - `record_operation_timing(operation_name, duration_ms, success)`: Record timing
  - `get_performance_stats(operation_name)`: Get performance stats
  - `get_all_performance_stats()`: Get all performance stats
- `AICLObserver`: Main observer
  - `record_message_processed(message_type, duration_ms, success)`: Record message
  - `record_connection_event(event_type, peer, success)`: Record connection
  - `get_system_status()`: Get complete system status

## Usage Examples

### Basic Message Handling with Enhanced Features
```python
from aicl import new_msg, SecurityManager, MessageStore, AICLObserver

# Create components
security = SecurityManager(secret_key=b"my_key")
store = MessageStore("messages.db")
observer = AICLObserver()

# Create and sign message
msg = new_msg(
    frm="sender",
    to="receiver",
    act="ask",
    payload={"text": {"content": "Hello, world!"}}
)

signed_msg = security.sign_message(msg)

# Store message
store.store_message(signed_msg)

# Record processing
observer.record_message_processed("ask", 12.5, True)
```

### Advanced Server with Full Feature Set
```python
from aicl import (
    run_server, new_msg, SecurityManager, MessageStore, 
    MessageRecovery, AICLObserver, AICLError
)

class AdvancedHandler:
    def __init__(self):
        self.security = SecurityManager(secret_key=b"server_key")
        self.store = MessageStore("server_messages.db")
        self.recovery = MessageRecovery(self.store)
        self.observer = AICLObserver()
    
    def handle_message(self, msg):
        start_time = time.time()
        
        try:
            # Security validation
            self.security.validate_message(msg)
            
            # Store message
            self.store.store_message(msg)
            
            # Process message
            response = self.process_message(msg)
            
            # Update status
            self.store.update_message_status(msg["id"], "processed")
            
            # Record success
            duration = (time.time() - start_time) * 1000
            self.observer.record_message_processed(msg["act"], duration, True)
            
            return [response]
            
        except AICLError as e:
            # Record error
            duration = (time.time() - start_time) * 1000
            self.observer.record_message_processed(msg["act"], duration, False)
            
            # Create error response
            error_msg = new_msg(
                frm="server",
                to=msg["from"],
                act="error",
                payload={"error": e.to_dict()}
            )
            
            return [self.security.sign_message(error_msg)]

# Run server
handler = AdvancedHandler()
run_server("127.0.0.1", 5555, handler.handle_message)
```

## Best Practices

### 1. Error Handling
- Always use AICLError for consistent error reporting
- Handle specific error types when possible
- Log errors with appropriate detail levels
- Provide meaningful error messages to users

### 2. Security
- Always sign messages in production environments
- Use strong secret keys for HMAC signing
- Implement appropriate rate limiting
- Regularly rotate secret keys
- Monitor for suspicious activity

### 3. Persistence
- Regularly clean up old messages to prevent database bloat
- Implement backup strategies for message databases
- Monitor storage usage
- Use appropriate transaction handling

### 4. Monitoring
- Monitor key metrics like message processing time
- Set up alerts for critical errors
- Regularly review health check results
- Track performance trends over time

## Testing

The enhanced AICL includes comprehensive tests for all new features. Run tests with:

```bash
python -m pytest tests/
```

## Deployment

### Production Considerations
1. Use strong secret keys for message signing
2. Implement appropriate rate limiting
3. Monitor system health and performance
4. Regularly backup message databases
5. Use TLS for network communication
6. Implement proper access controls
7. Monitor for security threats

### Scaling
1. Use connection pooling for high-volume applications
2. Implement horizontal scaling with message brokers
3. Use asynchronous processing where appropriate
4. Monitor resource usage and scale accordingly

## Conclusion

The enhanced AICL provides a robust, production-ready framework for LLM-to-LLM communication with comprehensive error handling, persistence, security, and monitoring features. These enhancements make it suitable for enterprise applications and production environments where reliability and security are critical.