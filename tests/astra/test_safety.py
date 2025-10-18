"""
ASTRA Core Safety Tests
Validates core safety constraints and invariants.
Created: October 16, 2025
"""
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from ..core.contracts import (
    Plan, PlanStep, ToolSpec, ExecutionContext, ExecutionMode,
    AlignmentProfile, Capability, SecurityLimits, ResourceLimits,
    ConsentToken
)
from ..core.verifier import PlanVerifier, SafetyViolation

@pytest.fixture
def test_profile():
    """Test alignment profile"""
    return AlignmentProfile(
        risk_tolerance="medium",
        consent_rules={
            Capability.FILE_DELETE: "explicit_with_backup",
            Capability.SYSTEM_CONFIG: "explicit",
            Capability.CODE_EXEC: "implicit"
        },
        red_lines=["data_exfiltration", "system_damage"]
    )

@pytest.fixture
def test_context(test_profile):
    """Test execution context"""
    return ExecutionContext(
        trace_id="test-trace-001",
        mode=ExecutionMode.CONFIRM,
        operator="test_user",
        working_dir=Path("/test/workspace"),
        alignment_profile=test_profile,
        env_overrides={}
    )

@pytest.fixture
def test_tool_spec():
    """Test tool specification"""
    return ToolSpec(
        name="test_tool",
        version="1.0",
        description="Test tool",
        capabilities={Capability.FILE_DELETE},
        args_schema={"type": "object"},
        limits=ResourceLimits(),
        security=SecurityLimits(
            allowed_paths=[Path("/test/workspace")],
            denied_paths=[Path("/system")]
        )
    )

def test_delete_requires_backup(test_profile, test_context):
    """Test that file deletion requires backup"""
    step = PlanStep(
        id="test-1",
        tool="file_delete",
        args={"path": "/test/workspace/file.txt"},
        expect="File deleted",
        reversible=False,
        alignment_note="Removing temporary file"
    )
    
    plan = Plan(goal="Test delete", steps=[step])
    verifier = PlanVerifier(test_profile)
    
    # Should raise without backup
    with pytest.raises(SafetyViolation, match="no backup step"):
        verifier.verify_plan(plan, test_context)
        
    # Should pass with backup step
    backup_step = PlanStep(
        id="backup-1",
        tool="file_backup",
        args={"path": "/test/workspace/file.txt"},
        expect="Backup created",
        reversible=True,
        alignment_note="Creating safety backup"
    )
    
    plan.steps.insert(0, backup_step)
    consent_levels = verifier.verify_plan(plan, test_context)
    assert "explicit_with_backup" in consent_levels

def test_path_safety(test_profile, test_context):
    """Test path safety constraints"""
    step = PlanStep(
        id="test-1", 
        tool="file_read",
        args={"path": "/system/critical.dat"},
        expect="File read",
        alignment_note="Reading file"
    )
    
    plan = Plan(goal="Test path safety", steps=[step])
    verifier = PlanVerifier(test_profile)
    
    # Should fail - path under denied
    with pytest.raises(SafetyViolation, match="under denied path"):
        verifier.verify_plan(plan, test_context)
        
    # Should pass - path under allowed
    step.args["path"] = "/test/workspace/safe.txt"
    verifier.verify_plan(plan, test_context)

def test_red_line_violation(test_profile, test_context):
    """Test red line violations are caught"""
    step = PlanStep(
        id="test-1",
        tool="network_post",
        args={"url": "http://evil.com"},
        expect="Data sent",
        alignment_note="Sending data for data_exfiltration"
    )
    
    plan = Plan(goal="Test red lines", steps=[step])
    verifier = PlanVerifier(test_profile)
    
    with pytest.raises(SafetyViolation, match="violates red line"):
        verifier.verify_plan(plan, test_context)

def test_consent_token_validation():
    """Test consent token validation"""
    now = datetime.now()
    
    # Valid token
    token = ConsentToken(
        token="test-token",
        capabilities={Capability.FILE_DELETE},
        scope="task",
        granted_by="test_user",
        expires_at=now + timedelta(hours=1)
    )
    assert token.is_valid
    
    # Expired token
    token.expires_at = now - timedelta(minutes=1)
    assert not token.is_valid

def test_alignment_notes_required(test_profile, test_context):
    """Test alignment notes are required"""
    step = PlanStep(
        id="test-1",
        tool="file_read",
        args={"path": "/test/workspace/file.txt"},
        expect="File read",
        alignment_note=""  # Empty note
    )
    
    plan = Plan(goal="Test notes", steps=[step])
    assert not plan.validate_alignment_notes()