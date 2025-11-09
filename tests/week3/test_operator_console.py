"""
Test Suite: Operator Console MVP (Week-3 Days 21-24)

Tests:
  - Plan preview generation
  - Consent recording and retrieval
  - API endpoint integration
  - Error handling
"""

import pytest
from fastapi.testclient import TestClient
from src.services.plan_preview_service import PlanPreviewService, ActionType, RiskLevel
from src.services.consent_service import ConsentService, ConsentDecision


# ============================================================================
# Test: Plan Preview Service
# ============================================================================

def test_plan_preview_service_create():
    """Test plan preview generation"""
    service = PlanPreviewService()
    
    plan = service.create_plan_preview(
        plan_id="test_plan_001",
        title="Test Configuration Update",
        description="Update nginx configuration",
        actions=[
            {
                "type": "read",
                "description": "Read current config",
                "resources": {"file": "/etc/nginx/nginx.conf"},
                "dependencies": [],
            },
            {
                "type": "write",
                "description": "Write updated config",
                "resources": {"file": "/etc/nginx/nginx.conf"},
                "dependencies": ["test_plan_001_action_0"],
            },
            {
                "type": "execute",
                "description": "Restart nginx",
                "resources": {"command": "systemctl restart nginx"},
                "dependencies": ["test_plan_001_action_1"],
            },
        ],
    )
    
    assert plan.plan_id == "test_plan_001"
    assert plan.title == "Test Configuration Update"
    assert len(plan.nodes) == 3
    assert plan.max_risk_level == RiskLevel.HIGH  # execute is high risk
    assert plan.requires_consent is True  # high risk requires consent
    assert plan.reversible is False  # execute is not reversible
    assert plan.total_duration_ms > 0


def test_plan_preview_risk_calculation():
    """Test risk calculation for different action types"""
    service = PlanPreviewService()
    
    # Low risk: read from non-sensitive path
    plan_low = service.create_plan_preview(
        plan_id="plan_low",
        title="Low Risk",
        description="Read log file",
        actions=[
            {
                "type": "read",
                "description": "Read logs",
                "resources": {"file": "/var/log/app.log"},
                "dependencies": [],
            }
        ],
    )
    assert plan_low.max_risk_level == RiskLevel.LOW
    
    # High risk: write to sensitive path
    plan_high = service.create_plan_preview(
        plan_id="plan_high",
        title="High Risk",
        description="Modify system config",
        actions=[
            {
                "type": "write",
                "description": "Write to /etc",
                "resources": {"file": "/etc/important.conf"},
                "dependencies": [],
            }
        ],
    )
    assert plan_high.max_risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    # Critical risk: dangerous command
    plan_critical = service.create_plan_preview(
        plan_id="plan_critical",
        title="Critical Risk",
        description="Delete files",
        actions=[
            {
                "type": "execute",
                "description": "Remove files",
                "resources": {"command": "rm -rf /tmp/*"},
                "dependencies": [],
            }
        ],
    )
    assert plan_critical.max_risk_level == RiskLevel.CRITICAL


def test_plan_preview_to_dict():
    """Test plan serialization to dict"""
    service = PlanPreviewService()
    
    plan = service.create_plan_preview(
        plan_id="plan_dict",
        title="Test",
        description="Test plan",
        actions=[
            {
                "type": "read",
                "description": "Read file",
                "resources": {"file": "/test.txt"},
                "dependencies": [],
            }
        ],
    )
    
    plan_dict = service.to_dict(plan)
    
    assert isinstance(plan_dict, dict)
    assert "plan_id" in plan_dict
    assert "nodes" in plan_dict
    assert isinstance(plan_dict["nodes"], list)
    assert len(plan_dict["nodes"]) == 1
    assert "risk_level" in plan_dict["nodes"][0]


# ============================================================================
# Test: Consent Service
# ============================================================================

def test_consent_service_record():
    """Test recording consent decisions"""
    service = ConsentService("data/test_consent.jsonl")
    
    record = service.record_consent(
        plan_id="plan_001",
        action_id="plan_001_action_1",
        decision=ConsentDecision.APPROVED,
        reason="Necessary for deployment",
        user="operator",
        expires_in_hours=24,
    )
    
    assert record.plan_id == "plan_001"
    assert record.action_id == "plan_001_action_1"
    assert record.decision == ConsentDecision.APPROVED
    assert record.reason == "Necessary for deployment"
    assert record.user == "operator"
    assert record.expires_at is not None


def test_consent_service_check():
    """Test checking consent"""
    service = ConsentService("data/test_consent_check.jsonl")
    
    # Record approval
    service.record_consent(
        plan_id="plan_002",
        action_id="plan_002_action_1",
        decision=ConsentDecision.APPROVED,
        reason="Test",
        user="operator",
    )
    
    # Check consent
    has_consent, reason = service.check_consent("plan_002", "plan_002_action_1")
    assert has_consent is True
    assert reason is None
    
    # Check non-existent consent
    has_consent, reason = service.check_consent("plan_999", "plan_999_action_1")
    assert has_consent is False
    assert "No consent record found" in reason


def test_consent_service_denied():
    """Test denied consent"""
    service = ConsentService("data/test_consent_denied.jsonl")
    
    # Record denial
    service.record_consent(
        plan_id="plan_003",
        action_id="plan_003_action_1",
        decision=ConsentDecision.DENIED,
        reason="Too risky",
        user="operator",
    )
    
    # Check consent
    has_consent, reason = service.check_consent("plan_003", "plan_003_action_1")
    assert has_consent is False
    assert "Denied" in reason
    assert "Too risky" in reason


def test_consent_service_history():
    """Test consent history retrieval"""
    service = ConsentService("data/test_consent_history.jsonl")
    
    # Record multiple consents
    for i in range(5):
        service.record_consent(
            plan_id=f"plan_{i:03d}",
            action_id=f"plan_{i:03d}_action_1",
            decision=ConsentDecision.APPROVED,
            reason=f"Test {i}",
            user="operator",
        )
    
    # Get all history
    history = service.get_consent_history(limit=100)
    assert len(history) >= 5
    
    # Get filtered history
    history_filtered = service.get_consent_history(plan_id="plan_002", limit=100)
    assert all(r.plan_id == "plan_002" for r in history_filtered)


# ============================================================================
# Test: Console API Endpoints (requires FastAPI client)
# ============================================================================

def test_console_health():
    """Test console health endpoint"""
    # This is a placeholder - requires FastAPI test client integration
    # Will be implemented in next phase with full server integration
    pass


def test_plan_preview_endpoint():
    """Test /console/plan/preview endpoint"""
    # This is a placeholder - requires FastAPI test client integration
    pass


def test_consent_endpoint():
    """Test /console/consent endpoint"""
    # This is a placeholder - requires FastAPI test client integration
    pass


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("OPERATOR CONSOLE TEST SUITE (Week-3 Days 21-24)")
    print("="*80)
    print()
    
    # Run tests manually (for environments without pytest)
    tests = [
        ("Plan Preview: Create", test_plan_preview_service_create),
        ("Plan Preview: Risk Calculation", test_plan_preview_risk_calculation),
        ("Plan Preview: Serialization", test_plan_preview_to_dict),
        ("Consent: Record", test_consent_service_record),
        ("Consent: Check", test_consent_service_check),
        ("Consent: Denied", test_consent_service_denied),
        ("Consent: History", test_consent_service_history),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"✅ {name}")
            passed += 1
        except Exception as e:
            print(f"❌ {name}: {e}")
            failed += 1
    
    print()
    print(f"Results: {passed}/{len(tests)} PASSED ({100*passed//len(tests)}%)")
    
    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {failed} tests failed")
