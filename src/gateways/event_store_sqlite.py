"""
SQLite Event Store - Append-Only Gateway
=========================================

Implements EventStore interface with tamper-evident hash chain.

Design:
- Single-table schema (id, ts, typ, payload, identity, prev_hash, hash)
- Thread-safe via connection per instance
- Auto-creates database if missing
- Replay from any event ID

Author: ASTRA Core Team
Created: 2025-11-01 (Week-2 Refactor)
"""

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from domain.events import Event, new_event


class SQLiteEventStore:
    """
    Append-only event log with SHA256 hash chain.

    Thread Safety:
        Each instance gets its own connection (check_same_thread=False for FastAPI).
        For multi-process, use WAL mode (set on init).

    Example:
        >>> store = SQLiteEventStore()
        >>> event_id = store.append("plan_approved", {"plan": "..."}, {"warmth": 0.7})
        >>> for ev in store.replay():
        ...     print(ev.typ, ev.ts)
    """

    def __init__(self, db_path: str = "data/eventlog.sqlite"):
        """
        Initialize event store.

        Args:
            db_path: Path to SQLite database (created if missing)
        """
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path, check_same_thread=False)

        # Enable WAL mode for concurrent reads
        self.db.execute("PRAGMA journal_mode=WAL")

        # Create table if missing
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                ts TEXT NOT NULL,
                typ TEXT NOT NULL,
                payload TEXT NOT NULL,
                identity TEXT NOT NULL,
                prev_hash TEXT NOT NULL,
                hash TEXT NOT NULL,
                UNIQUE(hash)
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_events_typ ON events(typ)")
        self.db.commit()

    def _last_hash(self) -> str:
        """
        Get hash of most recent event.

        Returns:
            Last event hash, or "GENESIS" if no events
        """
        row = self.db.execute(
            "SELECT hash FROM events ORDER BY ROWID DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else "GENESIS"

    def append(
        self,
        typ: str,
        payload: dict[str, Any],
        identity_snapshot: dict[str, Any]
    ) -> str:
        """
        Append event to tamper-evident log.

        Args:
            typ: Event type (e.g., "plan_approved")
            payload: Event-specific data
            identity_snapshot: Current identity state

        Returns:
            Event ID (UUID)

        Thread Safety:
            Atomic via SQLite transaction
        """
        ev = new_event(typ, payload, identity_snapshot, self._last_hash())

        self.db.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                ev.id,
                ev.ts,
                ev.typ,
                json.dumps(ev.payload, sort_keys=True, ensure_ascii=False),
                json.dumps(ev.identity, sort_keys=True, ensure_ascii=False),
                ev.prev_hash,
                ev.hash
            )
        )
        self.db.commit()
        return ev.id

    def replay(self, from_id: str | None = None) -> Iterable[Event]:
        """
        Replay events from log.

        Args:
            from_id: Start from this event ID (None = full replay)

        Yields:
            Event objects in chronological order

        Example:
            >>> for ev in store.replay():
            ...     if ev.typ == "tool_executed":
            ...         print(f"Tool: {ev.payload['tool']}")
        """
        query = "SELECT id, ts, typ, payload, identity, prev_hash, hash FROM events"
        params = ()

        if from_id:
            query += " WHERE ROWID >= (SELECT ROWID FROM events WHERE id=?)"
            params = (from_id,)

        query += " ORDER BY ROWID ASC"

        cursor = self.db.execute(query, params)
        for (id_, ts, typ, payload_json, identity_json, prev_hash, hash_) in cursor:
            yield Event(
                id=id_,
                ts=ts,
                typ=typ,
                payload=json.loads(payload_json),
                identity=json.loads(identity_json),
                prev_hash=prev_hash,
                hash=hash_
            )

    def count(self) -> int:
        """Return total event count."""
        return self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def get_by_type(self, typ: str) -> Iterable[Event]:
        """Get all events of a specific type."""
        cursor = self.db.execute(
            "SELECT id, ts, typ, payload, identity, prev_hash, hash "
            "FROM events WHERE typ=? ORDER BY ROWID ASC",
            (typ,)
        )
        for (id_, ts, typ, payload_json, identity_json, prev_hash, hash_) in cursor:
            yield Event(
                id=id_,
                ts=ts,
                typ=typ,
                payload=json.loads(payload_json),
                identity=json.loads(identity_json),
                prev_hash=prev_hash,
                hash=hash_
            )

    def close(self):
        """Close database connection."""
        self.db.close()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, *args):
        """Context manager cleanup."""
        self.close()
