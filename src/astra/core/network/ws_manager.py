"""
ASTRA WebSocket Manager
Created: October 22, 2025

Provides reliable WebSocket connections with heartbeat, backoff,
and message queue management.
"""
from __future__ import annotations

import os
import asyncio
import json
import random
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import deque
from dataclasses import dataclass
import structlog

from fastapi import WebSocket, WebSocketDisconnect
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

logger = structlog.get_logger()

class EventType(str, Enum):
    """WebSocket event types"""
    NODE_ACTIVATION = "node_activation"
    MODE_CHANGE = "mode_change"
    NEW_MEMORY = "new_memory"
    GRAPH_UPDATE = "graph_update"
    HEARTBEAT = "heartbeat"

@dataclass
class WSEvent:
    """WebSocket event with metadata"""
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = datetime.now()

class ConnectionState:
    """Track connection state and metrics"""
    def __init__(self):
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.missed_heartbeats = 0
        self.message_count = 0
        self.error_count = 0
        self.reconnect_count = 0
        self.last_disconnect: Optional[datetime] = None
        self.next_retry: Optional[datetime] = None

class WSManager:
    """
    WebSocket connection manager with reliability features
    
    Features:
    - Heartbeat monitoring
    - Exponential backoff reconnection
    - Bounded message queue with drop-oldest policy
    - Port configuration via environment
    - Event type system
    """
    
    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        queue_size: int = 1000,
        base_retry_delay: float = 1.0,
        max_retry_delay: float = 60.0
    ):
        # Configuration
        self.port = int(os.getenv("ASTRA_WS_PORT", "8765"))
        self.heartbeat_interval = heartbeat_interval
        self.queue_size = queue_size
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        
        # Connection tracking
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.connection_states: Dict[str, ConnectionState] = {}
        
        # Message queue
        self.event_queue: deque[WSEvent] = deque(maxlen=queue_size)
        
        # Background tasks
        self.tasks: Set[asyncio.Task] = set()
        
    def start_background_tasks(self):
        """Start background maintenance tasks"""
        self.tasks.add(asyncio.create_task(
            self._heartbeat_monitor()
        ))
        self.tasks.add(asyncio.create_task(
            self._process_event_queue()
        ))
        
    def stop_background_tasks(self):
        """Stop all background tasks"""
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()
        
    async def register_connection(
        self,
        websocket: WebSocketServerProtocol,
        client_id: str
    ):
        """Register new WebSocket connection"""
        self.connections[client_id] = websocket
        self.connection_states[client_id] = ConnectionState()
        
        logger.info(
            "ws_client_connected",
            client_id=client_id,
            total_clients=len(self.connections)
        )
        
    async def unregister_connection(self, client_id: str):
        """Unregister WebSocket connection"""
        if client_id in self.connections:
            self.connections.pop(client_id)
            state = self.connection_states[client_id]
            state.last_disconnect = datetime.now()
            
            logger.info(
                "ws_client_disconnected",
                client_id=client_id,
                total_clients=len(self.connections)
            )
            
    def get_retry_delay(self, state: ConnectionState) -> float:
        """Calculate retry delay with exponential backoff"""
        if state.reconnect_count == 0:
            return self.base_retry_delay
            
        delay = min(
            self.base_retry_delay * (2 ** state.reconnect_count),
            self.max_retry_delay
        )
        
        # Add jitter (±10%)
        jitter = delay * 0.1
        delay += random.uniform(-jitter, jitter)
        
        return delay
        
    async def _heartbeat_monitor(self):
        """Monitor connection health via heartbeats"""
        while True:
            now = datetime.now()
            
            # Send heartbeats
            heartbeat = WSEvent(
                type=EventType.HEARTBEAT,
                data={"timestamp": now.isoformat()}
            )
            
            dead_connections = []
            
            for client_id, websocket in self.connections.items():
                state = self.connection_states[client_id]
                
                # Check for missed heartbeats
                if (now - state.last_heartbeat).total_seconds() > self.heartbeat_interval * 2:
                    state.missed_heartbeats += 1
                    if state.missed_heartbeats >= 3:
                        dead_connections.append(client_id)
                        continue
                        
                # Send heartbeat
                try:
                    await websocket.send(json.dumps({
                        "type": heartbeat.type,
                        "data": heartbeat.data
                    }))
                    state.last_heartbeat = now
                    state.missed_heartbeats = 0
                except Exception as e:
                    logger.error(
                        "ws_heartbeat_failed",
                        client_id=client_id,
                        error=str(e)
                    )
                    dead_connections.append(client_id)
                    
            # Clean up dead connections
            for client_id in dead_connections:
                await self.unregister_connection(client_id)
                
            await asyncio.sleep(self.heartbeat_interval)
            
    async def _process_event_queue(self):
        """Process and broadcast queued events"""
        while True:
            if not self.event_queue:
                await asyncio.sleep(0.1)
                continue
                
            # Get next event
            event = self.event_queue.popleft()
            
            # Broadcast to all connections
            dead_connections = []
            
            for client_id, websocket in self.connections.items():
                try:
                    await websocket.send(json.dumps({
                        "type": event.type,
                        "data": event.data,
                        "timestamp": event.timestamp.isoformat()
                    }))
                except Exception as e:
                    logger.error(
                        "ws_broadcast_failed",
                        client_id=client_id,
                        error=str(e)
                    )
                    dead_connections.append(client_id)
                    
            # Clean up dead connections
            for client_id in dead_connections:
                await self.unregister_connection(client_id)
                
    def queue_event(self, event_type: EventType, data: Dict[str, Any]):
        """Queue event for broadcasting"""
        event = WSEvent(type=event_type, data=data)
        
        # Queue will automatically drop oldest events if full
        self.event_queue.append(event)
        
        if len(self.event_queue) == self.queue_size:
            logger.warning(
                "ws_queue_full",
                dropped_events=len(self.event_queue) - self.queue_size
            )
            
    async def handle_client_message(
        self,
        websocket: WebSocketServerProtocol,
        client_id: str,
        message: str
    ):
        """Handle message from client"""
        try:
            data = json.loads(message)
            
            # Handle heartbeat response
            if data.get("type") == EventType.HEARTBEAT:
                state = self.connection_states[client_id]
                state.last_heartbeat = datetime.now()
                state.message_count += 1
                return
                
            # Handle other message types...
            logger.debug(
                "ws_message_received",
                client_id=client_id,
                type=data.get("type")
            )
            
        except Exception as e:
            logger.error(
                "ws_message_error",
                client_id=client_id,
                error=str(e)
            )
            
            state = self.connection_states[client_id]
            state.error_count += 1