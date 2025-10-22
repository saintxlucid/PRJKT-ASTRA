"""Tests for policy engine security features."""

import os
import pytest
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from evolution.security import (
    PolicyEngine,
    PolicyRule,
    SecurityToken,
    SecurityLevel,
    PolicyViolation
)


@pytest.fixture
def config_path(tmp_path):
    """Create a temporary policy config."""
    config = {
        "operations": {
            "test.low_op": {
                "level": "LOW",
                "requires_audit": True,
                "allowlist": ["test_user"]
            },
            "test.medium_op": {
                "level": "MEDIUM",
                "requires_audit": True,
                "allowlist": ["test_user"]
            },
            "test.high_op": {
                "level": "HIGH",
                "requires_hmac": True,
                "requires_audit": True,
                "allowlist": ["test_user"],
                "max_batch_size": 5
            },
            "test.critical_op": {
                "level": "CRITICAL",
                "requires_hmac": True,
                "requires_audit": True,
                "allowlist": ["test_admin"],
                "cooldown_seconds": 300
            }
        }
    }
    
    config_file = tmp_path / "policy.yaml"
    with open(config_file, "w") as f:
        yaml.safe_dump(config, f)
        
    return config_file


@pytest.fixture
def hmac_key():
    """Create a test HMAC key."""
    return os.urandom(32)


@pytest.fixture
def policy_engine(config_path, hmac_key, tmp_path):
    """Create a PolicyEngine instance."""
    return PolicyEngine(
        config_path,
        hmac_key,
        audit_path=tmp_path / "audit.log"
    )


def test_policy_engine_initialization(policy_engine):
    """Test policy engine initialization."""
    assert policy_engine.rules
    assert len(policy_engine.rules) == 4
    assert all(isinstance(r, PolicyRule) for r in policy_engine.rules.values())


def test_low_operation_validation(policy_engine):
    """Test validation of low-security operation."""
    context = {"user": "test_user"}
    assert policy_engine.validate_operation(
        "test.low_op",
        context=context
    )


def test_medium_operation_validation(policy_engine):
    """Test validation of medium-security operation."""
    token = SecurityToken(
        operation="test.medium_op",
        timestamp=datetime.now(),
        nonce="test123",
        hmac="dummy"
    )
    context = {"user": "test_user"}
    
    assert policy_engine.validate_operation(
        "test.medium_op",
        token=token,
        context=context
    )


def test_high_operation_validation(policy_engine):
    """Test validation of high-security operation."""
    # Create valid token
    token = policy_engine.create_token("test.high_op")
    context = {"user": "test_user", "batch_size": 3}
    
    assert policy_engine.validate_operation(
        "test.high_op",
        token=token,
        context=context
    )


def test_critical_operation_validation(policy_engine):
    """Test validation of critical operation."""
    token = policy_engine.create_token("test.critical_op")
    context = {"user": "test_admin"}
    
    assert policy_engine.validate_operation(
        "test.critical_op",
        token=token,
        context=context
    )


def test_operation_without_token(policy_engine):
    """Test operation requiring token fails without one."""
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation("test.high_op")
    assert "Security token required" in str(exc.value)


def test_operation_with_invalid_token(policy_engine):
    """Test operation fails with invalid token."""
    token = SecurityToken(
        operation="test.high_op",
        timestamp=datetime.now(),
        nonce="test123",
        hmac="invalid"
    )
    
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation(
            "test.high_op",
            token=token
        )
    assert "Invalid security token" in str(exc.value)


def test_operation_with_expired_token(policy_engine):
    """Test operation fails with expired token."""
    token = SecurityToken(
        operation="test.high_op",
        timestamp=datetime.now() - timedelta(minutes=10),
        nonce="test123",
        hmac="dummy"
    )
    
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation(
            "test.high_op",
            token=token
        )
    assert "Invalid security token" in str(exc.value)


def test_operation_with_unauthorized_user(policy_engine):
    """Test operation fails with unauthorized user."""
    token = policy_engine.create_token("test.high_op")
    context = {"user": "unauthorized_user"}
    
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation(
            "test.high_op",
            token=token,
            context=context
        )
    assert "not in allowlist" in str(exc.value)


def test_operation_exceeding_batch_size(policy_engine):
    """Test operation fails when exceeding batch size limit."""
    token = policy_engine.create_token("test.high_op")
    context = {
        "user": "test_user",
        "batch_size": 10  # Exceeds limit of 5
    }
    
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation(
            "test.high_op",
            token=token,
            context=context
        )
    assert "Batch size" in str(exc.value)


def test_operation_cooldown(policy_engine):
    """Test operation cooldown period."""
    token = policy_engine.create_token("test.critical_op")
    context = {"user": "test_admin"}
    
    # First operation should succeed
    assert policy_engine.validate_operation(
        "test.critical_op",
        token=token,
        context=context
    )
    
    # Second operation within cooldown should fail
    with pytest.raises(PolicyViolation) as exc:
        policy_engine.validate_operation(
            "test.critical_op",
            token=token,
            context=context
        )
    assert "cooldown" in str(exc.value)


def test_token_generation(policy_engine):
    """Test security token generation."""
    token = policy_engine.create_token("test.high_op")
    
    assert isinstance(token, SecurityToken)
    assert token.operation == "test.high_op"
    assert isinstance(token.timestamp, datetime)
    assert isinstance(token.nonce, str)
    assert isinstance(token.hmac, str)


def test_audit_logging(policy_engine, tmp_path):
    """Test audit log creation."""
    token = policy_engine.create_token("test.high_op")
    context = {"user": "test_user", "batch_size": 3}
    
    policy_engine.validate_operation(
        "test.high_op",
        token=token,
        context=context
    )
    
    # Check audit log was created
    audit_path = tmp_path / "audit.log"
    assert audit_path.exists()
    
    # Verify log contents
    with open(audit_path) as f:
        log_entry = f.readlines()[-1]
        assert "test.high_op" in log_entry
        assert "token_present" in log_entry