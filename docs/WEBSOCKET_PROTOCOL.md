# ASTRA WebSocket Protocol
Created: October 22, 2025

## Overview

The ASTRA WebSocket protocol provides real-time updates and bidirectional communication.
Default WebSocket port is 8765, configurable via `ASTRA_WS_PORT` environment variable.

## Connection Lifecycle

1. Client connects to `/ws` endpoint
2. Server accepts connection and starts heartbeat monitoring
3. Client and server exchange heartbeats every 30 seconds
4. If 3 heartbeats are missed, connection is considered dead
5. On disconnect, client attempts reconnection with exponential backoff

## Message Format

All messages follow this JSON structure:

```json
{
    "type": "event_type",
    "data": {
        // Event-specific payload
    },
    "timestamp": "2025-10-22T14:30:00.123Z"
}
```

## Event Types

### node_activation
Indicates nodes being activated in the memory graph.

```json
{
    "type": "node_activation",
    "data": {
        "node_ids": ["node_123", "node_456"],
        "activation_type": "recall",
        "strength": 0.8
    }
}
```

### mode_change
Signals a change in operational mode.

```json
{
    "type": "mode_change",
    "data": {
        "old_mode": "normal",
        "new_mode": "focused",
        "trigger": "user_request"
    }
}
```

### new_memory
Broadcast when new memory is created.

```json
{
    "type": "new_memory",
    "data": {
        "memory_id": "mem_789",
        "content": "Important information",
        "memory_type": "semantic",
        "timestamp": "2025-10-22T14:30:00.123Z"
    }
}
```

### graph_update
Full or partial graph update.

```json
{
    "type": "graph_update",
    "data": {
        "nodes": [
            {
                "id": "node_123",
                "content": "Node content",
                "type": "memory",
                "position": [1.0, 2.0, 3.0]
            }
        ],
        "edges": [
            {
                "source": "node_123",
                "target": "node_456",
                "weight": 0.75
            }
        ],
        "is_partial": false
    }
}
```

### heartbeat
Connection health check message.

```json
{
    "type": "heartbeat",
    "data": {
        "timestamp": "2025-10-22T14:30:00.123Z"
    }
}
```

## Queue Management

- Maximum queue size: 1000 messages
- Drop policy: Oldest messages dropped when queue full
- Warning logged when queue reaches capacity

## Reconnection Strategy

1. Initial retry delay: 1 second
2. Exponential backoff: delay *= 2 for each retry
3. Maximum delay: 60 seconds
4. Random jitter: ±10% added to delay
5. No maximum retry count

## Error Handling

1. Connection errors trigger reconnection flow
2. Malformed messages increment error count
3. Error counts tracked per connection
4. High error rates may trigger temporary blocks
5. All errors logged with client context

## Environment Variables

- `ASTRA_WS_PORT`: WebSocket server port (default: 8765)
- `ASTRA_WS_HOST`: WebSocket server host (default: 127.0.0.1)
- `ASTRA_WS_HEARTBEAT_INTERVAL`: Seconds between heartbeats (default: 30)
- `ASTRA_WS_QUEUE_SIZE`: Maximum queued messages (default: 1000)