"""Authentication conformance tests - ensure all protected endpoints require auth."""
import os
import httpx
import pytest

BASE = os.getenv("BASE_URL", "http://localhost:8001")

@pytest.mark.parametrize("endpoint", ["/answer", "/answer/stream", "/drain", "/admin/reload"])
def test_endpoints_require_auth(endpoint):
    """Protected endpoints must return 401/403 without valid auth headers."""
    try:
        if endpoint.startswith("/admin"):
            r = httpx.post(f"{BASE}{endpoint}", timeout=5)
        else:
            r = httpx.post(f"{BASE}{endpoint}", json={"query": "test"}, timeout=5)
    except httpx.ConnectError:
        pytest.skip("Service not running")
    
    assert r.status_code in (401, 403), f"{endpoint} must be protected, got {r.status_code}"

def test_health_endpoints_public():
    """Health endpoints should be publicly accessible."""
    for ep in ["/live", "/ready", "/health/full"]:
        try:
            r = httpx.get(f"{BASE}{ep}", timeout=5)
            assert r.status_code == 200, f"{ep} should be public"
        except httpx.ConnectError:
            pytest.skip("Service not running")
