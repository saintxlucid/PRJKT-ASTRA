"""
ASTRA UI Automation Tools
Safe UI automation with focus tracking and timeouts.
Created: October 16, 2025
"""
import asyncio
from typing import Optional, Dict, Any, Tuple
import structlog
import platform
from pathlib import Path

from src.astra.core.tool_bus import tool

logger = structlog.get_logger()

if platform.system() == "Windows":
    import win32gui
    import win32con
    import win32api
    from win32com.client import GetObject
else:
    # For Linux/macOS, you'd want to use something like PyAutoGUI
    # This is Windows-focused for now
    pass

class WindowNotFoundError(Exception):
    """Window not found error"""
    pass

def find_window(title: str) -> int:
    """
    Find window handle by title.
    Args:
        title: Window title to find
    Returns:
        Window handle
    """
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if title.lower() in window_title.lower():
                windows.append(hwnd)
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    
    if not windows:
        raise WindowNotFoundError(f"Window not found: {title}")
        
    return windows[0]

def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
    """Get window rectangle"""
    return win32gui.GetWindowRect(hwnd)

def click_point(x: int, y: int, delay: float = 0.1):
    """
    Click at screen coordinates.
    Args:
        x: X coordinate
        y: Y coordinate
        delay: Delay between mouse down/up
    """
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
    asyncio.sleep(delay)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)

def send_keys(text: str, delay: float = 0.05):
    """
    Send keystrokes to active window.
    Args:
        text: Text to type
        delay: Delay between keystrokes
    """
    for char in text:
        win32api.keybd_event(ord(char.upper()), 0, 0, 0)
        asyncio.sleep(delay)
        win32api.keybd_event(ord(char.upper()), 0, win32con.KEYEVENTF_KEYUP, 0)

@tool(
    name="ui_focus",
    description="Focus a window by title",
    schema={
        "type": "object",
        "properties": {
            "window_title": {"type": "string"},
            "timeout": {"type": "number", "default": 5}
        },
        "required": ["window_title"]
    },
    timeout=10
)
async def focus_window(
    window_title: str,
    timeout: float = 5
) -> Dict[str, Any]:
    """
    Focus a window by its title.
    Args:
        window_title: Title of window to focus
        timeout: Time to wait for window
    Returns:
        Dict with window info
    """
    try:
        start_time = asyncio.get_event_loop().time()
        while True:
            try:
                hwnd = find_window(window_title)
                break
            except WindowNotFoundError:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(f"Window not found after {timeout}s: {window_title}")
                await asyncio.sleep(0.1)
                
        # Activate window
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        
        # Get window info
        rect = get_window_rect(hwnd)
        
        return {
            "success": True,
            "window_title": window_title,
            "handle": hwnd,
            "rect": {
                "left": rect[0],
                "top": rect[1],
                "right": rect[2],
                "bottom": rect[3]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "window_title": window_title,
            "error": str(e)
        }

@tool(
    name="ui_click",
    description="Click at coordinates or element",
    schema={
        "type": "object",
        "properties": {
            "x": {"type": "number"},
            "y": {"type": "number"},
            "delay": {"type": "number", "default": 0.1}
        },
        "required": ["x", "y"]
    },
    timeout=10
)
async def click_coordinates(
    x: int,
    y: int,
    delay: float = 0.1
) -> Dict[str, Any]:
    """
    Click at specific screen coordinates.
    Args:
        x: X coordinate
        y: Y coordinate
        delay: Click delay
    Returns:
        Dict with click info
    """
    try:
        click_point(x, y, delay)
        return {
            "success": True,
            "x": x,
            "y": y
        }
    except Exception as e:
        return {
            "success": False,
            "x": x,
            "y": y,
            "error": str(e)
        }

@tool(
    name="ui_type",
    description="Type text in active window",
    schema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "delay": {"type": "number", "default": 0.05}
        },
        "required": ["text"]
    },
    timeout=30
)
async def type_text(
    text: str,
    delay: float = 0.05
) -> Dict[str, Any]:
    """
    Type text in the active window.
    Args:
        text: Text to type
        delay: Delay between keystrokes
    Returns:
        Dict with typing info
    """
    try:
        send_keys(text, delay)
        return {
            "success": True,
            "text": text
        }
    except Exception as e:
        return {
            "success": False,
            "text": text,
            "error": str(e)
        }

@tool(
    name="ui_hotkey",
    description="Send hotkey combination",
    schema={
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            }
        },
        "required": ["keys"]
    },
    timeout=10
)
async def send_hotkey(keys: List[str]) -> Dict[str, Any]:
    """
    Send hotkey combination.
    Args:
        keys: List of key names
    Returns:
        Dict with hotkey info
    """
    try:
        key_codes = [ord(k.upper()) for k in keys]
        
        # Press all keys
        for code in key_codes:
            win32api.keybd_event(code, 0, 0, 0)
            
        await asyncio.sleep(0.1)
        
        # Release in reverse order
        for code in reversed(key_codes):
            win32api.keybd_event(code, 0, win32con.KEYEVENTF_KEYUP, 0)
            
        return {
            "success": True,
            "keys": keys
        }
    except Exception as e:
        return {
            "success": False,
            "keys": keys,
            "error": str(e)
        }