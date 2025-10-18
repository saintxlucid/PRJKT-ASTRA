"""
ASTRA Task Agent Plugins
Safe, sandboxed tool integrations

Available plugins:
- file_ops: Safe filesystem operations
- system_info: System metrics and status
- ableton_plugin: DAW automation (Ableton, FL Studio)
"""

from .file_ops import register_file_ops
from .system_info import register_system_info
from . import ableton_plugin

__all__ = [
    'register_file_ops',
    'register_system_info',
    'ableton_plugin',
]
