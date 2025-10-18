"""
ASTRA Plugin Interface

Provides base class for drop-in capability plugins with consent integration.
All plugins register their capabilities through a standard interface.
"""

from typing import Any, Dict, Callable, Optional
from abc import ABC, abstractmethod


class AstraPlugin(ABC):
    """
    Base class for all ASTRA plugins.
    
    Plugins extend ASTRA's capabilities through a standardized registration
    interface. Each plugin declares its capabilities, version, and consent
    requirements.
    
    Attributes:
        name: Unique identifier for the plugin
        version: Semantic version string
        consent_required: Whether user consent is needed before execution
        description: Human-readable plugin description
        author: Plugin author/maintainer
        sacred_code: Optional alignment marker (default: "333")
    
    Example:
        ```python
        class MyPlugin(AstraPlugin):
            name = "my_capability"
            version = "1.0.0"
            consent_required = True
            
            def register(self):
                return {
                    "my.action": self._do_action,
                    "my.query": self._do_query
                }
            
            def _do_action(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
                return {"ok": True, "data": "action result"}
        ```
    """
    
    # Plugin metadata
    name: str = "unnamed"
    version: str = "0.1.0"
    consent_required: bool = False
    description: str = "No description provided"
    author: str = "ASTRA Core"
    sacred_code: str = "333"
    
    # Plugin lifecycle hooks
    _initialized: bool = False
    _enabled: bool = True
    
    @abstractmethod
    def register(self) -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
        """
        Register plugin capabilities.
        
        Returns:
            Dictionary mapping capability names to callable functions.
            Each function should accept a dict of inputs and return a dict
            with at minimum {"ok": bool} and optionally {"data": Any, "err": str}.
        
        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError(f"Plugin '{self.name}' must implement register()")
    
    def initialize(self) -> bool:
        """
        Optional initialization hook called once when plugin is loaded.
        
        Returns:
            True if initialization successful, False otherwise
        """
        self._initialized = True
        return True
    
    def shutdown(self) -> bool:
        """
        Optional cleanup hook called when plugin is unloaded.
        
        Returns:
            True if shutdown successful, False otherwise
        """
        self._enabled = False
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check plugin health status.
        
        Returns:
            Dictionary with health information:
            - status: "healthy" | "degraded" | "unhealthy"
            - details: Optional additional health details
        """
        return {
            "status": "healthy" if (self._initialized and self._enabled) else "unhealthy",
            "name": self.name,
            "version": self.version,
            "initialized": self._initialized,
            "enabled": self._enabled
        }
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata for discovery and documentation.
        
        Returns:
            Dictionary with plugin metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "consent_required": self.consent_required,
            "description": self.description,
            "author": self.author,
            "sacred_code": self.sacred_code,
            "initialized": self._initialized,
            "enabled": self._enabled
        }
    
    def __repr__(self) -> str:
        return f"<AstraPlugin {self.name} v{self.version} consent={self.consent_required}>"


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class PluginRegistrationError(PluginError):
    """Raised when plugin registration fails."""
    pass


class PluginConsentError(PluginError):
    """Raised when plugin execution is blocked by consent."""
    pass


class PluginExecutionError(PluginError):
    """Raised when plugin execution fails."""
    pass
