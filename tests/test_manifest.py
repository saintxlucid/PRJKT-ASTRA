"""
Tests for Action Manifest (undo semantics).

Tests:
- Record action to JSONL
- Read entries back
- Rollback single action
- Rollback multiple actions
- Rollback with count limit
- fs.move undo
- fs.delete undo (with backup)
- window.state undo (placeholder)
- Clear manifest
"""

import json
import tempfile
from pathlib import Path
import pytest

from controller.manifest import ActionManifest


@pytest.fixture
def temp_manifest():
    """Create temporary manifest file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        manifest_path = f.name
    
    manifest = ActionManifest(manifest_path)
    yield manifest
    
    # Cleanup
    Path(manifest_path).unlink(missing_ok=True)


def test_manifest_creation(temp_manifest):
    """Test manifest file creation."""
    assert temp_manifest.path.exists()
    assert temp_manifest.path.stat().st_size == 0
    assert len(temp_manifest) == 0


def test_record_action(temp_manifest):
    """Test recording action to manifest."""
    temp_manifest.record(
        "fs.move",
        {"src": "a.txt", "dst": "b.txt"},
        undo={"action": "fs.move", "args": {"src": "b.txt", "dst": "a.txt"}}
    )
    
    entries = temp_manifest.get_entries()
    assert len(entries) == 1
    assert entries[0]["action"] == "fs.move"
    assert entries[0]["args"]["src"] == "a.txt"
    assert entries[0]["undo"]["action"] == "fs.move"
    assert "ts" in entries[0]


def test_record_action_without_undo(temp_manifest):
    """Test recording action without undo info."""
    temp_manifest.record("shell.run", {"cmd": "echo test"}, undo=None)
    
    entries = temp_manifest.get_entries()
    assert len(entries) == 1
    assert entries[0]["action"] == "shell.run"
    assert entries[0]["undo"] is None


def test_record_multiple_actions(temp_manifest):
    """Test recording multiple actions."""
    temp_manifest.record("fs.move", {"src": "a.txt", "dst": "b.txt"}, 
                        undo={"action": "fs.move", "args": {"src": "b.txt", "dst": "a.txt"}})
    temp_manifest.record("fs.move", {"src": "b.txt", "dst": "c.txt"},
                        undo={"action": "fs.move", "args": {"src": "c.txt", "dst": "b.txt"}})
    temp_manifest.record("shell.run", {"cmd": "echo test"}, undo=None)
    
    entries = temp_manifest.get_entries()
    assert len(entries) == 3
    assert entries[0]["args"]["dst"] == "b.txt"
    assert entries[1]["args"]["dst"] == "c.txt"
    assert entries[2]["action"] == "shell.run"


def test_rollback_fs_move(temp_manifest):
    """Test rollback of fs.move action."""
    # Create test files
    with tempfile.TemporaryDirectory() as tmpdir:
        src = Path(tmpdir) / "test.txt"
        dst = Path(tmpdir) / "test_moved.txt"
        src.write_text("test content")
        
        # Record move
        temp_manifest.record(
            "fs.move",
            {"src": str(src), "dst": str(dst)},
            undo={"action": "fs.move", "args": {"src": str(dst), "dst": str(src)}}
        )
        
        # Execute move
        src.rename(dst)
        assert not src.exists()
        assert dst.exists()
        
        # Rollback
        results = temp_manifest.rollback()
        assert len(results) == 1
        assert results[0]["result"]["ok"] is True
        assert src.exists()
        assert not dst.exists()


def test_rollback_multiple_actions(temp_manifest):
    """Test rollback of multiple actions in reverse order."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = Path(tmpdir) / "file1.txt"
        file2 = Path(tmpdir) / "file2.txt"
        file3 = Path(tmpdir) / "file3.txt"
        
        file1.write_text("content1")
        
        # Record two moves
        temp_manifest.record("fs.move", {"src": str(file1), "dst": str(file2)},
                           undo={"action": "fs.move", "args": {"src": str(file2), "dst": str(file1)}})
        temp_manifest.record("fs.move", {"src": str(file2), "dst": str(file3)},
                           undo={"action": "fs.move", "args": {"src": str(file3), "dst": str(file2)}})
        
        # Execute moves (file1 -> file2 -> file3)
        file1.rename(file2)
        file2.rename(file3)
        
        assert not file1.exists()
        assert not file2.exists()
        assert file3.exists()
        
        # Rollback all (reverse order: file3->file2, then file2->file1)
        results = temp_manifest.rollback()
        assert len(results) == 2
        assert results[0]["result"]["ok"] is True  # file3->file2
        assert results[1]["result"]["ok"] is True  # file2->file1
        assert file1.exists()
        assert not file2.exists()
        assert not file3.exists()


def test_rollback_with_count(temp_manifest):
    """Test rollback with count limit."""
    # Record 3 actions
    temp_manifest.record("fs.move", {"src": "a", "dst": "b"},
                        undo={"action": "fs.move", "args": {"src": "b", "dst": "a"}})
    temp_manifest.record("fs.move", {"src": "c", "dst": "d"},
                        undo={"action": "fs.move", "args": {"src": "d", "dst": "c"}})
    temp_manifest.record("fs.move", {"src": "e", "dst": "f"},
                        undo={"action": "fs.move", "args": {"src": "f", "dst": "e"}})
    
    # Rollback only last 2
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create files for last 2 actions
        d = Path(tmpdir) / "d"
        c = Path(tmpdir) / "c"
        f = Path(tmpdir) / "f"
        e = Path(tmpdir) / "e"
        
        d.write_text("d")
        f.write_text("f")
        
        # Update manifest entries to use real paths
        entries = temp_manifest.get_entries()
        temp_manifest.clear()
        temp_manifest.record("fs.move", {"src": "a", "dst": "b"},
                           undo={"action": "fs.move", "args": {"src": "b", "dst": "a"}})
        temp_manifest.record("fs.move", {"src": str(c), "dst": str(d)},
                           undo={"action": "fs.move", "args": {"src": str(d), "dst": str(c)}})
        temp_manifest.record("fs.move", {"src": str(e), "dst": str(f)},
                           undo={"action": "fs.move", "args": {"src": str(f), "dst": str(e)}})
        
        results = temp_manifest.rollback(count=2)
        assert len(results) == 2
        # First rollback should be f->e (last action)
        assert results[0]["args"]["src"] == str(f)
        # Second rollback should be d->c (second-to-last action)
        assert results[1]["args"]["src"] == str(d)


def test_rollback_skip_no_undo(temp_manifest):
    """Test rollback skips actions without undo info."""
    temp_manifest.record("shell.run", {"cmd": "echo test"}, undo=None)
    temp_manifest.record("fs.move", {"src": "a", "dst": "b"},
                        undo={"action": "fs.move", "args": {"src": "b", "dst": "a"}})
    
    with tempfile.TemporaryDirectory() as tmpdir:
        b = Path(tmpdir) / "b"
        a = Path(tmpdir) / "a"
        b.write_text("content")
        
        # Update manifest with real paths
        temp_manifest.clear()
        temp_manifest.record("shell.run", {"cmd": "echo test"}, undo=None)
        temp_manifest.record("fs.move", {"src": str(a), "dst": str(b)},
                           undo={"action": "fs.move", "args": {"src": str(b), "dst": str(a)}})
        
        results = temp_manifest.rollback()
        # Should only rollback fs.move (shell.run has no undo)
        assert len(results) == 1
        assert results[0]["action"] == "fs.move"


def test_rollback_unknown_action(temp_manifest):
    """Test rollback handles unknown actions gracefully."""
    temp_manifest.record("unknown.action", {"arg": "value"},
                        undo={"action": "unknown.undo", "args": {}})
    
    results = temp_manifest.rollback()
    assert len(results) == 1
    assert results[0]["result"]["ok"] is False
    assert results[0]["result"]["error"] == "unknown_action"


def test_clear_manifest(temp_manifest):
    """Test clearing manifest."""
    temp_manifest.record("fs.move", {"src": "a", "dst": "b"}, undo=None)
    assert len(temp_manifest) == 1
    
    temp_manifest.clear()
    assert len(temp_manifest) == 0
    assert temp_manifest.path.exists()


def test_manifest_repr(temp_manifest):
    """Test manifest string representation."""
    temp_manifest.record("fs.move", {"src": "a", "dst": "b"}, undo=None)
    repr_str = repr(temp_manifest)
    assert "ActionManifest" in repr_str
    assert "entries=1" in repr_str


def test_empty_rollback(temp_manifest):
    """Test rollback on empty manifest."""
    results = temp_manifest.rollback()
    assert len(results) == 0


def test_fs_move_undo_missing_args():
    """Test fs.move undo with missing arguments."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        manifest_path = f.name
    
    manifest = ActionManifest(manifest_path)
    
    # Test missing src
    result = manifest._undo_fs_move({"dst": "b"})
    assert result["ok"] is False
    assert result["error"] == "missing_args"
    
    # Test missing dst
    result = manifest._undo_fs_move({"src": "a"})
    assert result["ok"] is False
    assert result["error"] == "missing_args"
    
    Path(manifest_path).unlink(missing_ok=True)


def test_fs_move_undo_src_not_found():
    """Test fs.move undo with non-existent source."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        manifest_path = f.name
    
    manifest = ActionManifest(manifest_path)
    
    result = manifest._undo_fs_move({"src": "/nonexistent/file.txt", "dst": "/other.txt"})
    assert result["ok"] is False
    assert result["error"] == "src_not_found"
    
    Path(manifest_path).unlink(missing_ok=True)


def test_window_state_undo_placeholder():
    """Test window.state undo returns placeholder."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        manifest_path = f.name
    
    manifest = ActionManifest(manifest_path)
    
    result = manifest._undo_window_state({"window": "VSCode", "state": "maximized"})
    assert result["ok"] is True
    assert "placeholder" in result["note"]
    
    Path(manifest_path).unlink(missing_ok=True)
