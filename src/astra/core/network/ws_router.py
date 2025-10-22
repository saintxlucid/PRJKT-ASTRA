"""
ASTRA WebSocket Router
Created: October 22, 2025

FastAPI router for WebSocket endpoints.
"""
from __future__ import annotations

import os
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog

from .ws_manager import WSManager, EventType

logger = structlog.get_logger()

# Create router
router = APIRouter()

# Global WebSocket manager
ws_manager: Optional[WSManager] = None

@asynccontextmanager
async def get_ws_manager():
    """Get or create WebSocket manager"""
    global ws_manager
    
    if ws_manager is None:
        ws_manager = WSManager()
        ws_manager.start_background_tasks()
        
    try:
        yield ws_manager
    finally:
        if ws_manager:
            ws_manager.stop_background_tasks()
            ws_manager = None

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint"""
    await websocket.accept()
    
    # Generate client ID
    client_id = f"{websocket.client.host}:{websocket.client.port}"
    
    async with get_ws_manager() as manager:
        try:
            # Register connection
            await manager.register_connection(websocket, client_id)
            
            while True:
                # Handle messages
                data = await websocket.receive_text()
                await manager.handle_client_message(
                    websocket, client_id, data
                )
                
        except WebSocketDisconnect:
            await manager.unregister_connection(client_id)
            
@router.post("/ws/broadcast")
async def broadcast_event(
    event_type: EventType,
    data: Dict
):
    """Broadcast event to all connected clients"""
    async with get_ws_manager() as manager:
        manager.queue_event(event_type, data)
        return {"status": "queued"}
        
@router.get("/ws/stats")
async def get_stats():
    """Get WebSocket connection statistics"""
    if not ws_manager:
        return {"status": "not_running"}
        
    stats = {
        "connections": len(ws_manager.connections),
        "queue_size": len(ws_manager.event_queue),
        "queue_capacity": ws_manager.queue_size
    }
    
    # Add per-connection stats
    stats["clients"] = [
        {
            "id": client_id,
            "connected_at": state.connected_at.isoformat(),
            "last_heartbeat": state.last_heartbeat.isoformat(),
            "message_count": state.message_count,
            "error_count": state.error_count,
            "reconnect_count": state.reconnect_count
        }
        for client_id, state in ws_manager.connection_states.items()
    ]
    
    return stats