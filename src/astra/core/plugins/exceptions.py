"""Plugin system exceptions"""

class PluginError(Exception):
    """Base class for plugin exceptions"""
    pass
    
class PluginLoadError(PluginError):
    """Error loading plugin module or manifest"""
    pass
    
class PluginValidationError(PluginError):
    """Error validating plugin schema or data"""
    pass
    
class PluginPermissionError(PluginError):
    """Error with plugin permissions"""
    pass
    
class PluginRuntimeError(PluginError):
    """Error during plugin execution"""
    pass