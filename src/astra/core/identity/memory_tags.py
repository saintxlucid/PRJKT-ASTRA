"""
ASTRA Memory Tags
=================

Role-aware memory event stamping.

Author: ASTRA Core Team
Created: 2025-11-03
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .role_context import get_current_role


@dataclass
class MemoryEvent:
    """Role-tagged memory event."""

    timestamp: datetime = field(default_factory=datetime.utcnow)
    role: str = field(default_factory=get_current_role)
    kind: str = "generic"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize event to dict.

        Returns:
            Dict representation

        Examples:
            >>> event = MemoryEvent(kind="chat", payload={"text": "Hello"})
            >>> event.to_dict()
            {'timestamp': '2025-11-03T12:34:56', 'role': 'ASTRA', 'kind': 'chat', 'payload': {...}}
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "role": self.role,
            "kind": self.kind,
            "payload": self.payload,
        }


def tag_memory(kind: str, payload: dict[str, Any]) -> MemoryEvent:
    """
    Create memory event with current role.

    Args:
        kind: Event type
        payload: Event data

    Returns:
        Tagged memory event

    Examples:
        >>> event = tag_memory("chat", {"text": "Hello"})
        >>> event.role
        'ASTRA'
    """
    return MemoryEvent(kind=kind, payload=payload)


__all__ = ["MemoryEvent", "tag_memory"]
