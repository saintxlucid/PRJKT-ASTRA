"""
ASTRA Plugin System
"""
import os
import json
import importlib
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger("astra.plugins")

@dataclass
class PluginInfo:
    """Plugin metadata"""
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    config: Dict[str, Any]

class PluginManager:
    """ASTRA plugin management system"""
    
    def __init__(self) -> None:
        self.plugin_dir = Path("plugins")
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins: Dict[str, PluginInfo] = {}
        self.loaded_modules: Dict[str, Any] = {}
        self.plugin_config = Path("core/plugins.json")
        
        self._load_plugin_config()
        
    def _load_plugin_config(self) -> None:
        """Load plugin configuration"""
        try:
            if self.plugin_config.exists():
                data = json.loads(self.plugin_config.read_text())
                self.plugins = {
                    name: PluginInfo(**info)
                    for name, info in data.items()
                }
        except Exception as e:
            logger.error(f"Failed to load plugin config: {str(e)}")
            
    def _save_plugin_config(self) -> None:
        """Save plugin configuration"""
        try:
            config = {
                name: {
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                    "author": info.author,
                    "entry_point": info.entry_point,
                    "config": info.config
                }
                for name, info in self.plugins.items()
            }
            
            self.plugin_config.write_text(json.dumps(config))
            
        except Exception as e:
            logger.error(f"Failed to save plugin config: {str(e)}")
            
    def register_plugin(self, info: PluginInfo) -> bool:
        """Register new plugin"""
        try:
            # Validate plugin structure
            plugin_path = self.plugin_dir / info.name
            if not plugin_path.exists():
                logger.error(f"Plugin directory not found: {info.name}")
                return False
                
            entry_file = plugin_path / info.entry_point
            if not entry_file.exists():
                logger.error(f"Plugin entry point not found: {info.entry_point}")
                return False
                
            # Add to registry
            self.plugins[info.name] = info
            self._save_plugin_config()
            
            logger.info(f"Registered plugin: {info.name} v{info.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin: {str(e)}")
            return False
            
    def unregister_plugin(self, name: str) -> bool:
        """Unregister plugin"""
        try:
            if name not in self.plugins:
                return False
                
            # Unload if loaded
            if name in self.loaded_modules:
                self.unload_plugin(name)
                
            # Remove from registry
            del self.plugins[name]
            self._save_plugin_config()
            
            logger.info(f"Unregistered plugin: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister plugin: {str(e)}")
            return False
            
    def load_plugin(self, name: str) -> bool:
        """Load plugin module"""
        try:
            if name not in self.plugins:
                logger.error(f"Plugin not registered: {name}")
                return False
                
            if name in self.loaded_modules:
                logger.warning(f"Plugin already loaded: {name}")
                return True
                
            info = self.plugins[name]
            
            # Import module
            plugin_path = self.plugin_dir / name
            spec = importlib.util.spec_from_file_location(
                name,
                plugin_path / info.entry_point
            )
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load plugin spec: {name}")
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Verify plugin interface
            if not hasattr(module, "initialize"):
                raise ValueError(
                    f"Plugin missing initialize() function: {name}"
                )
                
            if not hasattr(module, "shutdown"):
                raise ValueError(
                    f"Plugin missing shutdown() function: {name}"
                )
                
            # Initialize plugin
            module.initialize(info.config)
            
            self.loaded_modules[name] = module
            logger.info(f"Loaded plugin: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load plugin: {str(e)}")
            return False
            
    def unload_plugin(self, name: str) -> bool:
        """Unload plugin module"""
        try:
            if name not in self.loaded_modules:
                return False
                
            # Call shutdown
            module = self.loaded_modules[name]
            try:
                module.shutdown()
            except Exception as e:
                logger.error(f"Plugin shutdown failed: {str(e)}")
                
            # Remove module
            del self.loaded_modules[name]
            
            logger.info(f"Unloaded plugin: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unload plugin: {str(e)}")
            return False
            
    def get_plugin(self, name: str) -> Optional[Any]:
        """Get loaded plugin module"""
        return self.loaded_modules.get(name)
        
    def list_plugins(self) -> List[PluginInfo]:
        """List registered plugins"""
        return list(self.plugins.values())
        
    def update_plugin_config(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> bool:
        """Update plugin configuration"""
        try:
            if name not in self.plugins:
                return False
                
            # Update config
            info = self.plugins[name]
            info.config.update(config)
            
            # Reload if active
            if name in self.loaded_modules:
                self.unload_plugin(name)
                self.load_plugin(name)
                
            self._save_plugin_config()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update plugin config: {str(e)}")
            return False

_instance = None

def get_plugin_manager() -> PluginManager:
    """Get plugin manager singleton"""
    global _instance
    if _instance is None:
        _instance = PluginManager()
    return _instance