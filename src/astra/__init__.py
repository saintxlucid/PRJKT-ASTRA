"""
ASTRA - Autonomous System for Transcendent Reasoning and Advancement

A production-grade local AI assistant with semantic memory capabilities.
"""

__version__ = "2.0.0"
__author__ = "ASTRA Team"
__license__ = "MIT"

# Try to import settings, but don't fail if models module unavailable
try:
    from astra.models.config import Settings, get_settings
    settings = get_settings()
    __all__ = ["Settings", "settings", "get_settings", "__version__"]
except ImportError:
    settings = None
    __all__ = ["__version__"]
