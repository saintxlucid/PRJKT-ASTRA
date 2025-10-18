"""
Stream Router for Real-Time Memory Updates
WebSocket server for streaming graph updates to neural browser

Features:
- Async WebSocket connections
- Event-driven memory update broadcasting
- Connection pool management
- Graceful reconnection handling
"""

import asyncio
import json
from typing import Set, Dict, Any, List
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("⚠ websockets not installed. Install with: pip install websockets")
    websockets = None

try:
    from src.astra.visualization.memory_graph_service import MemoryGraphService
except ImportError:
    from astra.visualization.memory_graph_service import MemoryGraphService


class StreamRouter:
    """
    Manages WebSocket connections and broadcasts memory updates
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Initialize stream router
        
        Args:
            host: Host address to bind
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.connections: Set[WebSocketServerProtocol] = set()
        self.graph_service = MemoryGraphService()
        
        # Event queue
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # Server
        self.server = None
    
    async def start(self):
        """Start WebSocket server"""
        if not websockets:
            print("❌ Cannot start stream router: websockets not installed")
            return
        
        print(f"🌐 Starting stream router on ws://{self.host}:{self.port}")
        
        async with websockets.serve(self.handler, self.host, self.port):
            print(f"   ✓ Stream router listening")
            
            # Start event broadcaster
            broadcaster_task = asyncio.create_task(self.broadcast_events())
            
            # Keep running
            await asyncio.Future()  # Run forever
    
    async def handler(self, websocket: WebSocketServerProtocol):
        """Handle new WebSocket connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        print(f"   ✓ Client connected: {client_id}")
        
        self.connections.add(websocket)
        
        try:
            # Send initial graph
            await self.send_full_graph(websocket)
            
            # Listen for client messages
            async for message in websocket:
                await self.handle_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"   ○ Client disconnected: {client_id}")
        finally:
            self.connections.remove(websocket)
    
    async def send_full_graph(self, websocket: WebSocketServerProtocol):
        """Send complete graph to client"""
        try:
            # Build graph
            nodes, edges = self.graph_service.build_graph(max_nodes=200)
            
            # Serialize
            message = {
                "type": "full_graph",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "nodes": [
                        {
                            "id": n.id,
                            "content": n.content,
                            "memory_type": n.memory_type,
                            "position": n.position,
                            "importance": n.importance,
                            "color": n.color,
                            "size": n.size,
                            "active": n.active
                        }
                        for n in nodes
                    ],
                    "edges": [
                        {
                            "source": e.source_id,
                            "target": e.target_id,
                            "weight": e.weight,
                            "type": e.edge_type
                        }
                        for e in edges
                    ]
                }
            }
            
            await websocket.send(json.dumps(message))
            print(f"   ✓ Sent full graph ({len(nodes)} nodes, {len(edges)} edges)")
            
        except Exception as e:
            print(f"   ❌ Error sending graph: {e}")
    
    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await websocket.send(json.dumps({"type": "pong"}))
            
            elif msg_type == "request_graph":
                await self.send_full_graph(websocket)
            
            elif msg_type == "activate_nodes":
                node_ids = data.get("node_ids", [])
                await self.broadcast_node_activation(node_ids)
            
            elif msg_type == "set_mode":
                mode = data.get("mode")
                await self.broadcast_mode_change(mode)
            
        except json.JSONDecodeError:
            print(f"   ⚠ Invalid JSON from client")
        except Exception as e:
            print(f"   ❌ Error handling message: {e}")
    
    async def broadcast_events(self):
        """Process and broadcast queued events"""
        while True:
            try:
                # Get next event (wait if queue empty)
                event = await self.event_queue.get()
                
                # Broadcast to all connections
                if self.connections:
                    message = json.dumps(event)
                    await asyncio.gather(
                        *[conn.send(message) for conn in self.connections],
                        return_exceptions=True
                    )
                
            except Exception as e:
                print(f"   ❌ Error broadcasting: {e}")
            
            await asyncio.sleep(0.01)  # Small delay
    
    async def broadcast_node_activation(self, node_ids: List[str]):
        """Broadcast node activation event"""
        event = {
            "type": "node_activation",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "node_ids": node_ids
            }
        }
        await self.event_queue.put(event)
    
    async def broadcast_mode_change(self, mode: str):
        """Broadcast operational mode change"""
        event = {
            "type": "mode_change",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "mode": mode,
                "active": True
            }
        }
        await self.event_queue.put(event)
    
    async def broadcast_new_memory(self, memory_data: Dict[str, Any]):
        """Broadcast new memory addition"""
        event = {
            "type": "new_memory",
            "timestamp": datetime.now().isoformat(),
            "data": memory_data
        }
        await self.event_queue.put(event)
    
    async def broadcast_conversation_pulse(self, active_memories: List[str]):
        """Broadcast conversation activity pulse"""
        event = {
            "type": "conversation_pulse",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "active_memories": active_memories
            }
        }
        await self.event_queue.put(event)
    
    def queue_event(self, event: Dict[str, Any]):
        """Queue an event for broadcasting (sync interface)"""
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self.event_queue.put(event))
        except RuntimeError:
            # No event loop running
            pass


class StreamClient:
    """Client for receiving memory updates"""
    
    def __init__(self, uri: str = "ws://127.0.0.1:8765"):
        """
        Initialize stream client
        
        Args:
            uri: WebSocket server URI
        """
        self.uri = uri
        self.websocket: Optional[WebSocketServerProtocol] = None
        self.callbacks = {
            "full_graph": [],
            "node_activation": [],
            "mode_change": [],
            "new_memory": [],
            "conversation_pulse": []
        }
    
    async def connect(self):
        """Connect to stream server"""
        if not websockets:
            print("❌ Cannot connect: websockets not installed")
            return
        
        print(f"🔌 Connecting to {self.uri}...")
        
        try:
            self.websocket = await websockets.connect(self.uri)
            print("   ✓ Connected to stream server")
            
            # Start listening
            await self.listen()
            
        except Exception as e:
            print(f"   ❌ Connection failed: {e}")
    
    async def listen(self):
        """Listen for messages from server"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type")
                
                # Call registered callbacks
                if msg_type in self.callbacks:
                    for callback in self.callbacks[msg_type]:
                        try:
                            callback(data)
                        except Exception as e:
                            print(f"   ⚠ Callback error: {e}")
        
        except websockets.exceptions.ConnectionClosed:
            print("   ○ Connection closed")
    
    def on(self, event_type: str, callback):
        """Register callback for event type"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    async def send(self, message: Dict[str, Any]):
        """Send message to server"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
    
    async def request_graph(self):
        """Request full graph update"""
        await self.send({"type": "request_graph"})
    
    async def activate_nodes(self, node_ids: List[str]):
        """Request node activation"""
        await self.send({
            "type": "activate_nodes",
            "node_ids": node_ids
        })


async def main():
    """Test stream router"""
    print("🧬 Testing Stream Router\n")
    
    if not websockets:
        print("❌ websockets not installed")
        print("   Install with: pip install websockets")
        return
    
    # Start server
    router = StreamRouter()
    
    try:
        await router.start()
    except KeyboardInterrupt:
        print("\n\n✓ Stream router stopped")


if __name__ == "__main__":
    asyncio.run(main())
