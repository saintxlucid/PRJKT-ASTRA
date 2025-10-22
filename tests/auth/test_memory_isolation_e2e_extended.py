"""
Extended E2E tests for memory isolation with performance metrics.
"""

from .test_memory_isolation_e2e import *
from astra.auth.rbac import Role, Scope, rbac_manager
import time
import statistics

def test_memory_performance(test_client):
    """Test memory isolation performance impact."""
    # Prepare test data
    test_data = [
        {"key": f"perf-key-{i}", "value": f"perf-value-{i}"}
        for i in range(100)
    ]

    # Measure write performance
    write_times = []
    for item in test_data:
        start = time.time()
        response = test_client.post(
            "/memory",
            json=item,
            headers={"X-Test-User": "test-user-1"}
        )
        write_times.append(time.time() - start)
        assert response.status_code == 200

    # Measure read performance
    read_times = []
    for item in test_data:
        start = time.time()
        response = test_client.get(
            f"/memory/{item['key']}",
            headers={"X-Test-User": "test-user-1"}
        )
        read_times.append(time.time() - start)
        assert response.status_code == 200

    # Calculate p95 latencies
    p95_write = statistics.quantiles(write_times, n=20)[18]  # 95th percentile
    p95_read = statistics.quantiles(read_times, n=20)[18]

    # Performance requirements:
    # - Write p95 < 5ms
    # - Read p95 < 1ms
    assert p95_write < 0.005, f"Write p95 {p95_write*1000:.2f}ms exceeds 5ms target"
    assert p95_read < 0.001, f"Read p95 {p95_read*1000:.2f}ms exceeds 1ms target"

def test_rbac_isolation(test_client):
    """Test RBAC scope enforcement for memory operations."""
    # User with read-only role
    readonly_scopes = rbac_manager.get_role_scopes(Role.READONLY)
    assert Scope.MEMORY_READ in readonly_scopes
    assert Scope.MEMORY_WRITE not in readonly_scopes

    # Write attempt should fail for read-only user
    response = test_client.post(
        "/memory",
        json={"key": "test-key", "value": "test-value"},
        headers={
            "X-Test-User": "readonly-user",
            "X-Test-Role": "readonly"
        }
    )
    assert response.status_code in [401, 403]  # Unauthorized/Forbidden

    # Write with normal user should succeed
    response = test_client.post(
        "/memory",
        json={"key": "test-key", "value": "test-value"},
        headers={
            "X-Test-User": "normal-user",
            "X-Test-Role": "user"
        }
    )
    assert response.status_code == 200

    # Read should work for both users
    for user in ["readonly-user", "normal-user"]:
        response = test_client.get(
            "/memory/test-key",
            headers={"X-Test-User": user}
        )
        # Read-only user can read, but only gets null for other users' data
        if user == "readonly-user":
            assert response.status_code == 404
        else:
            assert response.status_code == 200
            assert response.json()["value"] == "test-value"

def test_admin_isolation_override(test_client):
    """Test that admins can access any user's memory."""
    # Regular user creates memory
    response = test_client.post(
        "/memory",
        json={"key": "secret-key", "value": "secret-value"},
        headers={"X-Test-User": "normal-user"}
    )
    assert response.status_code == 200

    # Admin can read user's memory
    response = test_client.get(
        "/memory/secret-key",
        headers={
            "X-Test-User": "admin-user",
            "X-Test-Role": "admin"
        }
    )
    assert response.status_code == 200
    assert response.json()["value"] == "secret-value"

    # Admin can modify user's memory
    response = test_client.post(
        "/memory",
        json={"key": "secret-key", "value": "modified-by-admin"},
        headers={
            "X-Test-User": "admin-user",
            "X-Test-Role": "admin"
        }
    )
    assert response.status_code == 200

    # Original user sees modified value
    response = test_client.get(
        "/memory/secret-key",
        headers={"X-Test-User": "normal-user"}
    )
    assert response.status_code == 200
    assert response.json()["value"] == "modified-by-admin"