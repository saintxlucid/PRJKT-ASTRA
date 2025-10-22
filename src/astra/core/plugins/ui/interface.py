"""
UI provider interface for plugin system interactions.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import List, Optional, Set

@dataclass
class PermissionRequest:
    """Permission request details for UI display"""
    plugin_id: str
    plugin_name: Optional[str]
    action_name: str
    action_description: Optional[str]
    permissions: Set[str]
    
@dataclass
class ConsentResponse:
    """User response to permission request"""
    granted: bool
    remember: bool  # Whether to remember this decision
    
class UIProvider(abc.ABC):
    """
    Abstract base class for UI integration.
    Implementations handle displaying prompts and collecting user input.
    """
    
    @abc.abstractmethod
    async def request_permissions(
        self,
        request: PermissionRequest
    ) -> ConsentResponse:
        """
        Display permission request and get user response
        
        Args:
            request: Permission request details
            
        Returns:
            User's consent response
        """
        pass
        
    @abc.abstractmethod
    async def notify_plugin_load(
        self,
        plugin_id: str,
        plugin_name: Optional[str] = None
    ) -> None:
        """
        Notify user that a plugin was loaded
        
        Args:
            plugin_id: Plugin identifier
            plugin_name: Optional friendly name
        """
        pass
        
    @abc.abstractmethod
    async def notify_plugin_error(
        self,
        plugin_id: str,
        error: str,
        details: Optional[str] = None
    ) -> None:
        """
        Notify user of a plugin error
        
        Args:
            plugin_id: Plugin identifier
            error: Error message
            details: Optional error details
        """
        pass