"""
Event Sourcing - Tamper-Evident Chain
======================================

Hash-chained event log for auditing "why did ASTRA do X?"

Design:
- Each event includes SHA256 of previous event (blockchain-style)
- Any tampering breaks the chain
- Full replay reconstructs session state
- Events include identity snapshot (values, policies at that moment)

Author: ASTRA Core Team
Created: 2025-11-01 (Week-2 Refactor)
"""

import json
import uuid
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any


@dataclass
class Event:
    """
    Immutable event record with hash chain.
    
    Attributes:
        id: Unique event identifier (UUID)
        ts: ISO8601 timestamp with timezone
        typ: Event type (e.g., "plan_approved", "tool_executed")
        payload: Event-specific data
        identity: Identity state snapshot (values, policies)
        prev_hash: SHA256 of previous event
        hash: SHA256 of this event (includes prev_hash)
    """
    id: str
    ts: str
    typ: str
    payload: dict[str, Any]
    identity: dict[str, Any]
    prev_hash: str
    hash: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)


def chain_hash(prev_hash: str, body: dict[str, Any]) -> str:
    """
    Compute SHA256 hash linking to previous event.
    
    Args:
        prev_hash: Hash of previous event ("GENESIS" for first event)
        body: Event data (id, ts, typ, payload, identity)
        
    Returns:
        Hex-encoded SHA256 hash
        
    Security:
        - Editing ANY past event breaks the chain
        - Inserting events impossible (would need to rehash all subsequent)
    """
    data = json.dumps(
        {"prev": prev_hash, "body": body}, 
        sort_keys=True, 
        ensure_ascii=False
    ).encode("utf-8")
    return sha256(data).hexdigest()


def new_event(
    typ: str, 
    payload: dict[str, Any], 
    identity: dict[str, Any], 
    prev_hash: str
) -> Event:
    """
    Create new event with hash chain.
    
    Args:
        typ: Event type
        payload: Event data
        identity: Current identity snapshot
        prev_hash: Hash of previous event
        
    Returns:
        Immutable Event object
    """
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(UTC).isoformat()
    
    body = {
        "id": event_id,
        "ts": timestamp,
        "typ": typ,
        "payload": payload,
        "identity": identity
    }
    
    event_hash = chain_hash(prev_hash, body)
    
    return Event(
        id=event_id,
        ts=timestamp,
        typ=typ,
        payload=payload,
        identity=identity,
        prev_hash=prev_hash,
        hash=event_hash
    )


def verify_chain(events: list[Event]) -> tuple[bool, list[str]]:
    """
    Verify hash chain integrity.
    
    Args:
        events: List of events in chronological order
        
    Returns:
        (is_valid, errors)
        - is_valid: True if chain unbroken
        - errors: List of error messages
    """
    if not events:
        return True, []
    
    errors = []
    
    # First event must link to GENESIS
    if events[0].prev_hash != "GENESIS":
        errors.append(f"Event 0: expected prev_hash=GENESIS, got {events[0].prev_hash}")
    
    # Verify each event's hash
    for i, ev in enumerate(events):
        body = {
            "id": ev.id,
            "ts": ev.ts,
            "typ": ev.typ,
            "payload": ev.payload,
            "identity": ev.identity
        }
        expected_hash = chain_hash(ev.prev_hash, body)
        if ev.hash != expected_hash:
            errors.append(
                f"Event {i} ({ev.id}): hash mismatch. "
                f"Expected {expected_hash[:8]}..., got {ev.hash[:8]}..."
            )
    
    # Verify chain linkage
    for i in range(1, len(events)):
        if events[i].prev_hash != events[i-1].hash:
            errors.append(
                f"Event {i} ({events[i].id}): broken chain. "
                f"prev_hash={events[i].prev_hash[:8]}..., "
                f"but previous event hash={events[i-1].hash[:8]}..."
            )
    
    return len(errors) == 0, errors


# Common event types (extend as needed)
EVENT_TYPES = {
    "plan_created": "Planner generated execution plan",
    "plan_approved": "User approved plan (with consent scope)",
    "plan_rejected": "User rejected plan",
    "tool_executed": "Tool executed in sandbox",
    "memory_added": "Memory record added",
    "memory_quarantined": "Memory signature verification failed",
    "identity_updated": "Identity values or policies changed",
    "model_loaded": "AI model loaded (with checksum verification)",
    "session_started": "ASTRA session initiated",
    "session_ended": "ASTRA session terminated"
}
