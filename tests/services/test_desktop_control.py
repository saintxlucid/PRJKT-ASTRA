import platform
import subprocess
from typing import List, Optional, TypedDict

import pytest

from astra.services.desktop_control import DesktopController, DesktopBackend, WindowInfo


class FakeBackend(DesktopBackend):
    def __init__(self, windows: List[WindowInfo], focused: Optional[int] = None) -> None:
        self._windows = list(windows)
        self._focused = focused

    def list_windows(self) -> List[WindowInfo]:
        return list(self._windows)

    def set_foreground(self, hwnd: int) -> bool:
        if any(w.hwnd == hwnd for w in self._windows):
            self._focused = hwnd
            return True
        return False

    def get_foreground(self) -> Optional[int]:
        return self._focused


def test_list_and_focus_with_fake_backend() -> None:
    backend = FakeBackend(
        [
            WindowInfo(hwnd=1, title="Visual Studio Code"),
            WindowInfo(hwnd=2, title="Notepad - notes.txt"),
            WindowInfo(hwnd=3, title="Chrome - ASTRA Dashboard"),
        ],
        focused=1,
    )
    dc = DesktopController(backend=backend)

    all_windows = dc.list_windows()
    assert len(all_windows) == 3

    code_windows = dc.list_windows("code")
    assert len(code_windows) == 1
    assert code_windows[0].title == "Visual Studio Code"

    assert dc.focus_window("Chrome") is True
    assert dc.get_active_window_title() == "Chrome - ASTRA Dashboard"


def test_focus_window_no_match_returns_false() -> None:
    backend = FakeBackend([WindowInfo(hwnd=5, title="Terminal")], focused=5)
    dc = DesktopController(backend=backend)
    assert dc.focus_window("Nonexistent App") is False


def test_focus_window_requires_query() -> None:
    backend = FakeBackend([WindowInfo(hwnd=5, title="Terminal")], focused=5)
    dc = DesktopController(backend=backend)
    with pytest.raises(ValueError):
        dc.focus_window("")


class _Calls(TypedDict):
    set: Optional[str]
    get: Optional[bool]


@pytest.mark.skipif(platform.system() != "Windows", reason="Clipboard via PowerShell is Windows-only")
def test_clipboard_roundtrip_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: _Calls = {"set": None, "get": None}

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(args, list) and args[-1].startswith("Set-Clipboard"):
            # Extract the here-string content roughly
            script = args[-1]
            content = script.split("@'\n", 1)[1].rsplit("\n'@", 1)[0]
            calls["set"] = content
            # Simulate success CompletedProcess
            class CPSuccess:
                def __init__(self) -> None:
                    self.returncode = 0
                    self.stdout = ""
                    self.stderr = ""

            return CPSuccess()
        elif isinstance(args, list) and args[-1] == "Get-Clipboard":
            calls["get"] = True

            class CPGet:
                def __init__(self, text: str) -> None:
                    self.returncode = 0
                    self.stdout = text
                    self.stderr = ""

            text_in: str = calls["set"] if isinstance(calls["set"], str) else ""
            return CPGet(text_in.rstrip("\n") + "\n")
        raise AssertionError("unexpected subprocess.run args: %r" % (args,))

    monkeypatch.setattr(subprocess, "run", fake_run)

    dc = DesktopController(backend=FakeBackend([]))
    text = "Hello\nWorld"
    dc.clipboard_set(text)
    read = dc.clipboard_get()
    assert read == text
