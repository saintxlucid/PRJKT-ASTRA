"""
ASTRA Plugin System - Package Initialization

Exposes plugin interface and loader for capability extensions.
"""

from astra.plugins.interface import (
    AstraPlugin,
    PluginError,
    PluginRegistrationError,
    PluginConsentError,
    PluginExecutionError
)

from astra.plugins.loader import (
    PluginLoader,
    load_plugins
)

__all__ = [
    # Interface
    "AstraPlugin",
    "PluginError",
    "PluginRegistrationError",
    "PluginConsentError",
    "PluginExecutionError",
    
    # Loader
    "PluginLoader",
    "load_plugins"
]

__version__ = "1.0.0"
