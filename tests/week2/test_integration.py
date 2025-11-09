"""
Week-2 Acceptance Test: End-to-End Integration
===============================================

Validates full boot → operation → shutdown cycle:
- Boot sequence completes
- Event logging works
- Policy enforcement active
- All components wired correctly

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Integration)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from boot import boot_astra, shutdown_astra, BootError


def test_boot_sequence():
    """Boot should complete without errors."""
    try:
        deps = boot_astra()
        
        # Check all dependencies initialized
        assert deps.event_store is not None
        assert deps.plan_verifier is not None
        assert deps.action_executor is not None
        assert deps.identity_snapshot is not None
        assert deps.boot_event_id is not None
        
        # Clean shutdown
        shutdown_astra(deps)
        
    except BootError as e:
        raise AssertionError(f"Boot failed: {e}")


def test_event_logging_during_boot():
    """Boot should log session_started event."""
    deps = boot_astra()
    
    # Check event logged
    assert deps.event_store.count() >= 1
    
    events = list(deps.event_store.get_by_type("session_started"))
    assert len(events) >= 1
    
    # Verify event structure
    event = events[0]
    assert event.typ == "session_started"
    assert hasattr(event, "payload")  # Note: Event uses 'payload' not 'data'
    assert hasattr(event, "identity")
    
    shutdown_astra(deps)


def test_action_executor_integration():
    """Action executor should be functional."""
    deps = boot_astra()
    
    # Execute allowed action
    result = deps.action_executor.run("list_dir", {"path": "."})
    
    # Should return dict
    assert isinstance(result, dict)
    assert "status" in result
    assert "output" in result or "error" in result
    
    shutdown_astra(deps)


def test_plan_verifier_integration():
    """PlanVerifier should be initialized."""
    deps = boot_astra()
    
    # Check plan
    approved, errors = deps.plan_verifier.check(
        {"action": "test", "safe": True},
        {}
    )
    
    assert isinstance(approved, bool)
    assert isinstance(errors, list)
    
    shutdown_astra(deps)


def test_identity_snapshot():
    """Identity snapshot should be captured."""
    deps = boot_astra()
    
    assert isinstance(deps.identity_snapshot, dict)
    # Should have at least policies_count
    assert "policies_count" in deps.identity_snapshot
    
    shutdown_astra(deps)


def test_event_store_persistence():
    """Event store should persist across boots."""
    # First boot
    deps1 = boot_astra()
    count1 = deps1.event_store.count()
    shutdown_astra(deps1)
    
    # Second boot (should see previous events)
    deps2 = boot_astra()
    count2 = deps2.event_store.count()
    
    # Should have more events after second boot
    assert count2 > count1
    
    shutdown_astra(deps2)


def test_graceful_shutdown():
    """Shutdown should log session_ended event."""
    deps = boot_astra()
    
    count_before = deps.event_store.count()
    shutdown_astra(deps)
    
    # Open new connection to check
    from gateways.event_store_sqlite import SQLiteEventStore
    store = SQLiteEventStore("data/eventlog.sqlite")
    count_after = store.count()
    
    # Should have logged session_ended
    assert count_after > count_before
    
    ended_events = list(store.get_by_type("session_ended"))
    assert len(ended_events) > 0


if __name__ == "__main__":
    """Run tests standalone."""
    print("Running end-to-end integration tests...\n")
    
    tests = [
        ("Boot sequence", test_boot_sequence),
        ("Event logging during boot", test_event_logging_during_boot),
        ("Action executor integration", test_action_executor_integration),
        ("PlanVerifier integration", test_plan_verifier_integration),
        ("Identity snapshot", test_identity_snapshot),
        ("Event store persistence", test_event_store_persistence),
        ("Graceful shutdown", test_graceful_shutdown),
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
