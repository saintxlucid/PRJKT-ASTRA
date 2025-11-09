# Event Bus & Registry Quick Reference

## Core Events

1. `astra.tool.before`
   - Emitted: Before tool execution
   - Data: tool name, args, context
   - Use: Pre-execution validation/logging

2. `astra.tool.executed`
   - Emitted: After tool execution
   - Data: tool name, args, context, result/error
   - Success: result, status=true
   - Error: error message, error_type, status=false

## Key Components

### Event Bus

```python
from astra.core.event_bus import get_event_bus

bus = get_event_bus()

# Subscribe
bus.subscribe("event.name", callback_fn)

# Emit
bus.emit("event.name", {"key": "value"})

# History
events = bus.get_history("event.name", limit=10)
```

### Tool Registry

```python
from astra.core.tool_bus import get_registry

registry = get_registry()

# Register tool
@tool(
    name="example",
    description="Example tool",
    schema={"type": "object", "properties": {}}
)
async def example_tool():
    pass

# Execute (auto-emits events)
result = await registry.execute("tool_name", args)
```

## Event Schema

### Tool Before Event

```json
{
  "tool": "tool_name",
  "args": {},
  "context": {
    "tool_id": "id",
    "metadata": {}
  }
}
```

### Tool Executed Event (Success)

```json
{
  "tool": "tool_name",
  "args": {},
  "context": {
    "tool_id": "id",
    "metadata": {}
  },
  "result": "result data",
  "success": true
}
```

### Tool Executed Event (Error)

```json
{
  "tool": "tool_name",
  "args": {},
  "context": {
    "tool_id": "id",
    "metadata": {}
  },
  "error": "error message",
  "error_type": "timeout|execution",
  "success": false
}
```

## Common Patterns

### Tool Execution Monitoring

```python
def monitor_tool(event):
    if not event.data["success"]:
        print(f"Tool failed: {event.data['error']}")

bus.subscribe("astra.tool.executed", monitor_tool)
```

### Event History Analysis

```python
def analyze_errors():
    errors = bus.get_history("astra.tool.executed")
    return [e for e in errors if not e.data["success"]]
```

### Context Propagation

```python
context = ToolContext(
    tool_id="op_123",
    metadata={"trace_id": "abc"}
)
await registry.execute("tool", args, context)
```
