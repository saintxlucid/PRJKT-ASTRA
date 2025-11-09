"""
ASTRA 2.0 Input Controller - Keyboard and Mouse Automation
"""
from typing import Tuple, Optional
import pyautogui
from ..security.permission_kernel import require_permission
from ..security.activity_audit import audit_action

# Configure PyAutoGUI safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.5  # Add delay between actions

class InputController:
    @require_permission("input.keyboard.type")
    def type_text(self, text: str, interval: float = 0.1) -> None:
        """Type text with optional delay between keystrokes"""
        audit_action("input.keyboard.type", {"length": len(text)})
        pyautogui.typewrite(text, interval=interval)
    
    @require_permission("input.mouse.move")
    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> None:
        """Move mouse to absolute screen coordinates"""
        audit_action("input.mouse.move", {"x": x, "y": y})
        pyautogui.moveTo(x, y, duration=duration)
    
    @require_permission("input.mouse.click")
    def click(self, button: str = "left", clicks: int = 1) -> None:
        """Perform mouse click at current position"""
        audit_action("input.mouse.click", {"button": button, "clicks": clicks})
        pyautogui.click(button=button, clicks=clicks)
    
    @require_permission("input.keyboard.hotkey")
    def press_hotkey(self, *keys: str) -> None:
        """Press multiple keys simultaneously (e.g., 'ctrl', 'c')"""
        audit_action("input.keyboard.hotkey", {"keys": keys})
        pyautogui.hotkey(*keys)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse coordinates (no permission needed)"""
        x, y = pyautogui.position()
        return (x, y)
    
    @require_permission("input.screen.screenshot")
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> bytes:
        """Capture screenshot of full screen or region"""
        audit_action("input.screen.screenshot", {"region": region})
        return pyautogui.screenshot(region=region)._getvalue()