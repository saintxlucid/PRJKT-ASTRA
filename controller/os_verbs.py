# controller/os_verbs.py
"""
Windows OS Automation Verbs for ASTRA OS.
Uses pywin32 for Win32 API access to control windows, apps, and system.
"""
import subprocess
import sys
from typing import Any

# Check if pywin32 is available (Windows only)
PYWIN32_AVAILABLE = False
if sys.platform == "win32":
    try:
        import win32api
        import win32con
        import win32gui
        import win32process

        PYWIN32_AVAILABLE = True
    except ImportError:
        print("Warning: pywin32 not installed. OS automation disabled.")


def window_list() -> dict[str, Any]:
    """
    List all visible windows.

    Returns:
        Dict with ok, windows list (hwnd, title, pid)
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    windows = []

    def enum_callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:  # Only include windows with titles
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                windows.append({"hwnd": hwnd, "title": title, "pid": pid})
        return True

    try:
        win32gui.EnumWindows(enum_callback, None)
        return {"ok": True, "windows": windows, "count": len(windows)}
    except Exception as e:
        return {"ok": False, "error": f"Failed to list windows: {e}"}


def window_focus(hwnd: int) -> dict[str, Any]:
    """
    Focus window by handle.

    Args:
        hwnd: Window handle (integer)

    Returns:
        Dict with ok, focused window info
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        # Check if window exists
        if not win32gui.IsWindow(hwnd):
            return {"ok": False, "error": f"Invalid window handle: {hwnd}"}

        # Bring window to foreground
        win32gui.SetForegroundWindow(hwnd)

        # Get window title for confirmation
        title = win32gui.GetWindowText(hwnd)

        return {"ok": True, "hwnd": hwnd, "title": title, "action": "focused"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to focus window: {e}"}


def window_find_by_title(title: str, exact: bool = False) -> dict[str, Any]:
    """
    Find window by title (substring or exact match).

    Args:
        title: Window title to search for
        exact: If True, require exact match (default: substring)

    Returns:
        Dict with ok, matching windows
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    result = window_list()
    if not result["ok"]:
        return result

    title_lower = title.lower()
    matches = []

    for window in result["windows"]:
        window_title = window["title"]
        if exact:
            if window_title == title:
                matches.append(window)
        else:
            if title_lower in window_title.lower():
                matches.append(window)

    return {"ok": True, "matches": matches, "count": len(matches)}


def window_move(hwnd: int, x: int, y: int, width: int, height: int) -> dict[str, Any]:
    """
    Move and resize window.

    Args:
        hwnd: Window handle
        x: Left position
        y: Top position
        width: Window width
        height: Window height

    Returns:
        Dict with ok, window geometry
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        if not win32gui.IsWindow(hwnd):
            return {"ok": False, "error": f"Invalid window handle: {hwnd}"}

        win32gui.MoveWindow(hwnd, x, y, width, height, True)

        return {
            "ok": True,
            "hwnd": hwnd,
            "geometry": {"x": x, "y": y, "width": width, "height": height},
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to move window: {e}"}


def window_maximize(hwnd: int) -> dict[str, Any]:
    """
    Maximize window.

    Args:
        hwnd: Window handle

    Returns:
        Dict with ok, window state
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        if not win32gui.IsWindow(hwnd):
            return {"ok": False, "error": f"Invalid window handle: {hwnd}"}

        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)

        return {"ok": True, "hwnd": hwnd, "state": "maximized"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to maximize window: {e}"}


def window_minimize(hwnd: int) -> dict[str, Any]:
    """
    Minimize window.

    Args:
        hwnd: Window handle

    Returns:
        Dict with ok, window state
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        if not win32gui.IsWindow(hwnd):
            return {"ok": False, "error": f"Invalid window handle: {hwnd}"}

        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

        return {"ok": True, "hwnd": hwnd, "state": "minimized"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to minimize window: {e}"}


def window_close(hwnd: int) -> dict[str, Any]:
    """
    Close window gracefully.

    Args:
        hwnd: Window handle

    Returns:
        Dict with ok, close status
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        if not win32gui.IsWindow(hwnd):
            return {"ok": False, "error": f"Invalid window handle: {hwnd}"}

        # Send WM_CLOSE message (graceful close)
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)

        return {"ok": True, "hwnd": hwnd, "action": "close_requested"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to close window: {e}"}


def app_launch(exe_path: str, args: list[str] | None = None) -> dict[str, Any]:
    """
    Launch application by executable path.

    Args:
        exe_path: Path to executable
        args: Optional command-line arguments

    Returns:
        Dict with ok, process ID
    """
    try:
        cmd = [exe_path]
        if args:
            cmd.extend(args)

        # Launch process without blocking
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )

        return {"ok": True, "exe": exe_path, "pid": process.pid, "args": args or []}
    except FileNotFoundError:
        return {"ok": False, "error": f"Executable not found: {exe_path}"}
    except Exception as e:
        return {"ok": False, "error": f"Failed to launch app: {e}"}


def process_kill(pid: int, force: bool = False) -> dict[str, Any]:
    """
    Kill process by PID.

    Args:
        pid: Process ID
        force: If True, force kill (default: graceful)

    Returns:
        Dict with ok, kill status
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        # Open process handle
        handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE, False, pid)

        # Terminate process
        exit_code = 1 if force else 0
        win32api.TerminateProcess(handle, exit_code)
        win32api.CloseHandle(handle)

        return {
            "ok": True,
            "pid": pid,
            "action": "killed",
            "force": force,
        }
    except Exception as e:
        return {"ok": False, "error": f"Failed to kill process {pid}: {e}"}


def screen_get_size() -> dict[str, Any]:
    """
    Get screen dimensions.

    Returns:
        Dict with ok, width, height
    """
    if not PYWIN32_AVAILABLE:
        return {"ok": False, "error": "pywin32 not available (Windows only)"}

    try:
        width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        return {"ok": True, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": f"Failed to get screen size: {e}"}


def volume_get() -> dict[str, Any]:
    """
    Get system volume level.

    Returns:
        Dict with ok, volume (0.0-1.0)

    Note: Requires pycaw or comtypes. Returns error if not available.
    """
    return {
        "ok": False,
        "error": "Volume control requires pycaw library (not implemented in basic version)",
    }


def volume_set(level: float) -> dict[str, Any]:
    """
    Set system volume level.

    Args:
        level: Volume level 0.0 (mute) to 1.0 (max)

    Returns:
        Dict with ok, volume level

    Note: Requires pycaw or comtypes. Returns error if not available.
    """
    return {
        "ok": False,
        "error": "Volume control requires pycaw library (not implemented in basic version)",
    }


# OS Verb registry for tool integration
OS_VERBS = {
    "window.list": {
        "func": window_list,
        "description": "List all visible windows",
        "scope": "info",
        "args": {},
    },
    "window.focus": {
        "func": window_focus,
        "description": "Focus window by handle",
        "scope": "action",
        "args": {"hwnd": "int"},
    },
    "window.find": {
        "func": window_find_by_title,
        "description": "Find window by title",
        "scope": "info",
        "args": {"title": "str", "exact": "bool"},
    },
    "window.move": {
        "func": window_move,
        "description": "Move and resize window",
        "scope": "action",
        "args": {"hwnd": "int", "x": "int", "y": "int", "width": "int", "height": "int"},
    },
    "window.maximize": {
        "func": window_maximize,
        "description": "Maximize window",
        "scope": "action",
        "args": {"hwnd": "int"},
    },
    "window.minimize": {
        "func": window_minimize,
        "description": "Minimize window",
        "scope": "action",
        "args": {"hwnd": "int"},
    },
    "window.close": {
        "func": window_close,
        "description": "Close window gracefully",
        "scope": "action",
        "args": {"hwnd": "int"},
    },
    "app.launch": {
        "func": app_launch,
        "description": "Launch application by path",
        "scope": "action",
        "args": {"exe_path": "str", "args": "list[str]"},
    },
    "process.kill": {
        "func": process_kill,
        "description": "Kill process by PID",
        "scope": "admin",
        "args": {"pid": "int", "force": "bool"},
    },
    "screen.size": {
        "func": screen_get_size,
        "description": "Get screen dimensions",
        "scope": "info",
        "args": {},
    },
}
