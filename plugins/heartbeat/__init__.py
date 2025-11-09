"""
Heartbeat Plugin - Example ASTRA Plugin

Provides system heartbeat capability for health monitoring.
Demonstrates basic plugin implementation pattern.
"""

from typing import Dict, Any
from astra.plugins.interface import AstraPlugin


class HeartbeatPlugin(AstraPlugin):
    """
    System heartbeat plugin.
    
    Provides a simple heartbeat capability that returns system pulse status.
    Useful for health monitoring and plugin system validation.
    """
    
    name = "heartbeat"
    version = "1.0.0"
    consent_required = False
    description = "System heartbeat monitoring capability"
    author = "ASTRA Core Team"
    sacred_code = "333"
    
    def register(self) -> Dict[str, Any]:
        """
        Register heartbeat capability.
        
        Returns:
            Dictionary with system.heartbeat capability
        """
        return {
            "system.heartbeat": self._heartbeat,
            "system.pulse": self._pulse,
            "system.alive": self._alive
        }
    
    def _heartbeat(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Full heartbeat with metadata.
        
        Args:
            inputs: Optional heartbeat parameters (ignored)
        
        Returns:
            Dictionary with heartbeat status and metadata
        """
        return {
            "ok": True,
            "data": {
                "pulse": "alive",
                "plugin": self.name,
                "version": self.version,
                "sacred_code": self.sacred_code,
                "status": "operational"
            }
        }
    
    def _pulse(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimal pulse check.
        
        Args:
            inputs: Optional pulse parameters (ignored)
        
        Returns:
            Dictionary with pulse status
        """
        return {
            "ok": True,
            "data": {"pulse": "alive"}
        }
    
    def _alive(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Boolean alive check.
        
        Args:
            inputs: Optional check parameters (ignored)
        
        Returns:
            Dictionary with alive status
        """
        return {
            "ok": True,
            "data": True
        }
