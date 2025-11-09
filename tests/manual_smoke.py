"""
Manual Smoke Tests - End-to-end integration validation.

Tests the complete security stack with correct tokenizer API.
Run: pytest tests/manual_smoke.py -v -s
"""

import tempfile
import time
from pathlib import Path
import pytest

from core.tokenizer import issue, verify
from controller.dispatch import dispatch
from controller.manifest import ActionManifest


@pytest.fixture
def temp_dir():
    """Create temporary directory for file operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_manifest():
    """Create temporary manifest file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        manifest_path = f.name

    manifest = ActionManifest(manifest_path)
    yield manifest

    # Cleanup
    Path(manifest_path).unlink(missing_ok=True)


class TestEndToEndIntegration:
    """End-to-end smoke tests for production readiness."""

    def test_e2e_valid_shell_command(self):
        """Test: Issue token -> dispatch shell.run -> verify success."""
        args = {"cmd": "echo Hello ASTRA"}
        token = issue("shell.run", "process", "", args, ttl_s=10, budget_ms=5000)

        # Verify token
        ok, reason, claims = verify(token, args)
        print(f"\n✅ Token verify result: ok={ok}, reason={reason}, sub={claims['sub'] if claims else None}")
        assert ok is True

        # Dispatch action with verified claims
        result = dispatch("shell.run", args, claims)

        print(f"✅ Shell command result: {result}")
        assert result["ok"] is True
        assert "stdout" in result
        assert "Hello ASTRA" in result["stdout"]

    def test_e2e_path_allowlist_blocks_system32(self):
        """Test: Path allowlist blocks C:\\Windows\\System32 access."""
        args = {"src": "C:\\Windows\\System32\\cmd.exe", "dst": "C:\\Temp\\bad.exe"}
        token = issue("fs.copy", "fs", "", args, ttl_s=10, budget_ms=5000)

        result = dispatch(token, "fs.copy", args)

        print(f"\n🛡️ Path blocked result: {result}")
        assert result["ok"] is False
        assert result["error"] == "path_blocked"

    def test_e2e_path_allowlist_allows_temp(self, temp_dir):
        """Test: Path allowlist allows temp directory access."""
        src = temp_dir / "source.txt"
        dst = temp_dir / "dest.txt"
        src.write_text("test content")

        args = {"src": str(src), "dst": str(dst)}
        token = issue("fs.copy", "fs", "", args, ttl_s=10, budget_ms=5000)

        result = dispatch(token, "fs.copy", args)

        print(f"\n✅ Temp file copy result: {result}")
        assert result["ok"] is True
        assert dst.exists()
        assert dst.read_text() == "test content"

    def test_e2e_timeout_enforcement(self):
        """Test: Long-running command times out per budget."""
        args = {"cmd": "ping 127.0.0.1 -n 10"}
        token = issue("shell.run", "process", "", args, ttl_s=60, budget_ms=1000)

        start = time.time()
        result = dispatch(token, "shell.run", args)
        elapsed = time.time() - start

        print(f"\n⏱️ Timeout result (elapsed={elapsed:.2f}s): {result}")
        assert result["ok"] is False
        assert result["error"] == "timeout"
        assert elapsed < 2.0  # Should timeout quickly

    def test_e2e_scope_validation_denies_wrong_scope(self):
        """Test: Token with wrong scope is denied."""
        args = {"cmd": "echo test"}
        # Wrong scope: fs instead of process
        token = issue("shell.run", "fs", "", args, ttl_s=10, budget_ms=5000)

        result = dispatch(token, "shell.run", args)

        print(f"\n🚫 Scope denied result: {result}")
        assert result["ok"] is False
        assert result["error"] == "scope_denied"

    def test_e2e_expired_token_rejected(self):
        """Test: Expired token is rejected."""
        args = {"cmd": "echo test"}
        token = issue("shell.run", "process", "", args, ttl_s=1, budget_ms=5000)

        time.sleep(2)  # Wait for expiry

        ok, reason, claims = verify(token, args)

        print(f"\n⏰ Expired token result: ok={ok}, reason={reason}")
        assert ok is False
        assert reason == "expired"

    def test_e2e_manifest_rollback_fs_move(self, temp_dir, temp_manifest):
        """Test: Manifest rollback restores moved files."""
        file1 = temp_dir / "original.txt"
        file2 = temp_dir / "moved.txt"
        file1.write_text("original content")

        # Record move operation
        temp_manifest.record(
            "fs.move",
            {"src": str(file1), "dst": str(file2)},
            undo={"action": "fs.move", "args": {"src": str(file2), "dst": str(file1)}}
        )

        # Execute move
        args = {"src": str(file1), "dst": str(file2)}
        token = issue("fs.move", "fs", "", args, ttl_s=10, budget_ms=5000)
        result = dispatch(token, "fs.move", args)

        print(f"\n📦 Move result: {result}")
        assert result["ok"] is True
        assert not file1.exists()
        assert file2.exists()

        # Rollback
        rollback_results = temp_manifest.rollback()

        print(f"↩️ Rollback result: {rollback_results}")
        assert len(rollback_results) == 1
        assert rollback_results[0]["result"]["ok"] is True
        assert file1.exists()
        assert not file2.exists()


class TestProductionScenarios:
    """Real-world production scenarios."""

    def test_scenario_safe_script_execution(self, temp_dir):
        """Scenario: Execute script in temp directory with timeout."""
        script = temp_dir / "test_script.bat"
        script.write_text("@echo off\necho Script executed successfully\n")

        args = {"cmd": str(script)}
        token = issue("shell.run", "process", "", args, ttl_s=30, budget_ms=5000)

        result = dispatch(token, "shell.run", args)

        print(f"\n📜 Script execution: {result}")
        assert result["ok"] is True
        assert "Script executed successfully" in result["stdout"]

    def test_scenario_prevented_privilege_escalation(self):
        """Scenario: Attempt to modify system files is blocked."""
        args = {
            "src": "C:\\Windows\\System32\\cmd.exe",
            "dst": "C:\\Users\\Public\\my_cmd.exe"
        }
        token = issue("fs.copy", "fs", "", args, ttl_s=10, budget_ms=5000)

        result = dispatch(token, "fs.copy", args)

        print(f"\n🛡️ Privilege escalation blocked: {result}")
        assert result["ok"] is False
        assert result["error"] == "path_blocked"

    def test_scenario_resource_exhaustion_prevented(self):
        """Scenario: Infinite loop script is killed by timeout."""
        args = {"cmd": "ping 127.0.0.1 -n 100"}
        token = issue("shell.run", "process", "", args, ttl_s=60, budget_ms=2000)

        start = time.time()
        result = dispatch(token, "shell.run", args)
        elapsed = time.time() - start

        print(f"\n⚡ Resource exhaustion prevented (elapsed={elapsed:.2f}s): {result}")
        assert result["ok"] is False
        assert result["error"] == "timeout"
        assert elapsed < 5.0  # Should be killed quickly


if __name__ == "__main__":
    print("=" * 80)
    print("ASTRA OS - Manual Smoke Tests")
    print("Testing: Token Security + Path Allowlist + Budget Enforcement + Manifest Rollback")
    print("=" * 80)
    pytest.main([__file__, "-v", "-s", "--tb=short"])
