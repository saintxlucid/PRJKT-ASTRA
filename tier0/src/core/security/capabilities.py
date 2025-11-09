"""ASTRA Tier-0: Capability Guard System

Provides fine-grained access control for desktop operations.
All desktop actions must be explicitly allowed via allowlist.

Created: October 18, 2025
"""

from enum import Enum
from typing import Set
import os


class Capability(str, Enum):
    """Desktop action capabilities"""
    FOCUS = "focus"
    LAUNCH = "launch"
    TILE = "tile"
    TYPE = "type"
    HOTKEY = "hotkey"
    SCREENSHOT = "screenshot"
    CLOSE = "close"


class CapabilityGuard:
    """
    Guards desktop operations through explicit allowlisting.
    
    Checks that each action is explicitly enabled via ASTRA_DESKTOP_ALLOWLIST env var
    or constructor argument.
    """
    
    def __init__(self, allowlist: str | None = None):
        """
        Initialize capability guard.
        
        Args:
            allowlist: Semicolon-separated list of allowed capabilities
                      (e.g., "focus;launch;tile;type")
                      If None, uses ASTRA_DESKTOP_ALLOWLIST env var
        """
        raw = (allowlist or os.getenv("ASTRA_DESKTOP_ALLOWLIST", "")).lower()
        self.allowed: Set[str] = {x.strip() for x in raw.split(";") if x.strip()}
    
    def check(self, cap: Capability) -> None:
        """
        Check if capability is allowed.
        
        Args:
            cap: Capability to check
            
        Raises:
            PermissionError: If capability is not in allowlist
        """
        if cap.value not in self.allowed:
            raise PermissionError(f"Capability '{cap.value}' not allowed by policy")
    
    def is_allowed(self, cap: Capability) -> bool:
        """Check if capability is allowed (returns boolean instead of raising)"""
        return cap.value in self.allowed
    
    def get_allowed(self) -> Set[str]:
        """Get set of all allowed capabilities"""
        return self.allowed.copy()
