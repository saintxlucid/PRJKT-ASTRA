"""
ASTRA OS Controller Dispatcher Tests
Tests for action handlers, path allowlist, budget enforcement.
"""
import pytest
import os
import tempfile
from pathlib import Path
from controller.dispatch import (
    dispatch,
    is_allowed_path,
    ALLOWED_PREFIXES,
    BLOCKED_PATHS
)
from core.tokenizer import issue


# ===== Path Allowlist Tests =====

def test_path_allowlist_home():
    """Test that home directory paths are allowed."""
    home = str(Path.home())
    test_path = os.path.join(home, "test.txt")
    
    assert is_allowed_path(test_path)


def test_path_allowlist_cwd():
    """Test that current working directory paths are allowed."""
    cwd = str(Path.cwd())
    test_path = os.path.join(cwd, "test.txt")
    
    assert is_allowed_path(test_path)


def test_path_allowlist_temp():
    """Test that temp directory paths are allowed."""
    temp = tempfile.gettempdir()
    test_path = os.path.join(temp, "test.txt")
    
    assert is_allowed_path(test_path)


def test_path_blocked_windows():
    """Test that Windows system paths are blocked."""
    blocked_paths = [
        r"C:\Windows\System32\test.dll",
        r"C:\Program Files\test.exe",
        r"C:\Program Files (x86)\test.exe",
    ]
    
    for path in blocked_paths:
        assert not is_allowed_path(path)


def test_path_blocked_unauthorized():
    """Test that paths outside allowed directories are blocked."""
    # Assuming C:\unauthorized is not in allowed prefixes
    test_path = r"C:\unauthorized\test.txt"
    
    # This should be blocked (unless it happens to be in an allowed prefix)
    if not any(test_path.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        assert not is_allowed_path(test_path)


# ===== File System Action Tests =====

def test_fs_copy_valid_path():
    """Test fs.copy with valid paths."""
    # Create temp source file
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as src:
        src.write("test content")
        src_path = src.name
    
    try:
        dst_path = src_path + ".copy"
        
        # Issue token
        args = {"src": src_path, "dst": dst_path}
        token = issue("fs.copy", "fs", dst_path, args)
        
        # Get claims (simulate verification)
        from core.tokenizer import verify
        ok, reason, claims = verify(token, args)
        assert ok
        
        # Dispatch
        result = dispatch("fs.copy", args, claims)
        
        assert result["ok"]
        assert os.path.exists(dst_path)
        
        # Cleanup
        os.unlink(dst_path)
        
    finally:
        os.unlink(src_path)


def test_fs_copy_blocked_path():
    """Test fs.copy with blocked Windows path."""
    args = {
        "src": r"C:\Windows\System32\test.dll",
        "dst": os.path.join(tempfile.gettempdir(), "evil.dll")
    }
    
    token = issue("fs.copy", "fs", args["dst"], args)
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("fs.copy", args, claims)
    
    assert not result["ok"]
    assert "path_not_allowed" in result["error"]


def test_fs_move_valid_path():
    """Test fs.move with valid paths."""
    # Create temp source file
    with tempfile.NamedTemporaryFile(delete=False, mode='w') as src:
        src.write("test content")
        src_path = src.name
    
    try:
        dst_path = src_path + ".moved"
        
        args = {"src": src_path, "dst": dst_path}
        token = issue("fs.move", "fs", dst_path, args)
        
        from core.tokenizer import verify
        ok, reason, claims = verify(token, args)
        assert ok
        
        result = dispatch("fs.move", args, claims)
        
        assert result["ok"]
        assert os.path.exists(dst_path)
        assert not os.path.exists(src_path)
        
        # Cleanup
        os.unlink(dst_path)
        
    except Exception:
        # Cleanup on failure
        if os.path.exists(src_path):
            os.unlink(src_path)
        if os.path.exists(dst_path):
            os.unlink(dst_path)
        raise


# ===== Shell Execution Tests =====

def test_shell_run_valid():
    """Test shell.run with valid command."""
    args = {"cmd": "echo hello"}
    token = issue("shell.run", "process", "*", args, budget_ms=5000)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("shell.run", args, claims)
    
    assert result["ok"]
    assert result["result"]["code"] == 0
    assert "hello" in result["result"]["out"]


def test_shell_run_scope_denied():
    """Test shell.run fails with wrong scope."""
    args = {"cmd": "echo test"}
    # Issue token with wrong scope
    token = issue("shell.run", "fs", "*", args)  # fs instead of process
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("shell.run", args, claims)
    
    assert not result["ok"]
    assert "scope_denied" in result["error"]


def test_shell_run_timeout():
    """Test shell.run enforces timeout."""
    # Command that takes longer than budget
    args = {"cmd": "ping 127.0.0.1 -n 10"}  # ~10 seconds
    token = issue("shell.run", "process", "*", args, budget_ms=1000)  # 1 second budget
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("shell.run", args, claims)
    
    assert not result["ok"]
    assert "timeout" in result["error"].lower()


def test_shell_run_missing_cmd():
    """Test shell.run fails without cmd."""
    args = {}  # Missing cmd
    token = issue("shell.run", "process", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("shell.run", args, claims)
    
    assert not result["ok"]
    assert "missing_cmd" in result["error"]


# ===== Subject Mismatch Test =====

def test_dispatch_subject_mismatch():
    """Test dispatch fails when action doesn't match token subject."""
    args = {"cmd": "echo test"}
    # Issue token for fs.copy but try to run shell.run
    token = issue("fs.copy", "process", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    # Try to dispatch different action
    result = dispatch("shell.run", args, claims)
    
    assert not result["ok"]
    assert "sub_mismatch" in result["error"]


# ===== Window Management Tests =====

def test_window_tile_placeholder():
    """Test window.tile returns placeholder response."""
    args = {"left": "VSCode", "right": "Chrome"}
    token = issue("window.tile", "ui", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("window.tile", args, claims)
    
    # Should succeed but indicate not implemented
    assert result["ok"]
    assert "not yet implemented" in result["result"]["message"]


def test_window_focus_scope_denied():
    """Test window.focus fails with wrong scope."""
    args = {"title": "VSCode"}
    token = issue("window.focus", "process", "*", args)  # wrong scope
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("window.focus", args, claims)
    
    assert not result["ok"]
    assert "scope_denied" in result["error"]


# ===== Audio Control Tests =====

def test_audio_set_placeholder():
    """Test audio.set returns placeholder response."""
    args = {"action": "mute"}
    token = issue("audio.set", "ui", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("audio.set", args, claims)
    
    assert result["ok"]
    assert "not yet implemented" in result["result"]["message"]


# ===== Unknown Action Test =====

def test_dispatch_unknown_action():
    """Test dispatch fails for unknown action."""
    args = {}
    token = issue("unknown.action", "admin", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("unknown.action", args, claims)
    
    assert not result["ok"]
    assert "unknown_action" in result["error"]


# ===== Response Format Tests =====

def test_dispatch_includes_timing():
    """Test all dispatch responses include elapsed time."""
    args = {"cmd": "echo test"}
    token = issue("shell.run", "process", "*", args)
    
    from core.tokenizer import verify
    ok, reason, claims = verify(token, args)
    assert ok
    
    result = dispatch("shell.run", args, claims)
    
    assert "ms" in result
    assert isinstance(result["ms"], int)
    assert result["ms"] >= 0
