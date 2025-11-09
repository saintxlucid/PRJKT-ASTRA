"""
ASTRA Identity State Management
================================

Thread-safe runtime role state.
"""

from __future__ import annotations

import threading


class RoleRuntime:
    """Thread-safe runtime role state manager."""

    def __init__(self, default: str = "ASTRA"):
        self._lock = threading.Lock()
        self._current = default

    @property
    def current_role(self) -> str:
        """Get current active role."""
        return self._current

    def set_role(self, role: str) -> None:
        """Set active role (thread-safe)."""
        with self._lock:
            self._current = role


__all__ = ["RoleRuntime"]
