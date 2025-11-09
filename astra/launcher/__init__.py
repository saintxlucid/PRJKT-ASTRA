"""
Main module for ASTRA launcher package.
"""

# These type aliases help clarify the function signatures
from typing import Awaitable, Any, Dict, List, Optional, Set
import subprocess
import tempfile
from pathlib import Path

# Explicit re-export of main class
from .cleanup import CleanupManager

# Type aliases
ProcessType = subprocess.Popen[bytes]
PathType = Path
TempDirType = tempfile.TemporaryDirectory[str]

__all__ = [
    'CleanupManager',
    'ProcessType',
    'PathType',
    'TempDirType',
]