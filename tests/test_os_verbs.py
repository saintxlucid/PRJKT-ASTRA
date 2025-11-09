# tests/test_os_verbs.py
"""
Tests for OS verbs - Windows automation functions.
Uses mocking for pywin32 functions since tests run in CI.
"""
import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_pywin32():
    """Mock pywin32 modules for all tests."""
    # Create mock modules
    win32api = MagicMock()
    win32con = MagicMock()
    win32gui = MagicMock()
    win32process = MagicMock()

    # Set up module mocks
    sys.modules["win32api"] = win32api
    sys.modules["win32con"] = win32con
    sys.modules["win32gui"] = win32gui
    sys.modules["win32process"] = win32process

    # Mock PYWIN32_AVAILABLE flag
    import controller.os_verbs as os_verbs

    os_verbs.PYWIN32_AVAILABLE = True

    yield {
        "win32api": win32api,
        "win32con": win32con,
        "win32gui": win32gui,
        "win32process": win32process,
    }


class TestWindowList:
    """Test window enumeration."""

    def test_window_list_empty(self, mock_pywin32):
        """Test listing windows when none exist."""
        from controller.os_verbs import window_list

        # Mock EnumWindows to call callback with no windows
        def mock_enum(callback, arg):
            # Don't call callback at all
            pass

        mock_pywin32["win32gui"].EnumWindows = mock_enum

        result = window_list()

        assert result["ok"] is True
        assert result["windows"] == []
        assert result["count"] == 0

    def test_window_list_multiple(self, mock_pywin32):
        """Test listing multiple windows."""
        from controller.os_verbs import window_list

        # Mock EnumWindows to call callback with sample windows
        def mock_enum(callback, arg):
            callback(12345, None)  # Visible window
            callback(67890, None)  # Another visible window

        mock_pywin32["win32gui"].EnumWindows = mock_enum
        mock_pywin32["win32gui"].IsWindowVisible = lambda hwnd: True
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: f"Window {hwnd}"
        mock_pywin32["win32process"].GetWindowThreadProcessId = lambda hwnd: (0, hwnd // 100)

        result = window_list()

        assert result["ok"] is True
        assert result["count"] == 2
        assert len(result["windows"]) == 2
        assert result["windows"][0]["hwnd"] == 12345
        assert result["windows"][0]["title"] == "Window 12345"
        assert result["windows"][0]["pid"] == 123

    def test_window_list_filters_invisible(self, mock_pywin32):
        """Test that invisible windows are filtered out."""
        from controller.os_verbs import window_list

        def mock_enum(callback, arg):
            callback(11111, None)  # Visible
            callback(22222, None)  # Invisible
            callback(33333, None)  # Visible

        mock_pywin32["win32gui"].EnumWindows = mock_enum
        mock_pywin32["win32gui"].IsWindowVisible = lambda hwnd: hwnd != 22222
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: f"Window {hwnd}"
        mock_pywin32["win32process"].GetWindowThreadProcessId = lambda hwnd: (0, hwnd // 100)

        result = window_list()

        assert result["ok"] is True
        assert result["count"] == 2
        assert 22222 not in [w["hwnd"] for w in result["windows"]]


class TestWindowFocus:
    """Test window focusing."""

    def test_window_focus_valid(self, mock_pywin32):
        """Test focusing a valid window."""
        from controller.os_verbs import window_focus

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].SetForegroundWindow = MagicMock()
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: "Test Window"

        result = window_focus(12345)

        assert result["ok"] is True
        assert result["hwnd"] == 12345
        assert result["title"] == "Test Window"
        assert result["action"] == "focused"
        mock_pywin32["win32gui"].SetForegroundWindow.assert_called_once_with(12345)

    def test_window_focus_invalid_handle(self, mock_pywin32):
        """Test focusing an invalid window handle."""
        from controller.os_verbs import window_focus

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: False

        result = window_focus(99999)

        assert result["ok"] is False
        assert "Invalid window handle" in result["error"]

    def test_window_focus_error(self, mock_pywin32):
        """Test error handling when focus fails."""
        from controller.os_verbs import window_focus

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].SetForegroundWindow = MagicMock(
            side_effect=Exception("Access denied")
        )

        result = window_focus(12345)

        assert result["ok"] is False
        assert "Failed to focus window" in result["error"]
        assert "Access denied" in result["error"]


class TestWindowFind:
    """Test finding windows by title."""

    def test_window_find_exact_match(self, mock_pywin32):
        """Test finding window with exact title match."""
        from controller.os_verbs import window_find_by_title

        # Mock window_list to return sample windows
        with patch("controller.os_verbs.window_list") as mock_list:
            mock_list.return_value = {
                "ok": True,
                "windows": [
                    {"hwnd": 111, "title": "Chrome", "pid": 1000},
                    {"hwnd": 222, "title": "Firefox", "pid": 2000},
                    {"hwnd": 333, "title": "Edge", "pid": 3000},
                ],
                "count": 3,
            }

            result = window_find_by_title("Chrome", exact=True)

            assert result["ok"] is True
            assert result["count"] == 1
            assert result["windows"][0]["hwnd"] == 111
            assert result["windows"][0]["title"] == "Chrome"

    def test_window_find_substring(self, mock_pywin32):
        """Test finding windows with substring match."""
        from controller.os_verbs import window_find_by_title

        with patch("controller.os_verbs.window_list") as mock_list:
            mock_list.return_value = {
                "ok": True,
                "windows": [
                    {"hwnd": 111, "title": "Google Chrome - Tab 1", "pid": 1000},
                    {"hwnd": 222, "title": "Mozilla Firefox - Tab 1", "pid": 2000},
                    {"hwnd": 333, "title": "Chrome Developer Tools", "pid": 3000},
                ],
                "count": 3,
            }

            result = window_find_by_title("Chrome", exact=False)

            assert result["ok"] is True
            assert result["count"] == 2
            assert 111 in [w["hwnd"] for w in result["windows"]]
            assert 333 in [w["hwnd"] for w in result["windows"]]

    def test_window_find_no_match(self, mock_pywin32):
        """Test finding non-existent window."""
        from controller.os_verbs import window_find_by_title

        with patch("controller.os_verbs.window_list") as mock_list:
            mock_list.return_value = {
                "ok": True,
                "windows": [
                    {"hwnd": 111, "title": "Chrome", "pid": 1000},
                ],
                "count": 1,
            }

            result = window_find_by_title("Safari", exact=True)

            assert result["ok"] is True
            assert result["count"] == 0
            assert result["windows"] == []


class TestWindowMove:
    """Test window move/resize."""

    def test_window_move_valid(self, mock_pywin32):
        """Test moving a valid window."""
        from controller.os_verbs import window_move

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].MoveWindow = MagicMock(return_value=True)
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: "Test Window"

        result = window_move(12345, 100, 200, 800, 600)

        assert result["ok"] is True
        assert result["hwnd"] == 12345
        assert result["x"] == 100
        assert result["y"] == 200
        assert result["width"] == 800
        assert result["height"] == 600
        mock_pywin32["win32gui"].MoveWindow.assert_called_once_with(12345, 100, 200, 800, 600, True)

    def test_window_move_invalid_handle(self, mock_pywin32):
        """Test moving invalid window."""
        from controller.os_verbs import window_move

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: False

        result = window_move(99999, 0, 0, 100, 100)

        assert result["ok"] is False
        assert "Invalid window handle" in result["error"]


class TestWindowStateControl:
    """Test window maximize/minimize/close."""

    def test_window_maximize(self, mock_pywin32):
        """Test maximizing a window."""
        from controller.os_verbs import window_maximize

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].ShowWindow = MagicMock()
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: "Test Window"
        mock_pywin32["win32con"].SW_MAXIMIZE = 3

        result = window_maximize(12345)

        assert result["ok"] is True
        assert result["action"] == "maximized"
        mock_pywin32["win32gui"].ShowWindow.assert_called_once_with(12345, 3)

    def test_window_minimize(self, mock_pywin32):
        """Test minimizing a window."""
        from controller.os_verbs import window_minimize

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].ShowWindow = MagicMock()
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: "Test Window"
        mock_pywin32["win32con"].SW_MINIMIZE = 6

        result = window_minimize(12345)

        assert result["ok"] is True
        assert result["action"] == "minimized"
        mock_pywin32["win32gui"].ShowWindow.assert_called_once_with(12345, 6)

    def test_window_close(self, mock_pywin32):
        """Test closing a window."""
        from controller.os_verbs import window_close

        mock_pywin32["win32gui"].IsWindow = lambda hwnd: True
        mock_pywin32["win32gui"].PostMessage = MagicMock()
        mock_pywin32["win32gui"].GetWindowText = lambda hwnd: "Test Window"
        mock_pywin32["win32con"].WM_CLOSE = 0x0010

        result = window_close(12345)

        assert result["ok"] is True
        assert result["action"] == "close_requested"
        mock_pywin32["win32gui"].PostMessage.assert_called_once_with(12345, 0x0010, 0, 0)


class TestAppLaunch:
    """Test app launching."""

    def test_app_launch_no_args(self, mock_pywin32):
        """Test launching app without arguments."""
        from controller.os_verbs import app_launch

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = app_launch("notepad.exe")

            assert result["ok"] is True
            assert result["exe"] == "notepad.exe"
            assert result["pid"] == 12345
            mock_popen.assert_called_once()

    def test_app_launch_with_args(self, mock_pywin32):
        """Test launching app with arguments."""
        from controller.os_verbs import app_launch

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 54321
            mock_popen.return_value = mock_process

            result = app_launch("notepad.exe", ["test.txt"])

            assert result["ok"] is True
            assert result["args"] == ["test.txt"]
            assert result["pid"] == 54321

    def test_app_launch_error(self, mock_pywin32):
        """Test app launch failure."""
        from controller.os_verbs import app_launch

        with patch("subprocess.Popen", side_effect=FileNotFoundError("Not found")):
            result = app_launch("nonexistent.exe")

            assert result["ok"] is False
            assert "Failed to launch" in result["error"]


class TestProcessKill:
    """Test process termination."""

    def test_process_kill_normal(self, mock_pywin32):
        """Test normal process termination."""
        from controller.os_verbs import process_kill

        mock_handle = MagicMock()
        mock_pywin32["win32api"].OpenProcess = MagicMock(return_value=mock_handle)
        mock_pywin32["win32api"].TerminateProcess = MagicMock()
        mock_pywin32["win32api"].CloseHandle = MagicMock()

        result = process_kill(12345, force=False)

        assert result["ok"] is True
        assert result["pid"] == 12345
        assert result["method"] == "normal"

    def test_process_kill_force(self, mock_pywin32):
        """Test forced process termination."""
        from controller.os_verbs import process_kill

        mock_handle = MagicMock()
        mock_pywin32["win32api"].OpenProcess = MagicMock(return_value=mock_handle)
        mock_pywin32["win32api"].TerminateProcess = MagicMock()
        mock_pywin32["win32api"].CloseHandle = MagicMock()

        result = process_kill(12345, force=True)

        assert result["ok"] is True
        assert result["method"] == "forced"

    def test_process_kill_error(self, mock_pywin32):
        """Test process kill error."""
        from controller.os_verbs import process_kill

        mock_pywin32["win32api"].OpenProcess = MagicMock(side_effect=Exception("Access denied"))

        result = process_kill(99999, force=False)

        assert result["ok"] is False
        assert "Failed to terminate" in result["error"]


class TestScreenInfo:
    """Test screen information."""

    def test_screen_get_size(self, mock_pywin32):
        """Test getting screen size."""
        from controller.os_verbs import screen_get_size

        mock_pywin32["win32api"].GetSystemMetrics = lambda metric: 1920 if metric == 0 else 1080
        mock_pywin32["win32con"].SM_CXSCREEN = 0
        mock_pywin32["win32con"].SM_CYSCREEN = 1

        result = screen_get_size()

        assert result["ok"] is True
        assert result["width"] == 1920
        assert result["height"] == 1080


class TestPywin32Unavailable:
    """Test graceful degradation when pywin32 is not available."""

    def test_functions_return_error_without_pywin32(self):
        """Test that all functions handle missing pywin32."""
        import controller.os_verbs as os_verbs

        # Temporarily set flag to False
        original_flag = os_verbs.PYWIN32_AVAILABLE
        os_verbs.PYWIN32_AVAILABLE = False

        try:
            # Test each function
            result = os_verbs.window_list()
            assert result["ok"] is False
            assert "pywin32 not available" in result["error"]

            result = os_verbs.window_focus(12345)
            assert result["ok"] is False

            result = os_verbs.app_launch("notepad.exe")
            assert result["ok"] is False

        finally:
            os_verbs.PYWIN32_AVAILABLE = original_flag
