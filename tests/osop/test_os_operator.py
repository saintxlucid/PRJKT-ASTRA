"""
OS Operator Tests

Tests for safe OS operations with consent gates.

Sacred Code: 333 ∞
"""

import pytest
from pathlib import Path
from astra.osop.operator import OSOperator, OSOPolicy, _is_allowed_path


@pytest.fixture
def test_policy():
    """Create test OS Operator policy."""
    return OSOPolicy(
        path_allowlist=[str(Path.cwd()), "/tmp", "C:/temp"],
        max_write_bytes=1024,
        kill_allowlist=["test_process"],
        service_allowlist=["test_service"],
        scheduler_prefix="TEST_",
    )


@pytest.fixture
def oso(test_policy):
    """Create OS Operator instance."""
    return OSOperator(test_policy)


# Path Validation Tests
def test_is_allowed_path_allowed():
    """Test path allowlist validation - allowed."""
    allowed_roots = [str(Path.cwd())]
    test_path = str(Path.cwd() / "test.txt")
    assert _is_allowed_path(test_path, allowed_roots) is True


def test_is_allowed_path_denied():
    """Test path allowlist validation - denied."""
    allowed_roots = ["/opt/astra"]
    test_path = "/etc/passwd"
    assert _is_allowed_path(test_path, allowed_roots) is False


def test_is_allowed_path_traversal():
    """Test path allowlist validation - directory traversal."""
    allowed_roots = ["/opt/astra"]
    test_path = "/opt/astra/../etc/passwd"
    # Should resolve and deny
    assert _is_allowed_path(test_path, allowed_roots) is False


# Read-Only Capabilities Tests
def test_system_info(oso):
    """Test system info retrieval."""
    info = oso.system_info()

    assert "platform" in info
    assert "system" in info
    assert "python_version" in info
    assert "cpus" in info
    assert info["sacred_code"] == "333"


def test_system_resources(oso):
    """Test system resources retrieval."""
    resources = oso.system_resources()

    assert "memory" in resources
    assert "cpu_load" in resources
    assert "disks" in resources
    assert "network" in resources
    assert resources["sacred_code"] == "333"


def test_disk_usage(oso):
    """Test disk usage retrieval."""
    usage = oso.disk_usage()

    # Returns dict of mount points -> usage stats
    assert isinstance(usage, dict)
    # Should have at least one partition
    if usage:
        first_key = next(iter(usage))
        assert "device" in usage[first_key]
        assert "fstype" in usage[first_key]


def test_process_list(oso):
    """Test process list retrieval."""
    processes = oso.process_list(limit=10)

    assert isinstance(processes, list)
    assert len(processes) <= 10

    if processes:
        proc = processes[0]
        assert "pid" in proc
        assert "name" in proc


# Write Capability Tests
def test_fs_read_allowed(oso, tmp_path):
    """Test file read with allowed path."""
    # Update policy to include tmp_path
    oso.policy.path_allowlist.append(str(tmp_path))

    test_file = tmp_path / "test.txt"
    test_file.write_text("hello astra 333")

    result = oso.fs_read(str(test_file))
    # fs_read returns dict with ok/data
    assert result["ok"] is True
    assert result["data"] == "hello astra 333"


def test_fs_read_denied(oso):
    """Test file read with denied path."""
    result = oso.fs_read("/etc/passwd")
    # Should return error dict, not raise
    assert result["ok"] is False
    assert "not in allowlist" in result["error"]


def test_fs_write_allowed(oso, tmp_path):
    """Test file write with allowed path."""
    # Update policy to include tmp_path
    oso.policy.path_allowlist.append(str(tmp_path))

    test_file = tmp_path / "write_test.txt"

    # Write without consent manager (should work for test)
    result = oso.fs_write(str(test_file), "test content 333", overwrite=False, consent_manager=None)

    # Verify result
    assert result["ok"] is True
    # Verify file
    assert test_file.read_text() == "test content 333"

    # Now read it back
    read_result = oso.fs_read(str(test_file))
    assert read_result["ok"] is True
    assert read_result["data"] == "test content 333"


def test_fs_write_denied(oso):
    """Test file write with denied path."""
    result = oso.fs_write("/etc/test.txt", "hacker", overwrite=False, consent_manager=None)
    # Should return error dict
    assert result["ok"] is False
    assert "not in allowlist" in result["error"]


def test_fs_write_size_limit(oso, tmp_path):
    """Test file write size limit enforcement."""
    # Update policy to include tmp_path
    oso.policy.path_allowlist.append(str(tmp_path))

    test_file = tmp_path / "large.txt"
    large_content = "x" * 2048  # Exceeds policy max_write_bytes (1024)

    result = oso.fs_write(str(test_file), large_content, overwrite=False, consent_manager=None)
    assert result["ok"] is False
    assert "exceeds max size" in result["error"]


# Health Check Test
def test_health_check(oso):
    """Test OS Operator health check."""
    health = oso.health_check()

    assert health["status"] == "healthy"
    assert "platform" in health
    assert "psutil_available" in health
    assert "policy" in health
    assert health["sacred_code"] == "333"


# Integration Test
def test_full_workflow(oso, tmp_path):
    """Test complete workflow: info → resources → read → write."""
    # Update policy
    oso.policy.path_allowlist.append(str(tmp_path))

    # 1. Get system info
    info = oso.system_info()
    assert info["cpus"] > 0

    # 2. Get resources
    resources = oso.system_resources()
    assert resources["memory"]["total"] > 0

    # 3. Write file
    test_file = tmp_path / "workflow.txt"
    result = oso.fs_write(
        str(test_file), "workflow test 333", overwrite=False, consent_manager=None
    )
    assert result["ok"] is True

    # 4. Read file
    result = oso.fs_read(str(test_file))
    assert result["ok"] is True
    assert result["data"] == "workflow test 333"

    # 5. Health check
    health = oso.health_check()
    assert health["status"] == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
