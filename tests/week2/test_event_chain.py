"""
Week-2 Acceptance Test: Event Chain Integrity
==============================================

Validates tamper-evident hash chain properties:
- Chain creation with proper hash linking
- Tampering detection (hash mismatch)
- Replay validation
- Multi-event chains

Author: ASTRA Core Team
Created: 2025-11-02 (Week-2 Integration)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from domain.events import new_event, verify_chain
from gateways.event_store_sqlite import SQLiteEventStore


def test_single_event_chain():
    """Single event should have genesis hash."""
    store = SQLiteEventStore(":memory:")
    
    event_id = store.append(
        "session_started",
        {"test": True},
        {"warmth": 0.7}
    )
    
    events = list(store.replay())
    assert len(events) == 1
    assert events[0].typ == "session_started"
    assert events[0].prev_hash == "GENESIS"  # Uppercase per events.py
    assert len(events[0].hash) == 64  # SHA256 hex = 64 chars


def test_multi_event_chain():
    """Multiple events should link properly."""
    store = SQLiteEventStore(":memory:")
    
    id1 = store.append("session_started", {}, {})
    id2 = store.append("plan_approved", {"plan": "test"}, {})
    id3 = store.append("tool_executed", {"tool": "read_file"}, {})
    
    events = list(store.replay())
    assert len(events) == 3
    
    # Verify chain linkage
    assert events[0].prev_hash == "GENESIS"  # Uppercase per events.py
    assert events[1].prev_hash == events[0].hash
    assert events[2].prev_hash == events[1].hash


def test_chain_integrity_validation():
    """verify_chain should detect tampering."""
    store = SQLiteEventStore(":memory:")
    
    store.append("session_started", {}, {})
    store.append("plan_approved", {"plan": "original"}, {})
    
    events = list(store.replay())
    
    # Original chain valid
    is_valid, error = verify_chain(events)
    assert is_valid is True
    assert error is None
    
    # Tamper with middle event (convert Event dataclass to dict for tampering test)
    events_as_dicts = [
        {
            "id": ev.id,
            "ts": ev.ts,
            "typ": ev.typ,
            "payload": ev.payload,  # Note: Event uses 'payload' not 'data'
            "identity": ev.identity,
            "prev_hash": ev.prev_hash,
            "hash": ev.hash
        }
        for ev in events
    ]
    events_as_dicts[1]["payload"] = {"plan": "tampered"}
    
    # Chain now invalid (need to convert back to Event dataclass)
    from domain.events import Event
    tampered_events = [Event(**d) for d in events_as_dicts]
    is_valid, error = verify_chain(tampered_events)
    assert is_valid is False
    assert len(error) > 0  # error is list[str]


def test_event_store_count():
    """Event count should be accurate."""
    store = SQLiteEventStore(":memory:")
    
    assert store.count() == 0
    
    store.append("session_started", {}, {})
    assert store.count() == 1
    
    store.append("plan_approved", {}, {})
    assert store.count() == 2


def test_get_by_type():
    """Filter events by type."""
    store = SQLiteEventStore(":memory:")
    
    store.append("session_started", {}, {})
    store.append("plan_approved", {"plan": "A"}, {})
    store.append("tool_executed", {"tool": "X"}, {})
    store.append("plan_approved", {"plan": "B"}, {})
    
    plans = list(store.get_by_type("plan_approved"))
    assert len(plans) == 2
    assert plans[0].payload["plan"] == "A"
    assert plans[1].payload["plan"] == "B"


if __name__ == "__main__":
    """Run tests standalone."""
    print("Running event chain tests...\n")
    
    tests = [
        ("Single event chain", test_single_event_chain),
        ("Multi-event chain", test_multi_event_chain),
        ("Chain integrity validation", test_chain_integrity_validation),
        ("Event store count", test_event_store_count),
        ("Filter by type", test_get_by_type),
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
