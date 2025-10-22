import asyncio
import json
import logging
from typing import Dict, Set, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sse_starlette.sse import EventSourceResponse
from typing import AsyncGenerator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CognitiveStreamManager:
    def __init__(self):
        self.websocket_clients: Set[WebSocket] = set()
        self.sse_clients: Set[asyncio.Queue] = set()
        self.last_metrics: Optional[Dict] = None
        
    async def connect_websocket(self, websocket: WebSocket):
        await websocket.accept()
        self.websocket_clients.add(websocket)
        if self.last_metrics:
            await websocket.send_json(self.last_metrics)
            
    async def disconnect_websocket(self, websocket: WebSocket):
        self.websocket_clients.remove(websocket)
        
    def connect_sse(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.sse_clients.add(queue)
        if self.last_metrics:
            queue.put_nowait(self.last_metrics)
        return queue
        
    def disconnect_sse(self, queue: asyncio.Queue):
        self.sse_clients.remove(queue)
        
    async def broadcast(self, metrics: Dict):
        self.last_metrics = metrics
        
        # Broadcast to WebSocket clients
        dead_ws = set()
        for websocket in self.websocket_clients:
            try:
                await websocket.send_json(metrics)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                dead_ws.add(websocket)
                
        # Clean up dead connections
        for websocket in dead_ws:
            self.websocket_clients.remove(websocket)
            
        # Broadcast to SSE clients
        for queue in self.sse_clients:
            await queue.put(metrics)

# Initialize the stream manager
stream_manager = CognitiveStreamManager()

async def cognitive_stream_endpoint(websocket: WebSocket):
    """WebSocket endpoint for cognitive metrics streaming"""
    await stream_manager.connect_websocket(websocket)
    try:
        while True:
            # Wait for any client messages (ping/pong, etc)
            await websocket.receive_text()
    except WebSocketDisconnect:
        await stream_manager.disconnect_websocket(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await stream_manager.disconnect_websocket(websocket)

async def cognitive_sse_endpoint() -> AsyncGenerator:
    """Server-Sent Events endpoint for cognitive metrics streaming"""
    queue = stream_manager.connect_sse()
    try:
        while True:
            metrics = await queue.get()
            yield {
                "event": "metrics",
                "data": json.dumps(metrics)
            }
    except asyncio.CancelledError:
        stream_manager.disconnect_sse(queue)
    except Exception as e:
        logger.error(f"SSE error: {e}")
        stream_manager.disconnect_sse(queue)

async def broadcast_metrics(metrics: Dict):
    """Broadcast metrics to all connected clients"""
    await stream_manager.broadcast(metrics)

def setup_cognitive_streaming(app: FastAPI):
    """Configure the FastAPI app with cognitive streaming endpoints"""
    app.websocket("/api/cognitive/stream")(cognitive_stream_endpoint)
    app.get("/api/cognitive/stream")(lambda: EventSourceResponse(cognitive_sse_endpoint()))