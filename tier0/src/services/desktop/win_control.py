"""ASTRA Tier-0: Windows Desktop Control

Provides voice-safe desktop control operations:
- Window focus/close
- Application launch
- Window tiling
- Text input
- Hotkey sequences
- Screenshots

All operations are guarded by CapabilityGuard policy.

Created: October 18, 2025
"""

import os
import time
import io
from typing import Optional
from pathlib import Path

from PIL import Image
import pyautogui
from pywinauto import Application
from pywinauto.findwindows import find_window
from pywinauto import Desktop

from ...core.security.capabilities import Capability, CapabilityGuard


# ---- Mini logger ----
class _Logger:
    def info(self, msg: str) -> None:
        print(f"[ASTRA][desktop] {msg}")
    
    def warn(self, msg: str) -> None:
        print(f"[ASTRA][desktop][WARN] {msg}")
    
    def error(self, msg: str) -> None:
        print(f"[ASTRA][desktop][ERR] {msg}")


logger = _Logger()


def _ensure_dir(path: str) -> None:
    """Ensure directory exists"""
    Path(path).mkdir(parents=True, exist_ok=True)


def require_enabled(flag: bool, msg: str) -> None:
    """Raise PermissionError if flag is False"""
    if not flag:
        raise PermissionError(msg)


def safe_path(path: str) -> str:
    """Normalize and expand environment variables in path"""
    return os.path.normpath(os.path.expandvars(path))


class WinDesktop:
    """
    Windows desktop control interface.
    
    All operations require explicit capability allowlisting via CapabilityGuard.
    """
    
    def __init__(self, guard: Optional[CapabilityGuard] = None):
        """
        Initialize desktop controller.
        
        Args:
            guard: CapabilityGuard instance (creates new one if None)
        """
        self.guard = guard or CapabilityGuard()
        self.enabled = os.getenv("ASTRA_DESKTOP_ENABLED", "true").lower() == "true"
    
    def _ensure(self) -> None:
        """Check if desktop control is enabled"""
        require_enabled(self.enabled, "Desktop control disabled by policy")
    
    # ---- Desktop Actions ----
    
    def focus(self, title_contains: str) -> str:
        """
        Focus window by title substring match.
        
        Args:
            title_contains: Substring of window title to focus
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If FOCUS capability not allowed
            RuntimeError: If window not found
        """
        self._ensure()
        self.guard.check(Capability.FOCUS)
        
        wins = Desktop(backend="uia").windows()
        for w in wins:
            window_text = w.window_text() or ""
            if title_contains.lower() in window_text.lower():
                w.set_focus()
                logger.info(f"Focused '{window_text}'")
                return f"Focused '{window_text}'."
        
        raise RuntimeError(f"Window not found: {title_contains}")
    
    def launch(self, exe_path: str, args: Optional[str] = None) -> str:
        """
        Launch executable with optional arguments.
        
        Args:
            exe_path: Path to executable
            args: Optional command-line arguments
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If LAUNCH capability not allowed or path not in SAFE_APPS_DIR
        """
        self._ensure()
        self.guard.check(Capability.LAUNCH)
        
        exe_path = safe_path(exe_path)
        safe_dir = os.getenv("ASTRA_SAFE_APPS_DIR", "C:\\Program Files\\").lower()
        
        if not exe_path.lower().startswith(safe_dir):
            raise PermissionError(f"Executable outside SAFE_APPS_DIR: {exe_path}")
        
        cmd = f'"{exe_path}" {args or ""}'.strip()
        Application(backend="uia").start(cmd)
        time.sleep(0.8)
        logger.info(f"Launched: {exe_path}")
        return "Launched"
    
    def tile(self, side: str) -> str:
        """
        Tile active window to screen side.
        
        Args:
            side: "left", "right", "up", or "down"
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If TILE capability not allowed
            ValueError: If side not in valid options
        """
        self._ensure()
        self.guard.check(Capability.TILE)
        
        side = side.lower().strip()
        hotkey_map = {
            "left": ("win", "left"),
            "right": ("win", "right"),
            "up": ("win", "up"),
            "down": ("win", "down"),
        }
        
        if side not in hotkey_map:
            raise ValueError(f"side must be {list(hotkey_map.keys())}")
        
        pyautogui.hotkey(*hotkey_map[side])
        logger.info(f"Tiled {side}")
        return f"Tiled {side}"
    
    def type_text(self, text: str) -> str:
        """
        Type text into focused window.
        
        Args:
            text: Text to type
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If TYPE capability not allowed
        """
        self._ensure()
        self.guard.check(Capability.TYPE)
        
        pyautogui.typewrite(text, interval=0.01)
        logger.info(f"Typed {len(text)} characters")
        return "Typed"
    
    def hotkey(self, *keys: str) -> str:
        """
        Send keyboard hotkey sequence.
        
        Args:
            keys: Keys to send (e.g., "alt", "tab")
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If HOTKEY capability not allowed
        """
        self._ensure()
        self.guard.check(Capability.HOTKEY)
        
        pyautogui.hotkey(*keys)
        logger.info(f"Hotkey sent: {'+'.join(keys)}")
        return "Hotkey sent"
    
    def screenshot(self, out_dir: str = "./screenshots") -> str:
        """
        Capture and save screenshot.
        
        Args:
            out_dir: Directory to save screenshot
            
        Returns:
            Path to saved screenshot
            
        Raises:
            PermissionError: If SCREENSHOT capability not allowed
        """
        self._ensure()
        self.guard.check(Capability.SCREENSHOT)
        
        _ensure_dir(out_dir)
        ts = int(time.time() * 1000)
        path = os.path.join(out_dir, f"shot_{ts}.png")
        
        im = pyautogui.screenshot()
        im.save(path)
        logger.info(f"Screenshot saved: {path}")
        return path
    
    def close(self, title_contains: str) -> str:
        """
        Close window by title substring match.
        
        Args:
            title_contains: Substring of window title to close
            
        Returns:
            Status message
            
        Raises:
            PermissionError: If CLOSE capability not allowed
            RuntimeError: If window close fails
        """
        self._ensure()
        self.guard.check(Capability.CLOSE)
        
        try:
            hwnd = find_window(best_match=title_contains)
            Desktop(backend="uia").window(handle=hwnd).close()
            logger.info(f"Closed window: {title_contains}")
            return "Closed"
        except Exception as e:
            raise RuntimeError(f"Close failed: {e}")
