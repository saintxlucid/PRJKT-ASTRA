"""
ASTRA Plugin Loader

Dynamic plugin discovery and loading system with consent integration.
Discovers plugins from specified directories and registers their capabilities.
"""

import importlib
import pkgutil
import inspect
import logging
from pathlib import Path
from typing import Dict, Callable, Any, List, Optional, Set
from functools import wraps

from astra.plugins.interface import (
    AstraPlugin, 
    PluginRegistrationError,
    PluginConsentError,
    PluginExecutionError
)

logger = logging.getLogger(__name__)


class PluginLoader:
    """
    Plugin discovery and loading system.
    
    Discovers plugins from specified directories, initializes them,
    and registers their capabilities with consent enforcement.
    
    Attributes:
        plugins: Dictionary of loaded plugin instances by name
        capabilities: Dictionary of registered capability callables
        consent_manager: Optional consent manager for gating
    """
    
    def __init__(self, consent_manager: Optional[Any] = None):
        """
        Initialize plugin loader.
        
        Args:
            consent_manager: Optional consent manager for capability gating
        """
        self.plugins: Dict[str, AstraPlugin] = {}
        self.capabilities: Dict[str, Callable] = {}
        self.consent_manager = consent_manager
        self._capability_to_plugin: Dict[str, str] = {}
    
    def load_plugins(
        self, 
        package_name: str = "plugins",
        plugin_dirs: Optional[List[Path]] = None
    ) -> Dict[str, Callable]:
        """
        Load all plugins from specified package/directories.
        
        Args:
            package_name: Python package name containing plugins
            plugin_dirs: Optional list of directories to search for plugins
        
        Returns:
            Dictionary of registered capabilities
        
        Raises:
            PluginRegistrationError: If plugin loading fails
        """
        if plugin_dirs is None:
            plugin_dirs = [Path("plugins")]
        
        logger.info(f"Loading plugins from package '{package_name}' and dirs {plugin_dirs}")
        
        loaded_count = 0
        capability_count = 0
        
        # Discover plugins from directories
        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                logger.warning(f"Plugin directory not found: {plugin_dir}")
                continue
            
            try:
                # Iterate through modules in directory
                for module_info in pkgutil.iter_modules([str(plugin_dir)]):
                    module_name = f"{package_name}.{module_info.name}"
                    
                    try:
                        # Import module
                        module = importlib.import_module(module_name)
                        
                        # Find plugin classes
                        for name, cls in inspect.getmembers(module, inspect.isclass):
                            if (issubclass(cls, AstraPlugin) and 
                                cls is not AstraPlugin and
                                hasattr(cls, 'register')):
                                
                                # Instantiate and register plugin
                                plugin_instance = cls()
                                caps = self._register_plugin(plugin_instance)
                                
                                loaded_count += 1
                                capability_count += len(caps)
                                
                                logger.info(
                                    f"Loaded plugin '{plugin_instance.name}' "
                                    f"v{plugin_instance.version} with {len(caps)} capabilities"
                                )
                    
                    except Exception as e:
                        logger.error(f"Failed to load plugin from {module_name}: {e}")
                        continue
            
            except Exception as e:
                logger.error(f"Failed to scan plugin directory {plugin_dir}: {e}")
                continue
        
        logger.info(
            f"Plugin loading complete: {loaded_count} plugins, "
            f"{capability_count} capabilities registered"
        )
        
        return self.capabilities
    
    def _register_plugin(self, plugin: AstraPlugin) -> Dict[str, Callable]:
        """
        Register a plugin instance and its capabilities.
        
        Args:
            plugin: Plugin instance to register
        
        Returns:
            Dictionary of registered capabilities
        
        Raises:
            PluginRegistrationError: If registration fails
        """
        # Check for duplicate plugin names
        if plugin.name in self.plugins:
            existing = self.plugins[plugin.name]
            logger.warning(
                f"Plugin '{plugin.name}' already registered "
                f"(v{existing.version}), skipping v{plugin.version}"
            )
            return {}
        
        # Initialize plugin
        try:
            if not plugin.initialize():
                raise PluginRegistrationError(
                    f"Plugin '{plugin.name}' initialization failed"
                )
        except Exception as e:
            raise PluginRegistrationError(
                f"Plugin '{plugin.name}' initialization error: {e}"
            )
        
        # Register capabilities
        try:
            capabilities = plugin.register()
            
            if not isinstance(capabilities, dict):
                raise PluginRegistrationError(
                    f"Plugin '{plugin.name}' register() must return dict, "
                    f"got {type(capabilities)}"
                )
            
            # Wrap each capability with consent enforcement
            wrapped_caps = {}
            for cap_name, cap_func in capabilities.items():
                if not callable(cap_func):
                    logger.warning(
                        f"Skipping non-callable capability '{cap_name}' "
                        f"in plugin '{plugin.name}'"
                    )
                    continue
                
                wrapped = self._wrap_with_consent(cap_func, plugin)
                wrapped_caps[cap_name] = wrapped
                self._capability_to_plugin[cap_name] = plugin.name
            
            # Store plugin and capabilities
            self.plugins[plugin.name] = plugin
            self.capabilities.update(wrapped_caps)
            
            return wrapped_caps
        
        except Exception as e:
            raise PluginRegistrationError(
                f"Failed to register capabilities for plugin '{plugin.name}': {e}"
            )
    
    def _wrap_with_consent(
        self, 
        func: Callable, 
        plugin: AstraPlugin
    ) -> Callable:
        """
        Wrap capability function with consent enforcement.
        
        Args:
            func: Original capability function
            plugin: Plugin instance owning the capability
        
        Returns:
            Wrapped function with consent checking
        """
        @wraps(func)
        def wrapper(inputs: Dict[str, Any]) -> Dict[str, Any]:
            # Check if consent is required
            if plugin.consent_required:
                if self.consent_manager is None:
                    logger.warning(
                        f"Plugin '{plugin.name}' requires consent but no "
                        f"consent manager configured"
                    )
                    return {
                        "ok": False,
                        "error": "Consent required but no consent manager available"
                    }
                
                # Check consent
                try:
                    if not self.consent_manager.is_allowed(plugin.name):
                        logger.info(
                            f"Plugin '{plugin.name}' execution blocked by consent"
                        )
                        return {
                            "ok": False,
                            "error": f"Consent required for plugin '{plugin.name}'"
                        }
                except Exception as e:
                    logger.error(f"Consent check failed for '{plugin.name}': {e}")
                    return {
                        "ok": False,
                        "error": f"Consent check error: {e}"
                    }
            
            # Execute capability
            try:
                result = func(inputs)
                
                # Validate result format
                if not isinstance(result, dict):
                    logger.error(
                        f"Capability returned invalid type: {type(result)}"
                    )
                    return {
                        "ok": False,
                        "error": "Invalid capability return type"
                    }
                
                if "ok" not in result:
                    logger.warning("Capability result missing 'ok' field")
                    result["ok"] = True
                
                return result
            
            except Exception as e:
                logger.error(
                    f"Plugin '{plugin.name}' execution error: {e}", 
                    exc_info=True
                )
                return {
                    "ok": False,
                    "error": f"Execution error: {str(e)}"
                }
        
        return wrapper
    
    def get_plugin(self, name: str) -> Optional[AstraPlugin]:
        """Get plugin instance by name."""
        return self.plugins.get(name)
    
    def get_capability(self, name: str) -> Optional[Callable]:
        """Get capability callable by name."""
        return self.capabilities.get(name)
    
    def list_plugins(self) -> List[Dict[str, Any]]:
        """Get list of all loaded plugin metadata."""
        return [plugin.get_metadata() for plugin in self.plugins.values()]
    
    def list_capabilities(self) -> List[str]:
        """Get list of all registered capability names."""
        return list(self.capabilities.keys())
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all loaded plugins.
        
        Returns:
            Dictionary with overall health status and per-plugin details
        """
        plugin_health = {}
        unhealthy_count = 0
        
        for name, plugin in self.plugins.items():
            health = plugin.health_check()
            plugin_health[name] = health
            if health["status"] != "healthy":
                unhealthy_count += 1
        
        return {
            "status": "healthy" if unhealthy_count == 0 else "degraded",
            "total_plugins": len(self.plugins),
            "healthy_plugins": len(self.plugins) - unhealthy_count,
            "unhealthy_plugins": unhealthy_count,
            "plugins": plugin_health
        }
    
    def shutdown_all(self) -> None:
        """Shutdown all loaded plugins."""
        logger.info("Shutting down all plugins")
        for name, plugin in self.plugins.items():
            try:
                plugin.shutdown()
                logger.debug(f"Shutdown plugin '{name}'")
            except Exception as e:
                logger.error(f"Error shutting down plugin '{name}': {e}")


# Convenience function for simple usage
def load_plugins(
    package: str = "plugins",
    plugin_dirs: Optional[List[Path]] = None,
    consent_manager: Optional[Any] = None
) -> Dict[str, Callable]:
    """
    Load plugins from specified package/directories.
    
    Args:
        package: Python package name containing plugins
        plugin_dirs: Optional list of directories to search
        consent_manager: Optional consent manager for capability gating
    
    Returns:
        Dictionary of registered capability callables
    """
    loader = PluginLoader(consent_manager=consent_manager)
    return loader.load_plugins(package_name=package, plugin_dirs=plugin_dirs)
