"""
ASTRA OS Security Tests
Tests for tokenizer, credential store, pipe server, and end-to-end security.
"""
import pytest
import time
from core.tokenizer import issue, verify, rotate_secret


# ===== Token Security Tests =====

def test_valid_token():
    """Test issuing and verifying a valid token."""
    args = {"cmd": "echo test"}
    token = issue("shell.run", "process", "*", args, ttl_s=5)
    ok, reason, claims = verify(token, args)
    
    assert ok
    assert reason == "ok"
    assert claims is not None
    assert claims["sub"] == "shell.run"


def test_tampered_signature():
    """Test detection of signature tampering."""
    args = {"cmd": "echo test"}
    token = issue("shell.run", "process", "*", args)
    
    # Tamper with signature
    bad_token = token[:-5] + "xxxxx"
    ok, reason, _ = verify(bad_token, args)
    
    assert not ok
    assert reason == "bad_sig"


def test_expired_token():
    """Test token expiry enforcement."""
    args = {"cmd": "echo test"}
    token = issue("shell.run", "process", "*", args, ttl_s=1)
    
    # Wait for expiry
    time.sleep(2)
    
    ok, reason, _ = verify(token, args)
    assert not ok
    assert reason == "expired"


def test_args_mismatch():
    """Test args immutability detection."""
    args = {"cmd": "echo test"}
    token = issue("shell.run", "process", "*", args)
    
    # Try to verify with different args
    ok, reason, _ = verify(token, {"cmd": "echo different"})
    
    assert not ok
    assert reason == "args_mismatch"


def test_args_order_independence():
    """Test that args order doesn't affect verification."""
    args1 = {"a": 1, "b": 2, "c": 3}
    args2 = {"c": 3, "a": 1, "b": 2}
    
    token = issue("test.action", "read", "*", args1)
    ok, reason, _ = verify(token, args2)
    
    assert ok
    assert reason == "ok"


def test_token_budget_encoding():
    """Test budget limits are encoded correctly."""
    args = {"cmd": "test"}
    token = issue("shell.run", "process", "*", args, budget_ms=5000)
    
    ok, reason, claims = verify(token, args)
    
    assert ok
    assert claims["budget"]["ms"] == 5000


def test_policy_levels():
    """Test different policy levels."""
    args = {"cmd": "test"}
    
    for policy in ["info", "action", "admin"]:
        token = issue("shell.run", "process", "*", args, policy=policy)
        ok, reason, claims = verify(token, args)
        
        assert ok
        assert claims["policy"] == policy


def test_secret_rotation():
    """Test dual-key secret rotation."""
    import secrets as sec
    args = {"cmd": "test"}
    
    # Issue token with current secret
    token = issue("shell.run", "process", "*", args)
    
    # Verify works
    ok, reason, _ = verify(token, args)
    assert ok
    
    # Rotate secret
    new_secret = sec.token_hex(32)
    rotate_secret(new_secret)
    
    # Old token should still work (dual-key window)
    ok, reason, _ = verify(token, args)
    assert ok
    
    # New token should work with new secret
    new_token = issue("shell.run", "process", "*", args)
    ok, reason, _ = verify(new_token, args)
    assert ok


# ===== Credential Store Tests =====

def test_credential_store_available():
    """Test if Windows Credential Manager is available."""
    from core.credential_store import is_credential_store_available
    
    # Should be True on Windows, False elsewhere
    available = is_credential_store_available()
    assert isinstance(available, bool)


@pytest.mark.skipif(
    not __import__('core.credential_store').credential_store.is_credential_store_available(),
    reason="Windows Credential Manager not available"
)
def test_credential_store_roundtrip():
    """Test storing and loading credentials."""
    import secrets as sec
    from core.credential_store import store_hmac_secret, load_hmac_secret, delete_hmac_secret
    
    # Generate test secret
    test_secret = sec.token_bytes(32)
    
    # Store
    assert store_hmac_secret(test_secret)
    
    # Load
    loaded = load_hmac_secret()
    assert loaded == test_secret
    
    # Cleanup
    delete_hmac_secret()


# ===== Integration Tests =====

def test_malformed_token():
    """Test handling of malformed tokens."""
    args = {"cmd": "test"}
    
    # No signature separator
    ok, reason, _ = verify("malformed_token_no_dot", args)
    assert not ok
    assert reason == "malformed"


def test_unique_token_ids():
    """Test that each token gets unique JTI."""
    from core.tokenizer import get_claims
    args = {"cmd": "test"}
    
    token1 = issue("shell.run", "process", "*", args)
    token2 = issue("shell.run", "process", "*", args)
    
    claims1 = get_claims(token1)
    claims2 = get_claims(token2)
    
    assert claims1 is not None
    assert claims2 is not None
    assert claims1["jti"] != claims2["jti"]


def test_token_max_ttl_cap():
    """Test that TTL is capped at maximum."""
    args = {"cmd": "test"}
    
    # Request 600s TTL (should be capped at 300s)
    token = issue("shell.run", "process", "*", args, ttl_s=600)
    ok, reason, claims = verify(token, args)
    
    assert ok
    # Should be capped at 300s
    assert (claims["exp"] - claims["nbf"]) <= 300


# ===== Path Security Tests =====

def test_path_allowlist_home():
    """Test that home directory paths are allowed."""
    import os
    home = os.path.expanduser("~")
    
    args = {"src": f"{home}/test.txt", "dst": f"{home}/test2.txt"}
    token = issue("fs.copy", "fs", args["dst"], args)
    
    ok, reason, _ = verify(token, args)
    assert ok


def test_path_allowlist_windows():
    """Test that Windows system paths would be blocked (dispatcher will enforce)."""
    args = {"src": "C:\\Windows\\System32\\test.dll", "dst": "evil.dll"}
    token = issue("fs.copy", "fs", args["dst"], args)
    
    # Token itself is valid (dispatcher will reject the path)
    ok, reason, _ = verify(token, args)
    assert ok
