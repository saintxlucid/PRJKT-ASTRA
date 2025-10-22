"""
IPC client for communicating with Electron main process.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional
import uuid
import structlog

logger = structlog.get_logger()

class IPCClient:
    """
    Client for communicating with Electron main process via IPC.
    Uses stdin/stdout for communication.
    """
    
    def __init__(self):
        self.pending_requests: Dict[str, asyncio.Future] = {}
        self._setup_io()
        
    def _setup_io(self) -> None:
        """Setup stdin/stdout handlers"""
        loop = asyncio.get_event_loop()
        
        # Setup stdin reader
        loop.add_reader(
            0,  # stdin fd
            self._handle_stdin
        )
        
    def _handle_stdin(self) -> None:
        """Handle incoming IPC message from stdin"""
        try:
            line = input()
            message = json.loads(line)
            
            if "id" in message:
                # This is a response to a request
                req_id = message["id"]
                if req_id in self.pending_requests:
                    future = self.pending_requests.pop(req_id)
                    if "error" in message:
                        future.set_exception(Exception(message["error"]))
                    else:
                        future.set_result(message.get("result"))
                        
            else:
                # This is an event
                self._handle_event(message)
                
        except Exception as e:
            logger.error("Error handling IPC message", error=str(e))
            
    def _handle_event(self, message: Dict[str, Any]) -> None:
        """Handle incoming event message"""
        try:
            event_type = message.get("type")
            if not event_type:
                return
                
            # TODO: Add event handlers/callbacks
                
        except Exception as e:
            logger.error(
                "Error handling IPC event",
                error=str(e),
                event=message
            )
            
    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Any:
        """
        Send request to main process and await response
        
        Args:
            method: Request method name
            params: Optional parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response data
        """
        req_id = str(uuid.uuid4())
        future = asyncio.Future()
        self.pending_requests[req_id] = future
        
        try:
            # Send request
            message = {
                "id": req_id,
                "method": method,
                "params": params or {}
            }
            print(json.dumps(message), flush=True)
            
            # Wait for response
            return await asyncio.wait_for(future, timeout)
            
        except asyncio.TimeoutError:
            self.pending_requests.pop(req_id, None)
            raise TimeoutError(f"Request {method} timed out")
            
        except Exception as e:
            self.pending_requests.pop(req_id, None)
            raise
            
    async def send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send notification to main process (no response expected)
        
        Args:
            method: Notification method name
            params: Optional parameters
        """
        message = {
            "method": method,
            "params": params or {}
        }
        print(json.dumps(message), flush=True)