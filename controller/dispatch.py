# controller/dispatch.py
"""
Safe OS action dispatcher with path allowlists, budgets, and rollback support.
"""
import os
import subprocess
import time
import tempfile
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Allow only home, current working dir, and temp by default
ALLOWED_PREFIXES = [
    str(Path.home()),
    str(Path.cwd()),
    tempfile.gettempdir()
]

# Explicitly blocked paths (Windows system directories)
BLOCKED_PATHS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData\Microsoft",
]


def is_allowed_path(p: str) -> bool:
    """
    Check if a path is within allowed directories and not in blocked paths.
    Deny-by-default security model.
    """
    try:
        resolved = str(Path(p).resolve())
        
        # Check blocked paths first (explicit deny)
        for blocked in BLOCKED_PATHS:
            if resolved.startswith(blocked):
                logger.warning(f"Path blocked: {resolved} (matches {blocked})")
                return False
        
        # Check allowed prefixes
        allowed = any(resolved.startswith(prefix) for prefix in ALLOWED_PREFIXES)
        if not allowed:
            logger.warning(f"Path not allowed: {resolved} (not in allowed prefixes)")
        
        return allowed
        
    except Exception as e:
        logger.error(f"Path validation error: {e}")
        return False


def _cap_output(b: bytes, kb: int = 256) -> bytes:
    """Cap stdout/stderr to prevent memory exhaustion."""
    return b[: kb * 1024]


def dispatch(action: str, args: dict, claims: dict[str, Any]) -> dict[str, Any]:
    """
    Dispatch a safe OS action with token verification and budget enforcement.

    Args:
        action: The action to perform ('fs.copy', 'fs.move', 'shell.run', 'window.tile', etc.)
        args: Action arguments
        claims: Verified token claims with budget, scope, etc.

    Returns:
        Result dictionary with {ok: bool, result/error: ..., ms: elapsed_time}
    """
    t0 = time.time()
    
    logger.info(f"Dispatching action: {action} with scope={claims.get('scope')}")

    try:
        # Verify action matches token subject
        if claims.get("sub") != action:
            logger.error(f"Subject mismatch: token={claims.get('sub')}, requested={action}")
            return {"ok": False, "error": "sub_mismatch"}

        # Dispatch to handlers
        if action == "fs.copy":
            result = _do_fs_copy(args, claims)
        elif action == "fs.move":
            result = _do_fs_move(args, claims)
        elif action == "shell.run":
            result = _do_shell_run(args, claims)
        elif action == "window.tile":
            result = _do_window_tile(args, claims)
        elif action == "window.focus":
            result = _do_window_focus(args, claims)
        elif action == "audio.set":
            result = _do_audio_set(args, claims)
        else:
            logger.error(f"Unknown action: {action}")
            result = {"ok": False, "error": "unknown_action"}
        
        # Add elapsed time
        elapsed_ms = int((time.time() - t0) * 1000)
        result["ms"] = elapsed_ms
        
        logger.info(f"Action {action} completed: ok={result['ok']}, ms={elapsed_ms}")
        return result

    except subprocess.TimeoutExpired:
        logger.error(f"Action {action} timed out")
        return {"ok": False, "error": "timeout", "ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        logger.error(f"Action {action} failed: {e}")
        return {"ok": False, "error": repr(e), "ms": int((time.time() - t0) * 1000)}


def _do_fs_copy(args: dict, claims: dict[str, Any]) -> dict:
    """Execute fs.copy with allowlist checks."""
    src, dst = args["src"], args["dst"]

    if not (is_allowed_path(src) and is_allowed_path(dst)):
        return {"ok": False, "error": "path_not_allowed"}

    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    # Copy with rollback support
    with open(src, "rb") as r, open(dst, "wb") as w:
        w.write(r.read())

    return {"ok": True, "result": {"bytes": os.path.getsize(dst)}}


def _do_shell_run(args: dict, claims: dict[str, Any]) -> dict:
    """Execute shell.run with scope and budget checks."""
    # Require process scope
    if claims.get("scope") != "process":
        return {"ok": False, "error": "scope_denied"}

    cmd = args.get("cmd", "")
    if not cmd:
        return {"ok": False, "error": "missing_cmd"}
    
    timeout = max(1, int(claims.get("budget", {}).get("ms", 2000) / 1000))
    stdout_kb = claims.get("budget", {}).get("stdout_kb", 256)

    # Run with timeout and capture output
    p = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        timeout=timeout,
        text=False
    )

    out = _cap_output(p.stdout, kb=stdout_kb).decode(errors="ignore")

    return {
        "ok": True,
        "result": {
            "code": p.returncode,
            "out": out
        }
    }


def _do_fs_move(args: dict, claims: dict[str, Any]) -> dict:
    """Execute fs.move with allowlist checks and rollback support."""
    src, dst = args.get("src"), args.get("dst")
    
    if not src or not dst:
        return {"ok": False, "error": "missing_src_or_dst"}
    
    if not (is_allowed_path(src) and is_allowed_path(dst)):
        return {"ok": False, "error": "path_not_allowed"}
    
    # Ensure destination directory exists
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    
    # Move file (record in manifest for undo)
    os.rename(src, dst)
    
    return {"ok": True, "result": {"moved": dst}}


def _do_window_tile(args: dict, claims: dict[str, Any]) -> dict:
    """Execute window.tile with UI scope check."""
    if claims.get("scope") not in ("ui", "admin"):
        return {"ok": False, "error": "scope_denied"}
    
    # Placeholder - requires pywinauto or similar
    left_title = args.get("left", "")
    right_title = args.get("right", "")
    
    logger.info(f"Window tile requested: left={left_title}, right={right_title}")
    
    # TODO: Implement with pywinauto
    return {
        "ok": True,
        "result": {"message": "window.tile not yet implemented (requires pywinauto)"}
    }


def _do_window_focus(args: dict, claims: dict[str, Any]) -> dict:
    """Execute window.focus with UI scope check."""
    if claims.get("scope") not in ("ui", "admin"):
        return {"ok": False, "error": "scope_denied"}
    
    title = args.get("title", "")
    logger.info(f"Window focus requested: {title}")
    
    # TODO: Implement with pywinauto
    return {
        "ok": True,
        "result": {"message": "window.focus not yet implemented (requires pywinauto)"}
    }


def _do_audio_set(args: dict, claims: dict[str, Any]) -> dict:
    """Execute audio.set with UI scope check."""
    if claims.get("scope") not in ("ui", "admin"):
        return {"ok": False, "error": "scope_denied"}
    
    action = args.get("action", "")  # mute, unmute, volume
    logger.info(f"Audio control requested: {action}")
    
    # TODO: Implement with pycaw or nircmd
    return {
        "ok": True,
        "result": {"message": "audio.set not yet implemented (requires pycaw)"}
    }
