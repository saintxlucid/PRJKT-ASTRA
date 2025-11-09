# controller/pipe_server.py
"""
Named Pipe IPC server for ASTRA Controller Service.
Accepts JSON requests, verifies tokens, and dispatches safe OS actions.
"""
import json
from typing import Any

try:
    import pywintypes
    import win32file
    import win32pipe
    WINDOWS = True
except ImportError:
    WINDOWS = False
    print("Warning: pywin32 not available. Mock mode for development.")

from core.tokenizer import verify
from controller.dispatch import dispatch

PIPE_NAME = r"\\.\pipe\astra_bus"


def serve_once() -> None:
    """Handle a single pipe connection."""
    if not WINDOWS:
        print("Mock pipe server - Windows APIs not available")
        return

    h = win32pipe.CreateNamedPipe(
        PIPE_NAME,
        win32pipe.PIPE_ACCESS_DUPLEX,
        win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
        1, 65536, 65536, 0, None
    )

    try:
        win32pipe.ConnectNamedPipe(h, None)
    except pywintypes.error:
        win32file.CloseHandle(h)
        return

    try:
        while True:
            rc, data = win32file.ReadFile(h, 65536)
            if rc != 0:
                break

            for line in data.decode(errors="ignore").splitlines():
                if not line.strip():
                    continue

                try:
                    req = json.loads(line)
                except Exception:
                    resp = {"id": None, "ok": False, "error": "bad_json"}
                    win32file.WriteFile(h, (json.dumps(resp) + "\n").encode())
                    continue

                # Verify token
                token = req.get("token", "")
                args = req.get("args", {})
                ok, reason, claims = verify(token, args)

                if not ok:
                    resp = {"id": req.get("id"), "ok": False, "error": f"token:{reason}"}
                else:
                    # Dispatch the action
                    resp = dispatch(req.get("action"), args, claims)
                    resp["id"] = req.get("id")

                win32file.WriteFile(h, (json.dumps(resp) + "\n").encode())

    except pywintypes.error:
        pass
    finally:
        win32file.CloseHandle(h)


def main() -> None:
    """Main server loop."""
    print(f"ASTRA Controller starting on {PIPE_NAME}")

    if not WINDOWS:
        print("Running in mock mode - install pywin32 for full functionality")
        return

    while True:
        try:
            serve_once()
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Error in pipe server: {e}")
            continue


if __name__ == "__main__":
    main()
