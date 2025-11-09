# Event Bus & Registry Implementation

## Overview

The Event Bus & Registry system provides a robust infrastructure for event emission, subscription, and tool management in ASTRA. This implementation enables monitoring tool execution, debugging integration points, and building event-driven workflows.

## Core Components

### 1. Event Bus (`src/astra/core/event_bus.py`)

The Event Bus provides centralized event management with these key features:

- **Event Emission**: Synchronous and asynchronous event publishing
- **Event Subscription**: Subscribe/unsubscribe to specific event types
- **Event History**: Rolling history of recent events with filtering
- **Error Handling**: Graceful error handling for subscriber callbacks

Core event types:

- `astra.tool.before`: Emitted before tool execution
- `astra.tool.executed`: Emitted after tool execution (success/failure)

### 2. Tool Registry Integration

The enhanced Tool Registry now integrates with the Event Bus to:

- Track all tool executions
- Monitor success/failure rates
- Capture execution context and results
- Enable event-driven workflows

## Usage Examples

### 1. Event Subscription

```python
from astra.core.event_bus import get_event_bus

# Get event bus instance
bus = get_event_bus()

# Subscribe to events
def on_tool_executed(event):
    tool_name = event.data["tool"]
    success = event.data["success"]
    print(f"Tool {tool_name} executed - Success: {success}")

bus.subscribe("astra.tool.executed", on_tool_executed)
```

### 2. Tool Execution Monitoring

```python
from astra.core.tool_bus import get_registry

# Get tool registry
registry = get_registry()

# Execute tool (events emitted automatically)
result = await registry.execute(
    "file_read",
    {"path": "config.json"},
    context=ToolContext(
        tool_id="file_read_1",
        metadata={"trace_id": "abc123"}
    )
)
```

### 3. Event History

```python
# Get recent tool executions
bus = get_event_bus()
executions = bus.get_history("astra.tool.executed", limit=10)

for event in executions:
    print(f"Tool: {event.data['tool']}")
    print(f"Success: {event.data['success']}")
    print(f"Timestamp: {event.timestamp}")
```

## Integration Points

### 1. Tool Bus Integration

- Automatic event emission for tool execution
- Context propagation through events
- Error tracking and timeout monitoring

### 2. Error Handling

- Failed subscriber callbacks don't block execution
- Error events include error type and details
- Context preserved in error cases

### 3. Performance Considerations

- Asynchronous event emission available
- Rolling history with size limit
- Event filtering capabilities

## Testing

The implementation includes comprehensive tests:

### 1. Event Bus Core

- Event subscription/unsubscription
- Event emission (sync/async)
- History management

### 2. Tool Integration

- Tool execution event flow
- Error handling scenarios
- Context propagation

### 3. Performance

- Subscriber error isolation
- History size management
- Async operation handling

## Best Practices

### 1. Event Design

- Use consistent event naming (`category.action.state`)
- Include relevant context in event data
- Consider event versioning for schema changes

### 2. Subscription Management

- Unsubscribe when no longer needed
- Handle errors in subscriber callbacks
- Consider async subscribers for heavy processing

### 3. Tool Registry Usage

- Always provide meaningful context
- Use timeouts for long-running operations
- Monitor error patterns with event history

## Next Steps

### 1. Monitoring

- Add Prometheus metrics for event patterns
- Track subscriber performance
- Monitor error rates

### 2. Extensions

- Event replay capabilities
- Event persistence options
- Pattern matching for subscriptions

### 3. Documentation

- API reference updates
- Event schema documentation
- Integration examples