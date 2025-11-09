# client/win_agent.py
"""
Client shim for issuing tokens and calling the controller via named pipe.
"""
import json
import uuid

try:
    import win32file
    import win32pipe
    WINDOWS = True
except ImportError:
    WINDOWS = False

from core.tokenizer import issue

PIPE = r"\\.\pipe\astra_bus"


def send(action: str, args: dict, scope: str = "process", policy: str = "action") -> dict:
    """
    Send an action request to the controller with a fresh token.

    Args:
        action: Action name (e.g., 'shell.run', 'fs.copy')
        args: Action arguments
        scope: Permission scope
        policy: Consent level ('info', 'action', 'admin')

    Returns:
        Response dictionary from controller
    """
    if not WINDOWS:
        return {"ok": False, "error": "win32api_not_available"}

    # Issue a fresh token
    res_hint = args.get("dst") or args.get("src") or "*"
    tok = issue(action, scope, res_hint, args, policy=policy)

    # Construct request
    req = {
        "id": str(uuid.uuid4()),
        "action": action,
        "args": args,
        "token": tok
    }

    # Open named pipe and send
    h = win32file.CreateFile(
        PIPE,
        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
        0,
        None,
        win32file.OPEN_EXISTING,
        0,
        None
    )

    try:
        win32file.WriteFile(h, (json.dumps(req) + "\n").encode())
        rc, data = win32file.ReadFile(h, 65536)
        return json.loads(data.decode().splitlines()[0])
    finally:
        win32file.CloseHandle(h)


# Convenience wrappers
def run_shell(cmd: str) -> dict:
    """Execute a shell command via controller."""
    return send("shell.run", {"cmd": cmd}, scope="process", policy="action")


def copy_file(src: str, dst: str) -> dict:
    """Copy a file via controller."""
    return send("fs.copy", {"src": src, "dst": dst}, scope="fs", policy="action")
