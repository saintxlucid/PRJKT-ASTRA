"""
Plugin system configuration and helper functions.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Optional

from .manager import PluginManager
from .sandbox import PluginSandbox
from .audit import AuditLogger
from .consent import ConsentManager
from .error_handling import handle_plugin_errors, run_with_error_handling

class PluginSystem:
    """
    Helper class for managing the plugin system.
    Provides simplified interface for common operations.
    """
    
    def __init__(
        self,
        plugin_dir: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
        sign_logs: bool = True,
        auto_consent: bool = False
    ):
        self.plugin_dir = plugin_dir or Path("plugins")
        self.storage_dir = storage_dir or Path("data")
        
        # Initialize components
        self.audit_logger = AuditLogger(
            log_dir=self.storage_dir / "audit",
            sign_logs=sign_logs
        )
        
        self.consent_manager = ConsentManager(
            storage_path=self.storage_dir / "consent",
            auto_grant=auto_consent
        )
        
        self.plugin_manager = PluginManager(
            plugin_dir=self.plugin_dir,
            storage_dir=self.storage_dir,
            audit_logger=self.audit_logger,
            consent_manager=self.consent_manager
        )
        
    @handle_plugin_errors(reraise=True)
    async def initialize(self) -> None:
        """Initialize the plugin system"""
        # Ensure directories exist
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Discover and load plugins
        self.plugin_manager.discover_plugins()
        await self.plugin_manager.load_plugins()
        
    @handle_plugin_errors(reraise=True)
    async def shutdown(self) -> None:
        """Shutdown the plugin system"""
        await self.plugin_manager.unload_plugins()
        
    @handle_plugin_errors()
    def get_plugin(self, plugin_id: str) -> Optional[PluginSandbox]:
        """Get a plugin sandbox by ID"""
        return self.plugin_manager.get_plugin(plugin_id)
        
    @handle_plugin_errors(default_return=[])
    def list_plugins(self) -> list[str]:
        """Get list of loaded plugin IDs"""
        return self.plugin_manager.list_plugins()
        
    @handle_plugin_errors()
    async def call_plugin(
        self,
        plugin_id: str,
        action: str,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Call a plugin action
        
        Args:
            plugin_id: Plugin ID
            action: Action name
            params: Optional parameters
            
        Returns:
            Action result or None on error
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            return None
            
        return await plugin.call_action(action, params)
        
    @handle_plugin_errors()
    async def reload_plugin(self, plugin_id: str) -> bool:
        """
        Reload a plugin
        
        Args:
            plugin_id: Plugin ID
            
        Returns:
            bool: True if reload succeeded
        """
        await self.plugin_manager.reload_plugin(plugin_id)
        return True