"""
Week-2 Acceptance Test: Identity Policies
==========================================

Validates policy compilation and enforcement:
- DSL compilation (YAML → executable rules)
- PlanVerifier approval/denial
- Condition matching (path_contains, action_is, context_has)
- Multiple policy scenarios

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Integration)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from domain.policies_dsl import compile_rule, PlanVerifier


def test_compile_simple_rule():
    """Simple rule should compile to callable."""
    rule_def = {
        "when": "action_is:read_file",
        "require": "path_contains:/workspace/",
        "deny_if": "path_contains:/secrets/"
    }
    
    rule_fn = compile_rule(rule_def)
    assert callable(rule_fn)
    
    # Should approve workspace file
    approved, errors = rule_fn(
        {"action": "read_file", "path": "/workspace/code.py"},
        {}
    )
    assert approved is True
    
    # Should deny secrets file
    approved, errors = rule_fn(
        {"action": "read_file", "path": "/workspace/secrets/api_key.txt"},
        {}
    )
    assert approved is False
    assert any("path_contains:/secrets/" in err for err in errors)


def test_plan_verifier_empty_policies():
    """PlanVerifier with no policies should approve (permissive)."""
    verifier = PlanVerifier([])
    
    approved, errors = verifier.check(
        {"action": "delete_database", "confirmation": False},
        {}
    )
    
    # Permissive mode: no policies = allow
    assert approved is True
    assert len(errors) == 0


def test_plan_verifier_denial():
    """PlanVerifier should deny when policy rejects."""
    rule_def = {
        "when": "action_is:delete_database",
        "require": "context_has:confirmation=true"
    }
    
    verifier = PlanVerifier([compile_rule(rule_def)])
    
    # Missing confirmation
    approved, errors = verifier.check(
        {"action": "delete_database"},
        {}
    )
    
    assert approved is False
    assert any("confirmation=true" in err for err in errors)


def test_plan_verifier_approval():
    """PlanVerifier should approve when all policies pass."""
    rule_def = {
        "when": "action_is:read_file",
        "require": "path_contains:/workspace/"
    }
    
    verifier = PlanVerifier([compile_rule(rule_def)])
    
    approved, errors = verifier.check(
        {"action": "read_file", "path": "/workspace/safe.txt"},
        {}
    )
    
    assert approved is True
    assert len(errors) == 0


def test_multiple_policies():
    """PlanVerifier should check all policies (AND logic)."""
    rule1 = compile_rule({
        "when": "action_is:write_file",
        "deny_if": "path_contains:/system/"
    })
    
    rule2 = compile_rule({
        "when": "action_is:write_file",
        "require": "path_contains:/workspace/"
    })
    
    verifier = PlanVerifier([rule1, rule2])
    
    # Valid path
    approved, errors = verifier.check(
        {"action": "write_file", "path": "/workspace/output.txt"},
        {}
    )
    assert approved is True
    
    # Violates rule1 (system path)
    approved, errors = verifier.check(
        {"action": "write_file", "path": "/system/config.txt"},
        {}
    )
    assert approved is False
    
    # Violates rule2 (not in workspace)
    approved, errors = verifier.check(
        {"action": "write_file", "path": "/tmp/temp.txt"},
        {}
    )
    assert approved is False


def test_action_is_condition():
    """action_is condition should match action field."""
    rule_def = {
        "when": "action_is:read_file"
    }
    
    rule_fn = compile_rule(rule_def)
    
    # Matching action
    approved, errors = rule_fn({"action": "read_file"}, {})
    assert approved is True
    
    # Non-matching action
    approved, errors = rule_fn({"action": "write_file"}, {})
    assert approved is True  # No deny_if, so approve


def test_path_contains_condition():
    """path_contains should check substring."""
    rule_def = {
        "when": "action_is:read_file",
        "require": "path_contains:.env"
    }
    
    rule_fn = compile_rule(rule_def)
    
    # Contains .env
    approved, errors = rule_fn(
        {"action": "read_file", "path": "/workspace/.env"},
        {}
    )
    assert approved is True
    
    # Doesn't contain .env
    approved, errors = rule_fn(
        {"action": "read_file", "path": "/workspace/code.py"},
        {}
    )
    assert approved is False


def test_context_has_condition():
    """context_has should check key=value."""
    rule_def = {
        "when": "action_is:deploy",
        "require": "context_has:environment=production"
    }
    
    rule_fn = compile_rule(rule_def)
    
    # Correct environment
    approved, errors = rule_fn(
        {"action": "deploy", "environment": "production"},
        {}
    )
    assert approved is True
    
    # Wrong environment
    approved, errors = rule_fn(
        {"action": "deploy", "environment": "staging"},
        {}
    )
    assert approved is False


if __name__ == "__main__":
    """Run tests standalone."""
    print("Running identity policy tests...\n")
    
    tests = [
        ("Compile simple rule", test_compile_simple_rule),
        ("Empty policies (permissive)", test_plan_verifier_empty_policies),
        ("Policy denial", test_plan_verifier_denial),
        ("Policy approval", test_plan_verifier_approval),
        ("Multiple policies", test_multiple_policies),
        ("action_is condition", test_action_is_condition),
        ("path_contains condition", test_path_contains_condition),
        ("context_has condition", test_context_has_condition),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            test_func()
            print(f"✅ {name}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")
    
    sys.exit(0 if failed == 0 else 1)
