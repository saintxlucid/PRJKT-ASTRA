"""
ASTRA OS Gate — Token-based privilege verification and audit system.

This module implements the Gate Contract: every privileged operation must pass
through token verification, scope validation, and audit logging before execution.

Phase A Week 1: Userland implementation (ETW + WFP + Minifilter integration)
Phase C+: Kernel-level implementation with capability-based syscall mediation

Architecture:
    Token → Scope Check → Danger Assessment → Operator Consent → Audit Log → ALLOW/DENY
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Scope(str, Enum):
    """Permission scopes for privileged operations."""

    FS = "fs"  # Filesystem operations
    NET = "net"  # Network operations
    PROC = "proc"  # Process management


class Decision(str, Enum):
    """Gate decision outcomes."""

    ALLOW = "ALLOW"  # Operation permitted
    DENY = "DENY"  # Operation denied
    CONSENT_REQUIRED = "CONSENT_REQUIRED"  # Operator approval needed
    EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"  # Emergency bypass active


@dataclass
class Token:
    """
    Cryptographic token authorizing scoped operations.

    Attributes:
        kid: Key ID (for rotation support)
        exp: Expiration timestamp (Unix epoch seconds)
        iat: Issued-at timestamp (Unix epoch seconds)
        sig: Signature (PQC hybrid: Dilithium + ECDSA)
        scopes: Authorized permission scopes
        operator_id: Unique operator identifier
    """

    kid: str
    exp: int
    iat: int
    sig: str
    scopes: list[Scope]
    operator_id: str

    def is_expired(self) -> bool:
        """Check if token has expired."""
        return time.time() > self.exp

    def has_scope(self, scope: Scope) -> bool:
        """Check if token authorizes a specific scope."""
        return scope in self.scopes

    def ttl_remaining(self) -> int:
        """Get remaining time-to-live in seconds."""
        return max(0, self.exp - int(time.time()))


@dataclass
class Action:
    """
    Privileged operation requiring gate verification.

    Attributes:
        scope: Permission scope (fs/net/proc)
        op: Operation name (e.g., "fs.delete", "net.connect")
        args: Operation-specific arguments
        pid: Process ID initiating the action
        timestamp: When action was requested
        context: Additional context (emotional state, workload, etc.)
    """

    scope: Scope
    op: str
    args: dict[str, Any]
    pid: int
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)

    def is_dangerous(self, policy: dict[str, Any]) -> bool:
        """
        Check if operation is flagged as dangerous in policy.

        Args:
            policy: Loaded permissions policy (from permissions.yaml)

        Returns:
            True if operation requires explicit consent
        """
        scope_policy = policy.get("scopes", {}).get(self.scope.value, {})
        danger_ops = scope_policy.get("danger", [])

        # Extract operation type from full op name (e.g., "fs.delete" → "delete")
        op_type = self.op.split(".")[-1]

        return op_type in danger_ops


@dataclass
class AuditEvent:
    """
    Immutable record of a gate decision.

    Stored in SQLite for compliance, rollback, and anomaly detection.
    """

    id: int | None
    timestamp: float
    operator_id: str
    pid: int
    scope: str
    op: str
    args_json: str
    decision: str
    token_kid: str
    context_json: str
    before_hash: str | None = None  # For undo journal
    after_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/metrics."""
        return {
            "timestamp": self.timestamp,
            "operator_id": self.operator_id,
            "pid": self.pid,
            "scope": self.scope,
            "op": self.op,
            "args": json.loads(self.args_json),
            "decision": self.decision,
            "context": json.loads(self.context_json),
        }


class GateVerifier:
    """
    Core gate verification engine.

    Validates tokens, checks scopes, assesses danger, logs audit events,
    and coordinates operator consent for dangerous operations.
    """

    def __init__(self, policy_path: Path, audit_db_path: Path):
        """
        Initialize gate verifier.

        Args:
            policy_path: Path to permissions.yaml
            audit_db_path: Path to SQLite audit database
        """
        self.policy_path = policy_path
        self.audit_db_path = audit_db_path
        self.policy = self._load_policy()
        self._init_audit_db()

        # Emergency override state (operator can bypass temporarily)
        self.emergency_active = False
        self.emergency_expires_at = 0.0

    def _load_policy(self) -> dict[str, Any]:
        """Load permissions policy from YAML."""
        with open(self.policy_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _init_audit_db(self) -> None:
        """Initialize SQLite audit database schema."""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()

        # Audit events table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS gate_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                operator_id TEXT NOT NULL,
                pid INTEGER NOT NULL,
                scope TEXT NOT NULL,
                op TEXT NOT NULL,
                args_json TEXT NOT NULL,
                decision TEXT NOT NULL,
                token_kid TEXT NOT NULL,
                context_json TEXT NOT NULL,
                before_hash TEXT,
                after_hash TEXT
            )
        """
        )

        # Index for fast queries
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gate_events_timestamp 
            ON gate_events(timestamp)
        """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gate_events_operator 
            ON gate_events(operator_id, timestamp)
        """
        )

        # Undo journal table (for reversible operations)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fs_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts DATETIME DEFAULT CURRENT_TIMESTAMP,
                pid INTEGER NOT NULL,
                path TEXT NOT NULL,
                op TEXT NOT NULL,
                before_hash TEXT,
                after_hash TEXT,
                undo_script TEXT NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def verify_token(self, token: Token) -> bool:
        """
        Verify token signature and expiration.

        Phase A Week 1: Stub implementation (accepts dev tokens)
        Phase A Week 2: PQC hybrid verification (Dilithium + ECDSA)

        Args:
            token: Token to verify

        Returns:
            True if token is valid and not expired
        """
        # TODO: Implement PQC hybrid signature verification
        # For now, just check expiration and accept dev tokens
        if token.is_expired():
            return False

        # Accept dev tokens in Phase A Week 1
        if token.kid.startswith("dev_"):
            return True

        # Placeholder: verify signature format
        if not token.sig or len(token.sig) < 64:
            return False

        return True

    def check_scope(self, token: Token, action: Action) -> bool:
        """
        Check if token authorizes the action's scope.

        Args:
            token: Verified token
            action: Requested action

        Returns:
            True if token has required scope
        """
        return token.has_scope(action.scope)

    def assess_danger(self, action: Action) -> bool:
        """
        Assess if action is dangerous and requires consent.

        Args:
            action: Requested action

        Returns:
            True if action requires operator consent
        """
        return action.is_dangerous(self.policy)

    def log_audit_event(
        self,
        token: Token,
        action: Action,
        decision: Decision,
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> int:
        """
        Write immutable audit event to database.

        Args:
            token: Token used for authorization
            action: Action that was gated
            decision: Gate decision (ALLOW/DENY/etc.)
            before_hash: File hash before operation (for undo)
            after_hash: File hash after operation (for undo)

        Returns:
            Event ID from database
        """
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()

        event = AuditEvent(
            id=None,
            timestamp=action.timestamp,
            operator_id=token.operator_id,
            pid=action.pid,
            scope=action.scope.value,
            op=action.op,
            args_json=json.dumps(action.args),
            decision=decision.value,
            token_kid=token.kid,
            context_json=json.dumps(action.context),
            before_hash=before_hash,
            after_hash=after_hash,
        )

        cursor.execute(
            """
            INSERT INTO gate_events (
                timestamp, operator_id, pid, scope, op, 
                args_json, decision, token_kid, context_json,
                before_hash, after_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                event.timestamp,
                event.operator_id,
                event.pid,
                event.scope,
                event.op,
                event.args_json,
                event.decision,
                event.token_kid,
                event.context_json,
                event.before_hash,
                event.after_hash,
            ),
        )

        event_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return event_id or 0

    def verify_and_log(self, token: Token, action: Action) -> Decision:
        """
        Main gate verification flow: verify → scope → danger → log → decide.

        Args:
            token: Authorization token
            action: Requested privileged operation

        Returns:
            Gate decision (ALLOW/DENY/CONSENT_REQUIRED)
        """
        # Emergency override check (operator can bypass temporarily)
        if self.emergency_active and time.time() < self.emergency_expires_at:
            decision = Decision.EMERGENCY_OVERRIDE
            self.log_audit_event(token, action, decision)
            return decision

        # Step 1: Verify token
        if not self.verify_token(token):
            decision = Decision.DENY
            self.log_audit_event(token, action, decision)
            return decision

        # Step 2: Check scope authorization
        if not self.check_scope(token, action):
            decision = Decision.DENY
            self.log_audit_event(token, action, decision)
            return decision

        # Step 3: Assess danger (requires consent?)
        is_dangerous = self.assess_danger(action)

        if is_dangerous:
            decision = Decision.CONSENT_REQUIRED
            self.log_audit_event(token, action, decision)
            return decision

        # Step 4: Allow operation (within scope, not dangerous)
        decision = Decision.ALLOW
        self.log_audit_event(token, action, decision)
        return decision

    def activate_emergency_override(self, duration_min: int = 30) -> bool:
        """
        Activate emergency override (operator bypass).

        Requires 2FA challenge (to be implemented in Phase A Week 2).

        Args:
            duration_min: Override duration in minutes (max 30)

        Returns:
            True if override activated
        """
        max_duration = self.policy.get("emergency", {}).get("max_duration_min", 30)
        duration_min = min(duration_min, max_duration)

        self.emergency_active = True
        self.emergency_expires_at = time.time() + (duration_min * 60)

        # TODO: Implement 2FA challenge (YubiKey or TOTP)

        return True

    def get_recent_events(self, operator_id: str, limit: int = 100) -> list[AuditEvent]:
        """
        Retrieve recent audit events for operator (for anomaly detection).

        Args:
            operator_id: Operator to query
            limit: Maximum events to return

        Returns:
            List of audit events ordered by timestamp descending
        """
        conn = sqlite3.connect(self.audit_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM gate_events 
            WHERE operator_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """,
            (operator_id, limit),
        )

        events = []
        for row in cursor.fetchall():
            events.append(
                AuditEvent(
                    id=row["id"],
                    timestamp=row["timestamp"],
                    operator_id=row["operator_id"],
                    pid=row["pid"],
                    scope=row["scope"],
                    op=row["op"],
                    args_json=row["args_json"],
                    decision=row["decision"],
                    token_kid=row["token_kid"],
                    context_json=row["context_json"],
                    before_hash=row["before_hash"],
                    after_hash=row["after_hash"],
                )
            )

        conn.close()
        return events


# Global gate instance (initialized once)
_gate: GateVerifier | None = None


def get_gate() -> GateVerifier:
    """Get global gate verifier instance (singleton)."""
    global _gate
    if _gate is None:
        policy_path = Path(__file__).parent / "permissions.yaml"
        audit_db_path = Path(__file__).parent / "audit" / "gate_events.db"
        audit_db_path.parent.mkdir(parents=True, exist_ok=True)
        _gate = GateVerifier(policy_path, audit_db_path)
    return _gate
