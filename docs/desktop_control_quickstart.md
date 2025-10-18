# Desktop Control Service (Windows)

A small, testable service for interacting with the Windows desktop:

- List visible windows with titles
- Focus a window by partial title
- Launch applications
- Clipboard get/set via PowerShell

## Usage

```python
from astra.services.desktop_control import DesktopController

# Create controller (Windows default). On non-Windows, inject a custom backend.
dc = DesktopController()

# List windows
for w in dc.list_windows():
    print(w.hwnd, w.title)

# Filter by title and focus
if dc.focus_window("Notepad"):
    print("Focused Notepad")

# Get active window title
print(dc.get_active_window_title())

# Launch an app (non-blocking)
proc = dc.launch_app("notepad.exe")

# Clipboard
dc.clipboard_set("Hello World")
print(dc.clipboard_get())
```

## Notes

- Windows-only default backend. On other OSes, pass a custom backend implementing `DesktopBackend`.
- Clipboard uses PowerShell `Set-Clipboard`/`Get-Clipboard` to preserve newlines and special characters.
- `launch_app(wait=True)` returns the process return code; otherwise returns `subprocess.Popen`.

## Testing

Unit tests use a `FakeBackend` to avoid OS-side effects and monkeypatch `subprocess.run` for clipboard calls.
Run:

- Single file: `pytest tests/services/test_desktop_control.py -q`
- Entire suite: `pytest -q`

## Extensibility

- Add move/resize window helpers in `WindowsBackend` (SetWindowPos)
- Add global hotkeys or automation hooks with Win32 APIs
- Provide alternate backends (e.g., macOS via AppKit, Linux via xdotool/wmctrl)
