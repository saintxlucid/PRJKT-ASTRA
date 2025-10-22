"""
Electron UI provider implementation.
Handles plugin UI interactions through IPC.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional, cast

import structlog
from ...ipc import IPCClient
from .interface import UIProvider, PermissionRequest, ConsentResponse

logger = structlog.get_logger()

class ElectronUIProvider(UIProvider):
    """
    UI provider implementation using Electron IPC.
    Communicates with the Electron main process for UI interactions.
    """
    
    def __init__(self, ipc_client: IPCClient):
        self.ipc = ipc_client
        
    async def request_permissions(
        self,
        request: PermissionRequest
    ) -> ConsentResponse:
        """
        Display permission request dialog and get user response
        
        Args:
            request: Permission request details
            
        Returns:
            User's consent response
        """
        try:
            # Format request for IPC
            req_data = {
                "plugin_id": request.plugin_id,
                "plugin_name": request.plugin_name,
                "action_name": request.action_name,
                "action_description": request.action_description,
                "permissions": list(request.permissions)
            }
            
            # Send request and await response
            response = await self.ipc.send_request(
                "plugin:permission-request",
                req_data
            )
            
            return ConsentResponse(
                granted=response["granted"],
                remember=response["remember"]
            )
            
        except Exception as e:
            logger.error(
                "Permission request failed",
                error=str(e),
                plugin_id=request.plugin_id
            )
            # Default to denying on error
            return ConsentResponse(granted=False, remember=False)
            
    async def notify_plugin_load(
        self,
        plugin_id: str,
        plugin_name: Optional[str] = None
    ) -> None:
        """Send plugin load notification"""
        try:
            await self.ipc.send_notification(
                "plugin:loaded",
                {
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_name
                }
            )
        except Exception as e:
            logger.error(
                "Failed to send plugin load notification",
                error=str(e),
                plugin_id=plugin_id
            )
            
    async def notify_plugin_error(
        self,
        plugin_id: str,
        error: str,
        details: Optional[str] = None
    ) -> None:
        """Send plugin error notification"""
        try:
            await self.ipc.send_notification(
                "plugin:error",
                {
                    "plugin_id": plugin_id,
                    "error": error,
                    "details": details
                }
            )
        except Exception as e:
            logger.error(
                "Failed to send plugin error notification",
                error=str(e),
                plugin_id=plugin_id
            )