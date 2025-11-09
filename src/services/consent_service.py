"""
Consent Management Service - Track user consent decisions for action plans.

Part of Week-3 Days 21-24: Operator Console MVP

Features:
  - Record consent decisions (approve/deny with reason)
  - Persist consent history (audit trail)
  - Check if action requires consent
  - Automatic expiration of consent (time-based)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import json
from pathlib import Path


class ConsentDecision(str, Enum):
    """User consent decisions"""
    APPROVED = "approved"
    DENIED = "denied"
    DEFERRED = "deferred"  # User wants to review later


@dataclass
class ConsentRecord:
    """Record of a consent decision"""
    plan_id: str
    action_id: str
    decision: ConsentDecision
    reason: str
    timestamp: str
    expires_at: Optional[str]
    user: str


class ConsentService:
    """
    Manage user consent for action plans.
    
    This service records consent decisions and enforces consent requirements
    before executing actions.
    """
    
    def __init__(self, storage_path: str = "data/consent_history.jsonl"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.consent_cache: dict[str, ConsentRecord] = {}
        self._load_history()
    
    def request_consent(
        self,
        plan_id: str,
        action_id: str,
        action_description: str,
        risk_level: str,
        user: str = "operator",
    ) -> dict:
        """
        Request consent for an action.
        
        Returns:
            Dict with keys: plan_id, action_id, description, risk_level, requires_consent
        """
        return {
            "plan_id": plan_id,
            "action_id": action_id,
            "description": action_description,
            "risk_level": risk_level,
            "requires_consent": risk_level in ["high", "critical"],
            "message": f"Action requires consent: {action_description}",
        }
    
    def record_consent(
        self,
        plan_id: str,
        action_id: str,
        decision: ConsentDecision,
        reason: str,
        user: str = "operator",
        expires_in_hours: Optional[int] = None,
    ) -> ConsentRecord:
        """
        Record a consent decision.
        
        Args:
            plan_id: Plan identifier
            action_id: Action identifier
            decision: Approve/deny/defer
            reason: User's reason for decision
            user: Username who made decision
            expires_in_hours: Optional expiration time for consent
        
        Returns:
            ConsentRecord
        """
        timestamp = datetime.utcnow()
        expires_at = None
        if expires_in_hours:
            expires_at = (timestamp + timedelta(hours=expires_in_hours)).isoformat() + "Z"
        
        record = ConsentRecord(
            plan_id=plan_id,
            action_id=action_id,
            decision=decision,
            reason=reason,
            timestamp=timestamp.isoformat() + "Z",
            expires_at=expires_at,
            user=user,
        )
        
        # Cache the record
        cache_key = f"{plan_id}:{action_id}"
        self.consent_cache[cache_key] = record
        
        # Persist to disk
        self._append_to_history(record)
        
        return record
    
    def check_consent(self, plan_id: str, action_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if an action has been consented to.
        
        Returns:
            Tuple of (has_consent, reason_if_denied)
        """
        cache_key = f"{plan_id}:{action_id}"
        record = self.consent_cache.get(cache_key)
        
        if not record:
            return (False, "No consent record found")
        
        # Check if consent expired
        if record.expires_at:
            expires = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00"))
            if datetime.now(expires.tzinfo) > expires:
                return (False, "Consent expired")
        
        # Check decision
        if record.decision == ConsentDecision.APPROVED:
            return (True, None)
        elif record.decision == ConsentDecision.DENIED:
            return (False, f"Denied: {record.reason}")
        else:  # DEFERRED
            return (False, "Decision deferred by user")
    
    def get_consent_history(
        self,
        plan_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[ConsentRecord]:
        """
        Get consent history, optionally filtered by plan_id.
        
        Args:
            plan_id: Optional plan_id filter
            limit: Max number of records to return
        
        Returns:
            List of ConsentRecord
        """
        records = list(self.consent_cache.values())
        
        if plan_id:
            records = [r for r in records if r.plan_id == plan_id]
        
        # Sort by timestamp descending
        records.sort(key=lambda r: r.timestamp, reverse=True)
        
        return records[:limit]
    
    def _load_history(self) -> None:
        """Load consent history from disk"""
        if not self.storage_path.exists():
            return
        
        with open(self.storage_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                
                data = json.loads(line)
                record = ConsentRecord(
                    plan_id=data["plan_id"],
                    action_id=data["action_id"],
                    decision=ConsentDecision(data["decision"]),
                    reason=data["reason"],
                    timestamp=data["timestamp"],
                    expires_at=data.get("expires_at"),
                    user=data["user"],
                )
                
                cache_key = f"{record.plan_id}:{record.action_id}"
                self.consent_cache[cache_key] = record
    
    def _append_to_history(self, record: ConsentRecord) -> None:
        """Append a consent record to disk"""
        data = {
            "plan_id": record.plan_id,
            "action_id": record.action_id,
            "decision": record.decision.value,
            "reason": record.reason,
            "timestamp": record.timestamp,
            "expires_at": record.expires_at,
            "user": record.user,
        }
        
        with open(self.storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")


# Example usage
if __name__ == "__main__":
    service = ConsentService("data/consent_test.jsonl")
    
    # Request consent
    request = service.request_consent(
        plan_id="plan_001",
        action_id="plan_001_action_2",
        action_description="Restart nginx service",
        risk_level="high",
    )
    print(f"Consent Request: {request}")
    
    # Record approval
    record = service.record_consent(
        plan_id="plan_001",
        action_id="plan_001_action_2",
        decision=ConsentDecision.APPROVED,
        reason="Necessary for config update to take effect",
        user="operator",
        expires_in_hours=24,
    )
    print(f"\nConsent Recorded: {record.decision.value}")
    
    # Check consent
    has_consent, reason = service.check_consent("plan_001", "plan_001_action_2")
    print(f"Has Consent: {has_consent} ({reason or 'Approved'})")
    
    # Get history
    history = service.get_consent_history(plan_id="plan_001")
    print(f"\nConsent History ({len(history)} records)")
