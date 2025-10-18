"""
Desktop Control Service (Windows-first)

Features:
- List visible windows (title + handle)
- Focus a window by partial title
- Launch applications
- Clipboard get/set using PowerShell (to avoid low-level WinAPI complexity)

Design notes:
- The service is implemented via a small backend interface so it can be mocked in tests
- Default backend targets Windows APIs (ctypes + powershell). On non-Windows, it degrades
  gracefully and raises NotImplementedError for window APIs while clipboard uses platform checks.

Safety:
- No global state; no background hooks. All calls are synchronous with timeouts where applicable.
- Launching apps returns a subprocess handle for caller-managed lifecycle.

"""
from __future__ import annotations

import platform
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional, Protocol, Tuple


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str


class DesktopBackend(Protocol):
    """Protocol for OS-specific desktop operations."""

    def list_windows(self) -> List[WindowInfo]:
        ...

    def set_foreground(self, hwnd: int) -> bool:
        ...

    def get_foreground(self) -> Optional[int]:
        ...


class WindowsBackend:
    """Windows implementation using ctypes and PowerShell for clipboard."""

    def __init__(self) -> None:
        if platform.system() != "Windows":
            raise NotImplementedError("WindowsBackend is only available on Windows")

        # Lazy import of ctypes when used
        import ctypes  # noqa: WPS433
        from ctypes import wintypes  # noqa: WPS433

        self._ctypes = ctypes
        self._wintypes = wintypes

        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32

        # Configure GetWindowTextW buffer
        self._GetWindowTextW = self._user32.GetWindowTextW
        self._GetWindowTextLengthW = self._user32.GetWindowTextLengthW
        self._IsWindowVisible = self._user32.IsWindowVisible
        self._EnumWindows = self._user32.EnumWindows
        self._SetForegroundWindow = self._user32.SetForegroundWindow
        self._GetForegroundWindow = self._user32.GetForegroundWindow

    def list_windows(self) -> List[WindowInfo]:
        ctypes = self._ctypes

        WindowEnumProc = ctypes.WINFUNCTYPE(
            self._wintypes.BOOL, self._wintypes.HWND, self._wintypes.LPARAM
        )

        results: List[WindowInfo] = []

        def _callback(hwnd: int, lparam: int) -> bool:  # noqa: ARG001
            # Only visible, titled windows
            if self._IsWindowVisible(hwnd):
                length = self._GetWindowTextLengthW(hwnd)
                if length > 0:
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    self._GetWindowTextW(hwnd, buffer, length + 1)
                    title = buffer.value.strip()
                    if title:
                        results.append(WindowInfo(hwnd=hwnd, title=title))
            return True

        cb = WindowEnumProc(_callback)
        self._EnumWindows(cb, 0)
        return results

    def set_foreground(self, hwnd: int) -> bool:
        return bool(self._SetForegroundWindow(hwnd))

    def get_foreground(self) -> Optional[int]:
        hwnd = int(self._GetForegroundWindow())
        return hwnd or None


class DesktopController:
    """High-level desktop control with injectable backend and safe helpers."""

    def __init__(self, backend: Optional[DesktopBackend] = None):
        if backend is not None:
            self._backend: DesktopBackend = backend
        elif platform.system() == "Windows":
            self._backend = WindowsBackend()
        else:
            raise NotImplementedError("DesktopController requires Windows or a custom backend")

    # -------- Windows management --------
    def list_windows(self, title_contains: Optional[str] = None) -> List[WindowInfo]:
        windows = self._backend.list_windows()
        if title_contains:
            needle = title_contains.lower()
            windows = [w for w in windows if needle in w.title.lower()]
        return windows

    def focus_window(self, title_contains: str) -> bool:
        if not title_contains:
            raise ValueError("title_contains must be a non-empty string")
        matches = self.list_windows(title_contains)
        if not matches:
            return False
        # Prefer exact startswith match if available
        matches.sort(key=lambda w: (not w.title.startswith(title_contains), len(w.title)))
        return self._backend.set_foreground(matches[0].hwnd)

    def get_active_window_title(self) -> Optional[str]:
        current = self._backend.get_foreground()
        if current is None:
            return None
        for w in self._backend.list_windows():
            if w.hwnd == current:
                return w.title
        return None

    # -------- App launching --------
    def launch_app(
        self,
        exe: str,
        *args: str,
        cwd: Optional[str] = None,
        wait: bool = False,
        timeout: Optional[float] = 30.0,
    ) -> subprocess.Popen | int:
        """
        Launch an application.

        Returns Popen if wait=False, or the process return code if wait=True.
        """
        if not exe:
            raise ValueError("exe must be provided")
        cmd = [exe, *args]
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if wait:
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                raise TimeoutError(f"Process timed out: {cmd!r}")
            # Attach for caller inspection if needed
            proc.stdout_data = stdout  # type: ignore[attr-defined]
            proc.stderr_data = stderr  # type: ignore[attr-defined]
            return proc.returncode
        return proc

    # -------- Clipboard using PowerShell (Windows) --------
    def clipboard_set(self, text: str) -> None:
        if platform.system() != "Windows":
            raise NotImplementedError("clipboard_set is only implemented on Windows")
        # Use here-string to preserve newlines and special chars
        ps_script = f"Set-Clipboard -Value @'\n{text}\n'@"
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def clipboard_get(self) -> str:
        if platform.system() != "Windows":
            raise NotImplementedError("clipboard_get is only implemented on Windows")
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
            check=True,
            capture_output=True,
            text=True,
        )
        # PowerShell adds trailing newlines sometimes; strip a single trailing newline
        return completed.stdout.rstrip("\n")


__all__ = [
    "DesktopController",
    "DesktopBackend",
    "WindowsBackend",
    "WindowInfo",
]
