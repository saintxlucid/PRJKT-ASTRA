# Plugin System Documentation

## Overview

The ASTRA plugin system provides a secure, isolated environment for running third-party extensions. It includes:

- Capability-based permission system
- Resource limit enforcement
- Comprehensive audit logging
- Version compatibility checks
- Safe dependency management

## Plugin Structure

A valid plugin must have:

1. `manifest.json` - Defines capabilities and requirements
2. `plugin.py` - Contains plugin implementation

### Manifest Example

```json
{
    "id": "my-plugin",
    "version": "1.0.0",
    "name": "My Plugin",
    "description": "Plugin description",
    "capabilities": {
        "minAbiVersion": "1.0",
        "maxAbiVersion": "1.0",
        "actions": [
            {
                "name": "my_action",
                "description": "Action description",
                "permissions": ["memory.read"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"}
                    }
                },
                "returnType": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            }
        ],
        "storage": {
            "persistent": true,
            "quota": 1024
        }
    },
    "sandbox": {
        "runtime": "python",
        "version": "3.8",
        "dependencies": []
    }
}
```

### Plugin Implementation

```python
class Plugin:
    async def initialize(self, context):
        """Called when plugin is loaded"""
        self.context = context
        
    async def my_action(self, params):
        """Implement action defined in manifest"""
        input_value = params.get("input", "")
        return {"result": f"Processed: {input_value}"}
        
    async def cleanup(self):
        """Called when plugin is unloaded"""
        pass
```

## Permission System

Available permissions:

- `memory.read` - Read from memory store
- `memory.write` - Write to memory store
- `fs.read` - Read from filesystem
- `fs.write` - Write to filesystem
- `network.connect` - Make network connections
- `process.exec` - Execute processes
- `ui.display` - Show UI elements
- `system.env` - Access environment variables

Permissions are:

- Explicitly declared in manifest
- Checked per-action
- Granted via user consent
- Audited for all uses

## Resource Limits

Enforced limits:

- Memory usage
- Execution time
- Storage quota
- Network bandwidth

Configurable via manifest:

```json
{
    "capabilities": {
        "resources": {
            "memoryLimit": 512,
            "timeoutMs": 5000
        }
    }
}
```

## Audit Logging

All plugin actions are logged with:

- Timestamp
- Action details
- Parameters
- Result/error
- Performance metrics
- Cryptographic signatures (optional)

## Best Practices

1. Security
   - Request minimum needed permissions
   - Handle permission denials gracefully
   - Clean up resources properly
   - Validate all inputs

2. Performance
   - Stay within resource limits
   - Use async operations
   - Implement timeouts
   - Clean up unused objects

3. Error Handling
   - Provide clear error messages
   - Handle cleanup in errors
   - Log relevant context
   - Use appropriate error types

## Common Issues

1. Permission Errors

   ```python
   try:
       await sandbox.call_action("my_action", params)
   except PluginPermissionError:
       # Handle missing permissions
   ```

2. Resource Limits

   ```python
   try:
       await memory_intensive_operation()
   except PluginRuntimeError as e:
       if "memory limit" in str(e):
           # Handle resource exhaustion
   ```

3. Initialization Failures

   ```python
   try:
       await sandbox.load()
   except PluginLoadError as e:
       # Handle load failure
   ```

## Testing

Run the test suite:

```bash
pytest tests/core/plugins/test_sandbox.py -v
```

Tests cover:

- Basic functionality
- Permission system
- Resource limits
- Error handling
- Audit logging
- Concurrent operations
