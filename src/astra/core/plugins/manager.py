"""
Plugin manager for coordinating multiple plugin instances.
Handles plugin discovery, dependencies, and lifecycle management.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
import structlog
import toml

from .sandbox import PluginSandbox
from .audit import AuditLogger
from .consent import ConsentManager
from .exceptions import PluginError

from typing import Dict, List, Optional, Set
from typing import List as ListType
import structlog
from tomli import load as toml_load

logger = structlog.get_logger()

@dataclass
class PluginConfig:
    """Plugin configuration from pyproject.toml"""
    enabled: bool = True
    auto_consent: bool = False
    env: Optional[Dict[str, str]] = None
    dependencies: List[str] = field(default_factory=list)

class PluginManager:
    """
    Manages multiple plugin instances.
    Handles discovery, dependencies, and lifecycle coordination.
    """
    
    def __init__(
        self,
        plugin_dir: Optional[Path] = None,
        storage_dir: Optional[Path] = None,
        audit_logger: Optional[AuditLogger] = None,
        consent_manager: Optional[ConsentManager] = None
    ):
        self.plugin_dir = plugin_dir or Path("plugins")
        self.storage_dir = storage_dir or Path("data")
        self.audit_logger = audit_logger or AuditLogger(sign_logs=True)
        self.consent_manager = consent_manager or ConsentManager()
        
        # Runtime state
        self.plugins: Dict[str, PluginSandbox] = {}
        self.configs: Dict[str, PluginConfig] = {}
        self._load_order: List[str] = []
        
    def _load_config(self, plugin_path: Path) -> Optional[PluginConfig]:
        """Load plugin configuration from pyproject.toml"""
        config_path = plugin_path / "pyproject.toml"
        if not config_path.exists():
            return None
            
        try:
            config = toml.load(config_path)
            plugin_config = config.get("tool", {}).get("astra", {})
            return PluginConfig(**plugin_config)
        except Exception as e:
            logger.error(
                "Failed to load plugin config",
                path=str(plugin_path),
                error=str(e)
            )
            return None
            
    def discover_plugins(self) -> None:
        """
        Discover available plugins and load configurations.
        Does not load plugin code.
        """
        self.configs.clear()
        
        # Scan plugin directory
        if not self.plugin_dir.exists():
            return
            
        for path in self.plugin_dir.iterdir():
            if not path.is_dir():
                continue
                
            # Load configuration
            config = self._load_config(path)
            if config:
                self.configs[path.name] = config
                
    def _resolve_dependencies(self) -> List[str]:
        """
        Resolve plugin load order based on dependencies.
        Returns ordered list of plugin IDs.
        """
        # Track resolved and visiting plugins for cycle detection
        resolved: Set[str] = set()
        visiting: Set[str] = set()
        order: List[str] = []
        
        def visit(plugin_id: str) -> None:
            """Depth-first dependency traversal"""
            if plugin_id in resolved:
                return
                
            if plugin_id in visiting:
                raise PluginError(f"Circular dependency detected: {plugin_id}")
                
            visiting.add(plugin_id)
            
            # Visit dependencies first
            config = self.configs.get(plugin_id)
            if config and config.dependencies:
                for dep in config.dependencies:
                    if dep not in self.configs:
                        raise PluginError(
                            f"Missing dependency {dep} for plugin {plugin_id}"
                        )
                    visit(dep)
                    
            visiting.remove(plugin_id)
            resolved.add(plugin_id)
            order.append(plugin_id)
            
        # Visit each plugin
        for plugin_id in self.configs:
            if not self.configs[plugin_id].enabled:
                continue
            visit(plugin_id)
            
        return order
        
    async def load_plugins(self) -> None:
        """
        Load and initialize all enabled plugins in dependency order.
        """
        # Resolve load order
        self._load_order = self._resolve_dependencies()
        
        # Load plugins in order
        for plugin_id in self._load_order:
            try:
                config = self.configs[plugin_id]
                if not config.enabled:
                    continue
                    
                # Create sandbox
                plugin_path = self.plugin_dir / plugin_id
                storage_path = self.storage_dir / "plugins" / plugin_id
                
                sandbox = PluginSandbox(
                    plugin_path=plugin_path,
                    storage_base=storage_path,
                    audit_logger=self.audit_logger,
                    consent_manager=self.consent_manager
                )
                
                # Load plugin
                await sandbox.load()
                self.plugins[plugin_id] = sandbox
                
                logger.info(f"Loaded plugin {plugin_id}")
                
            except Exception as e:
                logger.error(
                    f"Failed to load plugin {plugin_id}",
                    error=str(e)
                )
                
    async def unload_plugins(self) -> None:
        """
        Unload all plugins in reverse dependency order.
        """
        for plugin_id in reversed(self._load_order):
            if plugin_id not in self.plugins:
                continue
                
            try:
                await self.plugins[plugin_id].unload()
                del self.plugins[plugin_id]
                logger.info(f"Unloaded plugin {plugin_id}")
                
            except Exception as e:
                logger.error(
                    f"Error unloading plugin {plugin_id}",
                    error=str(e)
                )
                
    def get_plugin(self, plugin_id: str) -> Optional[PluginSandbox]:
        """Get plugin sandbox by ID"""
        return self.plugins.get(plugin_id)
        
    def list_plugins(self) -> List[str]:
        """Get list of loaded plugin IDs"""
        return list(self.plugins.keys())
        
    async def reload_plugin(self, plugin_id: str) -> None:
        """
        Reload a specific plugin
        
        Args:
            plugin_id: ID of plugin to reload
        """
        if plugin_id not in self.plugins:
            raise PluginError(f"Plugin {plugin_id} not loaded")
            
        try:
            # Unload
            await self.plugins[plugin_id].unload()
            del self.plugins[plugin_id]
            
            # Load again
            plugin_path = self.plugin_dir / plugin_id
            storage_path = self.storage_dir / "plugins" / plugin_id
            
            sandbox = PluginSandbox(
                plugin_path=plugin_path,
                storage_base=storage_path,
                audit_logger=self.audit_logger,
                consent_manager=self.consent_manager
            )
            
            await sandbox.load()
            self.plugins[plugin_id] = sandbox
            
            logger.info(f"Reloaded plugin {plugin_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to reload plugin {plugin_id}",
                error=str(e)
            )
            raise