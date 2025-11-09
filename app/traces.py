"""
ASTRA Trace Logger
==================

Thread-safe event trace buffer.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class TraceEvent:
    """Trace event."""

    ts: str
    kind: str
    payload: dict[str, Any]


class Tracer:
    """Thread-safe trace event logger."""

    def __init__(self, cap: int = 256):
        self._cap = cap
        self._buf: list[TraceEvent] = []
        self._lock = threading.Lock()

    def log(self, kind: str, payload: dict[str, Any]) -> None:
        """Log a trace event."""
        evt = TraceEvent(
            ts=datetime.utcnow().isoformat() + "Z",
            kind=kind,
            payload=payload
        )
        with self._lock:
            self._buf.append(evt)
            if len(self._buf) > self._cap:
                self._buf.pop(0)

    def tail(self) -> dict[str, Any]:
        """Get last 100 events."""
        with self._lock:
            return {
                "count": len(self._buf),
                "events": [{"ts": e.ts, "kind": e.kind, "payload": e.payload} for e in self._buf[-100:]]
            }


__all__ = ["Tracer", "TraceEvent"]
