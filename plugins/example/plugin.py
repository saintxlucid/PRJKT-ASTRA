"""
Example plugin implementation.
"""
from typing import Dict, Any
from astra.core.plugins.interface import BasePlugin

class Plugin(BasePlugin):
    """
    Example plugin demonstrating ASTRA plugin capabilities.
    """
    
    async def initialize(self, context: Any) -> None:
        """Store context for later use"""
        self.context = context
        
    async def greet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a greeting message"""
        name = params["name"]
        return {"message": f"Hello, {name}!"}
        
    async def add(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add two numbers"""
        a = params["a"]
        b = params["b"]
        return {"result": a + b}