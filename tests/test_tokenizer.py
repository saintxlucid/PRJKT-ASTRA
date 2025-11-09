# tests/test_tokenizer.py
"""
Unit tests for the Execution Tokenizer.
"""
import time

import pytest

from core.tokenizer import issue, verify, get_claims


def test_token_issue_and_verify_ok():
    """Valid token should verify successfully."""
    tok = issue("shell.run", "process", "*", {"cmd": "echo hi"}, ttl_s=5)
    ok, reason, claims = verify(tok, {"cmd": "echo hi"})

    assert ok is True
    assert reason == "ok"
    assert claims is not None
    assert claims["sub"] == "shell.run"
    assert claims["scope"] == "process"


def test_token_args_mismatch():
    """Token should reject if args don't match hash."""
    tok = issue("shell.run", "process", "*", {"cmd": "echo hi"}, ttl_s=5)
    ok, reason, claims = verify(tok, {"cmd": "echo bye"})

    assert ok is False
    assert reason == "args_mismatch"
    assert claims is not None  # Claims still returned for audit


def test_token_expiry():
    """Expired tokens should be rejected."""
    tok = issue("shell.run", "process", "*", {"cmd": "echo hi"}, ttl_s=1)
    time.sleep(2)
    ok, reason, claims = verify(tok, {"cmd": "echo hi"})

    assert ok is False
    assert reason == "expired"


def test_token_bad_signature():
    """Tampered tokens should fail signature check."""
    tok = issue("shell.run", "process", "*", {"cmd": "echo hi"}, ttl_s=5)
    # Flip a character to corrupt the signature
    tampered = tok[:-1] + ("X" if tok[-1] != "X" else "Y")
    ok, reason, claims = verify(tampered, {"cmd": "echo hi"})

    assert ok is False
    assert reason == "bad_sig"


def test_token_malformed():
    """Malformed tokens should be rejected."""
    ok, reason, claims = verify("not.a.valid.token", {"cmd": "echo hi"})

    assert ok is False
    assert "malformed" in reason or "exception" in reason or "bad_sig" in reason


def test_get_claims_without_verify():
    """Should extract claims for logging without full verification."""
    tok = issue("fs.copy", "fs", "/tmp", {"src": "a", "dst": "b"}, ttl_s=5)
    claims = get_claims(tok)

    assert claims is not None
    assert claims["sub"] == "fs.copy"
    assert claims["scope"] == "fs"
    assert "jti" in claims


def test_token_budget_encoding():
    """Budget should be encoded in claims."""
    tok = issue(
        "shell.run",
        "process",
        "*",
        {"cmd": "echo test"},
        ttl_s=10,
        budget_ms=3000
    )
    claims = get_claims(tok)

    assert claims["budget"]["ms"] == 3000
    assert claims["budget"]["stdout_kb"] == 256


def test_token_policy_levels():
    """Different policy levels should be encoded."""
    for policy in ["info", "action", "admin"]:
        tok = issue("test.action", "read", "*", {}, policy=policy)
        claims = get_claims(tok)
        assert claims["policy"] == policy


def test_token_max_ttl_cap():
    """TTL should be capped at maximum allowed."""
    tok = issue("test.action", "read", "*", {}, ttl_s=999999)
    claims = get_claims(tok)

    # Should be capped at 300 seconds (5 minutes)
    assert (claims["exp"] - claims["iat"]) <= 300


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
