"""
Plugin interface definitions and base classes.
"""
from __future__ import annotations

import abc
from typing import Any, Dict, Optional

class PluginInterface(abc.ABC):
    """
    Base interface for ASTRA plugins.
    All plugins must implement this interface.
    """
    
    @abc.abstractmethod
    async def initialize(self, context: Any) -> None:
        """
        Initialize plugin with runtime context.
        Called when plugin is first loaded.
        
        Args:
            context: Plugin runtime context
        """
        pass
        
    @abc.abstractmethod
    async def cleanup(self) -> None:
        """
        Cleanup plugin resources.
        Called before plugin is unloaded.
        """
        pass
        
    @abc.abstractmethod
    async def get_manifest(self) -> Dict[str, Any]:
        """
        Get plugin manifest defining capabilities.
        
        Returns:
            dict: Plugin manifest
        """
        pass
        
class BasePlugin(PluginInterface):
    """
    Base class for ASTRA plugins with default implementations.
    """
    
    async def initialize(self, context: Any) -> None:
        """Default no-op initialization"""
        pass
        
    async def cleanup(self) -> None:
        """Default no-op cleanup"""
        pass
        
    async def get_manifest(self) -> Dict[str, Any]:
        """
        Default implementation reads manifest.json
        Override to provide dynamic manifest.
        """
        from pathlib import Path
        import json
        
        manifest_path = Path(__file__).parent / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError("manifest.json not found")
            
        with manifest_path.open() as f:
            return json.load(f)